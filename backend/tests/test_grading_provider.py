# AI-assisted: LLM 환경설정 검증은 OpenAI Codex의 도움으로 작성했습니다.
# OWNER: grader (contracts.yaml ownership)
from types import SimpleNamespace as NS
import os
import subprocess
import sys
import pytest
from pydantic import BaseModel
from app.llm import chat
from app.grading import service
from app.config import Settings,settings
from app.worker.errors import PermanentJobError
from test_grading_validate import snapshot


class Sample(BaseModel):
    value: int


def configure(monkeypatch):
    # 외부 제공자 주소를 추측하지 않는다. 이 주소는 SDK 인자 전달만 확인하는 비네트워크 fixture다.
    monkeypatch.setenv('LLM_BASE_URL','https://pickle.example.invalid/v1')
    monkeypatch.setenv('LLM_MODEL','pickle-base-fixture')
    monkeypatch.setenv('LLM_API_KEY','pickle-fixture-key')


def test_pickle_options_and_getenv_key_are_used_at_request_time(monkeypatch,caplog):
    configure(monkeypatch)
    captured=[];requests=[]
    monkeypatch.setattr(settings,'LLM_API_KEY','stale-settings-key-must-not-be-used')
    def client(**kwargs):
        captured.append(kwargs)
        def parse(**options):
            requests.append(options)
            return NS(choices=[NS(finish_reason='stop',message=NS(parsed=Sample(value=1),refusal=None))],
                usage=NS(prompt_tokens=3,completion_tokens=2),model=options['model'])
        # Older SDKs can expose the raw wrapper without a raw parse helper.
        return NS(beta=NS(chat=NS(completions=NS(parse=parse,with_raw_response=NS()))))
    monkeypatch.setattr(chat,'OpenAI',client)
    chat.chat_structured([],Sample,timeout=3)
    monkeypatch.setenv('LLM_API_KEY','rotated-pickle-fixture-key')
    chat.chat_structured([],Sample,timeout=3)
    assert [c['api_key'] for c in captured]==['pickle-fixture-key','rotated-pickle-fixture-key']
    assert all(c['base_url']=='https://pickle.example.invalid/v1' for c in captured)
    assert all(r['model']=='pickle-base-fixture' for r in requests)
    assert all(c['max_retries']==0 for c in captured)
    assert 'fixture-key' not in caplog.text


@pytest.mark.parametrize('missing',['LLM_BASE_URL','LLM_MODEL','LLM_API_KEY'])
def test_missing_config_does_not_fall_back_to_openai_or_make_calls(monkeypatch,missing):
    configure(monkeypatch);monkeypatch.delenv(missing)
    monkeypatch.delenv('PICKLE_API_KEY',raising=False)
    if missing!='LLM_API_KEY': monkeypatch.setattr(settings,missing,'')
    monkeypatch.setenv('OPENAI_API_KEY','embedding-only-must-not-be-forwarded')
    monkeypatch.setattr(chat,'OpenAI',lambda **kwargs:pytest.fail('미설정 상태에서 SDK 호출'))
    with pytest.raises(chat.LLMConfigurationError,match=missing): chat.chat_structured([],Sample,timeout=3)
    monkeypatch.setattr(service,'build_evidence',lambda *args,**kwargs:pytest.fail('LLM 미설정 상태에서 검색 임베딩'))
    with pytest.raises(PermanentJobError,match='EVAL_INTERNAL'): service.evaluate_exam(snapshot())


@pytest.mark.parametrize('key_name',['LLM_API_KEY','PICKLE_API_KEY'])
def test_dotenv_supports_getenv_without_overwriting_process_environment(tmp_path,key_name):
    env_file=tmp_path/'.env'
    env_file.write_text(key_name+'=dotenv-fixture-key\nLLM_BASE_URL=https://pickle.example.invalid/v1\nLLM_MODEL=pickle-fixture\n',encoding='utf-8')
    script='''import sys,dotenv
original=dotenv.load_dotenv
def test_env(path,**kwargs):
    assert kwargs.get('override') is False
    return original(sys.argv[1],**kwargs)
dotenv.load_dotenv=test_env
from app.llm.chat import llm_options
assert llm_options()['api_key']==sys.argv[2]
'''
    environment=os.environ.copy()
    for name in ['LLM_API_KEY','PICKLE_API_KEY','LLM_BASE_URL','LLM_MODEL']: environment.pop(name,None)
    result=subprocess.run([sys.executable,'-c',script,str(env_file),'dotenv-fixture-key'],env=environment,capture_output=True)
    assert result.returncode==0
    environment['LLM_API_KEY']='process-fixture-key'
    result=subprocess.run([sys.executable,'-c',script,str(env_file),'process-fixture-key'],env=environment,capture_output=True)
    assert result.returncode==0


def test_requested_pickle_and_large_defaults(monkeypatch):
    for name in ['EMBED_API_KEY','EMBED_BASE_URL','EMBED_MODEL','EMBED_DIM','LLM_BASE_URL','LLM_MODEL']:
        monkeypatch.delenv(name,raising=False)
    isolated=Settings(_env_file=None)
    assert isolated.LLM_BASE_URL=='https://llm.pcl.kr/v1' and isolated.LLM_MODEL=='pickle-general'
    assert isolated.EMBED_BASE_URL=='https://api.openai.com/v1' and isolated.EMBED_MODEL=='text-embedding-3-large'
    assert isolated.EMBED_DIM==3072


def test_pickle_key_alias_is_read_dynamically_with_canonical_key_priority(monkeypatch):
    configure(monkeypatch)
    monkeypatch.setenv('PICKLE_API_KEY','pickle-alias-fixture')
    assert chat.llm_options()['api_key']=='pickle-fixture-key'
    monkeypatch.setenv('LLM_API_KEY','  ')
    assert chat.llm_options()['api_key']=='pickle-alias-fixture'
    monkeypatch.setenv('PICKLE_API_KEY','rotated-alias-fixture')
    assert chat.llm_options()['api_key']=='rotated-alias-fixture'
