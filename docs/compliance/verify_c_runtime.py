# AI-assisted: C/실제 A/B 경계 검증은 OpenAI Codex의 도움으로 작성되었습니다.
"""Pre-merge C browser + real HTTP/DB/TTS/jobs. STT text and grading inference are fixtures.

Run from the repo with an activated venv:
python docs/compliance/verify_c_runtime.py --workspace .. --frontend-url http://127.0.0.1:5175 --report docs/compliance/c-runtime.json
The frontend must load its owned C Host modules (not bootstrap stubs).
"""
import argparse
import importlib.util
import json
import hashlib
import shutil
from collections import Counter
import socket
import sys
import tempfile
import threading
import time
from pathlib import Path
from uuid import uuid4
from urllib.parse import urlsplit
from verify_core import compose_sources,package


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',type=Path,required=True)
    parser.add_argument('--frontend-url',required=True)
    parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args();root=args.workspace.resolve()
    from dotenv import load_dotenv
    primary=root if (root/'backend/app').is_dir() else root/'OpicTutor-With-AI'
    load_dotenv(primary/'backend/.env',override=False)
    args.frontend_url=args.frontend_url.rstrip('/')
    sources=compose_sources(root)
    tts=root/'OpicTutor-tts'
    package('app.tts',tts/'backend/app/tts')
    # Import the owner's import script explicitly, without inheriting its production files.
    spec=importlib.util.spec_from_file_location('owned_import_tts',tts/'backend/scripts/import_tts.py')
    importer=importlib.util.module_from_spec(spec);spec.loader.exec_module(importer)
    from app import db
    from app.config import settings
    from app.db import pool
    from app.schemas.internal import SttResult,WordTS,EvaluationLLMOutput
    from app.grading.validate import validate_output
    import app.stt.job as stt_job
    import app.grading.job as grade_job
    from app.worker.runner import execute
    import psycopg
    from psycopg import sql
    from psycopg.conninfo import make_conninfo
    import uvicorn
    from playwright.sync_api import sync_playwright,expect
    # Existing validated synthetic output factory. The fixture bypasses inference only.
    sys.path.insert(0,str(sources['grader']/'backend/tests'))
    from test_grading_validate import output
    def transcribe(path):
        text='I enjoy walking because it helps me relax. I walk near my home every day.'
        words=text.split();duration=2.2
        return SttResult(text=text,words=[WordTS(word=w,start=i*duration/len(words),end=(i+1)*duration/len(words)) for i,w in enumerate(words)],duration_sec=duration,speech_segments=[(0,duration)])
    def evaluate(snapshot,job_id=None):
        result=validate_output(EvaluationLLMOutput.model_validate(output(snapshot)),snapshot)
        return result,{'model':'C-audit-fixture','prompt_version':'opic-evaluation-system-v3+audit-fixture',
            'corpus_version':None,'retrieved_doc_ids':[]}
    stt_job.transcribe=transcribe
    grade_job.evaluate_exam=evaluate
    database='opic_c_browser_'+uuid4().hex[:16]
    stop=threading.Event();server=None;worker=None;server_thread=None;errors=[];requests=[];outcomes=[]
    report={'scope':'real Chromium + C frontend/Host + composed A/B HTTP/PostgreSQL/jobs and actual OmniVoice assets',
        'fixtures':['STT transcript generation','grading inference'],'human_microphone':False,'paid_requests':0}
    with psycopg.connect(settings.DATABASE_URL,autocommit=True,connect_timeout=5) as admin:
        admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(database)))
        settings.DATABASE_URL=make_conninfo(settings.DATABASE_URL,dbname=database)
        try:
            with tempfile.TemporaryDirectory(prefix='opic-c-browser-') as tmp:
                tmp=Path(tmp);settings.DATA_DIR=tmp/'data';settings.TTS_DIR=tmp/'tts'
                settings.CORS_ORIGINS=args.frontend_url
                settings.TTS_DIR.mkdir();settings.DATA_DIR.mkdir()
                importer.BACKEND=tmp/'backend'
                db.init_db()
                voice=json.loads((tts/'backend/static/tts/active_voice.json').read_text(encoding='utf-8'))['voice_id']
                assert importer.main([str(tts/'backend/static/tts'/voice),'--activate'])==0
                # Exercise the actual worker executor, including claims/leases/completion.
                def run_jobs():
                    while not stop.wait(.05):
                        try:
                            job=db.claim_job(['tts_prepare','stt','evaluate'],'c-browser-audit',60)
                            if job:outcomes.append({'type':job['type'],'result':execute(job,'c-browser-audit',60,stop)})
                        except Exception as exc:errors.append(type(exc).__name__);stop.set()
                worker=threading.Thread(target=run_jobs,daemon=True);worker.start()
                from app.main import app
                with socket.socket() as probe:probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
                server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=port,log_level='error',access_log=False))
                server_thread=threading.Thread(target=server.run,daemon=True);server_thread.start()
                deadline=time.monotonic()+15
                while not server.started:
                    if time.monotonic()>deadline:raise RuntimeError('Own API did not start')
                    time.sleep(.05)
                with sync_playwright() as p:
                    browser=p.chromium.launch(args=['--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream','--autoplay-policy=no-user-gesture-required'])
                    context=browser.new_context(viewport={'width':1280,'height':900},permissions=['microphone'])
                    # Only redirects the configured API origin to this verifier-owned loopback port.
                    def proxy(route):
                        req=route.request;url=urlsplit(req.url)
                        response=route.fetch(url=f'http://127.0.0.1:{port}'+url.path+('?' + url.query if url.query else ''))
                        requests.append({'method':req.method,'path':url.path,'status':response.status})
                        route.fulfill(response=response)
                    context.route('http://127.0.0.1:8000/**',proxy)
                    # Faster listening for automation; the actual files and native media decoder remain in use.
                    context.add_init_script("const play=HTMLMediaElement.prototype.play;HTMLMediaElement.prototype.play=function(){this.playbackRate=8;return play.call(this)};")
                    page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
                    page.goto(args.frontend_url+'/login');page.get_by_role('button',name='들어가기').click()
                    page.get_by_role('button',name='마이크 켜기').click();page.get_by_role('button',name='3초 테스트 녹음').click()
                    expect(page.get_by_role('button',name='다시 테스트')).to_be_enabled(timeout=7000)
                    page.locator('audio[aria-label="테스트 녹음 재생"]').evaluate("audio=>new Promise((resolve,reject)=>{audio.onended=resolve;audio.onerror=reject;audio.play().catch(reject)})")
                    page.get_by_role('checkbox',name='녹음한 내 목소리가 또렷하게 들려요').check()
                    start=page.get_by_role('button',name='이 설정으로 시험 준비하기',exact=True)
                    start.click()
                    expect(page).to_have_url(args.frontend_url+'/ready',timeout=15000)
                    sid=page.evaluate('localStorage.getItem("opictutor.session_id")')
                    questions=db.list_session_questions(sid)
                    page.get_by_role('button',name='시험 시작',exact=True).click()
                    for order in range(1,9):
                        record=page.get_by_role('button',name='녹음 시작',exact=True)
                        expect(record).to_be_enabled(timeout=15000)
                        record.click();page.wait_for_timeout(2200)
                        page.get_by_role('button',name='녹음 마치기',exact=True).click()
                        expect(page.get_by_role('heading',name='답변 처리 중',exact=True)).to_be_visible()
                        if order<8:expect(record).to_be_enabled(timeout=15000)
                    expect(page).to_have_url(args.frontend_url+'/result',timeout=15000)
                    expect(page.get_by_role('heading',name='예상 수준',exact=True)).to_be_visible(timeout=15000)
                    with pool.tx() as cur:
                        cur.execute('SELECT count(*) AS n FROM evaluations');before=cur.fetchone()['n']
                    page.reload();expect(page.get_by_role('heading',name='예상 수준',exact=True)).to_be_visible()
                    session=db.get_session(sid)
                    with pool.tx() as cur:
                        counts={}
                        for table in ['answers','evaluations','ai_requests']:
                            cur.execute(sql.SQL('SELECT count(*) AS n FROM {}').format(sql.Identifier(table)));counts[table]=cur.fetchone()['n']
                    assert session['status']=='done' and session['current_order_no']==9
                    assert counts=={'answers':8,'evaluations':before,'ai_requests':0} and before==1
                    assert [q['question_id'] for q in questions]==[q['question_id'] for q in db.list_session_questions(sid)]
                    assert not errors,errors
                    # Same-voice text refresh must preserve the old session file and URL.
                    previous=db.get_session_question(sid,1)
                    old_path=settings.TTS_DIR/previous['file_path']
                    old_hash=hashlib.sha256(old_path.read_bytes()).hexdigest()
                    source=tts/'backend/static/tts'/voice
                    manifest=json.loads((source/'manifest.json').read_text(encoding='utf-8'))
                    changed=tmp/'changed'/voice
                    (changed/'question').mkdir(parents=True)
                    ref=previous['question_id']
                    shutil.copyfile(source/'host/next.mp3',changed/'question'/f'{ref}.mp3')
                    manifest['items']=[{'id':f'question/{ref}','text_sha1':hashlib.sha1(('Updated '+previous['question_text']).encode()).hexdigest(),'seconds':1}]
                    (changed/'manifest.json').write_text(json.dumps(manifest),encoding='utf-8')
                    assert importer.main([str(changed)])==0
                    assert db.get_session_question(sid,1)['file_path']==previous['file_path']
                    assert hashlib.sha256(old_path.read_bytes()).hexdigest()==old_hash
                    assert any(r['status'] in (200,206) and '/media/tts/' in r['path'] for r in requests)
                    report.update(voice_id=voice,final_status='done',order=9,counts=counts,worker_outcomes=outcomes,
                        actual_media_http_responses=sum(r['status'] in (200,206) and '/media/tts/' in r['path'] for r in requests),
                        http_errors=[r for r in requests if r['status']>=400],same_questions=True,result_refresh_no_new_evaluation=True,
                        old_session_audio_preserved_after_changed_text=True,
                        media_status_counts=dict(Counter(r['status'] for r in requests if '/media/tts/' in r['path'])))
                    browser.close()
        finally:
            stop.set()
            if worker:worker.join(timeout=10)
            if server:server.should_exit=True
            if server_thread:server_thread.join(timeout=10)
            if pool._pool:pool._pool.close()
            admin.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(database)))
    report['isolated_database_and_temporary_assets_removed']=True
    args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=True))


if __name__=='__main__':main()
