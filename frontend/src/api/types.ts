// AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성되었습니다.
// 후속 수정: SkipOut·건너뛴 문항 결과 필드는 Claude(Anthropic)의 도움으로 작성되었습니다.
// OWNER: bootstrap (contracts.yaml ownership)
export type level = "NL" | "NM" | "NH" | "IL" | "IM1" | "IM2" | "IM3" | "IH" | "AL";
export type base_level = "NL" | "NM" | "NH" | "IL" | "IM" | "IH" | "AL";
export type session_status = "preparing" | "prepare_failed" | "ready" | "cancelled" | "in_progress" | "submitted" | "grading" | "grading_failed" | "done";
export type answer_stt_status = "queued" | "processing" | "done" | "rejected" | "failed";
export type evaluation_status = "queued" | "running" | "done" | "failed";
export type assessment_status = "assessed" | "insufficient_evidence";
export type fact_status = "demonstrated" | "not_demonstrated" | "not_observed";
export type evaluation_role = "scored" | "feedback_only";
export type task_fulfillment = "fulfilled" | "partial" | "not_fulfilled" | "not_assessable";
export type example_kind = "correction" | "practice";
export type im_estimation_status = "provisional" | "insufficient_evidence" | "not_applicable";

export interface HealthOut {
  ready: boolean;
  db: "ok" | "error";
  worker_seen_at: string | null;
  whisper_model: string;
  corpus_version: string | null;
  tts: { voice_id: string | null; assets: number; missing_pilot: (string)[] };
}

export interface ScenarioOut {
  scenario_id: string;
  label: string;
  description: string;
  question_count: number;
}

export interface HostLineOut {
  key: string;
  text: string;
  audio_url: string | null;
}

export interface CreateSessionIn {
  client_request_id: string;
  scenario_id?: string;
  mic_check_passed: boolean;
  replaces_session_id?: string | null;
}

export interface PrepareFailure {
  order_no: number | null;
  host_key: string | null;
  ref_id: string;
  error_code: string;
}

export interface PrepareProgress {
  total: number;
  linked: number;
  failures: (PrepareFailure)[];
}

export interface SessionOut {
  session_id: string;
  status: session_status;
  scenario_id: string;
  question_count: number;
  current_order_no: number;
  all_answered: boolean;
  prepare: PrepareProgress | null;
  latest_evaluation_status: evaluation_status | null;
  created_at: string;
  updated_at: string;
}

export interface QuestionOut {
  order_no: number;
  question_id: string;
  question_type: string;
  is_scored: boolean;
  text: string;
  audio_url: string;
  duration_sec: number | null;
  replay_count: number;
  replay_limit: number;
}

export interface CurrentQuestionOut {
  session_status: session_status;
  total: number;
  all_answered: boolean;
  question: QuestionOut | null;
  pending_answer: AnswerOut | null;
  host_lines: Record<string, HostLineOut>;
}

export interface ReplayOut {
  order_no: number;
  replay_count: number;
  replay_limit: number;
}

export interface SkipOut {
  order_no: number;
  session_status: session_status;
  current_order_no: number;
  all_answered: boolean;
}

export interface Metrics {
  duration_sec: number;
  speech_sec: number;
  word_count: number;
  wpm: number;
  articulation_wpm: number | null;
  long_pause_count: number;
  observed_filler_per100: number | null;
  metrics_version: string;
}

export interface AnswerOut {
  answer_id: string;
  order_no: number;
  attempt_no: number;
  stt_status: answer_stt_status;
  reject_reason: string | null;
  error_code: string | null;
  stt_text: string | null;
  metrics: Metrics | null;
  session_status: session_status;
  current_order_no: number;
  all_answered: boolean;
}

export interface Mistake {
  quote: string;
  problem: string;
  fix: string;
}

export interface ItemFeedback {
  order_no: number;
  evaluation_role: evaluation_role;
  task_fulfillment: task_fulfillment;
  evidence: (string)[];
  mistakes: (Mistake)[];
  upgrade_tip: string;
}

export interface FeedbackCard {
  title: string;
  why: string;
  before: string | null;
  after: string;
  example_kind: example_kind;
  related_order_nos: (number)[];
  success_condition: string;
}

export interface DimensionFeedback {
  summary: string;
  evidence_order_nos: (number)[];
  limitations: (string)[];
}

export interface DimensionFeedbackSet {
  functions_tasks: DimensionFeedback;
  accuracy: DimensionFeedback;
  context_content: DimensionFeedback;
  text_type: DimensionFeedback;
}

export interface QuoteRef {
  order_no: number;
  quote: string;
}

export interface FactEvidence {
  criterion: "functions_tasks" | "accuracy" | "context_content" | "text_type";
  observation: string;
  status: fact_status;
  order_no: number | null;
  quote: string | null;
}

export interface CoverageEntry {
  name: string;
  elicited_order_nos: (number)[];
  usable_order_nos: (number)[];
  gaps: (string)[];
}

export interface Coverage {
  functions: (CoverageEntry)[];
  time_frames: (CoverageEntry)[];
  contexts: (CoverageEntry)[];
}

export interface SustainedPerformance {
  capability: string;
  evidence: (QuoteRef)[];
  summary: string;
}

export interface BreakdownObservation {
  demanded_function: string;
  evidence: (QuoteRef)[];
  communicative_impact: string;
  recovery: string;
}

export interface UnusableItem {
  order_no: number;
  reason: string;
}

export interface EvaluationScope {
  submitted_order_nos: (number)[];
  scored_order_nos: (number)[];
  feedback_only_order_nos: (number)[];
  usable_order_nos: (number)[];
  unusable_items: (UnusableItem)[];
}

export interface AdditionalTask {
  target_function: string;
  reason: string;
  suggested_question: string;
}

// CR frontend-01: 서버 Tier 객체와 일치 (OpenAI Codex).
export interface Tier { name: string; color: string }

export interface EvaluationResult {
  assessment_status: assessment_status;
  assessment_basis: "transcript_and_metrics";
  rubric_version: string;
  prompt_version: string;
  im_rubric_version: string | null;
  evaluation_scope: EvaluationScope;
  input_issues: (string)[];
  base_level: base_level | null;
  estimated_level: level | null;
  im_estimation_status: im_estimation_status;
  provisional_label: string | null;
  tier: Tier | null;
  headline: string;
  grade_rationale: string;
  dimension_feedback: DimensionFeedbackSet;
  coverage: Coverage;
  fact_evidence: (FactEvidence)[];
  sustained_performance: (SustainedPerformance)[];
  breakdown_observations: (BreakdownObservation)[];
  fluency_observations: string;
  why_this_level: string;
  why_not_lower: string;
  next_level_gap: string;
  borderline_levels: (level)[];
  uncertainty_reasons: (string)[];
  items: (ItemFeedback)[];
  feedback_cards: (FeedbackCard)[];
  additional_tasks_needed: (AdditionalTask)[];
  limitations: (string)[];
  insufficient_reason: string | null;
  disclaimer: string;
}

export interface ResultItemOut {
  order_no: number;
  question_id: string;
  question_type: string;
  question_text: string;
  is_scored: boolean;
  stt_text: string | null;
  metrics: Metrics | null;
  skipped: boolean;
}

export interface ResultOut {
  session_status: session_status;
  evaluation_status: evaluation_status | null;
  run_no: number | null;
  result: EvaluationResult | null;
  answers: (ResultItemOut)[];
  error_code: string | null;
  graded_at: string | null;
}
