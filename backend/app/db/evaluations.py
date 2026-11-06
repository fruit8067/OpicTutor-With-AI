# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성되었습니다.
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

def submit_session(session_id: UUID) -> UUID:
    with tx() as cur:
        s=session_for_update(cur,session_id)
        if s['status'] in ('submitted','grading','done'):
            e=latest(cur,session_id)
            if e: return e['id']
        require_state(s,'in_progress')
        cur.execute("""SELECT q.order_no,a.id FROM session_questions q LEFT JOIN answers a
            ON a.session_question_id=q.id AND a.is_selected AND a.stt_status='done'
            WHERE q.session_id=%s ORDER BY q.order_no""",(session_id,))
        rows=cur.fetchall()
        if len(rows)!=s['question_count'] or any(r['id'] is None for r in rows): raise AppError('NOT_ALL_ANSWERED')
        selected=[r['id'] for r in rows]
        cur.execute("UPDATE sessions SET status='submitted',submitted_at=now(),selected_answer_ids=%s WHERE id=%s",(selected,session_id))
        return new_evaluation(cur,s,1,selected)

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
            q.target_time_frames,q.context_scope,a.id AS answer_id,a.stt_status,a.stt_text,a.metrics_json AS metrics,a.stt_version
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
                      model: str, prompt_version: str, rubric_version: str, im_rubric_version: str,
                      corpus_version: str, retrieved_doc_ids: list[str]) -> bool:
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
