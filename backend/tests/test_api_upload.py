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
    def question(value,order):
        rows=[a for a in answers.values() if a['order_no']==order]
        return {'client_request_ids':[a['client_request_id'] for a in rows],
                'latest_answer':rows[-1] if rows else None} if value==sid and 1<=order<=8 else None
    monkeypatch.setattr(db,'get_session_question',question)
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


@pytest.mark.parametrize('state,order,code',[
    ('ready',1,'INVALID_STATE'),('in_progress',2,'ORDER_MISMATCH')])
def test_upload_state_preflight_does_not_read_audio(client,monkeypatch,state,order,code):
    from starlette.datastructures import UploadFile
    c,sid,session,answers,path=client
    session['status']=state
    async def must_not_read(*args,**kwargs):
        raise AssertionError('상태/순서가 맞지 않는 새 업로드는 읽지 않아야 합니다.')
    monkeypatch.setattr(UploadFile,'read',must_not_read)
    response=send(c,sid,order=order)
    assert response.status_code==409 and response.json()['error']['code']==code
    assert not answers and not list(path.iterdir())


def test_preflight_preserves_old_attempt_retransmission(client):
    c,sid,session,answers,path=client
    first=send(c,sid,key='original').json()['answer_id']
    next(iter(answers.values()))['stt_status']='rejected'
    assert send(c,sid,key='rerecording').status_code==202
    session['status']='grading';session['current_order_no']=9
    duplicate=send(c,sid,key='original')
    assert duplicate.status_code==200 and duplicate.json()['answer_id']==first


@pytest.mark.parametrize('same_blob,retry_failure',[(True,False),(False,False),(True,True)])
def test_same_request_repairs_missing_file_after_publication_failure(client,monkeypatch,same_blob,retry_failure):
    from pathlib import Path
    c,sid,session,answers,path=client
    retried=[]
    def fail(aid,code): answers[aid].update(stt_status='failed',error_code=code)
    def retry(aid):
        if retry_failure and not retried:
            retried.append('temporary DB failure')
            raise AppError('INTERNAL_ERROR')
        retried.append(aid);answers[aid].update(stt_status='queued',error_code=None)
    monkeypatch.setattr(db,'fail_stt',fail)
    monkeypatch.setattr(db,'retry_stt',retry)
    with monkeypatch.context() as patch:
        def cannot_publish(*args,**kwargs): raise PermissionError('local fixture publication failure')
        patch.setattr(Path,'replace',cannot_publish)
        assert send(c,sid).status_code==500
    original=next(iter(answers.values()))
    assert original['stt_status']=='failed' and session['current_order_no']==1
    result=send(c,sid,data=b'voice' if same_blob else b'different blob')
    if retry_failure:
        assert result.status_code==500 and Path(original['audio_path']).is_file()
        result=send(c,sid)
    assert result.status_code==200 and result.json()['answer_id']==str(original['id'])
    assert result.json()['stt_status']==('queued' if same_blob else 'failed')
    assert len(answers)==1 and not list(path.rglob('.tmp/*'))
    assert Path(original['audio_path']).is_file() is same_blob
    assert retried==(['temporary DB failure',original['id']] if retry_failure else ([original['id']] if same_blob else []))
