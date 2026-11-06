# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성되었습니다.
# OWNER: data-layer (contracts.yaml ownership)
from __future__ import annotations
from pathlib import Path
from uuid import UUID
from datetime import datetime
from app.schemas.api import *
from app.schemas.internal import *

def get_rag_docs(doc_type: str, *, corpus_version: str | None = None, **filters) -> list[dict]:
    """계약에 정의된 get_rag_docs 호출. 구현 담당: data-layer."""
    raise NotImplementedError("data-layer: get_rag_docs")

def get_contrast_set(contrast_set_id: str, text_style: str = "stt") -> list[dict]:
    """계약에 정의된 get_contrast_set 호출. 구현 담당: data-layer."""
    raise NotImplementedError("data-layer: get_contrast_set")

def search_similar_answers(embedding: list[float], *, question_type: str | None, text_style: str = "stt", exclude_contrast_set_ids: list[str] = (), k: int = 5) -> list[dict]:
    """계약에 정의된 search_similar_answers 호출. 구현 담당: data-layer."""
    raise NotImplementedError("data-layer: search_similar_answers")

def current_corpus_version() -> str | None:
    """계약에 정의된 current_corpus_version 호출. 구현 담당: data-layer."""
    raise NotImplementedError("data-layer: current_corpus_version")
