# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성되었습니다.
# 후속 수정: 문항 건너뛰기(skip_question)와 v3 비동기 STT(접수 즉시 전진, 이전 문항 STT 반영,
# 마지막 STT 종결 시 평가 등록)는 Claude(Anthropic)의 도움으로 작성되었습니다.
# OWNER: data-layer (contracts.yaml ownership)
from uuid import UUID
from psycopg.types.json import Jsonb
from app.errors import AppError
from .pool import tx, session_for_update, require_state, idempotency_lock
from .jobs import enqueue
from .evaluations import maybe_enqueue_evaluation, stt_progress_cur

PENDING=('queued','processing')
# 답변 접수 후 STT 결과를 반영할 수 있는 세션 상태. submitted는 제출 후 남은 STT를 기다리는 상태다.
STT_OPEN=('in_progress','submitted')

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
        # v3: STT 완료를 기다리지 않고 접수 트랜잭션에서 바로 다음 문항으로 넘긴다.
        cur.execute('UPDATE sessions SET current_order_no=current_order_no+1 WHERE id=%s AND current_order_no=%s',(session_id,order_no))
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
        if s['status'] not in STT_OPEN or a['stt_status']!='queued': return False
        cur.execute("UPDATE answers SET stt_status='processing' WHERE id=%s",(answer_id,));return True

def summary(cur, s):
    cur.execute('SELECT * FROM sessions WHERE id=%s',(s['id'],));s=cur.fetchone()
    return {'session_status':s['status'],'current_order_no':s['current_order_no'],
            'all_answered':s['current_order_no']>s['question_count'],'stt_progress':stt_progress_cur(cur,s['id'])}

def complete_stt(answer_id: UUID, *, text: str, timestamps: list[dict], metrics: dict, stt_version: str) -> dict:
    """STT 결과를 저장하고 채택한다. 이전 문항이거나 제출 후(submitted)여도 반영한다.
    이미 done이면 멱등, 평가가 시작된 뒤 늦게 도착한 결과는 무시한다."""
    with tx() as cur:
        a,s=locked_answer(cur,answer_id)
        if a['stt_status']!='done' and s['status'] in STT_OPEN:
            if a['stt_status'] not in PENDING: raise AppError('INVALID_STATE')
            cur.execute('UPDATE answers SET is_selected=false WHERE session_question_id=%s AND is_selected',(a['session_question_id'],))
            cur.execute("""UPDATE answers SET stt_status='done',is_selected=true,stt_text=%s,timestamps_json=%s,
                metrics_json=%s,stt_version=%s,reject_reason=NULL,error_code=NULL WHERE id=%s""",
                (text,Jsonb(timestamps),Jsonb(metrics),stt_version,answer_id))
            # 호환: v3 배포 전에 접수되어 순서가 아직 그 문항에 머문 답변이면 여기서 전진한다(v3 접수분에는 해당 없음).
            cur.execute('UPDATE sessions SET current_order_no=current_order_no+1 WHERE id=%s AND current_order_no=%s AND status=%s',
                        (s['id'],a['order_no'],'in_progress'))
            maybe_enqueue_evaluation(cur,s)
        return summary(cur,s)

def reject_stt(answer_id: UUID, reason: str) -> None:
    with tx() as cur:
        a,s=locked_answer(cur,answer_id)
        if s['status'] in STT_OPEN and a['stt_status'] in PENDING:
            cur.execute("UPDATE answers SET stt_status='rejected',reject_reason=%s WHERE id=%s",(reason,answer_id))
            # 거부는 종결 상태다. 평가에서는 인식 불가 문항(unusable)으로 처리된다.
            maybe_enqueue_evaluation(cur,s)

def fail_stt(answer_id: UUID, error_code: str) -> None:
    with tx() as cur:
        a,s=locked_answer(cur,answer_id)
        if s['status'] in STT_OPEN and a['stt_status'] in PENDING:
            cur.execute("UPDATE answers SET stt_status='failed',error_code=%s WHERE id=%s",(error_code,answer_id))
            maybe_enqueue_evaluation(cur,s)

def retry_stt(answer_id: UUID) -> None:
    with tx() as cur:
        # v3: 평가 등록 전(in_progress/submitted)이면 이전 문항의 실패 답변도 원음으로 다시 처리할 수 있다.
        a,s=locked_answer(cur,answer_id);require_state(s,*STT_OPEN)
        if a['stt_status'] in PENDING: return
        if a['stt_status']!='failed': raise AppError('INVALID_STATE')
        cur.execute("SELECT 1 FROM answers WHERE session_question_id=%s AND stt_status IN ('queued','processing')",(a['session_question_id'],))
        if cur.fetchone(): raise AppError('ANSWER_PENDING')
        attempt=a['stt_attempt']+1
        cur.execute("UPDATE answers SET stt_status='queued',stt_attempt=%s,error_code=NULL WHERE id=%s",(attempt,answer_id))
        enqueue(cur,'stt',answer_id,f'stt:{answer_id}:{attempt}',{'stt_attempt':attempt})

def skip_question(session_id: UUID, order_no: int) -> dict:
    """현재 문항을 답변 없이 건너뛴다. 같은 문항 재요청은 멱등으로 현재 진행 상태만 돌려준다."""
    with tx() as cur:
        s=session_for_update(cur,session_id)
        cur.execute('SELECT id,skipped_at FROM session_questions WHERE session_id=%s AND order_no=%s FOR UPDATE',(session_id,order_no))
        q=cur.fetchone()
        if q is None: raise AppError('ORDER_MISMATCH')
        if q['skipped_at'] is None:
            require_state(s,'in_progress')
            if order_no!=s['current_order_no'] or order_no>s['question_count']: raise AppError('ORDER_MISMATCH')
            cur.execute("SELECT 1 FROM answers WHERE session_question_id=%s AND stt_status IN ('queued','processing')",(q['id'],))
            if cur.fetchone(): raise AppError('ANSWER_PENDING')
            cur.execute('UPDATE session_questions SET skipped_at=now() WHERE id=%s',(q['id'],))
            cur.execute('UPDATE sessions SET current_order_no=current_order_no+1 WHERE id=%s AND current_order_no=%s RETURNING *',(session_id,order_no))
            s=cur.fetchone()
        return {'order_no':order_no,'session_status':s['status'],'current_order_no':s['current_order_no'],
                'all_answered':s['current_order_no']>s['question_count']}
