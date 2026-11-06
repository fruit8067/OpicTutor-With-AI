# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성되었습니다.
# OWNER: bootstrap (contracts.yaml ownership)
from __future__ import annotations
from typing import Any, TypedDict
from pydantic import Field
from app.schemas.api import *

class SessionQuestionIn(ContractModel):
    order_no: int = Field(ge=1, le=8)
    question_id: str
    question_version: str
    question_text: str
    question_type: str
    is_scored: bool
    target_functions: list[str]
    target_time_frames: list[str]
    context_scope: list[str]

# DB 행은 psycopg dict_row와 동일한 매핑이다.
SessionRow = dict[str, Any]
AnswerRow = dict[str, Any]
JobRow = dict[str, Any]

class WordTS(ContractModel):
    word: str
    start: float
    end: float

class AudioProbe(ContractModel):
    duration_sec: float
    sample_rate: int
    rms_dbfs: float
    ok: bool
    reason: str | None

class SttResult(ContractModel):
    text: str
    words: list[WordTS]
    duration_sec: float
    speech_segments: list[tuple[float, float]]

class EvidenceBundle(ContractModel):
    docs: list[dict] = Field(default_factory=list)
    corpus_version: str | None = None
    retrieved_doc_ids: list[str] = Field(default_factory=list)

class EvaluationLLMOutput(ContractModel):
    assessment_basis: Literal['transcript_and_metrics']
    rubric_version: str
    prompt_version: str
    im_rubric_version: str | None
    evaluation_scope: EvaluationScope
    input_issues: list[str]
    base_level: base_level | None
    estimated_level: level | None
    im_estimation_status: im_estimation_status
    headline: str
    grade_rationale: str
    dimension_feedback: DimensionFeedbackSet
    coverage: Coverage
    fact_evidence: list[FactEvidence]
    sustained_performance: list[SustainedPerformance]
    breakdown_observations: list[BreakdownObservation]
    fluency_observations: str
    why_this_level: str
    why_not_lower: str
    next_level_gap: str
    borderline_levels: list[level]
    uncertainty_reasons: list[str]
    items: list[ItemFeedback]
    feedback_cards: list[FeedbackCard] = Field(max_length=5)
    additional_tasks_needed: list[AdditionalTask]
    limitations: list[str]
    insufficient_reason: str | None
    status: assessment_status
