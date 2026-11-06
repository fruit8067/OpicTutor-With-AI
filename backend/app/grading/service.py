# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성되었습니다.
# OWNER: grader (contracts.yaml ownership)
from __future__ import annotations
from pathlib import Path
from uuid import UUID
from datetime import datetime
from app.schemas.api import *
from app.schemas.internal import *

def evaluate_exam(snapshot: list[dict], *, exclude_contrast_set_ids: list[str] = (), job_id: UUID | None = None) -> tuple[EvaluationResult, dict]:
    """계약에 정의된 evaluate_exam 호출. 구현 담당: grader."""
    raise NotImplementedError("grader: evaluate_exam")
