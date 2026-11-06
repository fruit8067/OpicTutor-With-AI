# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성했습니다.
# OWNER: grader (contracts.yaml ownership)
import time
import json
import logging
import os
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from urllib.parse import urlsplit
from openai import (OpenAI, APIConnectionError, APITimeoutError, APIStatusError, RateLimitError, InternalServerError, BadRequestError,
                    LengthFinishReasonError,ContentFilterFinishReasonError)
from pydantic import BaseModel, ValidationError
from app.config import settings

# SDK의 요청 본문 DEBUG 로그에 사용자 전사가 남지 않도록 한다.
logging.getLogger('openai').setLevel(logging.WARNING)

class LLMTransientError(Exception): pass
class LLMRefusalError(Exception): pass
class LLMOutputError(Exception): pass
class LLMConfigurationError(ValueError): pass


@dataclass
class _Requests:
    limit: int
    records: list[dict] = field(default_factory=list)
    json_only: set[tuple[str,str]] = field(default_factory=set)

    @property
    def remaining(self): return self.limit-len(self.records)


_requests = ContextVar('evaluation_provider_requests', default=None)


@contextmanager
def _track_requests(limit: int):
    trace=_Requests(limit)
    token=_requests.set(trace)
    try: yield trace
    finally: _requests.reset(token)


def _error_status(exc):
    if _quota_error(exc): return 'error','EVAL_INTERNAL'
    if isinstance(exc,(LLMRefusalError,ContentFilterFinishReasonError)):
        return 'refused','LLM_REFUSED'
    if isinstance(exc,(LLMOutputError,LengthFinishReasonError,ValidationError,json.JSONDecodeError)):
        return 'invalid_output','LLM_INVALID_OUTPUT'
    if isinstance(exc,(LLMTransientError,APIConnectionError,APITimeoutError)) or (
            isinstance(exc,APIStatusError) and (exc.status_code in (408,429) or exc.status_code>=500)):
        return 'error','LLM_TRANSIENT'
    return 'error','EVAL_INTERNAL'


def _quota_error(exc):
    return getattr(exc,'code',None) in ('insufficient_quota','quota_exceeded','credit_limit_exceeded','quota_exhausted')


def _send(call, model: str):
    """실제 SDK 요청마다 예산을 차감하고 본문 없는 메타데이터만 수집한다."""
    trace=_requests.get()
    if trace is not None and trace.remaining<=0:
        raise LLMOutputError('LLM provider 요청 예산 소진')
    record=dict(model=model,input_tokens=None,output_tokens=None,latency_ms=0,status='error',error_code=None)
    if trace is not None: trace.records.append(record)
    started=time.monotonic();received=False
    try:
        response=call()
        received=True
        if getattr(response,'http_response',None) is not None and callable(getattr(response,'parse',None)):
            # Read only usage before the SDK's local structured parser can fail.
            # The payload is never logged or attached to the resulting error.
            payload=response.http_response.json()
            usage=payload.get('usage') or {}
            record.update(model=payload.get('model') or model,input_tokens=usage.get('prompt_tokens'),
                          output_tokens=usage.get('completion_tokens'))
            response=response.parse()
        usage=getattr(response,'usage',None)
        record.update(model=getattr(response,'model',model),input_tokens=getattr(usage,'prompt_tokens',None),
                      output_tokens=getattr(usage,'completion_tokens',None),status='ok')
        return response
    except Exception as exc:
        if isinstance(exc,(AttributeError,NotImplementedError)) and not received and trace is not None:
            # 로컬 SDK 메서드 미지원: 네트워크 요청 전 실패는 예산/로그에서 제외한다.
            trace.records.pop()
        record['status'],record['error_code']=_error_status(exc)
        raise
    finally:
        record['latency_ms']=int((time.monotonic()-started)*1000)


def _schema_error(exc,schema):
    names=set()
    def collect(node):
        if isinstance(node,dict):
            names.update(node.get('properties',{}))
            for value in node.values(): collect(value)
        elif isinstance(node,list):
            for value in node: collect(value)
    collect(schema.model_json_schema())
    labels=[]
    if isinstance(exc,ValidationError):
        for error in exc.errors(include_input=False,include_url=False):
            path='.'.join(str(part) if isinstance(part,int) or part in names else 'field' for part in error['loc']) or 'output'
            labels.append('schema.'+path+'.'+error['type'])
    else: labels=['schema.invalid_json']
    failure=LLMOutputError('LLM 응답 스키마 불일치: '+'; '.join(dict.fromkeys(labels)))
    failure.validation_errors=list(dict.fromkeys(labels))[:20]
    return failure

