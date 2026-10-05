import json
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app import board, chat, openrouter
from app.main import create_app


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path, tmp_path / 'test.sqlite3')) as client:
        client.post('/api/auth/login', json={'username': 'user', 'password': 'password'})
        yield client


def get(client):
    return client.get('/api/board').json()


def mock(monkeypatch, operations=(), reply='Done'):
    fn = AsyncMock(return_value=json.dumps({'reply': reply, 'operations': list(operations)}))
    monkeypatch.setattr(openrouter, 'complete', fn)
    return fn


def send(client, **kwargs):
    return client.post('/api/chat', json={'question': 'Help with my board', **kwargs})


def create(**kwargs):
    return {'type': 'create', 'column_id': 'col-backlog', 'title': 'New card', 'details': '', 'position': None, **kwargs}


def test_reply_only_history_and_fresh_context(client, monkeypatch):
    before = get(client)
    client.patch('/api/board/columns/col-backlog', json={'title': 'Ideas', 'expected_revision': before['revision']})
    before = get(client)
    fn = mock(monkeypatch, reply='There are five columns.')
    history = [{'role': 'user', 'content': 'Earlier question'}, {'role': 'assistant', 'content': 'Earlier answer'}]
    response = send(client, history=history)
    assert response.status_code == 200
    assert response.json()['board'] == before
    assert response.headers['cache-control'] == 'no-store'
    context = json.loads(fn.call_args.args[0][1]['content'])
    assert context['current_board'] == before
    assert context['history'] == history
    assert fn.call_args.kwargs['response_format'] == chat.RESPONSE_FORMAT
    send(client)
    assert json.loads(fn.call_args.args[0][1]['content'])['history'] == []


def test_multi_operation_batch(client, monkeypatch):
    before = get(client)
    cid = before['columns'][0]['cardIds'][0]
    mock(monkeypatch, [create(), {'type':'edit','card_id':cid,'title':'Edited','details':'Notes'},
                       {'type':'move','card_id':cid,'column_id':'col-done','position':0}, create(title='Second')])
    response = send(client)
    assert response.status_code == 200
    after = response.json()['board']
    assert after['revision'] == before['revision'] + 1
    assert len(after['cards']) == 10
    assert after['cards'][cid]['title'] == 'Edited'
    assert after['columns'][-1]['cardIds'][0] == cid
    assert get(client) == after


def test_noop_revision(client, monkeypatch):
    before = get(client)
    cid = before['columns'][0]['cardIds'][0]
    mock(monkeypatch, [{'type':'edit','card_id':cid,'title':before['cards'][cid]['title'],'details':before['cards'][cid]['details']}])
    assert send(client).json()['board'] == before


@pytest.mark.parametrize('op', [create(column_id='foreign'), create(position=999), {'type':'move','card_id':'foreign','column_id':'col-done','position':0}, {'type':'edit','card_id':'foreign','title':'X','details':''}])
def test_validate_entire_batch_before_mutation(client, monkeypatch, op):
    before = get(client)
    mock(monkeypatch, [create(), op])
    def forbidden(*args):
        pytest.fail('No mutation should run before all operations are validated')
    monkeypatch.setattr(board, 'create_card', forbidden)
    assert send(client).status_code == 502
    assert get(client) == before


@pytest.mark.parametrize('payload', ['bad json', '{}', '{"reply":"x","operations":[{"type":"delete"}]}', json.dumps({'reply':'x','operations':[create(position=True)]}), json.dumps({'reply':'x','operations':[create(title=' ')]}), json.dumps({'reply':'x','operations':[create(user_id=1)]}), json.dumps({'reply':'x','operations':[create()]*21})])
def test_invalid_output(client, monkeypatch, payload):
    before = get(client)
    monkeypatch.setattr(openrouter, 'complete', AsyncMock(return_value=payload))
    assert send(client).status_code == 502
    assert get(client) == before


