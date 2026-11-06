# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성했습니다.
# OWNER: grader (contracts.yaml ownership)
from uuid import UUID
from app import db
from app.worker.errors import PermanentJobError
from app.llm.chat import LLMTransientError,LLMRefusalError,LLMOutputError
from .service import evaluate_exam
from .prompt import exam_context

def live(job):
    cancel=job.get('_cancel')
    if cancel and cancel.is_set(): return False
    lease=job.get('_lease_valid')
    return not lease or lease()

def handle(job: dict) -> None:
    if not live(job): return
    eid=UUID(str(job['target_id']))
    if not db.mark_evaluation_running(eid): return
    try:
        evaluation=db.get_evaluation(eid)
        session=db.get_session(evaluation['session_id'])
        snapshot=db.load_exam_snapshot(evaluation['session_id'],evaluation['selected_answer_ids'])
        with exam_context({'scenario_id':session['scenario_id'],'coverage':session['settings_json'].get('coverage',{})}):
            result,meta=evaluate_exam(snapshot,job_id=job['id'])
        if not live(job): return
        db.finish_evaluation(eid,result=result.model_dump(mode='json'),assessment_status=result.assessment_status,
            base_level=result.base_level,estimated_level=result.estimated_level,im_estimation_status=result.im_estimation_status,
            model=meta['model'],prompt_version=meta['prompt_version'],rubric_version=result.rubric_version,
            im_rubric_version=result.im_rubric_version,corpus_version=meta['corpus_version'],
            retrieved_doc_ids=meta['retrieved_doc_ids'])
    except Exception as exc:
        if not live(job): return
        if isinstance(exc,LLMRefusalError): code='LLM_REFUSED'
        elif isinstance(exc,LLMTransientError): code='LLM_TRANSIENT'
        elif isinstance(exc,LLMOutputError): code='LLM_INVALID_OUTPUT'
        elif isinstance(exc,PermanentJobError) and str(exc) in ('EVAL_INPUT_INVALID','EVAL_INPUT_TOO_LARGE'):
            code=str(exc)
        else: code='EVAL_INTERNAL'
        db.fail_evaluation(eid,code,None)
        raise PermanentJobError(code) from exc
