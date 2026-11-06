# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성되었습니다.
# OWNER: data-layer (contracts.yaml ownership)
from datetime import datetime
from uuid import UUID
from psycopg.types.json import Jsonb
from .pool import tx

def enqueue(cur, kind, target_id, dedupe_key, payload=None):
    cur.execute("""INSERT INTO jobs(type,target_id,dedupe_key,status,payload)
        VALUES (%s,%s,%s,'queued',%s) ON CONFLICT(dedupe_key) DO NOTHING""",
        (kind,target_id,dedupe_key,Jsonb(payload or {})))

def claim_job(types: list[str], worker_id: str, lease_sec: int) -> dict | None:
    with tx() as cur:
        cur.execute("""WITH candidate AS (
            SELECT id FROM jobs WHERE type=ANY(%s) AND status IN ('queued','failed')
            AND next_run_at<=now() AND attempts<max_attempts ORDER BY created_at,id LIMIT 1 FOR UPDATE SKIP LOCKED)
            UPDATE jobs j SET status='running',attempts=attempts+1,locked_by=%s,
            locked_until=now()+make_interval(secs=>%s) FROM candidate c WHERE j.id=c.id RETURNING j.*""",
            (types,worker_id,lease_sec))
        return cur.fetchone()

def heartbeat_job(job_id: UUID, worker_id: str, lease_sec: int) -> bool:
    with tx() as cur:
        cur.execute("""UPDATE jobs SET locked_until=now()+make_interval(secs=>%s) WHERE id=%s
            AND locked_by=%s AND status='running' AND locked_until>now() RETURNING id""", (lease_sec,job_id,worker_id))
        return cur.fetchone() is not None

def complete_job(job_id: UUID, worker_id: str) -> None:
    with tx() as cur:
        cur.execute("""UPDATE jobs SET status='done',locked_by=NULL,locked_until=NULL,error_code=NULL,error_detail=NULL
            WHERE id=%s AND locked_by=%s AND status='running' AND locked_until>now()""", (job_id,worker_id))

def fail_job(job_id: UUID, worker_id: str, *, error_code: str, retryable: bool, detail: dict | None = None) -> str:
    with tx() as cur:
        cur.execute("""UPDATE jobs SET status=CASE WHEN %s AND attempts<max_attempts THEN 'failed' ELSE 'dead' END,
            next_run_at=now()+make_interval(secs=>power(2,attempts)::int),locked_by=NULL,locked_until=NULL,
            error_code=%s,error_detail=%s WHERE id=%s AND locked_by=%s AND status='running'
            AND locked_until>now() RETURNING status""", (retryable,error_code,Jsonb(detail),job_id,worker_id))
        row=cur.fetchone()
        if row: return row['status']
        cur.execute('SELECT status FROM jobs WHERE id=%s',(job_id,))
        row=cur.fetchone()
        return row['status'] if row else 'dead'

def recover_expired_jobs() -> int:
    with tx() as cur:
        cur.execute("""UPDATE jobs SET status=CASE WHEN attempts<max_attempts THEN 'failed' ELSE 'dead' END,
            locked_by=NULL,locked_until=NULL,next_run_at=now() WHERE status='running' AND locked_until<=now()""")
        return cur.rowcount

def last_job_activity() -> datetime | None:
    with tx() as cur:
        cur.execute("SELECT max(updated_at) AS seen FROM jobs WHERE status IN ('running','done')")
        return cur.fetchone()['seen']
