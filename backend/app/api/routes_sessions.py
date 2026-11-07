# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성되었습니다.
# 후속 수정: 문항 건너뛰기(Q3)는 Claude(Anthropic)의 도움으로 작성되었습니다.
# OWNER: session-api (contracts.yaml ownership)
from uuid import UUID
from fastapi import APIRouter,Header,Response
from app import db,exam,tts
from app.errors import AppError
from app.schemas.api import CreateSessionIn,SessionOut,CurrentQuestionOut,QuestionOut,ReplayOut,SkipOut
from app.exam.scenarios import coverage_for
from .deps import require_session,require_in_progress,session_out,answer_out,host_lines,REPLAY_LIMIT
from .routes_auth import optional_current_user

router=APIRouter()

@router.post('/sessions',response_model=SessionOut,status_code=202)
def create_session(data: CreateSessionIn,response: Response,authorization: str | None = Header(default=None)):
    if not data.mic_check_passed: raise AppError('MIC_CHECK_REQUIRED')
    existing=db.get_session_id_by_request_id(data.client_request_id)
    if existing is not None:
        response.status_code=200
        return session_out(existing)
    user=optional_current_user(authorization)
    questions=exam.build_question_set(data.scenario_id,data.client_request_id)
    sid,created=db.create_session(client_request_id=data.client_request_id,scenario_id=data.scenario_id,
        settings_json={'mic_check_passed':True,'coverage':coverage_for(data.scenario_id,questions)},
        questions=questions,replaces_session_id=data.replaces_session_id,
        user_id=user['id'] if user else None)
    response.status_code=202 if created else 200
    return session_out(sid)

@router.get('/sessions/{session_id}',response_model=SessionOut)
def get_session(session_id: UUID): return session_out(session_id)

@router.post('/sessions/{session_id}/prepare/retry',response_model=SessionOut,status_code=202)
def retry_prepare(session_id: UUID):
    db.retry_prepare(session_id);return session_out(session_id)

@router.post('/sessions/{session_id}/cancel',response_model=SessionOut)
def cancel(session_id: UUID):
    db.cancel_session(session_id);return session_out(session_id)

@router.post('/sessions/{session_id}/start',response_model=SessionOut)
def start(session_id: UUID):
    db.start_session(session_id);return session_out(session_id)

@router.get('/sessions/{session_id}/current',response_model=CurrentQuestionOut)
def current(session_id: UUID):
    s=require_session(session_id);require_in_progress(s)
    all_answered=s['current_order_no']>s['question_count']
    question=None;pending=None
    if not all_answered:
        q=db.get_session_question(session_id,s['current_order_no'])
        if q is None: raise AppError('INTERNAL_ERROR')
        if not q.get('file_path'): raise AppError('SERVICE_NOT_READY')
        question=QuestionOut(order_no=q['order_no'],question_id=q['question_id'],question_type=q['question_type'],
            is_scored=q['is_scored'],text=q['question_text'],audio_url=tts.tts_url(q['file_path']),
            duration_sec=q.get('duration_sec'),replay_count=q['replay_count'],replay_limit=REPLAY_LIMIT)
        a=q.get('latest_answer')
        if a and a['stt_status'] in ('queued','processing','rejected','failed'):
            pending=answer_out({**a,'session_id':session_id,'order_no':q['order_no']},s)
    return CurrentQuestionOut(session_status=s['status'],total=s['question_count'],all_answered=all_answered,
        question=question,pending_answer=pending,host_lines=host_lines(s))

@router.post('/sessions/{session_id}/questions/{order_no}/replay',response_model=ReplayOut)
def replay(session_id: UUID,order_no: int):
    count=db.increment_replay(session_id,order_no,REPLAY_LIMIT)
    return ReplayOut(order_no=order_no,replay_count=count,replay_limit=REPLAY_LIMIT)

@router.post('/sessions/{session_id}/questions/{order_no}/skip',response_model=SkipOut)
def skip(session_id: UUID,order_no: int):
    return SkipOut(**db.skip_question(session_id,order_no))
