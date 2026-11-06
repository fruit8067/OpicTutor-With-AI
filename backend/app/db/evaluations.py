# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성되었습니다.
# OWNER: data-layer (contracts.yaml ownership)
from __future__ import annotations
from pathlib import Path
from uuid import UUID
from datetime import datetime
from app.schemas.api import *
from app.schemas.internal import *

def submit_session(session_id: UUID) -> UUID:
    """계약에 정의된 submit_session 호출. 구현 담당: data-layer."""
    raise NotImplementedError("data-layer: submit_session")

def create_regrade(session_id: UUID) -> UUID:
    """계약에 정의된 create_regrade 호출. 구현 담당: data-layer."""
    raise NotImplementedError("data-layer: create_regrade")

def get_evaluation(evaluation_id: UUID) -> dict | None:
    """계약에 정의된 get_evaluation 호출. 구현 담당: data-layer."""
    raise NotImplementedError("data-layer: get_evaluation")

def get_latest_evaluation(session_id: UUID) -> dict | None:
    """계약에 정의된 get_latest_evaluation 호출. 구현 담당: data-layer."""
    raise NotImplementedError("data-layer: get_latest_evaluation")

def load_exam_snapshot(session_id: UUID, selected_answer_ids: list[UUID]) -> list[dict]:
    """계약에 정의된 load_exam_snapshot 호출. 구현 담당: data-layer."""
    raise NotImplementedError("data-layer: load_exam_snapshot")

def mark_evaluation_running(evaluation_id: UUID) -> bool:
    """계약에 정의된 mark_evaluation_running 호출. 구현 담당: data-layer."""
    raise NotImplementedError("data-layer: mark_evaluation_running")

def finish_evaluation(evaluation_id: UUID, *, result: dict, assessment_status: str, base_level: str | None, estimated_level: str | None, im_estimation_status: str, model: str, prompt_version: str, rubric_version: str, im_rubric_version: str, corpus_version: str, retrieved_doc_ids: list[str]) -> bool:
    """계약에 정의된 finish_evaluation 호출. 구현 담당: data-layer."""
    raise NotImplementedError("data-layer: finish_evaluation")

def fail_evaluation(evaluation_id: UUID, error_code: str, error_detail: dict | None) -> bool:
    """계약에 정의된 fail_evaluation 호출. 구현 담당: data-layer."""
    raise NotImplementedError("data-layer: fail_evaluation")
