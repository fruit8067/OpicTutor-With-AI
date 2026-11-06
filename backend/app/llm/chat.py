# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성했습니다.
# OWNER: grader (contracts.yaml ownership)
import time
import json
import logging
import os
from urllib.parse import urlsplit
from openai import (OpenAI, APIConnectionError, APITimeoutError, RateLimitError, InternalServerError, BadRequestError,
                    LengthFinishReasonError,ContentFilterFinishReasonError)
from pydantic import BaseModel, ValidationError
from app.config import settings

# SDK의 요청 본문 DEBUG 로그에 사용자 전사가 남지 않도록 한다.
logging.getLogger('openai').setLevel(logging.WARNING)

class LLMTransientError(Exception): pass
class LLMRefusalError(Exception): pass
class LLMOutputError(Exception): pass
class LLMConfigurationError(ValueError): pass

def llm_options() -> dict:
    """Pickle 인증 키는 호출 시점의 프로세스 환경변수에서 읽는다."""
    options={
        'base_url':(os.getenv('LLM_BASE_URL') or settings.LLM_BASE_URL).strip(),
        'model':(os.getenv('LLM_MODEL') or settings.LLM_MODEL).strip(),
        'api_key':os.getenv('LLM_API_KEY','').strip(),
    }
    missing=[name for name,key in [('LLM_BASE_URL','base_url'),('LLM_MODEL','model'),('LLM_API_KEY','api_key')] if not options[key]]
    if missing: raise LLMConfigurationError('필수 LLM 환경변수 누락: '+', '.join(missing))
    parsed=urlsplit(options['base_url'])
    if parsed.scheme not in ('https','http') or not parsed.netloc:
        raise LLMConfigurationError('LLM_BASE_URL 형식이 올바르지 않습니다.')
    return options

def chat_structured(messages: list[dict], schema: type[BaseModel], *, timeout: float) -> tuple[BaseModel, dict]:
    options=llm_options()
    client=OpenAI(base_url=options['base_url'],api_key=options['api_key'],timeout=timeout,max_retries=0)
    started=time.monotonic()
    common=dict(model=options['model'],messages=messages,temperature=0,max_tokens=8000)
    try:
        try:
            response=client.beta.chat.completions.parse(**common,response_format=schema)
        except (AttributeError,NotImplementedError):
            response=None
        except BadRequestError as exc:
            message=str(exc).lower()
            if not any(word in message for word in ('response_format','json_schema','structured output')):
                raise
            response=None
        if response is None:
            # JSON 모드 제공자에도 전체 출력 계약을 전달한다.
            fallback=[*messages,{'role':'user','content':'Return JSON matching this schema: '+json.dumps(schema.model_json_schema(),ensure_ascii=False)}]
            response=client.chat.completions.create(**{**common,'messages':fallback},response_format={'type':'json_object'})
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
                raise LLMOutputError('LLM 응답 스키마 불일치') from exc
        usage=response.usage
        meta={'model':response.model,'input_tokens':getattr(usage,'prompt_tokens',None),
              'output_tokens':getattr(usage,'completion_tokens',None),'latency_ms':int((time.monotonic()-started)*1000)}
        return parsed,meta
    except (APIConnectionError,APITimeoutError,RateLimitError,InternalServerError) as exc:
        raise LLMTransientError('LLM 일시적 연결/서비스 오류') from exc
    except LengthFinishReasonError as exc:
        raise LLMOutputError('LLM 응답 길이 제한 초과') from exc
    except ContentFilterFinishReasonError as exc:
        raise LLMRefusalError('LLM 콘텐츠 필터 거절') from exc
    except (ValidationError,json.JSONDecodeError) as exc:
        raise LLMOutputError('LLM 응답 스키마 불일치') from exc
