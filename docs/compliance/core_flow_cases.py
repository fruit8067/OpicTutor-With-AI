# AI-assisted: A/B 시험 흐름 검증은 OpenAI Codex의 도움으로 작성했습니다.
"""Real HTTP/DB/worker/grading boundaries with explicit TTS and inference fixtures.

Loaded by verify_core.py against isolated A/B modules and a disposable database.
No C implementation or real provider grading quality is claimed.
"""
import json
from pathlib import Path
from threading import Event
from uuid import UUID,uuid4
import hashlib
import math
import wave
from array import array
import httpx
from fastapi.testclient import TestClient
from app import db,tts
from app.main import app
from app.config import settings
from app.db.pool import tx
from app.stt import job as stt_job
from app.grading import job as grading_job
from app.grading.prompt import load_system_prompt
from app.llm import chat
from app.schemas.internal import SttResult,WordTS
from test_grading_validate import output


def claim(kind,worker):
    job=db.claim_job([kind],worker,60)
    assert job is not None
    job['_cancel']=Event()
    job['_lease_valid']=lambda:db.heartbeat_job(job['id'],worker,60)
    return job


def test_core_exam_result_refresh_failure_and_regrade(tmp_path,monkeypatch):
    db.init_db()
    monkeypatch.setattr(settings,'DATA_DIR',tmp_path/'audio-data')
    monkeypatch.setattr(tts,'tts_url',lambda path:'/media/tts/'+path)
    client=TestClient(app)
    key=uuid4().hex
    create={'client_request_id':key,'scenario_id':'default','mic_check_passed':True}
    r=client.post('/api/v1/sessions',json=create)
    assert r.status_code==202 and r.json()['status']=='preparing'
    sid=UUID(r.json()['session_id']);base=f'/api/v1/sessions/{sid}'
    questions=db.list_session_questions(sid)
    before=[(q['question_id'],q['order_no']) for q in questions]
    assert client.post('/api/v1/sessions',json=create).json()['session_id']==str(sid)
    assert client.post(base+'/start').status_code==409
    # C is not implemented here. The fixture registers pre-generated assets and uses the real atomic DB link.
    links={}
    for q in questions:
        links[q['order_no']]=db.upsert_tts_asset(kind='question',ref_id=q['question_id'],
            text_hash=hashlib.sha1(q['question_text'].strip().encode()).hexdigest(),voice_id='core-fixture',
            settings_version='fixture',file_path=f"fixture/{q['question_id']}.mp3",duration_sec=2)
    hosts={k:db.upsert_tts_asset(kind='host',ref_id=k,text_hash='fixture',voice_id='core-fixture',
        settings_version='fixture',file_path=f'fixture/{k}.mp3',duration_sec=1) for k in tts.HOST_LINES}
    assert db.fail_prepare(sid,1,[{'ref_id':questions[0]['question_id'],'error_code':'TTS_FILE_MISSING',
                                'order_no':1,'host_key':None}])
    assert client.post(base+'/prepare/retry').status_code==202
    assert before==[(q['question_id'],q['order_no']) for q in db.list_session_questions(sid)]
    assert not db.complete_prepare(sid,1,links,hosts)
    assert db.complete_prepare(sid,2,links,hosts)
    assert client.post(base+'/start').json()['status']=='in_progress'
    tone=tmp_path/'voice.wav'
    with wave.open(str(tone),'wb') as stream:
        stream.setnchannels(1);stream.setsampwidth(2);stream.setframerate(16000)
        stream.writeframes(array('h',(int(4000*math.sin(i*2*math.pi*220/16000)) for i in range(48000))).tobytes())
    audio=tone.read_bytes()
    def transcribe(path):
        words='I enjoy walking because it helps me relax and meet my friends'.split()
        return SttResult(text=' '.join(words),words=[WordTS(word=w,start=.1+i*.2,end=.2+i*.2) for i,w in enumerate(words)],
                         duration_sec=3,speech_segments=[(.1,2.8)])
    monkeypatch.setattr(stt_job,'transcribe',transcribe)
    for no in range(1,9):
        current=client.get(base+'/current').json()
        assert current['question']['order_no']==no
        request={'order_no':no,'client_request_id':uuid4().hex,'duration_ms':3000}
        files={'audio':('voice.wav',audio,'audio/wav')}
        answer=client.post(base+'/answers',data=request,files=files)
        assert answer.status_code==202 and answer.json()['current_order_no']==no
        aid=answer.json()['answer_id']
        assert client.post(base+'/answers',data=request,files=files).json()['answer_id']==aid
        assert client.post(base+'/submit').status_code==409
        assert db.count_ai_requests('evaluate')==0
        task=claim('stt','core-stt')
        assert str(task['target_id'])==aid
        stt_job.handle(task);db.complete_job(task['id'],'core-stt')
        polled=client.get(base+'/answers/'+aid).json()
        assert polled['stt_status']=='done' and polled['current_order_no']==no+1
    assert client.get(base+'/current').json()['all_answered']
    assert client.post(base+'/submit').status_code==202
    eid=db.get_latest_evaluation(sid)['id']
    assert client.post(base+'/submit').status_code==202 and db.get_latest_evaluation(sid)['id']==eid
    snapshot=db.load_exam_snapshot(sid,db.get_session(sid)['selected_answer_ids'])
    version='core-fixture-'+uuid4().hex
    with tx() as cur:
        for q in questions:
            if not q['is_scored']: continue
            cur.execute("""INSERT INTO rag_docs(id,doc_type,question_id,question_type,level,level_rank,
                contrast_set_id,text_style,text,metadata,corpus_version)
                VALUES (%s,'answer',%s,%s,'IL',4,%s,'stt','synthetic reference','{}',%s)""",
                (version+'-'+q['question_id'],q['question_id'],q['question_type'],q['question_id'],version))
    requests=[];mode={'fail':False}
    def provider(request):
        requests.append(json.loads(request.content))
        if mode['fail']: return httpx.Response(401,json={'error':{'message':'fixture invalid credential'}})
        return httpx.Response(200,json={'id':'core-fixture','object':'chat.completion','created':0,'model':'pickle-fixture',
            'choices':[{'index':0,'message':{'role':'assistant','content':json.dumps(output(snapshot))},'finish_reason':'stop'}],
            'usage':{'prompt_tokens':100,'completion_tokens':50,'total_tokens':150}})
    original=chat.OpenAI
    monkeypatch.setenv('LLM_BASE_URL','https://pickle.example.invalid/v1')
    monkeypatch.setenv('LLM_MODEL','pickle-fixture');monkeypatch.setenv('LLM_API_KEY','local-fixture-only')
    monkeypatch.setattr(chat,'OpenAI',lambda **kwargs:original(**kwargs,http_client=httpx.Client(transport=httpx.MockTransport(provider))))
    task=claim('evaluate','core-grader');grading_job.handle(task);db.complete_job(task['id'],'core-grader')
    result=client.get(base+'/result').json()
    assert result['session_status']=='done' and result['result']['estimated_level']=='IL'
    assert result['result']['evaluation_scope']['feedback_only_order_nos']==[1]
    for _ in range(10): assert client.get(base+'/result').json()==result
    assert len(requests)==db.count_ai_requests('evaluate')==1
    assert requests[0]['messages'][0]=={'role':'system','content':load_system_prompt()[0]}
    user_input=requests[0]['messages'][1]['content']
    assert user_input.count('<item metadata=')==8 and str(settings.DATA_DIR) not in user_input
    frozen=db.get_session(sid)['selected_answer_ids']
    assert client.post(base+'/regrade').status_code==202
    mode['fail']=True;task=claim('evaluate','core-grader')
    try: grading_job.handle(task)
    except Exception as exc:
        assert str(exc)=='EVAL_INTERNAL'
        db.fail_job(task['id'],'core-grader',error_code='EVAL_INTERNAL',retryable=False)
    else: raise AssertionError('invalid credential fixture must fail')
    failed=client.get(base+'/result').json()
    assert failed['session_status']=='grading_failed' and failed['result']==result['result']
    assert db.get_session(sid)['selected_answer_ids']==frozen
    assert client.post(base+'/regrade').status_code==202
    mode['fail']=False;task=claim('evaluate','core-grader')
    grading_job.handle(task);db.complete_job(task['id'],'core-grader')
    final=client.get(base+'/result').json()
    assert final['run_no']==3 and final['session_status']=='done'
    assert len(requests)==db.count_ai_requests('evaluate')==3
