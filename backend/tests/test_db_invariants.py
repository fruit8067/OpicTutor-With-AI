# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성되었습니다.
# OWNER: data-layer (contracts.yaml ownership)
"""실제 로컬 PostgreSQL에서 핵심 트랜잭션 불변 조건을 확인한다."""
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
import hashlib

import pytest
from psycopg.errors import CheckViolation, UniqueViolation
from app import db
from app.db.pool import tx
from app.errors import AppError
from app.schemas.internal import SessionQuestionIn


@pytest.fixture(scope='module', autouse=True)
def database():
    if not db.ping():
        pytest.skip('로컬 PostgreSQL/pgvector 미실행')
    db.init_db()
    db.init_db()


def questions():
    return [SessionQuestionIn(order_no=n, question_id=f'fixture-{n}', question_version='fixture',
        question_text=f'Question {n}', question_type='self_intro' if n == 1 else 'description',
        is_scored=n != 1, target_functions=['self_introduce' if n == 1 else 'describe'],
        target_time_frames=['present'], context_scope=['personal_familiar']) for n in range(1, 9)]


@pytest.fixture
def session():
    sid, _ = db.create_session(client_request_id=str(uuid4()), scenario_id='test',
        settings_json={'coverage': {'warnings': ['fixture']}}, questions=questions(), replaces_session_id=None)
    yield sid
    with tx() as cur:
        cur.execute('DELETE FROM ai_requests WHERE job_id IN (SELECT id FROM jobs WHERE target_id IN (SELECT id FROM evaluations WHERE session_id=%s))', (sid,))
        cur.execute('DELETE FROM jobs WHERE target_id=%s OR target_id IN (SELECT a.id FROM answers a JOIN session_questions q ON q.id=a.session_question_id WHERE q.session_id=%s) OR target_id IN (SELECT id FROM evaluations WHERE session_id=%s)', (sid,sid,sid))
        cur.execute('UPDATE sessions SET result_id=NULL WHERE id=%s', (sid,))
        cur.execute('DELETE FROM sessions WHERE id=%s', (sid,))


def ready(sid):
    with tx() as cur:
        cur.execute("UPDATE sessions SET status='ready' WHERE id=%s", (sid,))
    db.start_session(sid)


def answer(sid, no, key=None):
    return db.create_answer(session_id=sid, order_no=no, client_request_id=key or str(uuid4()),
        audio_path='fixture', audio_mime='audio/webm', audio_bytes=100, audio_hash='fixture',
        client_duration_ms=3000, answer_id=uuid4())


def complete(aid):
    return db.complete_stt(aid, text='This is a test.', timestamps=[], metrics={}, stt_version='fixture')


def test_concurrent_session_and_answer_idempotency(session):
    key = str(uuid4())
    def create(_):
        return db.create_session(client_request_id=key, scenario_id='test', settings_json={},
            questions=questions(), replaces_session_id=None)
    with ThreadPoolExecutor(max_workers=5) as ex:
        rows = list(ex.map(create, range(5)))
    assert len({r[0] for r in rows}) == 1 and sum(r[1] for r in rows) == 1
    sid = rows[0][0]
    with tx() as cur:
        cur.execute('DELETE FROM jobs WHERE target_id=%s',(sid,))
        cur.execute('DELETE FROM sessions WHERE id=%s',(sid,))
    ready(session)
    key = str(uuid4())
    with ThreadPoolExecutor(max_workers=5) as ex:
        rows = list(ex.map(lambda _: answer(session,1,key),range(5)))
    assert len({r[0]['id'] for r in rows}) == 1 and sum(r[1] for r in rows) == 1
    with ThreadPoolExecutor(max_workers=10) as ex:
        results = list(ex.map(lambda _: complete(rows[0][0]['id']),range(10)))
    assert {r['current_order_no'] for r in results} == {2}
    assert db.get_session(session)['current_order_no'] == 2
    assert answer(session,1,key)[1] is False


def test_late_prepare_and_warmup_unique(session):
    assert db.fail_prepare(session,1,[{'error_code':'TTS_FILE_MISSING'}])
    assert db.retry_prepare(session) == 2
    assert not db.fail_prepare(session,1,[])
    assert not db.complete_prepare(session,1,{}, {})
    db.cancel_session(session)
    assert not db.complete_prepare(session,2,{}, {})
    with pytest.raises(UniqueViolation):
        with tx() as cur:
            cur.execute('UPDATE session_questions SET is_scored=false WHERE session_id=%s AND order_no=2',(session,))


def test_submit_regrade_and_grade_constraints(session):
    ready(session)
    with pytest.raises(AppError, match='NOT_ALL_ANSWERED'):
        db.submit_session(session)
    for n in range(1,9):
        complete(answer(session,n)[0]['id'])
    eid=db.submit_session(session)
    assert db.submit_session(session) == eid
    snap=db.load_exam_snapshot(session,db.get_session(session)['selected_answer_ids'])
    assert len(snap)==8 and snap[0]['is_scored'] is False and snap[-1]['stt_version']=='fixture'
    assert db.fail_evaluation(eid,'LLM_TRANSIENT',None)
    new=db.create_regrade(session)
    assert new!=eid and db.create_regrade(session)==new
    assert not db.fail_evaluation(eid,'OLD',None)
    kwargs=dict(result={},assessment_status='assessed',base_level='IM',estimated_level='AL',im_estimation_status='provisional',
        model='fixture',prompt_version='opic-evaluation-system-v3',rubric_version='performance-feedback-actfl-speaking-v3',
        im_rubric_version='project-im-v1',corpus_version='fixture',retrieved_doc_ids=[])
    with pytest.raises(CheckViolation): db.finish_evaluation(new,**kwargs)
    kwargs['estimated_level']='IM2'
    assert not db.finish_evaluation(eid,**kwargs)
    assert db.finish_evaluation(new,**kwargs)
    assert not db.fail_evaluation(new,'LATE',None)
    assert db.get_session(session)['result_id']==new


