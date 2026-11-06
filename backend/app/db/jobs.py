# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성되었습니다.
# OWNER: data-layer (contracts.yaml ownership)
from __future__ import annotations
from pathlib import Path
from uuid import UUID
from datetime import datetime
from app.schemas.api import *
from app.schemas.internal import *

def claim_job(types: list[str], worker_id: str, lease_sec: int) -> dict | None:
    """계약에 정의된 claim_job 호출. 구현 담당: data-layer."""
    raise NotImplementedError("data-layer: claim_job")

def heartbeat_job(job_id: UUID, worker_id: str, lease_sec: int) -> bool:
    """계약에 정의된 heartbeat_job 호출. 구현 담당: data-layer."""
    raise NotImplementedError("data-layer: heartbeat_job")

def complete_job(job_id: UUID, worker_id: str) -> None:
    """계약에 정의된 complete_job 호출. 구현 담당: data-layer."""
    raise NotImplementedError("data-layer: complete_job")

def fail_job(job_id: UUID, worker_id: str, *, error_code: str, retryable: bool, detail: dict | None = None) -> str:
    """계약에 정의된 fail_job 호출. 구현 담당: data-layer."""
    raise NotImplementedError("data-layer: fail_job")

def recover_expired_jobs() -> int:
    """계약에 정의된 recover_expired_jobs 호출. 구현 담당: data-layer."""
    raise NotImplementedError("data-layer: recover_expired_jobs")

def last_job_activity() -> datetime | None:
    """계약에 정의된 last_job_activity 호출. 구현 담당: data-layer."""
    raise NotImplementedError("data-layer: last_job_activity")
