# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성되었습니다.
# 후속 수정: 건너뛴 문항 제출·스냅샷 처리와 v3 비동기 STT 제출(submitted 대기, 평가 등록 시점 채택)은
# Claude(Anthropic)의 도움으로 작성되었습니다.
# OWNER: data-layer (contracts.yaml ownership)
from uuid import UUID
from psycopg.types.json import Jsonb
from app.errors import AppError
from .pool import tx, session_for_update, require_state
from .jobs import enqueue

def latest(cur, sid):
    cur.execute('SELECT * FROM evaluations WHERE session_id=%s ORDER BY run_no DESC LIMIT 1',(sid,))
    return cur.fetchone()

def new_evaluation(cur, s, run_no, selected):
    cur.execute("""INSERT INTO evaluations(session_id,run_no,selected_answer_ids,status)
        VALUES (%s,%s,%s,'queued') RETURNING id""",(s['id'],run_no,selected))
    eid=cur.fetchone()['id']
    enqueue(cur,'evaluate',eid,f"evaluate:{s['id']}:{run_no}",{'run_no':run_no})
    cur.execute("UPDATE sessions SET status='grading' WHERE id=%s",(s['id'],))
    return eid

LATEST_ATTEMPT = """LEFT JOIN LATERAL (SELECT a.id,a.stt_status FROM answers a WHERE a.session_question_id=q.id
    ORDER BY (a.stt_status='done' AND a.is_selected) DESC, a.attempt_no DESC LIMIT 1) a ON true"""

def stt_progress_cur(cur, session_id) -> dict:
    """건너뛰지 않고 답변이 접수된 문항 기준 STT 진행 현황. 문항마다 채택(done) 답변, 없으면 최근 시도를 센다."""
    cur.execute(f"""SELECT COUNT(a.id)::int AS total,
        COUNT(*) FILTER (WHERE a.stt_status='done')::int AS done,
        COUNT(*) FILTER (WHERE a.stt_status IN ('queued','processing'))::int AS pending,
        COUNT(*) FILTER (WHERE a.stt_status IN ('rejected','failed'))::int AS unusable
        FROM session_questions q {LATEST_ATTEMPT} WHERE q.session_id=%s AND q.skipped_at IS NULL""",(session_id,))
    return dict(cur.fetchone())

def stt_progress(session_id: UUID) -> dict:
    with tx() as cur: return stt_progress_cur(cur,session_id)

def maybe_enqueue_evaluation(cur, s) -> UUID | None:
    """제출됐고(submitted) 남은 STT가 없으면 지금 채택 답변을 고정하고 평가를 등록한다.
    세션 행 잠금을 잡은 트랜잭션 안에서만 호출한다. 제출과 마지막 STT 종결 중 나중 쪽에서 한 번만 등록된다."""
    cur.execute('SELECT * FROM sessions WHERE id=%s',(s['id'],));s=cur.fetchone()
    if s['status']!='submitted': return None
    cur.execute(f"""SELECT q.order_no,q.skipped_at,a.id,a.stt_status FROM session_questions q {LATEST_ATTEMPT}
        WHERE q.session_id=%s ORDER BY q.order_no""",(s['id'],))
    rows=cur.fetchall()
    if any(r['stt_status'] in ('queued','processing') for r in rows): return None
    # 건너뛴 문항은 답변 없이, 거부·실패 답변은 그 상태 그대로 스냅샷에 실어 인식 불가 문항으로 평가한다.
    selected=[r['id'] for r in rows if r['id'] is not None and r['skipped_at'] is None]
    cur.execute('UPDATE sessions SET selected_answer_ids=%s WHERE id=%s',(selected,s['id']))
    return new_evaluation(cur,s,1,selected)

def submit_session(session_id: UUID) -> UUID | None:
    """모든 문항이 접수되거나 건너뛰어졌으면 제출한다. STT가 남아 있으면 submitted로 기다리고 None을 반환한다."""
    with tx() as cur:
        s=session_for_update(cur,session_id)
        if s['status'] in ('submitted','grading','grading_failed','done'):
            e=latest(cur,session_id)
            return e['id'] if e else None
        require_state(s,'in_progress')
        cur.execute("""SELECT q.order_no,q.skipped_at,EXISTS(SELECT 1 FROM answers a WHERE a.session_question_id=q.id) AS has_answer
            FROM session_questions q WHERE q.session_id=%s ORDER BY q.order_no""",(session_id,))
        rows=cur.fetchall()
        # 건너뛴 문항은 답변 없이 제출된다. 건너뛰지 않았는데 접수된 답변이 없으면 아직 끝나지 않은 것이다.
        if (s['current_order_no']<=s['question_count'] or len(rows)!=s['question_count']
                or any(not r['has_answer'] and r['skipped_at'] is None for r in rows)): raise AppError('NOT_ALL_ANSWERED')
        cur.execute("UPDATE sessions SET status='submitted',submitted_at=now() WHERE id=%s",(session_id,))
        return maybe_enqueue_evaluation(cur,s)

