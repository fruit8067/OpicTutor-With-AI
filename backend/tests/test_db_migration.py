# AI-assisted (OpenAI Codex). OWNER: data-layer.
from pathlib import Path
from uuid import uuid4
import pytest
from psycopg import sql
from app import db
from app.db.pool import tx


def test_legacy_1536_migration_preserves_source_and_reexecution_preserves_new_vectors():
    if not db.ping(): pytest.skip('로컬 PostgreSQL/pgvector 미실행')
    db.init_db()
    schema='embedding_migration_'+uuid4().hex
    migration=(Path(__file__).resolve().parents[1]/'migrations/003_embedding_3072.sql').read_text(encoding='utf-8')
    with tx() as cur:
        cur.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
        try:
            cur.execute(sql.SQL('SET LOCAL search_path TO {},public').format(sql.Identifier(schema)))
            cur.execute("""CREATE TABLE rag_docs(id TEXT PRIMARY KEY,text TEXT,metadata JSONB,embedding vector(1536));
                CREATE INDEX rag_docs_embedding ON rag_docs USING hnsw(embedding vector_cosine_ops)""")
            cur.execute("INSERT INTO rag_docs VALUES ('keep','source text','{\"topic\":\"keep\",\"_embedding_profile\":{}}',%s::vector)",
                        (str([1.0]+[0.0]*1535),))
            cur.execute(migration)
            row=cur.execute('SELECT text,metadata,embedding FROM rag_docs').fetchone()
            assert row['text']=='source text' and row['metadata']=={'topic':'keep'} and row['embedding'] is None
            vector=str([1.0]+[0.0]*3071)
            cur.execute('UPDATE rag_docs SET embedding=%s::vector',(vector,))
            cur.execute(migration)
            row=cur.execute('SELECT vector_dims(embedding) AS dim,embedding IS NOT NULL AS present FROM rag_docs').fetchone()
            assert row=={'dim':3072,'present':True}
            assert cur.execute("SELECT to_regclass(%s) AS idx",(schema+'.rag_docs_embedding',)).fetchone()['idx'] is None
        finally:
            cur.execute('SET LOCAL search_path TO public')
            cur.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))
