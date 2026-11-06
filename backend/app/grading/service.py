# AI-assisted: 평가 요청 예산과 기록은 OpenAI Codex의 도움으로 작성했습니다.
# OWNER: grader (contracts.yaml ownership)
import time
from uuid import UUID
from app import db
from app.config import settings
from app.schemas.api import EvaluationResult
from app.schemas.internal import EvaluationLLMOutput
from app.llm.chat import (chat_structured,llm_options,LLMConfigurationError,LLMTransientError,
                          LLMRefusalError,LLMOutputError,_track_requests,_error_status)
from app.worker.errors import PermanentJobError
from .validate import precheck_snapshot,validate_output
from .prompt import load_system_prompt,build_messages,TEMPLATE_VERSION
from .evidence import build_evidence
from .rules import contract,token_count


def _repair_guidance(error):
    labels=set(getattr(error,'validation_errors',[]) or str(error).split('; '))
    hints={
        'fact_evidence.null_quote':'fact_evidence에서 status가 not_observed이거나 order_no가 null이면 quote도 반드시 JSON null입니다. 문자열 "null"이나 인용문을 넣지 마세요.',
        'items.evidence: quote':'items.evidence는 해당 item의 verbatim_quote_candidates에서 그대로 복사하거나 빈 배열로 두세요. 요약/번역/수정한 문장은 인용이 아닙니다.',
        'feedback_cards.before':'카드 before는 related_order_nos의 실제 전사 구절이어야 합니다. 새 예문이면 before=null, example_kind=practice로 두세요.',
        'coverage.vocabulary':'coverage.name은 required_output_metadata의 영문 name만 그대로 사용하세요.',
        'coverage.elicited':'coverage.elicited_order_nos는 required_output_metadata에서 같은 name의 목록과 정확히 일치해야 합니다.',
        'evaluation_scope.usable':'evaluation_scope.usable_order_nos에는 usable_order_nos_allowed의 번호만 넣으세요. 자기소개 1번은 포함하지 마세요.',
        'non_IM.rubric_version':'base_level이 IM이 아니면 im_rubric_version은 JSON null, im_estimation_status는 not_applicable입니다.'}
    return '\n'.join(hint for label,hint in hints.items() if label in labels)


def evaluate_exam(snapshot: list[dict], *, exclude_contrast_set_ids: list[str] = (),
                  job_id: UUID | None = None) -> tuple[EvaluationResult, dict]:
    precheck_snapshot(snapshot)
    _,system_meta=load_system_prompt()
    try: llm_options()
    except LLMConfigurationError as exc: raise PermanentJobError('EVAL_INTERNAL') from exc
    evidence=build_evidence(snapshot,exclude_contrast_set_ids=exclude_contrast_set_ids)
    messages=build_messages(snapshot,evidence)
    invalid_retry=False
    totals={'total_input_tokens':0,'total_output_tokens':0,'total_latency_ms':0,'llm_calls':0}
    with _track_requests(1+contract()['policies']['llm_transient_retries']) as trace:
        for attempt in range(3):
            if token_count(messages)+token_count(EvaluationLLMOutput.model_json_schema())+1024>contract()['policies']['input_token_hard_limit']:
                raise PermanentJobError('EVAL_INPUT_TOO_LARGE')
            before=len(trace.records)
            usage={};failure=None
            try:
                parsed,usage=chat_structured(messages,EvaluationLLMOutput,timeout=settings.LLM_TIMEOUT_SEC)
                result=validate_output(parsed,snapshot)
            except Exception as exc:
                failure=exc
            records=trace.records[before:]
            if failure is not None and records and records[-1]['status']=='ok':
                records[-1]['status'],records[-1]['error_code']=_error_status(failure)
            for record in records:
                db.log_ai_request(job_id=job_id,purpose='evaluate',**record)
                totals['llm_calls']+=1
                totals['total_input_tokens']+=record['input_tokens'] or 0
                totals['total_output_tokens']+=record['output_tokens'] or 0
                totals['total_latency_ms']+=record['latency_ms']
            if failure is None:
                return result,{**usage,**totals,**system_meta,'system_prompt_sha1':system_meta['sha1'],
                    'user_template_version':TEMPLATE_VERSION,'prompt_version':system_meta['prompt_version']+'+'+TEMPLATE_VERSION,
                    'im_rubric_version':contract()['evaluation_criteria']['im_rubric_version'],
                    'corpus_version':evidence.corpus_version,'retrieved_doc_ids':evidence.retrieved_doc_ids}
            if isinstance(failure,LLMTransientError) and attempt<2 and trace.remaining>0:
                time.sleep(2**(attempt+1));continue
            if isinstance(failure,LLMOutputError) and not invalid_retry and attempt<2 and trace.remaining>0:
                invalid_retry=True
                messages=[*messages,{'role':'user','content':'이전 응답의 검증 오류: '+str(failure)+'. 동일 시험을 출력 계약과 대조하여 다시 평가하세요.\n'+_repair_guidance(failure)}]
                continue
            failure.evaluation_usage=totals.copy()
            raise failure
