"""
LLM 호출 래퍼 — 생성 모델과 평가 모델을 환경변수로 분리해 '같은 모델이 자기 답을 채점'하지 않게 한다.
  GEN_MODEL   : 답변 생성용 (기본 claude-sonnet-5-5)
  JUDGE_MODEL : 블라인드 평가용 (기본 claude-haiku-5-5 — 생성 모델과 다르게 둘 것)
  ANTHROPIC_API_KEY 필요.  pip install anthropic pyyaml

AI-assisted: Claude(Anthropic)의 도움으로 작성.
"""
import os

from anthropic import Anthropic

_client = None


def chat(system: str, user: str, model_env: str, default: str, max_tokens: int = 4000, temperature: float = 0.7) -> str:
    global _client
    _client = _client or Anthropic()
    resp = _client.messages.create(
        model=os.getenv(model_env, default),
        max_tokens=max_tokens,
        temperature=temperature,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(b.text for b in resp.content if b.type == "text")


def gen(system, user, **kw):
    return chat(system, user, "GEN_MODEL", "claude-sonnet-5-5", **kw)


def judge(system, user, **kw):
    return chat(system, user, "JUDGE_MODEL", "claude-haiku-5-5", temperature=0, **kw)
