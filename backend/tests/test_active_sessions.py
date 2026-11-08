# AI-assisted: v3 전역 분석 상태 조회(/sessions/active) 테스트는 Claude(Anthropic)의 도움으로 작성되었습니다.
# OWNER: session-api (contracts.yaml ownership)
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from app import db
from app.main import app
from app.db.pool import tx
from test_db_invariants import questions


def register(client):
    res=client.post('/api/v1/auth/register',json={'email':f'v3-{uuid4().hex[:10]}@example.ac.kr','password':'password123','nickname':'v3'})
    assert res.status_code==201
    return res.json()['user']['id'],{'Authorization':'Bearer '+res.json()['token']}


def make_session(user_id,status):
    sid,_=db.create_session(client_request_id=str(uuid4()),scenario_id='test',settings_json={},
        questions=questions(),replaces_session_id=None,user_id=user_id)
    with tx() as cur: cur.execute("UPDATE sessions SET status='ready' WHERE id=%s",(sid,))
    db.start_session(sid)
    ids=[db.create_answer(session_id=sid,order_no=n,client_request_id=str(uuid4()),audio_path='fixture',audio_mime='audio/webm',
        audio_bytes=100,audio_hash='fixture',client_duration_ms=3000,answer_id=uuid4())[0]['id'] for n in range(1,9)] if status!='in_progress' else []
    if status!='in_progress':
        db.submit_session(sid)
        for aid in ids[:5]: db.complete_stt(aid,text='This is a test.',timestamps=[],metrics={},stt_version='fixture')
    if status=='done':
        for aid in ids[5:]: db.complete_stt(aid,text='This is a test.',timestamps=[],metrics={},stt_version='fixture')
        with tx() as cur: cur.execute("UPDATE sessions SET status='done' WHERE id=%s",(sid,))
    return sid


def cleanup(sids):
    with tx() as cur:
        cur.execute("""DELETE FROM jobs WHERE target_id=ANY(%s) OR target_id IN (SELECT a.id FROM answers a JOIN session_questions q
            ON q.id=a.session_question_id WHERE q.session_id=ANY(%s)) OR target_id IN (SELECT id FROM evaluations WHERE session_id=ANY(%s))""",(sids,sids,sids))
        cur.execute('DELETE FROM sessions WHERE id=ANY(%s)',(sids,))


def test_active_sessions_are_user_scoped_and_report_progress():
    if not db.ping(): pytest.skip('로컬 PostgreSQL/pgvector 미실행')
    db.init_db()
    client=TestClient(app)
    assert client.get('/api/v1/sessions/active').status_code==401
    me,headers=register(client);other,other_headers=register(client)
    sids=[]
    try:
        waiting=make_session(me,'submitted');sids.append(waiting)
        running=make_session(me,'in_progress');sids.append(running)
        finished=make_session(me,'done');sids.append(finished)
        sids.append(make_session(other,'submitted'))
        body=client.get('/api/v1/sessions/active',headers=headers).json()
        items={i['session_id']:i for i in body['items']}
        assert set(items)=={str(waiting),str(running)}
        assert items[str(waiting)]['status']=='submitted'
        assert items[str(waiting)]['stt_progress']==dict(total=8,done=5,pending=3,unusable=0)
        assert body['in_progress_session_id']==str(running)
        assert [i['session_id'] for i in body['recent_finished']]==[str(finished)]
        assert body['latest_report_session_id'] in (str(waiting),str(finished))
        others=client.get('/api/v1/sessions/active',headers=other_headers).json()
        assert [i['session_id'] for i in others['items']]==[str(sids[-1])] and others['in_progress_session_id'] is None
        # 제출 후 STT 대기 중인 세션의 결과 조회는 평가 없이 진행 현황을 돌려준다.
        result=client.get(f'/api/v1/sessions/{waiting}/result',headers=headers).json()
        assert result['session_status']=='submitted' and result['evaluation_status'] is None
        assert result['stt_progress']['pending']==3
        assert client.get(f'/api/v1/sessions/{waiting}/result',headers=other_headers).status_code==403
    finally:
        cleanup(sids)
