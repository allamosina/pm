import asyncio
import json

import httpx2 as httpx
import pytest

from app import openrouter
from app.check_openrouter import check

SECRET = "test-key-never-log"
MESSAGES = [{"role": "user", "content": "2+2"}]


def success(content="4", finish="stop"):
    return {"choices": [{"message": {"content": content}, "finish_reason": finish}]}


@pytest.fixture
def mock_http(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", SECRET)
    original = httpx.AsyncClient
    def install(handler):
        def factory(**kwargs):
            return original(**kwargs, transport=httpx.MockTransport(handler))
        monkeypatch.setattr(openrouter.httpx, "AsyncClient", factory)
    return install


def test_request_and_response(mock_http):
    def handler(request):
        assert str(request.url) == openrouter.URL
        assert request.headers["authorization"] == f"Bearer {SECRET}"
        body = json.loads(request.content)
        assert body["model"] == "openai/gpt-oss-120b"
        assert body["messages"] == MESSAGES
        assert body["stream"] is False
        assert body["provider"] == {"require_parameters": True}
        assert body["max_tokens"] == 2048
        assert request.extensions["timeout"]["connect"] == 10
        assert request.extensions["timeout"]["read"] == 60
        return httpx.Response(200, json=success(" 4\n"))
    mock_http(handler)
    assert asyncio.run(openrouter.complete(MESSAGES)) == "4"


def test_structured_format_forwarded(mock_http):
    format = {"type": "json_schema", "json_schema": {"name": "answer", "strict": True, "schema": {"type": "object"}}}
    def handler(request):
        assert json.loads(request.content)["response_format"] == format
        return httpx.Response(200, json=success('{"answer":4}'))
    mock_http(handler)
    assert json.loads(asyncio.run(openrouter.complete(MESSAGES, response_format=format))) == {"answer": 4}


@pytest.mark.parametrize("key", [None, "", "  "])
def test_missing_key_fails_before_network(monkeypatch, key):
    if key is None:
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    else:
        monkeypatch.setenv("OPENROUTER_API_KEY", key)
    def forbidden(**kwargs):
        pytest.fail("Network must not be called without a key")
    monkeypatch.setattr(openrouter.httpx, "AsyncClient", forbidden)
    with pytest.raises(openrouter.OpenRouterError) as error:
        asyncio.run(openrouter.complete(MESSAGES))
    assert error.value.code == "configuration"


@pytest.mark.parametrize("status,code", [(400,"provider"),(401,"authentication"),(402,"credits"),(403,"forbidden"),(408,"timeout"),(429,"rate_limit"),(500,"provider"),(502,"provider"),(503,"provider"),(504,"timeout")])
def test_http_errors_are_safe(mock_http, status, code, caplog):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(status, text=f"provider body: {SECRET}")
    mock_http(handler)
    with pytest.raises(openrouter.OpenRouterError) as error:
        asyncio.run(openrouter.complete(MESSAGES))
    assert error.value.code == code
    assert SECRET not in str(error.value) + caplog.text
    assert len(calls) == 1


@pytest.mark.parametrize("payload", [{"error": {"code": 429, "message": SECRET}}, {"error": None}])
def test_embedded_error_with_success_status(mock_http, payload):
    mock_http(lambda request: httpx.Response(200, json=payload))
    with pytest.raises(openrouter.OpenRouterError) as error:
        asyncio.run(openrouter.complete(MESSAGES))
    assert error.value.code in {"rate_limit", "provider"}
    assert SECRET not in str(error.value)


@pytest.mark.parametrize("payload", [None, [], {}, {"choices": []}, success(None), success(""), success("   "), success("partial", "length"), success("refused", "content_filter"), {"choices": [None]}])
def test_invalid_or_incomplete_output(mock_http, payload):
    mock_http(lambda request: httpx.Response(200, json=payload))
    with pytest.raises(openrouter.OpenRouterError) as error:
        asyncio.run(openrouter.complete(MESSAGES))
    assert error.value.code == "invalid_response"


def test_non_json(mock_http):
    mock_http(lambda request: httpx.Response(200, text="not JSON"))
    with pytest.raises(openrouter.OpenRouterError, match="invalid response"):
        asyncio.run(openrouter.complete(MESSAGES))


@pytest.mark.parametrize("exception,code", [(httpx.ReadTimeout,"timeout"),(httpx.ConnectError,"network")])
def test_transport_failure(mock_http, exception, code):
    def handler(request):
        raise exception(SECRET, request=request)
    mock_http(handler)
    with pytest.raises(openrouter.OpenRouterError) as error:
        asyncio.run(openrouter.complete(MESSAGES))
    assert error.value.code == code
    assert SECRET not in str(error.value)


def test_total_deadline(mock_http, monkeypatch):
    monkeypatch.setattr(openrouter, "TIMEOUT_SECONDS", 0.01)
    async def handler(request):
        await asyncio.sleep(1)
        return httpx.Response(200, json=success())
    mock_http(handler)
    with pytest.raises(openrouter.OpenRouterError) as error:
        asyncio.run(openrouter.complete(MESSAGES))
    assert error.value.code == "timeout"


def test_live_check_logic_with_mock(mock_http, capsys):
    mock_http(lambda request: httpx.Response(200, json=success()))
    asyncio.run(check())
    assert "2+2 = 4" in capsys.readouterr().out


def test_live_check_rejects_wrong_answer(mock_http):
    mock_http(lambda request: httpx.Response(200, json=success("5")))
    with pytest.raises(openrouter.OpenRouterError) as error:
        asyncio.run(check())
    assert error.value.code == "unexpected_answer"
