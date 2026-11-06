# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성되었습니다.
# OWNER: data-layer (contracts.yaml ownership)
from uuid import UUID
from psycopg.types.json import Jsonb
from app.errors import AppError
from .pool import tx, session_for_update, require_state, idempotency_lock
from .jobs import enqueue

ANSWER_SQL = "SELECT a.*,q.session_id,q.order_no FROM answers a JOIN session_questions q ON q.id=a.session_question_id WHERE a.id=%s"

def create_answer(*, session_id: UUID, order_no: int, client_request_id: str, audio_path: str,
                  audio_mime: str, audio_bytes: int, audio_hash: str, client_duration_ms: int,
                  answer_id: UUID) -> tuple[dict, bool]:
    with tx() as cur:
        idempotency_lock(cur,client_request_id)
        s=session_for_update(cur,session_id)
        cur.execute("""SELECT a.*,q.session_id,q.order_no FROM answers a JOIN session_questions q
            ON q.id=a.session_question_id WHERE a.client_request_id=%s""",(client_request_id,))
        old=cur.fetchone()
        if old:
            if old['session_id']!=session_id or old['order_no']!=order_no: raise AppError('ORDER_MISMATCH')
            return old,False
        require_state(s,'in_progress')
        if order_no!=s['current_order_no'] or order_no>s['question_count']: raise AppError('ORDER_MISMATCH')
        cur.execute('SELECT id FROM session_questions WHERE session_id=%s AND order_no=%s',(session_id,order_no))
        q=cur.fetchone()
        if q is None: raise AppError('ORDER_MISMATCH')
        cur.execute('SELECT stt_status,attempt_no FROM answers WHERE session_question_id=%s',(q['id'],))
        attempts=cur.fetchall()
        if any(a['stt_status'] in ('queued','processing') for a in attempts): raise AppError('ANSWER_PENDING')
        attempt=max((a['attempt_no'] for a in attempts),default=0)+1
        cur.execute("""INSERT INTO answers(id,session_question_id,attempt_no,client_request_id,audio_path,audio_mime,
            audio_bytes,audio_hash,client_duration_ms,stt_status) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'queued') RETURNING *""",
            (answer_id,q['id'],attempt,client_request_id,audio_path,audio_mime,audio_bytes,audio_hash,client_duration_ms))
        answer=cur.fetchone()
        enqueue(cur,'stt',answer_id,f'stt:{answer_id}:1',{'stt_attempt':1})
        return {**answer,'session_id':session_id,'order_no':order_no},True

def get_answer(answer_id: UUID) -> dict | None:
    with tx() as cur:
        cur.execute(ANSWER_SQL,(answer_id,));return cur.fetchone()

def locked_answer(cur, answer_id):
    cur.execute(ANSWER_SQL,(answer_id,));a=cur.fetchone()
    if a is None: raise AppError('ANSWER_NOT_FOUND')
    s=session_for_update(cur,a['session_id'])
    cur.execute(ANSWER_SQL+' FOR UPDATE OF a',(answer_id,))
    return cur.fetchone(),s

def mark_stt_processing(answer_id: UUID) -> bool:
    with tx() as cur:
        a,s=locked_answer(cur,answer_id)
        if s['status']!='in_progress' or a['stt_status']!='queued': return False
        cur.execute("UPDATE answers SET stt_status='processing' WHERE id=%s",(answer_id,));return True

def complete_stt(answer_id: UUID, *, text: str, timestamps: list[dict], metrics: dict, stt_version: str) -> dict:
    with tx() as cur:
        a,s=locked_answer(cur,answer_id)
        if a['stt_status']!='done':
            require_state(s,'in_progress')
            if a['stt_status'] not in ('queued','processing') or s['current_order_no']!=a['order_no']: raise AppError('INVALID_STATE')
            cur.execute('UPDATE answers SET is_selected=false WHERE session_question_id=%s AND is_selected',(a['session_question_id'],))
            cur.execute("""UPDATE answers SET stt_status='done',is_selected=true,stt_text=%s,timestamps_json=%s,
                metrics_json=%s,stt_version=%s,reject_reason=NULL,error_code=NULL WHERE id=%s""",
                (text,Jsonb(timestamps),Jsonb(metrics),stt_version,answer_id))
            cur.execute('UPDATE sessions SET current_order_no=current_order_no+1 WHERE id=%s AND current_order_no=%s RETURNING *',(s['id'],a['order_no']))
            s=cur.fetchone()
        return {'session_status':s['status'],'current_order_no':s['current_order_no'],'all_answered':s['current_order_no']>s['question_count']}

def reject_stt(answer_id: UUID, reason: str) -> None:
    with tx() as cur:
        a,s=locked_answer(cur,answer_id)
        if s['status']=='in_progress' and a['stt_status'] in ('queued','processing'):
            cur.execute("UPDATE answers SET stt_status='rejected',reject_reason=%s WHERE id=%s",(reason,answer_id))

def fail_stt(answer_id: UUID, error_code: str) -> None:
    with tx() as cur:
        a,s=locked_answer(cur,answer_id)
        if s['status']=='in_progress' and a['stt_status'] in ('queued','processing'):
            cur.execute("UPDATE answers SET stt_status='failed',error_code=%s WHERE id=%s",(error_code,answer_id))

def retry_stt(answer_id: UUID) -> None:
    with tx() as cur:
        a,s=locked_answer(cur,answer_id);require_state(s,'in_progress')
        if a['stt_status'] in ('queued','processing'): return
        if a['stt_status']!='failed' or s['current_order_no']!=a['order_no']: raise AppError('INVALID_STATE')
        cur.execute("SELECT 1 FROM answers WHERE session_question_id=%s AND stt_status IN ('queued','processing')",(a['session_question_id'],))
        if cur.fetchone(): raise AppError('ANSWER_PENDING')
        attempt=a['stt_attempt']+1
        cur.execute("UPDATE answers SET stt_status='queued',stt_attempt=%s,error_code=NULL WHERE id=%s",(attempt,answer_id))
        enqueue(cur,'stt',answer_id,f'stt:{answer_id}:{attempt}',{'stt_attempt':attempt})
