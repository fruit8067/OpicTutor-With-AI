# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성되었습니다.
# OWNER: data-layer (contracts.yaml ownership)
from contextlib import contextmanager
from pathlib import Path
from threading import Lock
from pgvector.psycopg import register_vector
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from app.config import settings
from app.errors import AppError

_pool = None
_lock = Lock()

def _configure(conn):
    with conn.transaction():
        if conn.execute("SELECT 1 FROM pg_type WHERE typname='vector'").fetchone():
            register_vector(conn)

def get_pool() -> ConnectionPool:
    global _pool
    with _lock:
        if _pool is None:
            _pool = ConnectionPool(settings.DATABASE_URL, min_size=0, max_size=12, timeout=5,
                kwargs={'row_factory': dict_row, 'connect_timeout': 5}, configure=_configure, open=True)
    return _pool

@contextmanager
def tx():
    with get_pool().connection() as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                yield cur

def init_db() -> None:
    with tx() as cur:
        cur.execute("SELECT pg_advisory_xact_lock(hashtext('opic-schema-migrations'))")
        cur.execute('CREATE TABLE IF NOT EXISTS schema_migrations (name TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())')
        for path in sorted((Path(__file__).resolve().parents[2] / 'migrations').glob('*.sql')):
            cur.execute('SELECT name FROM schema_migrations WHERE name=%s', (path.name,))
            if cur.fetchone() is None:
                cur.execute(path.read_text(encoding='utf-8'))
                cur.execute('INSERT INTO schema_migrations(name) VALUES (%s)', (path.name,))

def ping() -> bool:
    try:
        with tx() as cur: cur.execute('SELECT 1')
        return True
    except Exception:
        return False

def session_for_update(cur, session_id):
    cur.execute('SELECT * FROM sessions WHERE id=%s FOR UPDATE', (session_id,))
    row = cur.fetchone()
    if row is None: raise AppError('SESSION_NOT_FOUND')
    return row

def require_state(row, *states):
    if row['status'] not in states: raise AppError('INVALID_STATE')

def idempotency_lock(cur, key):
    if key is not None: cur.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))', (key,))
