# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성되었습니다.
# OWNER: data-layer (contracts.yaml ownership)
from __future__ import annotations
from pathlib import Path
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel
from app.schemas.api import *
from app.schemas.internal import *

def seed_session(status: str = "ready", scenario_id: str = "default", link_tts: bool = False) -> UUID:
    """계약에 정의된 seed_session 호출. 구현 담당: data-layer."""
    raise NotImplementedError("data-layer: seed_session")

def seed_queued_answer(session_id: UUID, audio_path: str, order_no: int | None = None) -> UUID:
    """계약에 정의된 seed_queued_answer 호출. 구현 담당: data-layer."""
    raise NotImplementedError("data-layer: seed_queued_answer")

def seed_grading_session(level: str = "IM2", text_style: str = "stt") -> tuple[UUID, UUID]:
    """계약에 정의된 seed_grading_session 호출. 구현 담당: data-layer."""
    raise NotImplementedError("data-layer: seed_grading_session")