def llm_options() -> dict:
    """Pickle 인증 키는 호출 시점의 프로세스 환경변수에서 읽는다."""
    options={
        'base_url':(os.getenv('LLM_BASE_URL') or settings.LLM_BASE_URL).strip(),
        'model':(os.getenv('LLM_MODEL') or settings.LLM_MODEL).strip(),
        'api_key':os.getenv('LLM_API_KEY','').strip() or os.getenv('PICKLE_API_KEY','').strip(),
    }
    missing=[name for name,key in [('LLM_BASE_URL','base_url'),('LLM_MODEL','model'),('LLM_API_KEY','api_key')] if not options[key]]
    if missing: raise LLMConfigurationError('필수 LLM 환경변수 누락: '+', '.join(missing)+' (LLM_API_KEY 대신 PICKLE_API_KEY 가능)')
    parsed=urlsplit(options['base_url'])
    if parsed.scheme not in ('https','http') or not parsed.netloc:
        raise LLMConfigurationError('LLM_BASE_URL 형식이 올바르지 않습니다.')
    return options

def chat_structured(messages: list[dict], schema: type[BaseModel], *, timeout: float) -> tuple[BaseModel, dict]:
    options=llm_options()
    client=OpenAI(base_url=options['base_url'],api_key=options['api_key'],timeout=timeout,max_retries=0)
    started=time.monotonic()
    common=dict(model=options['model'],messages=messages,temperature=0,max_tokens=8000)
    trace=_requests.get()
    provider=(options['base_url'],options['model'])
    try:
        response=None
        try:
            # 속성 접근 자체가 미지원이면 HTTP 요청이 없으므로 차감/기록하지 않는다.
            if trace is None or provider not in trace.json_only:
                endpoint=client.beta.chat.completions
                raw=getattr(endpoint,'with_raw_response',None)
                parse=getattr(raw,'parse',None) or endpoint.parse
                response=_send(lambda:parse(**common,response_format=schema),options['model'])
        except (AttributeError,NotImplementedError):
            if trace is not None: trace.json_only.add(provider)
        except BadRequestError as exc:
            message=str(exc).lower()
            if not any(word in message for word in ('response_format','json_schema','structured output')):
                raise
            if trace is not None: trace.json_only.add(provider)
        if response is None:
            # JSON 모드 제공자에도 전체 출력 계약을 전달한다.
            fallback=[*messages,{'role':'user','content':'Return JSON matching this schema: '+json.dumps(schema.model_json_schema(),ensure_ascii=False)}]
            response=_send(lambda:client.chat.completions.create(**{**common,'messages':fallback},response_format={'type':'json_object'}),options['model'])
        if not response.choices:
            raise LLMOutputError('LLM 응답 choice 누락')
        choice=response.choices[0];message=choice.message
        if getattr(message,'refusal',None) or choice.finish_reason=='content_filter':
            raise LLMRefusalError('LLM 거절')
        if choice.finish_reason!='stop':
            raise LLMOutputError('LLM 응답 미완료')
        parsed=getattr(message,'parsed',None)
        if parsed is None:
            try: parsed=schema.model_validate_json(message.content or '')
            except (ValidationError,ValueError,TypeError) as exc:
                raise _schema_error(exc,schema) from exc
        usage=response.usage
        meta={'model':response.model,'input_tokens':getattr(usage,'prompt_tokens',None),
              'output_tokens':getattr(usage,'completion_tokens',None),'latency_ms':int((time.monotonic()-started)*1000)}
        return parsed,meta
    except RateLimitError as exc:
        # Allocated quota is not a temporary per-minute throttle. Preserve the
        # provider code for the batch controller, without automatic retries.
        if _quota_error(exc): raise
        raise LLMTransientError('LLM 일시적 요청 제한') from exc
    except (APIConnectionError,APITimeoutError,InternalServerError) as exc:
        raise LLMTransientError('LLM 일시적 연결/서비스 오류') from exc
    except APIStatusError as exc:
        if exc.status_code==408:
            raise LLMTransientError('LLM HTTP 요청 시간 초과') from exc
        raise
    except LengthFinishReasonError as exc:
        raise LLMOutputError('LLM 응답 길이 제한 초과') from exc
    except ContentFilterFinishReasonError as exc:
        raise LLMRefusalError('LLM 콘텐츠 필터 거절') from exc
    except (ValidationError,json.JSONDecodeError) as exc:
        raise _schema_error(exc,schema) from exc
    finally:
        close=getattr(client,'close',None)
        if close is not None: close()
