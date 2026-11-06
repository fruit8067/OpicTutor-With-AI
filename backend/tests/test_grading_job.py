# AI-assisted: 평가 저장 전 리스 검사는 OpenAI Codex의 도움으로 작성했습니다.
# OWNER: grader (contracts.yaml ownership)
from uuid import uuid4
from app.grading import job
from app.grading.validate import validate_output
from app.schemas.internal import EvaluationLLMOutput
from test_grading_validate import snapshot,output


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
