# AI-assisted: 평가 재시도·검색 누출 방지 테스트는 OpenAI Codex의 도움으로 작성했습니다.
# OWNER: grader (contracts.yaml ownership)
import pytest
from app.grading import service,evidence
from app.schemas.internal import EvidenceBundle,EvaluationLLMOutput
from app.llm.chat import LLMTransientError,LLMRefusalError,LLMOutputError
from app.worker.errors import PermanentJobError
from test_grading_validate import snapshot,output


def setup_service(monkeypatch,failures):
    logs=[];calls=[];waits=[]
    monkeypatch.setattr(service.settings,'LLM_API_KEY','local-test-no-network')
    monkeypatch.setattr(service,'build_evidence',lambda *args,**kwargs:EvidenceBundle(corpus_version='fixture'))
    monkeypatch.setattr(service,'token_count',lambda value:100)
    monkeypatch.setattr(service.db,'log_ai_request',lambda **kwargs:logs.append(kwargs))
    monkeypatch.setattr(service.time,'sleep',lambda seconds:waits.append(seconds))
    def chat(*args,**kwargs):
        calls.append(args[0])
        if failures: raise failures.pop(0)
        return EvaluationLLMOutput.model_validate(output()),dict(model='fixture',input_tokens=10,output_tokens=5,latency_ms=1)
    monkeypatch.setattr(service,'chat_structured',chat)
    return calls,logs,waits


def test_transient_retries_are_bounded_and_logged(monkeypatch):
    calls,logs,waits=setup_service(monkeypatch,[LLMTransientError('temporary'),LLMTransientError('temporary')])
    result,meta=service.evaluate_exam(snapshot())
    assert len(calls)==3 and waits==[2,4]
    assert [log['status'] for log in logs]==['error','error','ok']
    assert meta['llm_calls']==3 and meta['total_input_tokens']==10
    assert all('messages' not in log and 'text' not in log for log in logs)


def test_invalid_output_retries_once_refusal_never(monkeypatch):
    calls,logs,waits=setup_service(monkeypatch,[LLMOutputError('items.role')])
    service.evaluate_exam(snapshot())
    assert len(calls)==2 and 'items.role' in calls[1][-1]['content'] and not waits
    calls,logs,waits=setup_service(monkeypatch,[LLMRefusalError('refused')])
    with pytest.raises(LLMRefusalError): service.evaluate_exam(snapshot())
    assert len(calls)==1 and logs[0]['status']=='refused'


def test_invalid_input_and_hard_limit_make_no_call(monkeypatch):
    calls,logs,waits=setup_service(monkeypatch,[])
    with pytest.raises(PermanentJobError): service.evaluate_exam(snapshot()[:-1])
    assert not calls
    monkeypatch.setattr(service,'token_count',lambda value:60001)
    with pytest.raises(PermanentJobError,match='EVAL_INPUT_TOO_LARGE'): service.evaluate_exam(snapshot())
    assert not calls and not logs


def test_excluded_direct_and_similar_sets_never_leak(monkeypatch):
    rows=snapshot()
    def doc(qid):
        return dict(id=qid+'-IM2-stt',doc_type='answer',level='IM2',contrast_set_id=qid,text='reference',text_style='stt',corpus_version='fixture')
    monkeypatch.setattr(evidence.db,'current_corpus_version',lambda:'fixture')
    monkeypatch.setattr(evidence.db,'get_contrast_set',lambda qid,**kwargs:[doc(qid)])
    monkeypatch.setattr(evidence.db,'get_rag_docs',lambda *args,**kwargs:[])
    monkeypatch.setattr(evidence,'embed_texts',lambda texts:[[1.0]])
    seen=[]
    def search(vector,**kwargs):
        seen.append(kwargs['exclude_contrast_set_ids'])
        # 잘못된 검색 구현이 제외 대조 세트를 돌려줘도 평가 엔진이 다시 거른다.
        return [doc('Q002'),doc('OTHER')]
    monkeypatch.setattr(evidence.db,'search_similar_answers',search)
    monkeypatch.setattr(evidence,'token_count',lambda value:100)
    result=evidence.build_evidence(rows,exclude_contrast_set_ids=['Q002'])
    assert all(d['contrast_set_id']!='Q002' for d in result.docs)
    assert all(d['order_no']!=1 for d in result.docs)
    assert seen==[['Q002']] and 'OTHER-IM2-stt' in result.retrieved_doc_ids
