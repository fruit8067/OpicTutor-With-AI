# AI-assisted: M1 개발용 시험 데이터 검증은 OpenAI Codex의 도움으로 작성했습니다.
# OWNER: data-layer (contracts.yaml ownership)
import json
import pytest
from app import db,exam
from app.config import settings
from app.db import dev
from app.db.pool import tx
from app.errors import AppError
from app.schemas.internal import SessionQuestionIn


def bank():
    kinds=['self_intro','description','routine','past_experience','comparison','roleplay_ask','roleplay_solve','issue']
    return [SessionQuestionIn(order_no=n,question_id=f'fixture-Q{n}',question_version='fixture',question_text='Tell me about your day.',
        question_type=kind,is_scored=n!=1,target_functions=['self_introduce' if n==1 else 'describe'],
        target_time_frames=['present'],context_scope=['personal_familiar']) for n,kind in enumerate(kinds,1)]


@pytest.fixture
def corpus(tmp_path,monkeypatch):
    monkeypatch.setattr(settings,'RAG_BUILD_DIR',tmp_path)
    monkeypatch.setattr(dev,'seed_questions',lambda scenario:bank())
    rows=[dict(question_id=q.question_id,level='IM2',text_style='stt',answer_text='I enjoy walking with my friends.',est_seconds=30)
          for q in bank()[1:]]
    (tmp_path/'answers.jsonl').write_text('\n'.join(json.dumps(row) for row in rows),encoding='utf-8')
    return tmp_path,rows


def test_grading_seed_works_without_optional_warmup_and_leaves_no_stt_work(corpus):
    if not db.ping(): pytest.skip('로컬 PostgreSQL 미실행')
    db.init_db();sid,eid=dev.seed_grading_session()
    try:
        session=db.get_session(sid)
        rows=db.load_exam_snapshot(sid,session['selected_answer_ids'])
        assert session['status']=='grading' and session['settings_json']['fixed_warmup']
        assert len(rows)==8 and not rows[0]['is_scored']
        assert rows[0]['stt_version']=='dev:synthetic-fixed-warmup:v1'
        assert all(row['stt_status']=='done' for row in rows)
        with tx() as cur:
            cur.execute("SELECT count(*) AS n FROM jobs WHERE type='stt' AND status='queued' AND target_id=ANY(%s)",
                        (session['selected_answer_ids'],))
            assert cur.fetchone()['n']==0
        assert db.get_evaluation(eid)['status']=='queued'
    finally:
        with tx() as cur:
            cur.execute('DELETE FROM jobs WHERE target_id=%s OR target_id=%s OR target_id IN (SELECT a.id FROM answers a JOIN session_questions q ON q.id=a.session_question_id WHERE q.session_id=%s)',(sid,eid,sid))
            cur.execute('DELETE FROM sessions WHERE id=%s',(sid,))


@pytest.mark.parametrize('mode',['missing','empty_text','nonfinite_duration'])
def test_invalid_scored_seed_fails_before_creating_a_partial_session(corpus,mode):
    if not db.ping(): pytest.skip('로컬 PostgreSQL 미실행')
    db.init_db();folder,rows=corpus
    if mode=='missing': rows=rows[1:]
    elif mode=='empty_text': rows[0]['answer_text']=''
    else: rows[0]['est_seconds']=float('nan')
    (folder/'answers.jsonl').write_text('\n'.join(json.dumps(row) for row in rows),encoding='utf-8')
    with tx() as cur: cur.execute('SELECT count(*) AS n FROM sessions');before=cur.fetchone()['n']
    with pytest.raises(ValueError,match='fixture-Q2'): dev.seed_grading_session()
    with tx() as cur: cur.execute('SELECT count(*) AS n FROM sessions');assert cur.fetchone()['n']==before


def test_dev_seed_does_not_replace_an_unsupported_scenario(monkeypatch):
    def unsupported(*args): raise AppError('SCENARIO_UNAVAILABLE')
    monkeypatch.setattr(exam,'build_question_set',unsupported)
    with pytest.raises(AppError,match='SCENARIO_UNAVAILABLE'): dev.seed_questions('missing-scenario')


def test_stub_fallback_reads_canonical_question_field_without_text_alias(tmp_path,monkeypatch):
    rows=[dict(id=q.question_id,status='pilot',question=q.question_text,**{
        k:getattr(q,k) for k in ['question_type','is_scored','target_functions','target_time_frames','context_scope']}) for q in bank()]
    (tmp_path/'questions.jsonl').write_text('\n'.join(json.dumps(row) for row in rows),encoding='utf-8')
    monkeypatch.setattr(settings,'RAG_BUILD_DIR',tmp_path)
    def missing(*args): raise NotImplementedError()
    monkeypatch.setattr(exam,'build_question_set',missing)
    assert len(dev.seed_questions('default'))==8
    with pytest.raises(AppError,match='SCENARIO_UNAVAILABLE'): dev.seed_questions('missing-scenario')
