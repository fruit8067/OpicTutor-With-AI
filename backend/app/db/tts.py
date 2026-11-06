# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성되었습니다.
# OWNER: data-layer (contracts.yaml ownership)
from __future__ import annotations
from pathlib import Path
from uuid import UUID
from datetime import datetime
from app.schemas.api import *
from app.schemas.internal import *

def upsert_tts_asset(*, kind: str, ref_id: str, text_hash: str, voice_id: str, settings_version: str, file_path: str, duration_sec: float | None, status: str = "available") -> UUID:
    """계약에 정의된 upsert_tts_asset 호출. 구현 담당: data-layer."""
    raise NotImplementedError("data-layer: upsert_tts_asset")

def find_tts_asset(*, kind: str, ref_id: str, text_hash: str, voice_id: str) -> dict | None:
    """계약에 정의된 find_tts_asset 호출. 구현 담당: data-layer."""
    raise NotImplementedError("data-layer: find_tts_asset")

def complete_prepare(session_id: UUID, attempt: int, question_links: dict[int, UUID], host_links: dict[str, UUID]) -> bool:
    """계약에 정의된 complete_prepare 호출. 구현 담당: data-layer."""
    raise NotImplementedError("data-layer: complete_prepare")

def fail_prepare(session_id: UUID, attempt: int, errors: list[dict]) -> bool:
    """계약에 정의된 fail_prepare 호출. 구현 담당: data-layer."""
    raise NotImplementedError("data-layer: fail_prepare")
