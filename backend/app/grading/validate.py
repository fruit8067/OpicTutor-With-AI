# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성되었습니다.
# OWNER: grader (contracts.yaml ownership)
from __future__ import annotations
from pathlib import Path
from uuid import UUID
from datetime import datetime
from app.schemas.api import *
from app.schemas.internal import *

def precheck_snapshot(snapshot: list[dict]) -> None:
    """계약에 정의된 precheck_snapshot 호출. 구현 담당: grader."""
    raise NotImplementedError("grader: precheck_snapshot")

def validate_output(raw: EvaluationLLMOutput, snapshot: list[dict]) -> EvaluationResult:
    """계약에 정의된 validate_output 호출. 구현 담당: grader."""
    raise NotImplementedError("grader: validate_output")
