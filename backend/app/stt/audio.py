# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성되었습니다.
# OWNER: worker-stt (contracts.yaml ownership)
from __future__ import annotations
from pathlib import Path
from uuid import UUID
from datetime import datetime
from app.schemas.api import *
from app.schemas.internal import *

def probe_audio(path: Path) -> AudioProbe:
    """계약에 정의된 probe_audio 호출. 구현 담당: worker-stt."""
    raise NotImplementedError("worker-stt: probe_audio")
