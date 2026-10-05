"""Isolated browser-test entry point; never imported by the production application."""
import json

from app import openrouter
from app.main import create_app


async def fake_complete(messages, **kwargs):
    context = json.loads(messages[-1]['content'])
    question = context['question']
    current = context['current_board']
    operations = []
    reply = 'Your board has five columns.'
    if question == 'Create two cards':
        operations = [{'type':'create','column_id':'col-backlog','title':title,'details':'Test notes','position':None} for title in ['AI One','AI Two']]
        reply = 'Created two cards.'
    elif question == 'Edit and move it':
        assert len(context['history']) == 2
        cid = next(cid for cid,c in current['cards'].items() if c['title']=='AI One')
        operations = [{'type':'edit','card_id':cid,'title':'AI Edited','details':'Updated'}, {'type':'move','card_id':cid,'column_id':'col-done','position':0}]
        reply = 'Edited and moved the card.'
    elif question == 'Fail safely':
        raise openrouter.OpenRouterError('provider','AI unavailable. Please retry.')
    return json.dumps({'reply':reply,'operations':operations})


openrouter.complete = fake_complete
app = create_app()
