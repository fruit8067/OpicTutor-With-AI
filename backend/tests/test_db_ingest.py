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
        return [[1.0]+[0.0]*(settings.EMBED_DIM-1) for _ in texts]
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
        vector=[1.0]+[0.0]*(settings.EMBED_DIM-1)
        assert db.search_similar_answers(vector,question_type='description',k=1)[0]['id']==prefix+'-answer'
        assert not db.search_similar_answers(vector,question_type='description',exclude_contrast_set_ids=[prefix])
        # Equal dimensions do not make embeddings from different models compatible.
        monkeypatch.setattr(settings,'EMBED_MODEL','fixture-other-3072-model')
        assert not db.search_similar_answers(vector,question_type='description')
        calls.clear()
        ingest_rag.ingest()
        assert len(calls[0])==2
        calls.clear()
        ingest_rag.ingest()
        assert all(not batch for batch in calls)
        assert db.search_similar_answers(vector,question_type='description',k=1)[0]['id']==prefix+'-answer'
        # Changing provider must also invalidate cached vectors, without storing its URL/key.
        monkeypatch.setattr(settings,'EMBED_BASE_URL','https://embedding.example.invalid/v1')
        assert not db.search_similar_answers(vector,question_type='description')
        calls.clear()
        ingest_rag.ingest()
        assert len(calls[0])==2
        row=db.get_rag_docs('question',corpus_version=prefix)[0]
        assert row['metadata']['_embedding_profile']['dimensions']==3072
        assert 'example.invalid' not in json.dumps(row['metadata'])
        with pytest.raises(ValueError,match='차원'): db.search_similar_answers([1.0],question_type=None)
    finally:
        with tx() as cur: cur.execute('DELETE FROM rag_docs WHERE id=ANY(%s)',(ids,))


def test_failed_second_batch_resumes_only_uncommitted_embeddings(monkeypatch):
    if not db.ping(): pytest.skip('로컬 PostgreSQL/pgvector 미실행')
    db.init_db()
    prefix='resume-'+uuid4().hex
    docs=[{'id':f'{prefix}-{i}','doc_type':'question','text':f'resume fixture {i}'} for i in range(101)]
    monkeypatch.setattr(ingest_rag,'load_documents',lambda:(prefix,docs))
    monkeypatch.setattr(settings,'EMBED_API_KEY','local-test-no-network')
    calls=[]
    def embed(texts):
        calls.append(len(texts))
        if len(calls)==2: raise RuntimeError('second batch failure fixture')
        return [[1.0]+[0.0]*3071 for _ in texts]
    monkeypatch.setattr(ingest_rag,'embed_texts',embed)
    try:
        with pytest.raises(RuntimeError,match='second batch'): ingest_rag.ingest()
        with tx() as cur:
            cur.execute('SELECT count(*) AS n FROM rag_docs WHERE corpus_version=%s',(prefix,))
            assert cur.fetchone()['n']==100
        calls.clear()
        monkeypatch.setattr(ingest_rag,'embed_texts',lambda texts:calls.append(len(texts)) or [[1.0]+[0.0]*3071 for _ in texts])
        ingest_rag.ingest()
        assert [n for n in calls if n]==[1]
    finally:
        with tx() as cur: cur.execute('DELETE FROM rag_docs WHERE corpus_version=%s',(prefix,))
