# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성되었습니다.
# OWNER: data-layer (contracts.yaml ownership)
import time
from openai import OpenAI, APIConnectionError, APITimeoutError, APIStatusError, RateLimitError, InternalServerError
from app.config import settings
from app.db.ai_requests import log_ai_request

def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts: return []
    client=OpenAI(base_url=settings.EMBED_BASE_URL,api_key=settings.EMBED_API_KEY,max_retries=0,timeout=settings.LLM_TIMEOUT_SEC)
    vectors=[]
    for offset in range(0,len(texts),100):
        batch=texts[offset:offset+100]
        for attempt in range(3):
            started=time.monotonic()
            try:
                try:
                    response=client.embeddings.create(model=settings.EMBED_MODEL,input=batch,dimensions=settings.EMBED_DIM)
                except Exception as exc:
                    if 'dimensions' in str(exc).lower():
                        response=client.embeddings.create(model=settings.EMBED_MODEL,input=batch)
                    else:
                        raise
                has_indices = all(getattr(item, 'index', None) is not None for item in response.data)
                if has_indices:
                    data = sorted(response.data, key=lambda item: item.index)
                    if [item.index for item in data] != list(range(len(batch))):
                        raise ValueError('임베딩 응답 개수 또는 인덱스가 설정과 다릅니다.')
                else:
                    data = response.data
                    if len(data) != len(batch):
                        raise ValueError('임베딩 응답 개수가 설정과 다릅니다.')

                if any(len(item.embedding) != settings.EMBED_DIM for item in data):
                    raise ValueError('임베딩 응답 차원이 설정과 다릅니다.')
                total_tokens = getattr(response.usage, 'total_tokens', None) if getattr(response, 'usage', None) else None
                log_ai_request(job_id=None,purpose='embed',model=settings.EMBED_MODEL,
                    input_tokens=total_tokens,output_tokens=None,latency_ms=int((time.monotonic()-started)*1000),
                    status='ok',error_code=None)
                vectors.extend(item.embedding for item in data)
                break
            except Exception as exc:
                transient=isinstance(exc,(APIConnectionError,APITimeoutError,RateLimitError,InternalServerError)) or (
                    isinstance(exc,APIStatusError) and (exc.status_code in (408,429) or exc.status_code>=500))
                log_ai_request(job_id=None,purpose='embed',model=settings.EMBED_MODEL,input_tokens=None,output_tokens=None,
                    latency_ms=int((time.monotonic()-started)*1000),status='error',
                    error_code='EMBED_TRANSIENT' if transient else 'EMBED_ERROR')
                if transient and attempt<2:
                    time.sleep(2**attempt)
                    continue
                raise
    return vectors
