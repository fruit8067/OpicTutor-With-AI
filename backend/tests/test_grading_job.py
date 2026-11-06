# AI-assisted: 평가 저장 전 리스 검사는 OpenAI Codex의 도움으로 작성했습니다.
# OWNER: grader (contracts.yaml ownership)
from uuid import uuid4
from app.grading import job
from app.grading.validate import validate_output
from app.schemas.internal import EvaluationLLMOutput
from test_grading_validate import snapshot,output
import pytest
from app.llm.chat import LLMOutputError
from app.worker.errors import PermanentJobError


def test_lost_lease_does_not_save_or_fail_new_worker_result(monkeypatch):
    eid,sid,jid=uuid4(),uuid4(),uuid4();calls=[];checks=iter([True,False])
    monkeypatch.setattr(job.db,'mark_evaluation_running',lambda value:True)
    monkeypatch.setattr(job.db,'get_evaluation',lambda value:dict(session_id=sid,selected_answer_ids=[]))
    monkeypatch.setattr(job.db,'get_session',lambda value:dict(scenario_id='default',settings_json={'coverage':{}}))
    monkeypatch.setattr(job.db,'load_exam_snapshot',lambda *args:snapshot())
    result=validate_output(EvaluationLLMOutput.model_validate(output()),snapshot())
    monkeypatch.setattr(job,'evaluate_exam',lambda *args,**kwargs:(result,{}))
    monkeypatch.setattr(job.db,'finish_evaluation',lambda *args,**kwargs:calls.append('finish'))
    monkeypatch.setattr(job.db,'fail_evaluation',lambda *args,**kwargs:calls.append('fail'))
    job.handle(dict(id=jid,target_id=eid,_lease_valid=lambda:next(checks)))
    assert not calls


def test_lost_lease_before_start_does_not_change_evaluation(monkeypatch):
    def must_not_start(*args): raise AssertionError('리스 없는 작업이 시작됨')
    monkeypatch.setattr(job.db,'mark_evaluation_running',must_not_start)
    job.handle(dict(id=uuid4(),target_id=uuid4(),_lease_valid=lambda:False))


@pytest.mark.parametrize('structured',[True,False])
def test_failed_output_records_only_validator_codes_not_arbitrary_exception_text(monkeypatch,structured):
    eid,sid=uuid4(),uuid4();saved=[]
    raw=output();raw['evaluation_scope']['scored_order_nos']=[1]
    with pytest.raises(LLMOutputError) as caught:
        validate_output(EvaluationLLMOutput.model_validate(raw),snapshot())
    failure=caught.value if structured else LLMOutputError('private response body must not be saved')
    monkeypatch.setattr(job.db,'mark_evaluation_running',lambda value:True)
    monkeypatch.setattr(job.db,'get_evaluation',lambda value:dict(session_id=sid,selected_answer_ids=[]))
    monkeypatch.setattr(job.db,'get_session',lambda value:dict(scenario_id='default',settings_json={'coverage':{}}))
    monkeypatch.setattr(job.db,'load_exam_snapshot',lambda *args:snapshot())
    def fail(*args,**kwargs): raise failure
    monkeypatch.setattr(job,'evaluate_exam',fail)
    monkeypatch.setattr(job.db,'fail_evaluation',lambda *args:saved.append(args))
    with pytest.raises(PermanentJobError): job.handle(dict(id=uuid4(),target_id=eid))
    assert saved==[(eid,'LLM_INVALID_OUTPUT',{'validation_errors':['evaluation_scope.scored']} if structured else None)]
