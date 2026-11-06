# AI-assisted (OpenAI Codex). OWNER: orchestrator.
"""Real uvicorn CLI from the session checkout, with its main-based DB dependency.

Checks startup, HTTP contract and preparing/cancel boundaries. No TTS override,
module composition, inference call or new C implementation is used by the server.
"""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from uuid import uuid4
from dotenv import dotenv_values
import httpx
import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',type=Path,required=True)
    parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args();root=args.workspace.resolve()
    single=(root/'backend/app').is_dir()
    repo=root if single else root/'OpicTutor-session'
    primary=root if single else root/'OpicTutor-With-AI'
    values=dotenv_values(primary/'backend/.env')
    original=os.getenv('DATABASE_URL') or values.get('DATABASE_URL') or 'postgresql://opic:opic@127.0.0.1:5432/opic'
    database='opic_api_native_'+uuid4().hex[:16]
    testing=(primary/'data/testing').resolve();testing.mkdir(exist_ok=True)
    with psycopg.connect(original,autocommit=True,connect_timeout=5) as admin:
        admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(database)))
        try:
            with tempfile.TemporaryDirectory(prefix='standalone-api-',dir=testing) as temporary:
                managed=Path(temporary).resolve()
                if managed.parent!=testing: raise RuntimeError('Unexpected verifier directory')
                with socket.socket() as listener:
                    listener.bind(('127.0.0.1',0));port=listener.getsockname()[1]
                target=make_conninfo(original,dbname=database)
                environment={**os.environ,'DATABASE_URL':target,
                    'DATA_DIR':os.path.relpath(managed,repo/'backend').replace(os.sep,'/'),
                    'PYTHONIOENCODING':'utf-8'}
                with (managed/'server.log').open('w',encoding='utf-8') as log:
                    child=subprocess.Popen([sys.executable,'-m','uvicorn','app.main:app','--host','127.0.0.1',
                        '--port',str(port),'--no-access-log','--log-level','error'],cwd=repo/'backend',env=environment,
                        stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
                    try:
                        with httpx.Client(base_url=f'http://127.0.0.1:{port}',timeout=5) as client:
                            deadline=time.monotonic()+15
                            while True:
                                if child.poll() is not None: raise RuntimeError('Own standalone API process exited during startup')
                                try:
                                    opened=client.get('/openapi.json')
                                    if opened.status_code==200: break
                                except httpx.TransportError: pass
                                if time.monotonic()>deadline: raise RuntimeError('Own standalone API startup deadline exceeded')
                                time.sleep(.1)
                            health=client.get('/api/v1/health').json()
                            assert health['db']=='ok' and health['ready'] is False
                            scenarios=client.get('/api/v1/scenarios')
                            assert scenarios.status_code==200 and any(s['scenario_id']=='default' for s in scenarios.json())
                            request={'client_request_id':uuid4().hex,'mic_check_passed':False}
                            rejected=client.post('/api/v1/sessions',json=request)
                            assert rejected.status_code==422 and rejected.json()['error']['code']=='MIC_CHECK_REQUIRED'
                            request['mic_check_passed']=True
                            created=client.post('/api/v1/sessions',json=request)
                            assert created.status_code==202 and created.json()['status']=='preparing'
                            sid=created.json()['session_id'];base='/api/v1/sessions/'+sid
                            repeated=client.post('/api/v1/sessions',json=request)
                            assert repeated.status_code==200 and repeated.json()['session_id']==sid
                            assert client.get(base).json()['status']=='preparing'
                            blocked=client.post(base+'/start')
                            assert blocked.status_code==409 and blocked.json()['error']['code']=='INVALID_STATE'
                            cancelled=client.post(base+'/cancel')
                            assert cancelled.status_code==200 and cancelled.json()['status']=='cancelled'
                            paths=opened.json()['paths']
                            count=sum(m in ('get','post','put','patch','delete') for p,methods in paths.items()
                                if p.startswith('/api/v1') for m in methods)
                            with psycopg.connect(target,connect_timeout=5) as connection:
                                counts={table:connection.execute(sql.SQL('SELECT count(*) FROM {}').format(sql.Identifier(table))).fetchone()[0]
                                    for table in ['sessions','session_questions','jobs','answers','ai_requests']}
                            assert counts=={'sessions':1,'session_questions':8,'jobs':1,'answers':0,'ai_requests':0}
                            result={'transport':'standalone python -m uvicorn + real loopback HTTP',
                                'scope':'startup and preparing/cancel API only; no TTS override or full exam claim',
                                'api_operations':count,'db':health['db'],'ready':health['ready'],
                                'scenarios':[s['scenario_id'] for s in scenarios.json()],
                                'mic_check_rejected':True,'create_status':created.status_code,
                                'duplicate_status':repeated.status_code,'preparing_start_blocked':True,
                                'cancel_status':cancelled.json()['status'],'row_counts':counts,
                                'data_dir_configuration_relative':True,'c_implementation_added':False}
                    finally:
                        if child.poll() is None:
                            if os.name=='nt':
                                # The Windows venv launcher can have a base-Python
                                # descendant. Stop only this verifier-owned tree.
                                subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],
                                    stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True)
                            else: child.terminate()
                        try: child.wait(timeout=10)
                        except subprocess.TimeoutExpired: child.kill();child.wait(timeout=5)
        finally:
            admin.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(database)))
    result['own_process_and_database_cleaned']=True
    args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=True))
    return 0


if __name__=='__main__': raise SystemExit(main())
