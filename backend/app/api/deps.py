# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성되었습니다.
# OWNER: session-api (contracts.yaml ownership)
from uuid import UUID
from app import db,tts
from app.errors import AppError
from app.schemas.api import SessionOut,AnswerOut,PrepareProgress,HostLineOut

REPLAY_LIMIT=1
RECORD_MIN_MS=2000
RECORD_MAX_MS=120000
UPLOAD_TOLERANCE_MS=5000
UPLOAD_MAX_BYTES=10485760
MIME_EXT={'audio/webm':'webm','audio/ogg':'ogg','audio/wav':'wav','audio/mp4':'m4a'}

def require_session(sid):
    s=db.get_session(sid)
    if s is None: raise AppError('SESSION_NOT_FOUND')
    return s

def require_answer(sid,aid):
    a=db.get_answer(aid)
    if a is None or a['session_id']!=sid: raise AppError('ANSWER_NOT_FOUND')
    return a

def require_in_progress(s):
    if s['status']!='in_progress': raise AppError('INVALID_STATE')

def session_out(sid):
    s=require_session(sid)
    prepare=None
    if s['status'] in ('preparing','prepare_failed','ready'):
        qs=db.list_session_questions(sid)
        prepare=PrepareProgress(total=s['question_count']+len(tts.HOST_LINES),
            linked=sum(q.get('tts_asset_id') is not None for q in qs)+len(s.get('host_lines',{})),
            failures=s.get('prepare_error_json') or [])
    return SessionOut(session_id=s['id'],status=s['status'],scenario_id=s['scenario_id'],question_count=s['question_count'],
        current_order_no=s['current_order_no'],all_answered=s['current_order_no']>s['question_count'],prepare=prepare,
        latest_evaluation_status=s.get('latest_evaluation_status'),created_at=s['created_at'],updated_at=s['updated_at'])

def answer_out(a,s=None):
    s=s or require_session(a['session_id'])
    return AnswerOut(answer_id=a['id'],order_no=a['order_no'],attempt_no=a['attempt_no'],stt_status=a['stt_status'],
        reject_reason=a.get('reject_reason'),error_code=a.get('error_code'),stt_text=a.get('stt_text'),metrics=a.get('metrics_json'),
        session_status=s['status'],current_order_no=s['current_order_no'],all_answered=s['current_order_no']>s['question_count'])

def host_lines(s):
    linked=s.get('host_lines',{})
    return {key:HostLineOut(key=key,text=text,audio_url=tts.tts_url(linked[key]['file_path']) if key in linked else None)
        for key,text in tts.HOST_LINES.items()}
