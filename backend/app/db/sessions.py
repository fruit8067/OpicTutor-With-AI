# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성되었습니다.
# OWNER: data-layer (contracts.yaml ownership)
from uuid import UUID
from psycopg.types.json import Jsonb
from app.errors import AppError
from app.schemas.internal import SessionQuestionIn, SessionRow
from .pool import tx, session_for_update, require_state, idempotency_lock
from .jobs import enqueue

def create_session(*, client_request_id: str | None, scenario_id: str, settings_json: dict,
                   questions: list[SessionQuestionIn], replaces_session_id: UUID | None,
                   user_id: UUID | None = None) -> tuple[UUID, bool]:
    with tx() as cur:
        idempotency_lock(cur,client_request_id)
        if client_request_id is not None:
            cur.execute('SELECT id FROM sessions WHERE client_request_id=%s',(client_request_id,))
            existing=cur.fetchone()
            if existing: return existing['id'],False
        if replaces_session_id:
            old=session_for_update(cur,replaces_session_id)
            require_state(old,'preparing','ready','prepare_failed')
            cur.execute("UPDATE sessions SET status='cancelled' WHERE id=%s",(replaces_session_id,))
        cur.execute("""INSERT INTO sessions(client_request_id,replaces_session_id,scenario_id,settings_json,status,question_count,user_id)
            VALUES (%s,%s,%s,%s,'preparing',%s,%s) RETURNING id""",
            (client_request_id,replaces_session_id,scenario_id,Jsonb(settings_json),len(questions),user_id))
        sid=cur.fetchone()['id']
        for question in questions:
            q=question.model_dump() if hasattr(question,'model_dump') else dict(question)
            cur.execute("""INSERT INTO session_questions(session_id,order_no,question_id,question_version,question_text,
                question_type,is_scored,target_functions,target_time_frames,context_scope)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""", (sid,*(q[k] for k in
                ('order_no','question_id','question_version','question_text','question_type','is_scored',
                 'target_functions','target_time_frames','context_scope'))))
        enqueue(cur,'tts_prepare',sid,f'tts_prepare:{sid}:1',{'prepare_attempt':1})
        return sid,True

def get_session(session_id: UUID) -> SessionRow | None:
    with tx() as cur:
        cur.execute("""SELECT s.*,
            (SELECT status FROM evaluations WHERE session_id=s.id ORDER BY run_no DESC LIMIT 1) AS latest_evaluation_status,
            COALESCE((SELECT jsonb_object_agg(h.line_key,jsonb_build_object('tts_asset_id',a.id,'file_path',a.file_path,
            'duration_sec',a.duration_sec)) FROM session_host_lines h JOIN tts_assets a ON a.id=h.tts_asset_id
            WHERE h.session_id=s.id),'{}'::jsonb) AS host_lines FROM sessions s WHERE s.id=%s""",(session_id,))
        return cur.fetchone()


def get_session_id_by_request_id(client_request_id: str) -> UUID | None:
    with tx() as cur:
        cur.execute('SELECT id FROM sessions WHERE client_request_id=%s',(client_request_id,))
        row=cur.fetchone()
        return row['id'] if row else None

def list_session_questions(session_id: UUID) -> list[dict]:
    with tx() as cur:
        cur.execute("""SELECT q.*,a.file_path,a.duration_sec FROM session_questions q LEFT JOIN tts_assets a
            ON a.id=q.tts_asset_id WHERE session_id=%s ORDER BY order_no""",(session_id,))
        return cur.fetchall()

def get_session_question(session_id: UUID, order_no: int) -> dict | None:
    with tx() as cur:
        cur.execute("""SELECT q.*,t.file_path,t.duration_sec,(SELECT row_to_json(a) FROM answers a
            WHERE a.session_question_id=q.id ORDER BY attempt_no DESC LIMIT 1) AS latest_answer,
            ARRAY(SELECT a.client_request_id FROM answers a WHERE a.session_question_id=q.id
                  ORDER BY a.attempt_no) AS client_request_ids
            FROM session_questions q LEFT JOIN tts_assets t ON t.id=q.tts_asset_id
            WHERE q.session_id=%s AND q.order_no=%s""",(session_id,order_no))
        return cur.fetchone()

def retry_prepare(session_id: UUID) -> int:
    with tx() as cur:
        s=session_for_update(cur,session_id)
        if s['status']=='preparing': return s['prepare_attempt']
        require_state(s,'prepare_failed')
        attempt=s['prepare_attempt']+1
        cur.execute("UPDATE sessions SET status='preparing',prepare_attempt=%s,prepare_error_json=NULL WHERE id=%s",(attempt,session_id))
        enqueue(cur,'tts_prepare',session_id,f'tts_prepare:{session_id}:{attempt}',{'prepare_attempt':attempt})
        return attempt

def cancel_session(session_id: UUID) -> str:
    with tx() as cur:
        s=session_for_update(cur,session_id)
        require_state(s,'preparing','prepare_failed','ready','cancelled')
        if s['status']!='cancelled': cur.execute("UPDATE sessions SET status='cancelled' WHERE id=%s",(session_id,))
        return 'cancelled'

def start_session(session_id: UUID) -> SessionRow:
    with tx() as cur:
        s=session_for_update(cur,session_id)
        require_state(s,'ready','in_progress')
        if s['status']=='in_progress': return s
        cur.execute("UPDATE sessions SET status='in_progress',started_at=now() WHERE id=%s RETURNING *",(session_id,))
        return cur.fetchone()

def increment_replay(session_id: UUID, order_no: int, limit: int) -> int:
    with tx() as cur:
        s=session_for_update(cur,session_id);require_state(s,'in_progress')
        if order_no!=s['current_order_no']: raise AppError('ORDER_MISMATCH')
        cur.execute("""UPDATE session_questions SET replay_count=replay_count+1 WHERE session_id=%s
            AND order_no=%s AND replay_count<%s RETURNING replay_count""",(session_id,order_no,limit))
        row=cur.fetchone()
        if row is None: raise AppError('REPLAY_LIMIT')
        return row['replay_count']
