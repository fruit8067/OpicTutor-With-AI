# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성되었습니다.
# 후속 수정: SkipOut·건너뛴 문항 결과 필드는 Claude(Anthropic)의 도움으로 작성되었습니다.
# OWNER: bootstrap (contracts.yaml ownership)
from __future__ import annotations
from datetime import datetime
from uuid import UUID
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

level = Literal['NL', 'NM', 'NH', 'IL', 'IM1', 'IM2', 'IM3', 'IH', 'AL']
base_level = Literal['NL', 'NM', 'NH', 'IL', 'IM', 'IH', 'AL']
session_status = Literal['preparing', 'prepare_failed', 'ready', 'cancelled', 'in_progress', 'submitted', 'grading', 'grading_failed', 'done']
answer_stt_status = Literal['queued', 'processing', 'done', 'rejected', 'failed']
evaluation_status = Literal['queued', 'running', 'done', 'failed']
assessment_status = Literal['assessed', 'insufficient_evidence']
fact_status = Literal['demonstrated', 'not_demonstrated', 'not_observed']
evaluation_role = Literal['scored', 'feedback_only']
task_fulfillment = Literal['fulfilled', 'partial', 'not_fulfilled', 'not_assessable']
example_kind = Literal['correction', 'practice']
im_estimation_status = Literal['provisional', 'insufficient_evidence', 'not_applicable']

class ContractModel(BaseModel):
    model_config = ConfigDict(extra='forbid', from_attributes=True)

class Tier(ContractModel):
    name: str
    color: str

class TtsStatus(ContractModel):
    voice_id: str | None
    assets: int
    missing_pilot: list[str]

class HealthOut(ContractModel):
    ready: bool
    db: Literal['ok', 'error']
    worker_seen_at: datetime | None
    whisper_model: str
    corpus_version: str | None
    tts: TtsStatus

class ScenarioOut(ContractModel):
    scenario_id: str
    label: str
    description: str
    question_count: int

class HostLineOut(ContractModel):
    key: str
    text: str
    audio_url: str | None

class CreateSessionIn(ContractModel):
    client_request_id: str
    scenario_id: str = 'default'
    mic_check_passed: bool
    replaces_session_id: UUID | None = None

class PrepareFailure(ContractModel):
    order_no: int | None
    host_key: str | None
    ref_id: str
    error_code: str

class PrepareProgress(ContractModel):
    total: int
    linked: int
    failures: list[PrepareFailure]

class SessionOut(ContractModel):
    session_id: UUID
    status: session_status
    scenario_id: str
    question_count: int
    current_order_no: int
    all_answered: bool
    prepare: PrepareProgress | None
    latest_evaluation_status: evaluation_status | None
    created_at: datetime
    updated_at: datetime

class QuestionOut(ContractModel):
    order_no: int
    question_id: str
    question_type: str
    is_scored: bool
    text: str
    audio_url: str
    duration_sec: float | None
    replay_count: int
    replay_limit: int

class CurrentQuestionOut(ContractModel):
    session_status: session_status
    total: int
    all_answered: bool
    question: QuestionOut | None
    pending_answer: AnswerOut | None
    host_lines: dict[str, HostLineOut]

class ReplayOut(ContractModel):
    order_no: int
    replay_count: int
    replay_limit: int

class SkipOut(ContractModel):
    order_no: int
    session_status: session_status
    current_order_no: int
    all_answered: bool

class Metrics(ContractModel):
    duration_sec: float
    speech_sec: float
    word_count: int
    wpm: float
    articulation_wpm: float | None
    long_pause_count: int
    observed_filler_per100: float | None
    metrics_version: str

class AnswerOut(ContractModel):
    answer_id: UUID
    order_no: int
    attempt_no: int
    stt_status: answer_stt_status
    reject_reason: str | None
    error_code: str | None
    stt_text: str | None
    metrics: Metrics | None
    session_status: session_status
    current_order_no: int
    all_answered: bool

class Mistake(ContractModel):
    quote: str
    problem: str
    fix: str

