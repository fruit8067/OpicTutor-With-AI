# AI-assisted: 실제 로컬 ASR/워커 검증은 OpenAI Codex의 도움으로 작성했습니다.
"""Run the real worker CLI and cached Whisper on an existing synthetic sample.

No C code, inference mock, microphone recording, or external provider call is used.
Creates and drops an isolated PostgreSQL database; original audio/model files are read only.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from uuid import uuid4
from verify_core import compose_sources


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',type=Path,required=True)
    parser.add_argument('--audio',type=Path)
    parser.add_argument('--report',type=Path)
    parser.add_argument('--answers',type=int,choices=[1,8],default=1)
    parser.add_argument('--child',action='store_true',help=argparse.SUPPRESS)
    args=parser.parse_args()
    sources=compose_sources(args.workspace,emit_manifest=not args.child)
    if args.child:
        sys.argv=['app.worker','--types','stt','--once']
        from app.worker.__main__ import main as worker_main
        return worker_main()
    if args.audio is None or not args.audio.is_file(): parser.error('--audio must name an existing synthetic sample')
    audio=args.audio.resolve()
    import psycopg
    from psycopg import sql
    from psycopg.conninfo import make_conninfo
    from app import db
    from app.config import settings
    from app.db import pool
    from app.db.dev import seed_session
    from app.stt.audio import probe_audio
    if pool._pool is not None: raise RuntimeError('Run this verifier in a fresh Python process.')
    probe=probe_audio(audio)
    if not probe.ok: raise ValueError('Synthetic audio rejected: '+str(probe.reason))
    database='opic_ab_native_'+uuid4().hex[:16]
    cache=args.workspace.resolve()/'OpicTutor-With-AI/data'
    if not (cache/'models/models--Systran--faster-whisper-small.en').is_dir():
        parser.error('Expected cached small.en model; this verifier does not download weights.')
    with psycopg.connect(settings.DATABASE_URL,autocommit=True) as admin:
        admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(database)))
        settings.DATABASE_URL=make_conninfo(settings.DATABASE_URL,dbname=database)
        try:
            db.init_db()
            if args.answers==8:
                return full_http_exam(args,sources,audio,probe,cache,settings,db,pool)
            sid=seed_session(status='in_progress');aid=uuid4()
            db.create_answer(session_id=sid,order_no=1,client_request_id=uuid4().hex,audio_path=str(audio),
                audio_mime='audio/wav',audio_bytes=audio.stat().st_size,audio_hash=hashlib.sha256(audio.read_bytes()).hexdigest(),
                client_duration_ms=round(probe.duration_sec*1000),answer_id=aid)
            environment={**os.environ,'DATABASE_URL':settings.DATABASE_URL,'DATA_DIR':str(cache),
                'WHISPER_MODEL':'small.en','WHISPER_DEVICE':'cpu','WHISPER_COMPUTE_TYPE':'int8',
                'HF_HUB_OFFLINE':'1','WORKER_ID':'native-check-'+uuid4().hex}
            started=time.monotonic()
            child=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--workspace',str(args.workspace),'--child'],
                env=environment,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=120)
            elapsed=time.monotonic()-started
            row=db.get_answer(aid);session=db.get_session(sid)
            with pool.tx() as cur:
                cur.execute("SELECT status,attempts FROM jobs WHERE type='stt' AND target_id=%s",(aid,))
                job=cur.fetchone()
            transcript=row.get('stt_text') or ''
            result={'scope':'Real worker CLI + cached faster-whisper small.en + real DB; synthetic SAPI audio, not microphone',
                'worker_exit_code':child.returncode,'elapsed_sec_including_startup':round(elapsed,3),
                'audio_sha256':hashlib.sha256(audio.read_bytes()).hexdigest(),'audio_duration_sec':probe.duration_sec,
                'answer_status':row['stt_status'],'session_order_no':session['current_order_no'],'job':job,
                'stt_version':row['stt_version'],'metrics':row.get('metrics_json'),
                'transcript_nonempty':bool(transcript.strip()),
                'synthetic_expected_keywords_observed':all(word in transcript.casefold() for word in ['park','weekend']),
                'transcript_absent_from_worker_logs':bool(transcript) and transcript not in child.stdout+child.stderr,
                'external_llm_requests':db.count_ai_requests('evaluate'),'external_embedding_requests':db.count_ai_requests('embed'),
                'model_network_disabled':True,'microphone_used':False,'c_implementation_added':False,
                'sources':{role:subprocess.check_output(['git','rev-parse','HEAD'],cwd=path,text=True).strip()
                           for role,path in sources.items()}}
            if not (child.returncode==0 and row['stt_status']=='done' and session['current_order_no']==2
                    and job=={'status':'done','attempts':1} and result['transcript_nonempty']
                    and result['transcript_absent_from_worker_logs']
                    and result['external_llm_requests']==result['external_embedding_requests']==0):
                print(json.dumps(result,ensure_ascii=True),flush=True)
                raise RuntimeError('Native worker verification failed; child stderr tail: '+child.stderr[-1500:])
            if args.report:
                args.report.parent.mkdir(parents=True,exist_ok=True)
                args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            print(json.dumps(result,ensure_ascii=True),flush=True)
        finally:
            if pool._pool is not None: pool._pool.close()
            admin.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(database)))
    return 0


def full_http_exam(args,sources,audio,probe,cache,settings,db,pool):
    from fastapi.testclient import TestClient
    from app.main import app
    from app import tts
    from uuid import UUID
    testing=(cache/'testing').resolve();testing.mkdir(exist_ok=True)
    # Only this verifier-owned directory is recursively cleaned; the original sample/model cache is untouched.
    with tempfile.TemporaryDirectory(prefix='native-ab-',dir=testing) as temporary:
        managed=Path(temporary).resolve()
        if managed.parent!=testing: raise RuntimeError('Unexpected temporary audio directory')
        settings.DATA_DIR=managed
        tts.tts_url=lambda file_path:'/media/tts/'+file_path  # Explicit C URL boundary fixture, not a C implementation.
        client=TestClient(app)
        request_key=uuid4().hex
        response=client.post('/api/v1/sessions',json={'client_request_id':request_key,'mic_check_passed':True})
        assert response.status_code==202
        sid=UUID(response.json()['session_id']);base=f'/api/v1/sessions/{sid}'
        questions=db.list_session_questions(sid)
        links={q['order_no']:db.upsert_tts_asset(kind='question',ref_id=q['question_id'],
            text_hash=hashlib.sha1(q['question_text'].strip().encode()).hexdigest(),voice_id='native-fixture',
            settings_version='fixture',file_path=f"fixture/{q['question_id']}.mp3",duration_sec=2) for q in questions}
        hosts={key:db.upsert_tts_asset(kind='host',ref_id=key,text_hash='fixture',voice_id='native-fixture',
            settings_version='fixture',file_path=f'fixture/{key}.mp3',duration_sec=1) for key in tts.HOST_LINES}
        assert db.complete_prepare(sid,1,links,hosts)
        assert client.post(base+'/start').status_code==200
        records=[];clip=audio.read_bytes()
        for order in range(1,9):
            fields={'order_no':order,'client_request_id':uuid4().hex,'duration_ms':round(probe.duration_sec*1000)}
            files={'audio':('synthetic.wav',clip,'audio/wav')}
            accepted=client.post(base+'/answers',data=fields,files=files)
            assert accepted.status_code==202 and accepted.json()['current_order_no']==order
            aid=UUID(accepted.json()['answer_id'])
            replay=client.post(base+'/answers',data=fields,files=files)
            assert replay.status_code==200 and replay.json()['answer_id']==str(aid)
            assert client.post(base+'/submit').status_code==409
            environment={**os.environ,'DATABASE_URL':settings.DATABASE_URL,'DATA_DIR':str(cache),
                'WHISPER_MODEL':'small.en','WHISPER_DEVICE':'cpu','WHISPER_COMPUTE_TYPE':'int8',
                'HF_HUB_OFFLINE':'1','WORKER_ID':'native-check-'+uuid4().hex}
            started=time.monotonic()
            child=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--workspace',str(args.workspace),'--child'],
                env=environment,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=120)
            row=db.get_answer(aid);transcript=row.get('stt_text') or ''
            polled=client.get(base+'/answers/'+str(aid)).json()
            with pool.tx() as cur:
                cur.execute("SELECT status,attempts FROM jobs WHERE type='stt' AND target_id=%s",(aid,))
                job=cur.fetchone()
            assert child.returncode==0 and row['stt_status']=='done' and polled['current_order_no']==order+1
            assert job=={'status':'done','attempts':1} and transcript.strip()
            assert transcript not in child.stdout+child.stderr
            assert db.count_ai_requests('evaluate')==db.count_ai_requests('embed')==0
            record={'order_no':order,'worker_exit_code':child.returncode,'answer_status':row['stt_status'],
                    'session_order_after':polled['current_order_no'],'job':job,'metrics':row['metrics_json'],
                    'worker_sec_including_startup':round(time.monotonic()-started,3),
                    'transcript_logged':False}
            records.append(record)
            print(json.dumps({'native_answer':record},ensure_ascii=True),flush=True)
        assert client.get(base+'/current').json()['all_answered']
        assert client.post(base+'/submit').status_code==202
        first=db.get_latest_evaluation(sid)
        assert client.post(base+'/submit').status_code==202 and db.get_latest_evaluation(sid)['id']==first['id']
        result=client.get(base+'/result').json()
        assert result['session_status']=='grading' and result['evaluation_status']=='queued' and len(result['answers'])==8
        assert [r['order_no'] for r in result['answers'] if not r['is_scored']]==[1]
        report={'scope':'8 real HTTP uploads + 8 native worker CLI/Whisper transcriptions + real DB + submit; C fixtures only',
                'audio_source':'Windows SAPI Zira synthetic English, repeated to exercise transport/ASR, not question-answer quality',
                'audio_sha256':hashlib.sha256(clip).hexdigest(),'audio_duration_sec':probe.duration_sec,
                'model':'small.en','device':'cpu','compute_type':'int8','model_network_disabled':True,
                'microphone_used':False,'c_implementation_added':False,'answers':records,
                'selected_answers':len(db.get_session(sid)['selected_answer_ids']),
                'session_status':result['session_status'],'evaluation_status':result['evaluation_status'],
                'external_llm_requests':db.count_ai_requests('evaluate'),'external_embedding_requests':db.count_ai_requests('embed'),
                'provider_evaluation':'not run; remains queued, not a successful grading claim',
                'sources':{role:subprocess.check_output(['git','rev-parse','HEAD'],cwd=path,text=True).strip()
                           for role,path in sources.items()}}
        if args.report:
            args.report.parent.mkdir(parents=True,exist_ok=True)
            args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({'native_exam_summary':{key:value for key,value in report.items() if key!='answers'}},ensure_ascii=True),flush=True)
    return 0


if __name__=='__main__': raise SystemExit(main())
