# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성되었습니다.
# 후속 수정: 건너뛴 문항 표시는 Claude(Anthropic)의 도움으로 작성되었습니다.
# OWNER: session-api (contracts.yaml ownership)
from uuid import UUID
from fastapi import APIRouter,Header
from app import db
from app.errors import AppError
from app.schemas.api import SessionOut,ResultOut,ResultItemOut
from .deps import require_session,session_out

router=APIRouter()

@router.post('/sessions/{session_id}/submit',response_model=SessionOut,status_code=202)
def submit(session_id: UUID,authorization: str | None = Header(default=None)):
    require_session(session_id,authorization)
    db.submit_session(session_id);return session_out(session_id,authorization)

@router.get('/sessions/{session_id}/result',response_model=ResultOut)
def result(session_id: UUID,authorization: str | None = Header(default=None)):
    s=require_session(session_id,authorization)
    if s['status'] not in ('submitted','grading','grading_failed','done'): raise AppError('INVALID_STATE')
    latest=db.get_latest_evaluation(session_id)
    # 재평가 중에도 이전의 성공 결과는 보존한다.
    displayed=db.get_evaluation(s['result_id']) if s.get('result_id') else latest
    rows=db.load_exam_snapshot(session_id,s.get('selected_answer_ids') or [])
    answers=[ResultItemOut(**{k:r[k] for k in ['order_no','question_id','question_type','question_text','is_scored','stt_text','metrics','skipped']}) for r in rows]
    return ResultOut(session_status=s['status'],evaluation_status=latest['status'] if latest else None,
        run_no=latest['run_no'] if latest else None,result=displayed.get('result_json') if displayed else None,
        answers=answers,error_code=latest.get('error_code') if latest else None,
        graded_at=displayed['updated_at'] if displayed and displayed['status']=='done' else None)

@router.post('/sessions/{session_id}/regrade',response_model=SessionOut,status_code=202)
def regrade(session_id: UUID,authorization: str | None = Header(default=None)):
    require_session(session_id,authorization)
    db.create_regrade(session_id);return session_out(session_id,authorization)

@router.post('/sessions/{session_id}/chat',status_code=501)
def chat(session_id: UUID): raise AppError('NOT_IMPLEMENTED')
