# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성되었습니다.
# OWNER: tts-host (contracts.yaml ownership)
from __future__ import annotations
from pathlib import Path
from uuid import UUID
from datetime import datetime
from app.schemas.api import *
from app.schemas.internal import *

def text_hash(text: str) -> str:
    """계약에 정의된 text_hash 호출. 구현 담당: tts-host."""
    raise NotImplementedError("tts-host: text_hash")

def active_voice_id() -> str | None:
    """계약에 정의된 active_voice_id 호출. 구현 담당: tts-host."""
    raise NotImplementedError("tts-host: active_voice_id")

def tts_url(file_path: str) -> str:
    """계약에 정의된 tts_url 호출. 구현 담당: tts-host."""
    raise NotImplementedError("tts-host: tts_url")

def tts_status() -> dict:
    """계약에 정의된 tts_status 호출. 구현 담당: tts-host."""
    raise NotImplementedError("tts-host: tts_status")
