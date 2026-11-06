# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성되었습니다.
# OWNER: data-layer (contracts.yaml ownership)
from __future__ import annotations
from pathlib import Path
from uuid import UUID
from datetime import datetime
from app.schemas.api import *
from app.schemas.internal import *

def log_ai_request(*, job_id: UUID | None, purpose: str, model: str, input_tokens: int | None, output_tokens: int | None, latency_ms: int | None, status: str, error_code: str | None) -> None:
    """계약에 정의된 log_ai_request 호출. 구현 담당: data-layer."""
    raise NotImplementedError("data-layer: log_ai_request")

def count_ai_requests(purpose: str, since: datetime | None = None) -> int:
    """계약에 정의된 count_ai_requests 호출. 구현 담당: data-layer."""
    raise NotImplementedError("data-layer: count_ai_requests")
