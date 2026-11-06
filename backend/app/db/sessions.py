# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성되었습니다.
# OWNER: data-layer (contracts.yaml ownership)
from __future__ import annotations
from pathlib import Path
from uuid import UUID
from datetime import datetime
from app.schemas.api import *
from app.schemas.internal import *

def create_session(*, client_request_id: str | None, scenario_id: str, settings_json: dict, questions: list[SessionQuestionIn], replaces_session_id: UUID | None) -> tuple[UUID, bool]:
    """계약에 정의된 create_session 호출. 구현 담당: data-layer."""
    raise NotImplementedError("data-layer: create_session")

def get_session(session_id: UUID) -> SessionRow | None:
    """계약에 정의된 get_session 호출. 구현 담당: data-layer."""
    raise NotImplementedError("data-layer: get_session")

def list_session_questions(session_id: UUID) -> list[dict]:
    """계약에 정의된 list_session_questions 호출. 구현 담당: data-layer."""
    raise NotImplementedError("data-layer: list_session_questions")

def get_session_question(session_id: UUID, order_no: int) -> dict | None:
    """계약에 정의된 get_session_question 호출. 구현 담당: data-layer."""
    raise NotImplementedError("data-layer: get_session_question")

def retry_prepare(session_id: UUID) -> int:
    """계약에 정의된 retry_prepare 호출. 구현 담당: data-layer."""
    raise NotImplementedError("data-layer: retry_prepare")

def cancel_session(session_id: UUID) -> str:
    """계약에 정의된 cancel_session 호출. 구현 담당: data-layer."""
    raise NotImplementedError("data-layer: cancel_session")

def start_session(session_id: UUID) -> SessionRow:
    """계약에 정의된 start_session 호출. 구현 담당: data-layer."""
    raise NotImplementedError("data-layer: start_session")

def increment_replay(session_id: UUID, order_no: int, limit: int) -> int:
    """계약에 정의된 increment_replay 호출. 구현 담당: data-layer."""
    raise NotImplementedError("data-layer: increment_replay")