def test_pending_retry_and_order(session):
    ready(session)
    aid=answer(session,1)[0]['id']
    with pytest.raises(AppError,match='ANSWER_PENDING'): answer(session,1)
    with pytest.raises(AppError,match='ORDER_MISMATCH'): answer(session,2)
    db.fail_stt(aid,'STT_ENGINE_ERROR');db.retry_stt(aid)
    assert db.get_answer(aid)['stt_attempt']==2
    db.reject_stt(aid,'silence')
    newer=answer(session,1)[0]['id']
    requests=db.get_session_question(session,1)['client_request_ids']
    assert set(requests)=={db.get_answer(aid)['client_request_id'],db.get_answer(newer)['client_request_id']}
    complete(newer)
    with pytest.raises(AppError): complete(aid)
    assert db.get_session(session)['current_order_no']==2


def test_job_claims_and_lease(session):
    with tx() as cur:
        cur.execute("UPDATE jobs SET next_run_at=now()+interval '1 day' WHERE target_id=%s",(session,))
        for i in range(2):
            cur.execute("INSERT INTO jobs(type,target_id,dedupe_key,status) VALUES ('stt',%s,%s,'queued')",(session,str(uuid4())))
    with ThreadPoolExecutor(max_workers=2) as ex:
        jobs=list(ex.map(lambda w:db.claim_job(['stt'],w,60),['fixture-1','fixture-2']))
    assert all(jobs) and jobs[0]['id']!=jobs[1]['id']
    for j in jobs:
        assert not db.heartbeat_job(j['id'],'wrong',60)
        assert db.heartbeat_job(j['id'],j['locked_by'],60)
        with tx() as cur:
            cur.execute("UPDATE jobs SET locked_until=now()-interval '1 second' WHERE id=%s",(j['id'],))
        assert not db.heartbeat_job(j['id'],j['locked_by'],60)
    assert db.recover_expired_jobs()>=2


def test_expired_last_attempt_can_be_recovered(session):
    with tx() as cur:
        cur.execute("UPDATE jobs SET next_run_at=now()+interval '1 day' WHERE target_id=%s",(session,))
        cur.execute("""INSERT INTO jobs(type,target_id,dedupe_key,status,max_attempts)
            VALUES ('stt',%s,%s,'queued',1) RETURNING id""",(session,str(uuid4())))
        jid=cur.fetchone()['id']
    job=db.claim_job(['stt'],'crashed-worker',60)
    assert job['id']==jid and job['attempts']==1
    with tx() as cur:
        cur.execute("UPDATE jobs SET locked_until=now()-interval '1 second' WHERE id=%s",(jid,))
    assert db.recover_expired_jobs()>=1
    recovered=db.claim_job(['stt'],'replacement-worker',60)
    assert recovered is not None and recovered['id']==jid
    # 재시도 상한은 핸들러가 보고한 실패에 적용한다. 리스 만료만으로 대상 답변을 고립시키지 않는다.
    assert db.fail_job(jid,'replacement-worker',error_code='STT_ENGINE_ERROR',retryable=True)=='dead'


def test_prepare_links_are_atomic(session):
    question_links={};host_links={};asset_ids=[]
    # Python strip이 제거하는 Unicode 공백도 TTS manifest와 같은 해시로 연결한다.
    with tx() as cur:
        cur.execute('UPDATE session_questions SET question_text=%s WHERE session_id=%s AND order_no=1',
                    ('\t \u2003Question 1\n\u00a0',session))
    for q in questions():
        asset=db.upsert_tts_asset(kind='question',ref_id=q.question_id,
            text_hash=hashlib.sha1(q.question_text.encode()).hexdigest(),voice_id=str(session),settings_version='fixture',
            file_path=f'fixture/{q.question_id}.mp3',duration_sec=3)
        question_links[q.order_no]=asset;asset_ids.append(asset)
    for key in ['greeting','say_again','next','finish']:
        asset=db.upsert_tts_asset(kind='host',ref_id=key,text_hash='fixture',voice_id=str(session),
            settings_version='fixture',file_path=f'fixture/{key}.mp3',duration_sec=3)
        host_links[key]=asset;asset_ids.append(asset)
    try:
        with pytest.raises(AppError): db.complete_prepare(session,1,{1:question_links[1]},host_links)
        assert db.get_session(session)['status']=='preparing'
        assert db.complete_prepare(session,1,question_links,host_links)
        assert db.get_session(session)['status']=='ready'
        assert len(db.get_session(session)['host_lines'])==4
        assert all(q['file_path'] for q in db.list_session_questions(session))
        assert not db.complete_prepare(session,1,question_links,host_links)
    finally:
        # 세션 FK를 먼저 제거하고 테스트가 만든 자산만 정리한다.
        with tx() as cur:
            cur.execute('DELETE FROM session_host_lines WHERE session_id=%s',(session,))
            cur.execute('UPDATE session_questions SET tts_asset_id=NULL WHERE session_id=%s',(session,))
            cur.execute('DELETE FROM tts_assets WHERE id=ANY(%s)',(asset_ids,))
