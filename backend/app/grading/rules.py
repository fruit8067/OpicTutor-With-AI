# AI-assisted: 평가 계약 로드는 OpenAI Codex의 도움으로 작성했습니다.
# OWNER: grader (contracts.yaml ownership)
from functools import lru_cache
from pathlib import Path
import json
import yaml
import tiktoken


@lru_cache(maxsize=1)
def contract():
    return yaml.safe_load((Path(__file__).resolve().parents[3]/'agents/contracts.yaml').read_text(encoding='utf-8'))


@lru_cache(maxsize=1)
def encoding():
    # OpenAI 호환 제공자의 알려지지 않은 모델에도 같은 보수적 회귀 토크나이저를 사용한다.
    from app.config import settings
    try: return tiktoken.encoding_for_model(settings.LLM_MODEL)
    except KeyError: return tiktoken.get_encoding('cl100k_base')


def token_count(value):
    text=value if isinstance(value,str) else json.dumps(value,ensure_ascii=False,sort_keys=True,default=str)
    return len(encoding().encode(text,disallowed_special=()))