def create_regrade(session_id: UUID) -> UUID:
    with tx() as cur:
        s=session_for_update(cur,session_id);e=latest(cur,session_id)
        if s['status']=='grading' and e: return e['id']
        require_state(s,'grading_failed','done')
        return new_evaluation(cur,s,e['run_no']+1,s['selected_answer_ids'])

def get_evaluation(evaluation_id: UUID) -> dict | None:
    with tx() as cur:
        cur.execute('SELECT * FROM evaluations WHERE id=%s',(evaluation_id,));return cur.fetchone()

def get_latest_evaluation(session_id: UUID) -> dict | None:
    with tx() as cur: return latest(cur,session_id)

def load_exam_snapshot(session_id: UUID, selected_answer_ids: list[UUID]) -> list[dict]:
    with tx() as cur:
        cur.execute("""SELECT q.order_no,q.question_id,q.question_type,q.question_text,q.is_scored,q.target_functions,
            q.target_time_frames,q.context_scope,a.id AS answer_id,a.stt_status,a.stt_text,a.metrics_json AS metrics,a.stt_version,
            q.skipped_at IS NOT NULL AS skipped
            FROM session_questions q LEFT JOIN answers a ON a.session_question_id=q.id AND a.id=ANY(%s::uuid[])
            WHERE q.session_id=%s ORDER BY q.order_no""",(selected_answer_ids,session_id))
        return cur.fetchall()

def locked_evaluation(cur,eid):
    cur.execute('SELECT session_id FROM evaluations WHERE id=%s',(eid,));ref=cur.fetchone()
    if ref is None: return None,None
    s=session_for_update(cur,ref['session_id']);e=latest(cur,s['id'])
    if e['id']!=eid or s['status']!='grading' or e['status'] not in ('queued','running'): return None,None
    return s,e

def mark_evaluation_running(evaluation_id: UUID) -> bool:
    with tx() as cur:
        s,e=locked_evaluation(cur,evaluation_id)
        if e is None: return False
        cur.execute("UPDATE evaluations SET status='running' WHERE id=%s",(evaluation_id,));return True

def finish_evaluation(evaluation_id: UUID, *, result: dict, assessment_status: str,
                      base_level: str | None, estimated_level: str | None, im_estimation_status: str,
                      model: str, prompt_version: str, rubric_version: str, im_rubric_version: str | None,
                      corpus_version: str | None, retrieved_doc_ids: list[str]) -> bool:
    with tx() as cur:
        s,e=locked_evaluation(cur,evaluation_id)
        if e is None: return False
        cur.execute("""UPDATE evaluations SET status='done',result_json=%s,assessment_status=%s,base_level=%s,
            estimated_level=%s,im_estimation_status=%s,model=%s,prompt_version=%s,rubric_version=%s,im_rubric_version=%s,
            corpus_version=%s,retrieved_doc_ids=%s,error_code=NULL,error_detail=NULL WHERE id=%s""",
            (Jsonb(result),assessment_status,base_level,estimated_level,im_estimation_status,model,prompt_version,
             rubric_version,im_rubric_version,corpus_version,retrieved_doc_ids,evaluation_id))
        cur.execute("UPDATE sessions SET status='done',result_id=%s WHERE id=%s",(evaluation_id,s['id']));return True

def fail_evaluation(evaluation_id: UUID, error_code: str, error_detail: dict | None) -> bool:
    with tx() as cur:
        s,e=locked_evaluation(cur,evaluation_id)
        if e is None: return False
        cur.execute("UPDATE evaluations SET status='failed',error_code=%s,error_detail=%s WHERE id=%s",(error_code,Jsonb(error_detail),evaluation_id))
        cur.execute("UPDATE sessions SET status='grading_failed' WHERE id=%s",(s['id'],));return True
