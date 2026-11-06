# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성되었습니다.
# OWNER: data-layer (contracts.yaml ownership)
from types import SimpleNamespace as NS
import pytest
import httpx
from app.llm import embeddings


def test_embedding_batches_order_dimension_and_logging(monkeypatch):
    requests, logs = [], []
    def create(**kwargs):
        requests.append(kwargs)
        return NS(data=[NS(index=i,embedding=[float(i)]*3) for i in reversed(range(len(kwargs['input'])))],usage=NS(total_tokens=42))
    monkeypatch.setattr(embeddings,'OpenAI',lambda **kwargs:NS(embeddings=NS(create=create)))
    monkeypatch.setattr(embeddings,'log_ai_request',lambda **kwargs:logs.append(kwargs))
    monkeypatch.setattr(embeddings.settings,'EMBED_DIM',3)
    vectors=embeddings.embed_texts(['private answer']*101)
    assert [len(r['input']) for r in requests]==[100,1]
    assert vectors[1]==[1.0]*3 and len(vectors)==101
    assert all('text' not in entry and 'input' not in entry for entry in logs)
    assert sum(entry['input_tokens'] for entry in logs)==84
    monkeypatch.setattr(embeddings.settings,'EMBED_DIM',4)
    with pytest.raises(ValueError): embeddings.embed_texts(['private'])
    assert logs[-1]['status']=='error'


def test_duplicate_embedding_indices_do_not_attach_vectors_to_wrong_documents(monkeypatch):
    logs=[]
    monkeypatch.setattr(embeddings.settings,'EMBED_DIM',3)
    monkeypatch.setattr(embeddings,'log_ai_request',lambda **kwargs:logs.append(kwargs))
    response=NS(data=[NS(index=0,embedding=[1.0]*3),NS(index=0,embedding=[2.0]*3)],usage=NS(total_tokens=2))
    monkeypatch.setattr(embeddings,'OpenAI',lambda **kwargs:NS(embeddings=NS(create=lambda **options:response)))
    with pytest.raises(ValueError): embeddings.embed_texts(['first document','second document'])
    assert len(logs)==1 and logs[0]['error_code']=='EMBED_ERROR'


@pytest.mark.parametrize('status,attempts',[(408,3),(503,3),(401,1)])
def test_http_timeouts_retry_but_authentication_failures_do_not(monkeypatch,status,attempts):
    real_client=embeddings.OpenAI
    calls=[];logs=[];waits=[]
    def respond(request):
        calls.append(request.url.path)
        return httpx.Response(status,json={'error':{'message':'provider fixture failure'}})
    monkeypatch.setattr(embeddings.settings,'EMBED_API_KEY','local-fixture-no-network')
    monkeypatch.setattr(embeddings.settings,'EMBED_BASE_URL','https://embedding.example.invalid/v1')
    monkeypatch.setattr(embeddings,'OpenAI',lambda **kwargs:real_client(**kwargs,
        http_client=httpx.Client(transport=httpx.MockTransport(respond))))
    monkeypatch.setattr(embeddings,'log_ai_request',lambda **kwargs:logs.append(kwargs))
    monkeypatch.setattr(embeddings.time,'sleep',lambda seconds:waits.append(seconds))
    with pytest.raises(Exception): embeddings.embed_texts(['private transcript fixture'])
    assert len(calls)==len(logs)==attempts
    assert waits==([1,2] if attempts==3 else [])
    assert all(row['error_code']==('EMBED_TRANSIENT' if attempts==3 else 'EMBED_ERROR') for row in logs)
    assert all('private transcript' not in str(row) for row in logs)