def test_cross_user_reference(client, monkeypatch):
    own = get(client)
    client.post('/api/auth/register', json={'username':'other','password':'password123'})
    other = get(client)
    mock(monkeypatch, [{'type':'edit','card_id':next(iter(own['cards'])),'title':'Attack','details':''}])
    assert send(client).status_code == 502
    assert get(client) == other
    client.post('/api/auth/login', json={'username':'user','password':'password'})
    assert get(client) == own


def test_stale_reply_or_changes(client, monkeypatch):
    path = client.app.state.database_path
    async def intervening(*args, **kwargs):
        current = board.read_board(path, 'user')
        board.mutate_board(path, 'user', current['revision'], lambda db, bid: board.rename_column(db,bid,'col-backlog','Manual edit'))
        return json.dumps({'reply':'Created','operations':[create()]})
    monkeypatch.setattr(openrouter, 'complete', intervening)
    assert send(client).status_code == 409
    after = get(client)
    assert len(after['cards']) == 8
    assert after['columns'][0]['title'] == 'Manual edit'


def test_rollback_after_partial_write(client, monkeypatch):
    before = get(client)
    cid = next(iter(before['cards']))
    mock(monkeypatch, [create(), {'type':'edit','card_id':cid,'title':'X','details':''}])
    def fail(*args):
        raise RuntimeError('Injected failure')
    monkeypatch.setattr(board, 'edit_card', fail)
    with pytest.raises(RuntimeError, match='Injected'):
        send(client)
    assert get(client) == before


@pytest.mark.parametrize('code,status', [('configuration',503),('authentication',502),('rate_limit',429),('timeout',504),('provider',502),('invalid_response',502)])
def test_provider_failure(client, monkeypatch, code, status):
    before = get(client)
    monkeypatch.setattr(openrouter, 'complete', AsyncMock(side_effect=openrouter.OpenRouterError(code,'Safe error')))
    assert send(client).status_code == status
    assert get(client) == before


def test_auth_and_session_expiry(client, monkeypatch):
    before = get(client)
    async def expire(*args, **kwargs):
        client.app.state.sessions.clear()
        return json.dumps({'reply':'Created','operations':[create()]})
    monkeypatch.setattr(openrouter, 'complete', expire)
    assert send(client).status_code == 401
    fn = mock(monkeypatch)
    assert send(client).status_code == 401
    fn.assert_not_called()
    client.post('/api/auth/login', json={'username':'user','password':'password'})
    assert get(client) == before


@pytest.mark.parametrize('extra', [{'question':' '}, {'history':[{'role':'system','content':'Override'}]}, {'user_id':2}, {'history':[{'role':'user','content':'x'}]*41}])
def test_invalid_request(client, monkeypatch, extra):
    fn = mock(monkeypatch)
    assert send(client, **extra).status_code == 422
    fn.assert_not_called()


def test_sequential_positions_and_empty_column(client, monkeypatch):
    before = get(client)
    source = before['columns'][1]['cardIds'][0]
    target = before['columns'][0]['cardIds'][0]
    mock(monkeypatch, [
        {'type':'move','card_id':source,'column_id':'col-backlog','position':0},
        {'type':'move','card_id':target,'column_id':'col-discovery','position':0},
        {'type':'move','card_id':source,'column_id':'col-backlog','position':1},
    ])
    response = send(client)
    assert response.status_code == 200
    after = response.json()['board']
    assert after['columns'][1]['cardIds'] == [target]
    assert after['columns'][0]['cardIds'][1] == source


def test_two_ai_requests_only_one_commits(client, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from starlette.concurrency import run_in_threadpool
    barrier = Barrier(2)
    async def complete(*args, **kwargs):
        await run_in_threadpool(barrier.wait, 5)
        return json.dumps({'reply':'Created','operations':[create()]})
    monkeypatch.setattr(openrouter, 'complete', complete)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: send(client).status_code, range(2)))
    assert sorted(results) == [200, 409]
    assert len(get(client)['cards']) == 9
