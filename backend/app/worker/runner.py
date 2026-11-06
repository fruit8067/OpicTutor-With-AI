# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성했습니다.
# OWNER: worker-stt (contracts.yaml ownership)
import logging
import socket
import os
import time
from threading import Thread,Event
from app import db
from app.config import settings
from .errors import PermanentJobError,RetryableJobError
from .registry import get_handler,available_types

log=logging.getLogger(__name__)

def execute(job,worker_id,lease_sec,stop):
    cancel=Event();heartbeat_stop=Event();finished=Event();outcome={}
    job={**job,'_cancel':cancel}
    def lease_valid():
        if cancel.is_set(): return False
        try: valid=db.heartbeat_job(job['id'],worker_id,lease_sec)
        except Exception: valid=False
        if not valid: cancel.set()
        return valid
    job['_lease_valid']=lease_valid
    def heartbeat():
        while not heartbeat_stop.wait(lease_sec/3):
            if not lease_valid(): return
    def handle():
        try: get_handler(job['type'])(job)
        except BaseException as exc: outcome['exception']=exc
        finally: finished.set()
    started=time.monotonic()
    ticker=Thread(target=heartbeat,daemon=True,name='job-heartbeat')
    handler=Thread(target=handle,daemon=True,name='job-handler')
    ticker.start();handler.start();deadline=None
    try:
        while not finished.wait(0.2):
            if stop.is_set() and deadline is None: deadline=time.monotonic()+lease_sec
            if deadline is not None and time.monotonic()>=deadline:
                cancel.set();return 'lease_recovery'
    except KeyboardInterrupt:
        stop.set()
        # 진행 중 작업은 최대 한 리스 동안 마치도록 기다린다.
        if not finished.wait(lease_sec):
            cancel.set();heartbeat_stop.set();return 'lease_recovery'
    finally:
        heartbeat_stop.set()
    if not lease_valid():
        status='lease_lost'
    elif 'exception' not in outcome:
        db.complete_job(job['id'],worker_id);status='done'
    else:
        error=outcome['exception']
        code=getattr(error,'error_code','HANDLER_NOT_READY' if isinstance(error,NotImplementedError) else 'JOB_INTERNAL')
        status=db.fail_job(job['id'],worker_id,error_code=code,retryable=not isinstance(error,PermanentJobError))
    log.info('job=%s type=%s attempt=%s elapsed=%.2f result=%s',job['id'],job['type'],job['attempts'],time.monotonic()-started,status)
    return status

def run(types,once=False,stop=None):
    stop=stop or Event()
    worker_id=settings.WORKER_ID or f'{socket.gethostname()}-{os.getpid()}'
    active=available_types(types)
    for kind in set(types)-set(active): log.warning('type=%s result=handler_not_ready_unclaimed',kind)
    if not active: return 0
    if 'stt' in active:
        from app.stt.engine import load_model
        load_model()
    last_recovery=0;delay=0.5;failed=False
    while not stop.is_set():
        try:
            now=time.monotonic()
            if now-last_recovery>=30:
                db.recover_expired_jobs();last_recovery=now
            job=db.claim_job(active,worker_id,60)
            if job is None:
                if once: break
                stop.wait(delay);delay=min(2,delay*1.5);continue
            delay=0.5
            result=execute(job,worker_id,60,stop)
            failed=result!='done'
            if once: break
        except KeyboardInterrupt:
            stop.set()
    return int(failed)
