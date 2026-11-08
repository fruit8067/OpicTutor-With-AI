# AI-assisted: 저장 세션 재전송 검증은 OpenAI Codex의 도움으로 작성했습니다.
# 후속 수정: 인증 인자 추가에 맞춘 호출 시그니처 수정은 Claude(Anthropic)의 도움으로 작성되었습니다.
# OWNER: session-api (contracts.yaml ownership)
from uuid import uuid4
from types import SimpleNamespace
import pytest
from fastapi import Response
from app.api import routes_sessions
from app.schemas.api import CreateSessionIn
from app.errors import AppError


def test_existing_session_replays_even_when_question_bank_is_unavailable(monkeypatch):
    sid=uuid4();response=Response()
    monkeypatch.setattr(routes_sessions,'db',SimpleNamespace(
        get_session_id_by_request_id=lambda key:sid if key=='original-request' else None,
        create_session=lambda **kwargs:pytest.fail('재전송이 준비 작업을 다시 만들면 안 됨')))
    monkeypatch.setattr(routes_sessions,'session_out',lambda value,authorization=None:{'session_id':value})
    def unavailable(*args,**kwargs): raise AppError('SCENARIO_UNAVAILABLE')
    monkeypatch.setattr(routes_sessions.exam,'build_question_set',unavailable)
    result=routes_sessions.create_session(CreateSessionIn(client_request_id='original-request',mic_check_passed=True),response,authorization=None)
    assert response.status_code==200 and result['session_id']==sid
    with pytest.raises(AppError,match='SCENARIO_UNAVAILABLE'):
        routes_sessions.create_session(CreateSessionIn(client_request_id='new-request',mic_check_passed=True),Response(),authorization=None)