class ItemFeedback(ContractModel):
    order_no: int
    evaluation_role: evaluation_role
    task_fulfillment: task_fulfillment
    evidence: list[str] = Field(max_length=3)
    mistakes: list[Mistake] = Field(max_length=5)
    upgrade_tip: str

class FeedbackCard(ContractModel):
    title: str
    why: str
    before: str | None
    after: str
    example_kind: example_kind
    related_order_nos: list[int]
    success_condition: str

class DimensionFeedback(ContractModel):
    summary: str
    evidence_order_nos: list[int]
    limitations: list[str]

class DimensionFeedbackSet(ContractModel):
    functions_tasks: DimensionFeedback
    accuracy: DimensionFeedback
    context_content: DimensionFeedback
    text_type: DimensionFeedback

class QuoteRef(ContractModel):
    order_no: int
    quote: str

class FactEvidence(ContractModel):
    criterion: Literal['functions_tasks', 'accuracy', 'context_content', 'text_type']
    observation: str
    status: fact_status
    order_no: int | None
    quote: str | None

class CoverageEntry(ContractModel):
    name: str
    elicited_order_nos: list[int]
    usable_order_nos: list[int]
    gaps: list[str]

class Coverage(ContractModel):
    functions: list[CoverageEntry]
    time_frames: list[CoverageEntry]
    contexts: list[CoverageEntry]

class SustainedPerformance(ContractModel):
    capability: str
    evidence: list[QuoteRef]
    summary: str

class BreakdownObservation(ContractModel):
    demanded_function: str
    evidence: list[QuoteRef]
    communicative_impact: str
    recovery: str

class UnusableItem(ContractModel):
    order_no: int
    reason: str

class EvaluationScope(ContractModel):
    submitted_order_nos: list[int]
    scored_order_nos: list[int]
    feedback_only_order_nos: list[int]
    usable_order_nos: list[int]
    unusable_items: list[UnusableItem]

class AdditionalTask(ContractModel):
    target_function: str
    reason: str
    suggested_question: str

class EvaluationResult(ContractModel):
    assessment_status: assessment_status
    assessment_basis: Literal['transcript_and_metrics']
    rubric_version: str
    prompt_version: str
    im_rubric_version: str | None
    evaluation_scope: EvaluationScope
    input_issues: list[str]
    base_level: base_level | None
    estimated_level: level | None
    im_estimation_status: im_estimation_status
    provisional_label: str | None
    tier: Tier | None
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
    disclaimer: str

class ResultItemOut(ContractModel):
    order_no: int
    question_id: str
    question_type: str
    question_text: str
    is_scored: bool
    stt_text: str | None
    metrics: Metrics | None
    skipped: bool = False

class ResultOut(ContractModel):
    session_status: session_status
    evaluation_status: evaluation_status | None
    run_no: int | None
    result: EvaluationResult | None
    answers: list[ResultItemOut]
    error_code: str | None
    graded_at: datetime | None

class RegisterIn(ContractModel):
    email: str
    password: str
    nickname: str

class LoginIn(ContractModel):
    email: str
    password: str

class UserOut(ContractModel):
    id: UUID
    email: str
    nickname: str
    created_at: datetime

class AuthOut(ContractModel):
    token: str
    user: UserOut

class LogoutOut(ContractModel):
    ok: bool = True

for _name in ['HealthOut', 'ScenarioOut', 'HostLineOut', 'CreateSessionIn', 'PrepareFailure', 'PrepareProgress', 'SessionOut', 'QuestionOut', 'CurrentQuestionOut', 'ReplayOut', 'Metrics', 'AnswerOut', 'Mistake', 'ItemFeedback', 'FeedbackCard', 'DimensionFeedback', 'DimensionFeedbackSet', 'QuoteRef', 'FactEvidence', 'CoverageEntry', 'Coverage', 'SustainedPerformance', 'BreakdownObservation', 'UnusableItem', 'EvaluationScope', 'AdditionalTask', 'EvaluationResult', 'ResultItemOut', 'ResultOut', 'RegisterIn', 'LoginIn', 'UserOut', 'AuthOut', 'LogoutOut']:
    globals()[_name].model_rebuild()
