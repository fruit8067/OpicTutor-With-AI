# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성되었습니다.
# OWNER: session-api (contracts.yaml ownership)
from __future__ import annotations
from pathlib import Path
from uuid import UUID
from datetime import datetime
from app.schemas.api import *
from app.schemas.internal import *

def list_scenarios() -> list[ScenarioOut]:
    """계약에 정의된 list_scenarios 호출. 구현 담당: session-api."""
    raise NotImplementedError("session-api: list_scenarios")
