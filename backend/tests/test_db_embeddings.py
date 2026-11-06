# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성되었습니다.
# OWNER: data-layer (contracts.yaml ownership)
from types import SimpleNamespace as NS
import pytest
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
