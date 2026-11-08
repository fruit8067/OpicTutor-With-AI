# AI-assisted: STT 작업의 DB 연결 회귀 테스트는 OpenAI Codex의 도움으로 작성했습니다.
# 후속 수정: v3 비동기 STT 계약(접수 즉시 전진, 제출 후 STT 대기) 반영은 Claude(Anthropic)의 도움으로 작성되었습니다.
# OWNER: worker-stt (contracts.yaml ownership)
from uuid import uuid4
from threading import Event
import pytest
from app import db
from app.db.dev import seed_session,seed_queued_answer
from app.db.pool import tx
from app.stt import job
from app.schemas.internal import SttResult,WordTS
from app.worker.runner import execute
from app.worker.errors import RetryableJobError
from test_stt_audio import wav


@pytest.fixture
def session():
    if not db.ping(): pytest.skip('로컬 PostgreSQL 미실행')
    db.init_db();sid=seed_session(status='in_progress')
    yield sid
    with tx() as cur:
        cur.execute('DELETE FROM jobs WHERE target_id=%s OR target_id IN (SELECT a.id FROM answers a JOIN session_questions q ON q.id=a.session_question_id WHERE q.session_id=%s)',(sid,sid))
        cur.execute('DELETE FROM sessions WHERE id=%s',(sid,))


def test_real_corrupt_and_silence_are_final_and_do_not_move_order(session,tmp_path):
    # v3: 순서는 업로드 접수 때 이미 전진한다. 거부는 재녹음 요청이 아니라 종결 상태(인식 불가 문항)다.
    for no,(filename,reason) in enumerate([('silence.wav','silence'),('corrupt.webm','corrupt')],1):
        path=tmp_path/filename
        if reason=='silence': wav(path,3)
        else: path.write_bytes(b'corrupt')
        aid=seed_queued_answer(session,str(path))
        assert db.get_session(session)['current_order_no']==no+1
        job.handle(dict(id=uuid4(),target_id=aid,type='stt',attempts=1,max_attempts=3,payload={'stt_attempt':1},_cancel=Event()))
        answer=db.get_answer(aid)
        assert answer['stt_status']=='rejected' and answer['reject_reason']==reason
        assert db.get_session(session)['current_order_no']==no+1


def test_processing_answer_is_recovered_and_old_attempt_is_ignored(session,tmp_path,monkeypatch):
    aid=seed_queued_answer(session,str(wav(tmp_path/'answer.wav',3)))
    worker='crashed-'+uuid4().hex
    original=db.claim_job(['stt'],worker,60)
    assert original['target_id']==aid
    assert db.mark_stt_processing(aid)
    with tx() as cur: cur.execute("UPDATE jobs SET locked_until=now()-interval '1 second' WHERE id=%s",(original['id'],))
    db.recover_expired_jobs()
    replacement='new-'+uuid4().hex
    recovered=db.claim_job(['stt'],replacement,60)
    assert recovered['attempts']==2
    monkeypatch.setattr(job,'transcribe',lambda path:SttResult(text='I walk every weekend.',words=[WordTS(word='I',start=0,end=.2),
        WordTS(word='walk',start=.3,end=.6)],duration_sec=3,speech_segments=[(.1,2)]))
    assert execute(recovered,replacement,60,Event())=='done'
    assert db.get_answer(aid)['stt_status']=='done' and db.get_session(session)['current_order_no']==2
    assert db.get_answer(aid)['stt_version'].startswith('faster-whisper:')
    stale={**recovered,'payload':{'stt_attempt':0}}
    job.handle(stale)
    assert db.get_session(session)['current_order_no']==2


def test_file_publication_race_is_retried_not_rejected(session,tmp_path):
    aid=seed_queued_answer(session,str(wav(tmp_path/'answer.wav',3)))
    pending=tmp_path/'not-published-yet.wav'
    with tx() as cur: cur.execute('UPDATE answers SET audio_path=%s WHERE id=%s',(str(pending),aid))
    work=dict(id=uuid4(),target_id=aid,type='stt',attempts=1,max_attempts=3,payload={'stt_attempt':1},_cancel=Event())
    with pytest.raises(RetryableJobError,match='STT_DECODE_ERROR'): job.handle(work)
    assert db.get_answer(aid)['stt_status']=='processing'
    wav(pending,3)
    work['attempts']=2
    job.handle(work)
    assert db.get_answer(aid)['reject_reason']=='silence'
    assert db.get_session(session)['current_order_no']==2
