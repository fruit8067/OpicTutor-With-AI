# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성되었습니다.
# OWNER: data-layer (contracts.yaml ownership)
from __future__ import annotations
from pathlib import Path
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel
from app.schemas.api import *
from app.schemas.internal import *

def embed_texts(texts: list[str]) -> list[list[float]]:
    """계약에 정의된 embed_texts 호출. 구현 담당: data-layer."""
    raise NotImplementedError("data-layer: embed_texts")
