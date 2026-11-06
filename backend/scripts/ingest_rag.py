# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성되었습니다.
# OWNER: data-layer (contracts.yaml ownership)
"""100개씩 커밋하므로 중단 후 같은 명령으로 재개할 수 있다."""
import argparse
import json
from collections import Counter
from psycopg.types.json import Jsonb
from app.config import settings
from app.db.pool import tx
from app.llm.embeddings import embed_texts

FIELDS=('id','doc_type','question_id','question_type','level','level_rank','contrast_set_id','text_style','text')

def load_documents():
    root=settings.RAG_BUILD_DIR
    version=(root/'VERSION').read_text(encoding='utf-8').strip()
    if not version: raise ValueError('코퍼스 VERSION이 비어 있습니다.')
    docs=[]
    for filename,kind in [('rubrics','rubric'),('upgrade_patterns','upgrade_pattern'),('questions','question'),('answers','answer')]:
        for line in (root/(filename+'.jsonl')).read_text(encoding='utf-8').splitlines():
            if not line.strip(): continue
            doc=json.loads(line)
            if doc.get('doc_type')!=kind or not isinstance(doc.get('text'),str) or not doc['text'].strip():
                raise ValueError('코퍼스 문서 형식이 올바르지 않습니다: '+str(doc.get('id')))
            docs.append(doc)
    if len({d['id'] for d in docs})!=len(docs): raise ValueError('코퍼스 문서 ID 중복')
    return version,docs

def ingest(dry_run=False):
    if settings.EMBED_DIM != 1536:
        raise ValueError('계약 v3 DB 벡터 차원은 1536입니다. EMBED_DIM을 확인하세요.')
    version,docs=load_documents()
    with tx() as cur:
        cur.execute('SELECT id,text,corpus_version,embedding IS NOT NULL AS embedded FROM rag_docs')
        old={row['id']:row for row in cur.fetchall()}
    def needs_embedding(doc):
        previous=old.get(doc['id'])
        return doc['doc_type'] in ('question','answer') and (not previous or not previous['embedded']
            or previous['text']!=doc['text'] or previous['corpus_version']!=version)
    expected=sum(needs_embedding(d) for d in docs)
    print(f'corpus_version={version}, 예상 임베딩={expected}, 전체={len(docs)}')
    if dry_run: return
    if expected and not settings.EMBED_API_KEY: raise ValueError('EMBED_API_KEY를 backend/.env에 설정하세요.')
    for offset in range(0,len(docs),100):
        batch=docs[offset:offset+100]
        pending=[d for d in batch if needs_embedding(d)]
        vectors=dict(zip((d['id'] for d in pending),embed_texts([d['text'] for d in pending])))
        with tx() as cur:
            for doc in batch:
                vector=vectors.get(doc['id'])
                values=[doc.get(field) for field in FIELDS]
                meta={k:v for k,v in doc.items() if k not in FIELDS}
                cur.execute("""INSERT INTO rag_docs(id,doc_type,question_id,question_type,level,level_rank,
                    contrast_set_id,text_style,text,metadata,corpus_version,embedding)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::vector)
                    ON CONFLICT(id) DO UPDATE SET doc_type=excluded.doc_type,question_id=excluded.question_id,
                    question_type=excluded.question_type,level=excluded.level,level_rank=excluded.level_rank,
                    contrast_set_id=excluded.contrast_set_id,text_style=excluded.text_style,text=excluded.text,
                    metadata=excluded.metadata,corpus_version=excluded.corpus_version,created_at=now(),
                    embedding=CASE WHEN excluded.doc_type IN ('question','answer')
                        THEN COALESCE(excluded.embedding,rag_docs.embedding) ELSE NULL END""",
                    (*values,Jsonb(meta),version,str(vector) if vector is not None else None))
        print(f'저장: {min(offset+100,len(docs))}/{len(docs)}')
    print(dict(Counter(d['doc_type'] for d in docs)))

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--dry-run',action='store_true')
    args=parser.parse_args()
    try: ingest(args.dry_run)
    except (OSError,ValueError) as exc: parser.exit(1,str(exc)+'\n')

if __name__=='__main__': main()
