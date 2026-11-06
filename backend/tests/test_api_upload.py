# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성되었습니다.
# OWNER: session-api (contracts.yaml ownership)
"""계약 가짜 구현으로 HTTP 경계와 파일 저장 실패 복구를 검증한다."""
from datetime import datetime,timezone
from uuid import uuid4
import hashlib
import pytest
from fastapi.testclient import TestClient
from app import db
from app.main import app
from app.config import settings
from app.errors import AppError


@pytest.fixture
def client(tmp_path,monkeypatch):
    sid=uuid4();now=datetime.now(timezone.utc)
    session=dict(id=sid,status='in_progress',question_count=8,current_order_no=1,scenario_id='default',
        created_at=now,updated_at=now,host_lines={})
    answers={};keys={}
    monkeypatch.setattr(settings,'DATA_DIR',tmp_path)
    monkeypatch.setattr(db,'get_session',lambda value:session.copy() if value==sid else None)
    monkeypatch.setattr(db,'get_answer',lambda aid:answers.get(aid))
    def create(**kwargs):
        key=kwargs['client_request_id']
        if key in keys: return answers[keys[key]],False
        if session['status']!='in_progress': raise AppError('INVALID_STATE')
        if kwargs['order_no']!=session['current_order_no']: raise AppError('ORDER_MISMATCH')
        if any(a['order_no']==kwargs['order_no'] and a['stt_status']=='queued' for a in answers.values()): raise AppError('ANSWER_PENDING')
        aid=kwargs['answer_id'];row={**kwargs,'id':aid,'attempt_no':1,'stt_status':'queued'}
        answers[aid]=row;keys[key]=aid;return row,True
    monkeypatch.setattr(db,'create_answer',create)
    monkeypatch.setattr(db,'submit_session',lambda sid:(_ for _ in ()).throw(AppError('NOT_ALL_ANSWERED')))
    return TestClient(app,raise_server_exceptions=False),sid,session,answers,tmp_path


def send(client,sid,data=b'voice',mime='audio/webm',duration=3000,key='one',order=1):
    return client.post(f'/api/v1/sessions/{sid}/answers',data={'order_no':order,'client_request_id':key,'duration_ms':duration},
        files={'audio':('answer.webm',data,mime)})


def test_upload_accepted_deduplicated_and_polling(client):
    c,sid,session,answers,path=client
    response=send(c,sid,mime='audio/webm;codecs=opus')
    assert response.status_code==202 and response.json()['current_order_no']==1
    aid=response.json()['answer_id'];row=next(iter(answers.values()))
    assert row['audio_hash']==hashlib.sha256(b'voice').hexdigest()
    assert len(list(path.rglob('*.webm')))==1
    session['current_order_no']=2
    assert send(c,sid).status_code==200
    assert send(c,sid).json()['answer_id']==aid
    assert len(list(path.rglob('*.webm')))==1 and not list(path.rglob('.tmp/*'))
    assert c.get(f'/api/v1/sessions/{sid}/answers/{aid}').status_code==200
    assert c.get(f'/api/v1/sessions/{uuid4()}/answers/{aid}').status_code==404


@pytest.mark.parametrize('kwargs,status,code',[
    ({'duration':1500},422,'AUDIO_TOO_SHORT'),({'duration':125001},422,'AUDIO_TOO_LONG'),
    ({'mime':'text/plain'},415,'UNSUPPORTED_MEDIA'),({'data':b'x'*(10485760+1)},413,'PAYLOAD_TOO_LARGE'),
    ({'data':b''},422,'AUDIO_TOO_SHORT'),({'order':2},409,'ORDER_MISMATCH')])
def test_upload_failures_clean_temp_files(client,kwargs,status,code):
    c,sid,session,answers,path=client
    response=send(c,sid,**kwargs)
    assert response.status_code==status and response.json()['error']['code']==code
    assert not answers and not [p for p in path.rglob('*') if p.is_file()]


def test_pending_early_submit_and_reserved_chat(client):
    c,sid,*_=client
    assert send(c,sid).status_code==202
    assert send(c,sid,key='two').json()['error']['code']=='ANSWER_PENDING'
    assert c.post(f'/api/v1/sessions/{sid}/submit').json()['error']['code']=='NOT_ALL_ANSWERED'
    assert c.post(f'/api/v1/sessions/{sid}/chat').status_code==501
    response=c.post('/api/v1/sessions',json={'client_request_id':'new','mic_check_passed':False})
    assert response.json()['error']['code']=='MIC_CHECK_REQUIRED'


def test_invalid_uuid_has_contract_error(client):
    c,*_=client
    response=c.get('/api/v1/sessions/invalid')
    assert response.status_code==422 and response.json()['error']['code']=='VALIDATION_ERROR'
