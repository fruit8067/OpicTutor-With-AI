# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성되었습니다.
# OWNER: session-api (contracts.yaml ownership)
"""실제 PostgreSQL과 HTTP 계층 연결. TTS/STT 계산은 명시적인 fixture로 대체한다."""
from uuid import uuid4,UUID
import hashlib
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app import db,tts
from app.main import app
from app.config import settings
from app.db.pool import tx
from test_exam_builder import corpus


def test_real_db_http_flow(corpus,tmp_path,monkeypatch):
    if not db.ping(): pytest.skip('로컬 PostgreSQL/pgvector 미실행')
    db.init_db()
    monkeypatch.setattr(settings,'DATA_DIR',tmp_path/'data')
    monkeypatch.setattr(tts,'tts_url',lambda path:'/media/tts/'+path)
    client=TestClient(app)
    request={'client_request_id':str(uuid4()),'mic_check_passed':True}
    created=client.post('/api/v1/sessions',json=request)
    assert created.status_code==202
    sid=UUID(created.json()['session_id']);prefix=f'/api/v1/sessions/{sid}'
    assets=[]
    try:
        assert created.json()['status']=='preparing'
        assert client.post('/api/v1/sessions',json=request).status_code==200
        assert client.get(prefix+'/current').status_code==409
        links={}
        for q in db.list_session_questions(sid):
            aid=db.upsert_tts_asset(kind='question',ref_id=q['question_id'],text_hash=hashlib.sha1(q['question_text'].encode()).hexdigest(),
                voice_id=str(sid),settings_version='fixture',file_path=q['question_id']+'.mp3',duration_sec=3)
            links[q['order_no']]=aid;assets.append(aid)
        hosts={}
        for key,text in tts.HOST_LINES.items():
            aid=db.upsert_tts_asset(kind='host',ref_id=key,text_hash=hashlib.sha1(text.encode()).hexdigest(),voice_id=str(sid),
                settings_version='fixture',file_path=key+'.mp3',duration_sec=3)
            hosts[key]=aid;assets.append(aid)
        assert db.complete_prepare(sid,1,links,hosts)
        assert client.get(prefix).json()['prepare']['linked']==12
        assert client.post(prefix+'/start').json()['status']=='in_progress'
        current=client.get(prefix+'/current').json()
        assert current['question']['is_scored'] is False
        assert client.post(prefix+'/questions/1/replay').json()['replay_count']==1
        assert client.post(prefix+'/questions/1/replay').json()['error']['code']=='REPLAY_LIMIT'
        for no in range(1,9):
            key=str(uuid4())
            def upload(order=no,request_key=key):
                return client.post(prefix+'/answers',data={'order_no':order,'client_request_id':request_key,'duration_ms':3000},
                    files={'audio':('fixture.webm',b'fixture audio','audio/webm')})
            first=upload()
            assert first.status_code==202 and first.json()['current_order_no']==no
            assert upload().status_code==200
            assert upload(no+1,str(uuid4())).json()['error']['code']=='ORDER_MISMATCH'
            assert upload(no,str(uuid4())).json()['error']['code']=='ANSWER_PENDING'
            answer=UUID(first.json()['answer_id'])
            assert Path(db.get_answer(answer)['audio_path']).read_bytes()==b'fixture audio'
            metrics=dict(duration_sec=3,speech_sec=2,word_count=5,wpm=100,articulation_wpm=150,
                long_pause_count=0,observed_filler_per100=None,metrics_version='m1')
            db.complete_stt(answer,text='This is a test answer.',timestamps=[],metrics=metrics,stt_version='fixture')
            assert upload().json()['answer_id']==str(answer)
            if no==7:
                assert client.post(prefix+'/submit').json()['error']['code']=='NOT_ALL_ANSWERED'
        assert client.get(prefix+'/current').json()['all_answered']
        assert client.post(prefix+'/submit').status_code==202
        eid=db.get_latest_evaluation(sid)['id']
        assert client.post(prefix+'/submit').status_code==202
        assert db.get_latest_evaluation(sid)['id']==eid
        result=client.get(prefix+'/result')
        assert result.status_code==200 and result.json()['evaluation_status']=='queued'
        assert len(result.json()['answers'])==8 and result.json()['answers'][0]['is_scored'] is False
        count=db.count_ai_requests('evaluate')
        for _ in range(10): assert client.get(prefix+'/result').json()==result.json()
        assert db.count_ai_requests('evaluate')==count
    finally:
        with tx() as cur:
            cur.execute('DELETE FROM jobs WHERE target_id=%s OR target_id IN (SELECT a.id FROM answers a JOIN session_questions q ON q.id=a.session_question_id WHERE q.session_id=%s) OR target_id IN (SELECT id FROM evaluations WHERE session_id=%s)',(sid,sid,sid))
            cur.execute('DELETE FROM sessions WHERE id=%s',(sid,))
            cur.execute('DELETE FROM tts_assets WHERE id=ANY(%s)',(assets,))
