# AI-assisted: 평가 계약 로드는 OpenAI Codex의 도움으로 작성했습니다.
# OWNER: grader (contracts.yaml ownership)
from functools import lru_cache
from pathlib import Path
import json
import os
import yaml
import tiktoken


@lru_cache(maxsize=1)
def contract():
    return yaml.safe_load((Path(__file__).resolve().parents[3]/'agents/contracts.yaml').read_text(encoding='utf-8'))


@lru_cache(maxsize=1)
def encoding():
    # 미등록 제공자 모델은 cl100k_base로 근사한다. 실제 Pickle 토큰 수/한도는 제공자 사용량으로 확인해야 한다.
    from app.config import settings
    try: return tiktoken.encoding_for_model(os.getenv('LLM_MODEL') or settings.LLM_MODEL)
    except KeyError: return tiktoken.get_encoding('cl100k_base')


def token_count(value):
    text=value if isinstance(value,str) else json.dumps(value,ensure_ascii=False,sort_keys=True,default=str)
    return len(encoding().encode(text,disallowed_special=()))
