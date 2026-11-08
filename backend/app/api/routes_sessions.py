# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성되었습니다.
# 후속 수정: 문항 건너뛰기(Q3)와 v3 활성 세션 조회(/sessions/active)는 Claude(Anthropic)의 도움으로 작성되었습니다.
# OWNER: session-api (contracts.yaml ownership)
from uuid import UUID
from fastapi import APIRouter,Header,Response
from app import db,exam,tts
from app.errors import AppError
from app.schemas.api import (CreateSessionIn,SessionOut,CurrentQuestionOut,QuestionOut,ReplayOut,SkipOut,
    SessionHistorySummaryOut,SessionHistoryItemOut,UserHistoryOut,DeleteSessionOut,ActiveSessionsOut)
from app.exam.scenarios import coverage_for
from .deps import require_session,require_in_progress,session_out,answer_out,host_lines,progress_for,REPLAY_LIMIT
from .routes_auth import optional_current_user,require_current_user

router=APIRouter()

@router.post('/sessions',response_model=SessionOut,status_code=202)
def create_session(data: CreateSessionIn,response: Response,authorization: str | None = Header(default=None)):
    if not data.mic_check_passed: raise AppError('MIC_CHECK_REQUIRED')
    existing=db.get_session_id_by_request_id(data.client_request_id)
    if existing is not None:
        response.status_code=200
        return session_out(existing,authorization)
    user=optional_current_user(authorization)
    questions=exam.build_question_set(data.scenario_id,data.client_request_id)
    sid,created=db.create_session(client_request_id=data.client_request_id,scenario_id=data.scenario_id,
        settings_json={'mic_check_passed':True,'coverage':coverage_for(data.scenario_id,questions)},
        questions=questions,replaces_session_id=data.replaces_session_id,
        user_id=user['id'] if user else None)
    response.status_code=202 if created else 200
    return session_out(sid,authorization)

@router.get('/sessions/history',response_model=UserHistoryOut)
def get_user_history(authorization: str | None = Header(default=None)):
    user=require_current_user(authorization)
    rows=db.list_user_sessions(user['id'])
    items=[SessionHistoryItemOut(**r) for r in rows]
    completed=[it for it in items if it.status=='done']
    in_prog=[it for it in items if it.status in ('preparing','ready','in_progress')]
    latest_done=completed[0] if completed else None
    summary=SessionHistorySummaryOut(
        total_sessions=len(items),
        completed_sessions=len(completed),
        in_progress_sessions=len(in_prog),
        total_speech_sec=round(sum(it.total_speech_sec for it in items),1),
        total_answered_questions=sum(it.answered_count for it in items),
        latest_assessment_status=latest_done.assessment_status if latest_done else None,
        latest_base_level=latest_done.base_level if latest_done else None,
        latest_estimated_level=latest_done.estimated_level if latest_done else None,
        latest_im_estimation_status=latest_done.im_estimation_status if latest_done else None,
        latest_provisional_label=latest_done.provisional_label if latest_done else None,
    )
    return UserHistoryOut(summary=summary,items=items)

# /sessions/{session_id}보다 먼저 등록해야 'active'가 UUID 경로로 해석되지 않는다.
@router.get('/sessions/active',response_model=ActiveSessionsOut)
def get_active_sessions(authorization: str | None = Header(default=None)):
    """헤더 배지·완료 알림용 가벼운 폴링 응답. 로그인 사용자 본인의 세션만 돌려준다."""
    user=require_current_user(authorization)
    return ActiveSessionsOut(**db.list_active_sessions(user['id']))

@router.get('/sessions/{session_id}',response_model=SessionOut)
def get_session(session_id: UUID,authorization: str | None = Header(default=None)):
    return session_out(session_id,authorization)

@router.delete('/sessions/{session_id}',response_model=DeleteSessionOut)
def delete_session(session_id: UUID,authorization: str | None = Header(default=None)):
    user=require_current_user(authorization)
    db.delete_user_session(session_id,user['id'])
    return DeleteSessionOut(ok=True,session_id=session_id)

@router.post('/sessions/{session_id}/prepare/retry',response_model=SessionOut,status_code=202)
def retry_prepare(session_id: UUID,authorization: str | None = Header(default=None)):
    require_session(session_id,authorization)
    db.retry_prepare(session_id);return session_out(session_id,authorization)

@router.post('/sessions/{session_id}/cancel',response_model=SessionOut)
def cancel(session_id: UUID,authorization: str | None = Header(default=None)):
    require_session(session_id,authorization)
    db.cancel_session(session_id);return session_out(session_id,authorization)

@router.post('/sessions/{session_id}/start',response_model=SessionOut)
def start(session_id: UUID,authorization: str | None = Header(default=None)):
    require_session(session_id,authorization)
    db.start_session(session_id);return session_out(session_id,authorization)

@router.get('/sessions/{session_id}/current',response_model=CurrentQuestionOut)
def current(session_id: UUID,authorization: str | None = Header(default=None)):
    s=require_session(session_id,authorization);require_in_progress(s)
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
        question=question,pending_answer=pending,host_lines=host_lines(s),stt_progress=progress_for(s))

@router.post('/sessions/{session_id}/questions/{order_no}/replay',response_model=ReplayOut)
def replay(session_id: UUID,order_no: int,authorization: str | None = Header(default=None)):
    require_session(session_id,authorization)
    count=db.increment_replay(session_id,order_no,REPLAY_LIMIT)
    return ReplayOut(order_no=order_no,replay_count=count,replay_limit=REPLAY_LIMIT)

@router.post('/sessions/{session_id}/questions/{order_no}/skip',response_model=SkipOut)
def skip(session_id: UUID,order_no: int,authorization: str | None = Header(default=None)):
    require_session(session_id,authorization)
    return SkipOut(**db.skip_question(session_id,order_no))
