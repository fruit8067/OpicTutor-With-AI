# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성되었습니다.
# OWNER: data-layer (contracts.yaml ownership)
import json
from uuid import uuid4
import pytest
from app import db
from app.config import settings
from app.db.pool import tx
from scripts import ingest_rag


def test_ingest_resume_metadata_and_vector_search(tmp_path,monkeypatch):
    if not db.ping(): pytest.skip('로컬 PostgreSQL/pgvector 미실행')
    db.init_db()
    prefix='fixture-'+uuid4().hex
    docs=[dict(id=prefix+'-'+kind,doc_type=kind,text='example '+kind,
        question_id=prefix,question_type='description',level='IM2' if kind=='answer' else None,
        level_rank=5 if kind=='answer' else None,contrast_set_id=prefix,text_style='stt',topic='fixture')
        for kind in ['rubric','upgrade_pattern','question','answer']]
    for filename,doc in zip(['rubrics','upgrade_patterns','questions','answers'],docs):
        (tmp_path/(filename+'.jsonl')).write_text(json.dumps(doc)+'\n',encoding='utf-8')
    (tmp_path/'VERSION').write_text(prefix,encoding='utf-8')
    monkeypatch.setattr(settings,'RAG_BUILD_DIR',tmp_path)
    monkeypatch.setattr(settings,'EMBED_API_KEY','test-no-network')
    calls=[]
    def embed(texts):
        calls.append(texts)
        return [[1.0]+[0.0]*1535 for _ in texts]
    monkeypatch.setattr(ingest_rag,'embed_texts',embed)
    ids=[d['id'] for d in docs]
    try:
        ingest_rag.ingest(dry_run=True)
        assert not calls
        ingest_rag.ingest()
        assert len(calls[0])==2
        calls.clear()
        ingest_rag.ingest()
        assert all(not batch for batch in calls)
        result=db.get_rag_docs('question',corpus_version=prefix,topic='fixture')
        assert result[0]['id']==prefix+'-question'
        assert db.current_corpus_version()==prefix
        assert db.get_contrast_set(prefix)[0]['id']==prefix+'-answer'
        assert db.search_similar_answers([1.0]+[0.0]*1535,question_type='description',k=1)[0]['id']==prefix+'-answer'
        assert not db.search_similar_answers([1.0]+[0.0]*1535,question_type='description',exclude_contrast_set_ids=[prefix])
    finally:
        with tx() as cur: cur.execute('DELETE FROM rag_docs WHERE id=ANY(%s)',(ids,))
