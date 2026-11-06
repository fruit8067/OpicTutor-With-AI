# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성되었습니다.
# OWNER: data-layer (contracts.yaml ownership)
from psycopg import sql
from psycopg.types.json import Jsonb
from .pool import tx

def get_rag_docs(doc_type: str, *, corpus_version: str | None = None, **filters) -> list[dict]:
    clauses=[sql.SQL('doc_type=%s')];params=[doc_type]
    if corpus_version is not None: clauses.append(sql.SQL('corpus_version=%s'));params.append(corpus_version)
    columns={'id','question_id','question_type','level','level_rank','contrast_set_id','text_style'}
    for key,value in filters.items():
        if key in columns: clauses.append(sql.SQL('{}=%s').format(sql.Identifier(key)));params.append(value)
        else: clauses.append(sql.SQL('metadata @> %s'));params.append(Jsonb({key:value}))
    with tx() as cur:
        cur.execute(sql.SQL('SELECT * FROM rag_docs WHERE {} ORDER BY level_rank,id').format(sql.SQL(' AND ').join(clauses)),params)
        return cur.fetchall()

def get_contrast_set(contrast_set_id: str, text_style: str = 'stt') -> list[dict]:
    return get_rag_docs('answer',contrast_set_id=contrast_set_id,text_style=text_style)

def search_similar_answers(embedding: list[float], *, question_type: str | None, text_style: str = 'stt',
                           exclude_contrast_set_ids: list[str] = (), k: int = 5) -> list[dict]:
    with tx() as cur:
        cur.execute("""SELECT * FROM rag_docs WHERE doc_type='answer' AND embedding IS NOT NULL AND text_style=%s
            AND (%s::text IS NULL OR question_type=%s) AND (contrast_set_id IS NULL OR NOT (contrast_set_id=ANY(%s::text[])))
            ORDER BY embedding <=> %s::vector LIMIT %s""",(text_style,question_type,question_type,list(exclude_contrast_set_ids),str(embedding),k))
        return cur.fetchall()

def current_corpus_version() -> str | None:
    with tx() as cur:
        cur.execute('SELECT corpus_version FROM rag_docs ORDER BY created_at DESC,id DESC LIMIT 1');row=cur.fetchone()
        return row['corpus_version'] if row else None
