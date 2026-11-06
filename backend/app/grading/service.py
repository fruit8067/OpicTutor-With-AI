# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성했습니다.
# OWNER: grader (contracts.yaml ownership)
import time
from app import db
from app.config import settings
from app.schemas.internal import EvaluationLLMOutput
from app.llm.chat import chat_structured,llm_options,LLMConfigurationError,LLMTransientError,LLMRefusalError,LLMOutputError
from app.worker.errors import PermanentJobError
from .validate import precheck_snapshot,validate_output
from .prompt import load_system_prompt,build_messages,TEMPLATE_VERSION
from .evidence import build_evidence
from .rules import contract,token_count

def evaluate_exam(snapshot: list[dict], *, exclude_contrast_set_ids: list[str] = (), job_id=None):
    precheck_snapshot(snapshot)
    system,system_meta=load_system_prompt()
    try: options=llm_options()
    except LLMConfigurationError as exc: raise PermanentJobError('EVAL_INTERNAL') from exc
    evidence=build_evidence(snapshot,exclude_contrast_set_ids=exclude_contrast_set_ids)
    messages=build_messages(snapshot,evidence)
    invalid_retry=False
    totals={'total_input_tokens':0,'total_output_tokens':0,'total_latency_ms':0,'llm_calls':0}
    for attempt in range(3):
        # 공급자별 채팅 오버헤드에 여유를 주며 시스템/답변/스키마를 조용히 자르지 않는다.
        if token_count(messages)+token_count(EvaluationLLMOutput.model_json_schema())+1024>contract()['policies']['input_token_hard_limit']:
            raise PermanentJobError('EVAL_INPUT_TOO_LARGE')
        started=time.monotonic();usage={};failure=None;status='error'
        try:
            parsed,usage=chat_structured(messages,EvaluationLLMOutput,timeout=settings.LLM_TIMEOUT_SEC)
            result=validate_output(parsed,snapshot)
            status='ok'
        except LLMRefusalError as exc: failure=exc;status='refused';code='LLM_REFUSED'
        except LLMOutputError as exc: failure=exc;status='invalid_output';code='LLM_INVALID_OUTPUT'
        except LLMTransientError as exc: failure=exc;code='LLM_TRANSIENT'
        except Exception as exc: failure=exc;code='EVAL_INTERNAL'
        db.log_ai_request(job_id=job_id,purpose='evaluate',model=usage.get('model',options['model']),
            input_tokens=usage.get('input_tokens'),output_tokens=usage.get('output_tokens'),
            latency_ms=usage.get('latency_ms',int((time.monotonic()-started)*1000)),status=status,
            error_code=code if failure else None)
        totals['llm_calls']+=1
        for total,key in [('total_input_tokens','input_tokens'),('total_output_tokens','output_tokens')]:
            totals[total]+=usage.get(key) or 0
        totals['total_latency_ms']+=usage.get('latency_ms',int((time.monotonic()-started)*1000))
        if failure is None:
            return result,{**usage,**totals,**system_meta,'system_prompt_sha1':system_meta['sha1'],
                'user_template_version':TEMPLATE_VERSION,'prompt_version':system_meta['prompt_version']+'+'+TEMPLATE_VERSION,
                'im_rubric_version':contract()['evaluation_criteria']['im_rubric_version'],
                'corpus_version':evidence.corpus_version,'retrieved_doc_ids':evidence.retrieved_doc_ids}
        if isinstance(failure,LLMTransientError) and attempt<2:
            time.sleep(2**(attempt+1));continue
        if isinstance(failure,LLMOutputError) and not invalid_retry and attempt<2:
            invalid_retry=True
            # 오류 위치·규칙만 넣는다. 원본 응답이나 내부 예외 본문을 다시 노출하지 않는다.
            messages=[*messages,{'role':'user','content':'이전 응답의 검증 오류: '+str(failure)+'. 동일 시험을 출력 계약과 대조하여 다시 평가하세요.'}]
            continue
        raise failure
