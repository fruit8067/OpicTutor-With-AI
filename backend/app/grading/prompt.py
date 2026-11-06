# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성되었습니다.
# OWNER: grader (contracts.yaml ownership)
from __future__ import annotations
from pathlib import Path
from uuid import UUID
from datetime import datetime
from app.schemas.api import *
from app.schemas.internal import *

def load_system_prompt() -> tuple[str, dict]:
    """계약에 정의된 load_system_prompt 호출. 구현 담당: grader."""
    raise NotImplementedError("grader: load_system_prompt")

def build_messages(snapshot: list[dict], evidence: EvidenceBundle) -> list[dict]:
    """계약에 정의된 build_messages 호출. 구현 담당: grader."""
    raise NotImplementedError("grader: build_messages")
