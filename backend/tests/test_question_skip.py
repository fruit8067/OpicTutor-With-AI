# AI-assisted: 문항 건너뛰기 테스트는 Claude(Anthropic)의 도움으로 작성되었습니다.
# OWNER: session-api (contracts.yaml ownership)
"""문항 건너뛰기(Q3): 실제 DB 흐름, 채점 입력 검증, 프롬프트 표시."""
import hashlib
from uuid import uuid4,UUID
import pytest
from fastapi.testclient import TestClient
from app import db,tts
from app.main import app
from app.config import settings
from app.db.pool import tx
from app.grading.validate import precheck_snapshot,validate_output
from app.grading.prompt import build_messages
from app.schemas.internal import EvaluationLLMOutput,EvidenceBundle
from app.worker.errors import PermanentJobError
from app.llm.chat import LLMOutputError
from test_exam_builder import corpus  # noqa: F401  (fixture)
from test_grading_validate import snapshot,output

METRICS=dict(duration_sec=3,speech_sec=2,word_count=5,wpm=100,articulation_wpm=150,
    long_pause_count=0,observed_filler_per100=None,metrics_version='m1')


def skipped_rows(*orders):
    rows=snapshot()
    for row in rows:
        row['skipped']=row['order_no'] in orders
        if row['skipped']: row.update(answer_id=None,stt_status=None,stt_text=None,metrics=None,stt_version=None)
    return rows


def test_skipped_rows_pass_precheck_but_not_unskipped_missing_answers():
    precheck_snapshot(skipped_rows(3,5))
    rows=skipped_rows();rows[2].update(stt_status=None,stt_text=None)
    with pytest.raises(PermanentJobError): precheck_snapshot(rows)
    rows=skipped_rows(3);rows[2]['stt_text']='leftover'
    with pytest.raises(PermanentJobError): precheck_snapshot(rows)


def test_skipped_question_must_be_unusable_and_not_assessable():
    rows=skipped_rows(3)
    raw=output(rows)
    with pytest.raises(LLMOutputError): validate_output(EvaluationLLMOutput.model_validate(raw),rows)
    raw['evaluation_scope'].update(usable_order_nos=[n for n in range(2,9) if n!=3],unusable_items=[dict(order_no=3,reason='사용자가 건너뜀')])
    for entries in raw['coverage'].values():
        for entry in entries: entry['usable_order_nos']=[n for n in entry['usable_order_nos'] if n!=3]
    raw['fact_evidence']=[f for f in raw['fact_evidence'] if f['order_no']!=3]
    raw['feedback_cards'][1]['related_order_nos']=[5]
    raw['items'][2].update(task_fulfillment='not_assessable',evidence=[])
    assert validate_output(EvaluationLLMOutput.model_validate(raw),rows).assessment_status=='assessed'


def test_prompt_marks_skipped_question():
    rows=skipped_rows(4)
    text=build_messages(rows,EvidenceBundle())[1]['content']
    assert '<transcript status="skipped"/>' in text and '&quot;skipped&quot;: true' in text


def test_real_db_skip_flow(corpus,tmp_path,monkeypatch):  # noqa: F811
    if not db.ping(): pytest.skip('로컬 PostgreSQL/pgvector 미실행')
    db.init_db()
    monkeypatch.setattr(settings,'DATA_DIR',tmp_path/'data')
    monkeypatch.setattr(tts,'tts_url',lambda path:'/media/tts/'+path)
    client=TestClient(app)
    created=client.post('/api/v1/sessions',json={'client_request_id':str(uuid4()),'mic_check_passed':True})
    sid=UUID(created.json()['session_id']);prefix=f'/api/v1/sessions/{sid}'
    assets=[]
    try:
        links={};hosts={}
        for q in db.list_session_questions(sid):
            aid=db.upsert_tts_asset(kind='question',ref_id=q['question_id'],text_hash=hashlib.sha1(q['question_text'].encode()).hexdigest(),
                voice_id=str(sid),settings_version='fixture',file_path=q['question_id']+'.mp3',duration_sec=3)
            links[q['order_no']]=aid;assets.append(aid)
        for key,text in tts.HOST_LINES.items():
            aid=db.upsert_tts_asset(kind='host',ref_id=key,text_hash=hashlib.sha1(text.encode()).hexdigest(),voice_id=str(sid),
                settings_version='fixture',file_path=key+'.mp3',duration_sec=3)
            hosts[key]=aid;assets.append(aid)
        assert client.post(prefix+'/questions/1/skip').json()['error']['code']=='INVALID_STATE'  # 시작 전
        assert db.complete_prepare(sid,1,links,hosts)
        client.post(prefix+'/start')
        assert client.post(prefix+'/questions/2/skip').json()['error']['code']=='ORDER_MISMATCH'
        skipped={1,4,8}
        for no in range(1,9):
            if no in skipped:
                r=client.post(prefix+f'/questions/{no}/skip')
                assert r.status_code==200 and r.json()['current_order_no']==no+1
                assert client.post(prefix+f'/questions/{no}/skip').json()==r.json()      # 멱등
                continue
            key=str(uuid4())
            up=client.post(prefix+'/answers',data={'order_no':no,'client_request_id':key,'duration_ms':3000},
                files={'audio':('a.webm',b'fixture audio','audio/webm')})
            assert up.status_code==202
            assert client.post(prefix+f'/questions/{no}/skip').json()['error']['code']=='ANSWER_PENDING'
            db.complete_stt(UUID(up.json()['answer_id']),text='This is a test answer.',timestamps=[],metrics=METRICS,stt_version='fixture')
        assert client.get(prefix+'/current').json()['all_answered']
        assert client.post(prefix+'/submit').status_code==202
        s=db.get_session(sid)
        assert len(s['selected_answer_ids'])==5
        rows=db.load_exam_snapshot(sid,s['selected_answer_ids'])
        assert {r['order_no'] for r in rows if r['skipped']}==skipped
        precheck_snapshot(rows)
        answers=client.get(prefix+'/result').json()['answers']
        assert [a['order_no'] for a in answers if a['skipped']]==sorted(skipped)
        assert all(a['stt_text'] is None and a['metrics'] is None for a in answers if a['skipped'])
    finally:
        with tx() as cur:
            cur.execute('DELETE FROM jobs WHERE target_id=%s OR target_id IN (SELECT a.id FROM answers a JOIN session_questions q ON q.id=a.session_question_id WHERE q.session_id=%s) OR target_id IN (SELECT id FROM evaluations WHERE session_id=%s)',(sid,sid,sid))
            cur.execute('DELETE FROM sessions WHERE id=%s',(sid,))
            cur.execute('DELETE FROM tts_assets WHERE id=ANY(%s)',(assets,))
