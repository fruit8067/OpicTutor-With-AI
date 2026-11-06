# AI-assisted: provider 경계 회귀 검증은 OpenAI Codex의 도움으로 작성했습니다.
# OWNER: grader (contracts.yaml ownership)
import json
import httpx
import pytest
from app.llm import chat
from app.grading import service
from app.schemas.internal import EvidenceBundle
from test_grading_validate import snapshot,output


def response(content=None):
    return httpx.Response(200,json={'id':'fixture','object':'chat.completion','created':0,'model':'pickle-fixture',
        'choices':[{'index':0,'message':{'role':'assistant','content':json.dumps(output()) if content is None else content},'finish_reason':'stop'}],
        'usage':{'prompt_tokens':100,'completion_tokens':50,'total_tokens':150}})


@pytest.fixture
def provider(monkeypatch):
    monkeypatch.setenv('LLM_BASE_URL','https://pickle.example.invalid/v1')
    monkeypatch.setenv('LLM_MODEL','pickle-fixture')
    monkeypatch.setenv('LLM_API_KEY','local-fixture-no-network')
    monkeypatch.setattr(service,'build_evidence',lambda *a,**kw:EvidenceBundle(corpus_version='fixture'))
    monkeypatch.setattr(service,'token_count',lambda value:100)
    logs=[];waits=[];clients=[];requests=[]
    monkeypatch.setattr(service.db,'log_ai_request',lambda **kw:logs.append(kw))
    monkeypatch.setattr(service.time,'sleep',lambda seconds:waits.append(seconds))
    real_client=chat.OpenAI
    def install(handler):
        def transport(request):
            requests.append(json.loads(request.content))
            return handler(len(requests))
        def client(**kwargs):
            instance=real_client(**kwargs,http_client=httpx.Client(transport=httpx.MockTransport(transport)))
            clients.append(instance)
            return instance
        monkeypatch.setattr(chat,'OpenAI',client)
        return requests,logs,waits
    yield install
    for client in clients: client.close()


@pytest.mark.parametrize('status',[408,429,502])
def test_http_transient_is_retried_and_each_request_logged(provider,status):
    requests,logs,waits=provider(lambda n:httpx.Response(status,json={'error':{'message':'temporary'}}) if n==1 else response())
    result,meta=service.evaluate_exam(snapshot())
    assert result.estimated_level=='IL' and len(requests)==meta['llm_calls']==len(logs)==2
    assert logs[0]['error_code']=='LLM_TRANSIENT' and logs[1]['status']=='ok' and waits==[2]


def test_json_fallback_counts_both_requests_and_keeps_bodies_out_of_log(provider):
    requests,logs,waits=provider(lambda n:httpx.Response(400,json={'error':{'message':'response_format json_schema unsupported'}}) if n==1 else response())
    _,meta=service.evaluate_exam(snapshot())
    assert len(requests)==meta['llm_calls']==len(logs)==2 and not waits
    assert [r['response_format']['type'] for r in requests]==['json_schema','json_object']
    assert meta['total_input_tokens']==100 and meta['total_output_tokens']==50
    assert all(set(row)=={'job_id','purpose','model','input_tokens','output_tokens','latency_ms','status','error_code'} for row in logs)


def test_fallback_and_invalid_output_share_three_http_request_budget(provider):
    requests,logs,_=provider(lambda n:httpx.Response(400,json={'error':{'message':'response_format json_schema unsupported'}}) if n%2 else response('{'))
    with pytest.raises(chat.LLMOutputError,match='예산 소진'):
        service.evaluate_exam(snapshot())
    assert len(requests)==len(logs)==3
    assert logs[1]['status']=='invalid_output' and logs[1]['error_code']=='LLM_INVALID_OUTPUT'
    assert chat._requests.get() is None
