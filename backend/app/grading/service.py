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
                messages=[*messages,{'role':'user','content':'이전 응답의 검증 오류: '+str(failure)+'. 동일 시험을 출력 계약과 대조하여 다시 평가하세요.'}]
                continue
            failure.evaluation_usage=totals.copy()
            raise failure
