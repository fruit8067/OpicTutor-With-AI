# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성되었습니다.
# OWNER: data-layer (contracts.yaml ownership)
from uuid import UUID
import hashlib
from psycopg.types.json import Jsonb
from app.errors import AppError
from .pool import tx, session_for_update

def upsert_tts_asset(*, kind: str, ref_id: str, text_hash: str, voice_id: str, settings_version: str,
                     file_path: str, duration_sec: float | None, status: str = 'available') -> UUID:
    with tx() as cur:
        cur.execute("""INSERT INTO tts_assets(cache_key,kind,ref_id,text_hash,voice_id,settings_version,file_path,duration_sec,status)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(cache_key) DO UPDATE SET
            settings_version=excluded.settings_version,file_path=excluded.file_path,duration_sec=excluded.duration_sec,
            status=excluded.status,error_code=NULL RETURNING id""",
            (f'{kind}:{ref_id}:{text_hash}:{voice_id}',kind,ref_id,text_hash,voice_id,settings_version,file_path,duration_sec,status))
        return cur.fetchone()['id']

def find_tts_asset(*, kind: str, ref_id: str, text_hash: str, voice_id: str) -> dict | None:
    with tx() as cur:
        cur.execute('SELECT * FROM tts_assets WHERE cache_key=%s',(f'{kind}:{ref_id}:{text_hash}:{voice_id}',))
        return cur.fetchone()

def complete_prepare(session_id: UUID, attempt: int, question_links: dict[int, UUID], host_links: dict[str, UUID]) -> bool:
    with tx() as cur:
        s=session_for_update(cur,session_id)
        if s['status']!='preparing' or s['prepare_attempt']!=attempt: return False
        cur.execute('SELECT order_no,question_text FROM session_questions WHERE session_id=%s',(session_id,))
        hashes={r['order_no']:hashlib.sha1(r['question_text'].strip().encode('utf-8')).hexdigest() for r in cur.fetchall()}
        if set(question_links)!=set(hashes) or set(host_links)!={'greeting','say_again','next','finish'}:
            raise AppError('INVALID_STATE')
        for no,asset in question_links.items():
            cur.execute("""UPDATE session_questions q SET tts_asset_id=a.id FROM tts_assets a
                WHERE q.session_id=%s AND q.order_no=%s AND a.id=%s AND a.kind='question' AND a.ref_id=q.question_id
                AND a.text_hash=%s AND a.status='available'""",(session_id,no,asset,hashes[no]))
            if cur.rowcount!=1: raise AppError('INVALID_STATE')
        for key,asset in host_links.items():
            cur.execute("SELECT id FROM tts_assets WHERE id=%s AND kind='host' AND ref_id=%s AND status='available'",(asset,key))
            if cur.fetchone() is None: raise AppError('INVALID_STATE')
            cur.execute("""INSERT INTO session_host_lines(session_id,line_key,tts_asset_id) VALUES (%s,%s,%s)
                ON CONFLICT(session_id,line_key) DO UPDATE SET tts_asset_id=excluded.tts_asset_id""",(session_id,key,asset))
        cur.execute("UPDATE sessions SET status='ready',prepare_error_json=NULL WHERE id=%s",(session_id,))
        return True

def fail_prepare(session_id: UUID, attempt: int, errors: list[dict]) -> bool:
    with tx() as cur:
        cur.execute("""UPDATE sessions SET status='prepare_failed',prepare_error_json=%s WHERE id=%s
            AND status='preparing' AND prepare_attempt=%s RETURNING id""",(Jsonb(errors),session_id,attempt))
        return cur.fetchone() is not None
