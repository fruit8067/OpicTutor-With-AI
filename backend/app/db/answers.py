# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성되었습니다.
# OWNER: data-layer (contracts.yaml ownership)
from __future__ import annotations
from pathlib import Path
from uuid import UUID
from datetime import datetime
from app.schemas.api import *
from app.schemas.internal import *

def create_answer(*, session_id: UUID, order_no: int, client_request_id: str, audio_path: str, audio_mime: str, audio_bytes: int, audio_hash: str, client_duration_ms: int, answer_id: UUID) -> tuple[dict, bool]:
    """계약에 정의된 create_answer 호출. 구현 담당: data-layer."""
    raise NotImplementedError("data-layer: create_answer")

def get_answer(answer_id: UUID) -> dict | None:
    """계약에 정의된 get_answer 호출. 구현 담당: data-layer."""
    raise NotImplementedError("data-layer: get_answer")

def mark_stt_processing(answer_id: UUID) -> bool:
    """계약에 정의된 mark_stt_processing 호출. 구현 담당: data-layer."""
    raise NotImplementedError("data-layer: mark_stt_processing")

def complete_stt(answer_id: UUID, *, text: str, timestamps: list[dict], metrics: dict, stt_version: str) -> dict:
    """계약에 정의된 complete_stt 호출. 구현 담당: data-layer."""
    raise NotImplementedError("data-layer: complete_stt")

def reject_stt(answer_id: UUID, reason: str) -> None:
    """계약에 정의된 reject_stt 호출. 구현 담당: data-layer."""
    raise NotImplementedError("data-layer: reject_stt")

def fail_stt(answer_id: UUID, error_code: str) -> None:
    """계약에 정의된 fail_stt 호출. 구현 담당: data-layer."""
    raise NotImplementedError("data-layer: fail_stt")

def retry_stt(answer_id: UUID) -> None:
    """계약에 정의된 retry_stt 호출. 구현 담당: data-layer."""
    raise NotImplementedError("data-layer: retry_stt")
