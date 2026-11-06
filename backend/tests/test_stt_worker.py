# AI-assisted: 작업 실행·리스·stub 검사 테스트는 OpenAI Codex의 도움으로 작성했습니다.
# OWNER: worker-stt (contracts.yaml ownership)
from threading import Event
from uuid import uuid4
from app.worker import runner,registry
from app.worker.errors import PermanentJobError,RetryableJobError


def setup(monkeypatch,handler,heartbeat=True):
    calls=[]
    monkeypatch.setattr(runner,'get_handler',lambda kind:handler)
    monkeypatch.setattr(runner.db,'heartbeat_job',lambda *args:heartbeat)
    monkeypatch.setattr(runner.db,'complete_job',lambda *args:calls.append('done'))
    def fail(*args,**kwargs): calls.append(kwargs);return 'failed' if kwargs['retryable'] else 'dead'
    monkeypatch.setattr(runner.db,'fail_job',fail)
    return calls


def job(): return dict(id=uuid4(),target_id=uuid4(),type='stt',attempts=1,max_attempts=3,payload={})


def test_worker_dispatches_and_completes(monkeypatch):
    seen=[];calls=setup(monkeypatch,lambda work:seen.append(work))
    assert runner.execute(job(),'fixture',1,Event())=='done'
    assert calls==['done'] and isinstance(seen[0]['_cancel'],Event)


def test_worker_classifies_retryable_and_permanent(monkeypatch):
    for error,retryable in [(RetryableJobError('TEMP'),True),(PermanentJobError('INVALID'),False),(RuntimeError('private'),True)]:
        def handler(work): raise error
        calls=setup(monkeypatch,handler)
        runner.execute(job(),'fixture',1,Event())
        assert calls[0]['retryable'] is retryable
        assert 'private' not in calls[0]['error_code']


def test_lost_lease_cancels_handler_without_completion(monkeypatch):
    seen=[]
    def handler(work):
        assert work['_cancel'].wait(1)
        seen.append(True)
    calls=setup(monkeypatch,handler,heartbeat=False)
    assert runner.execute(job(),'fixture',0.06,Event())=='lease_lost'
    assert seen and not calls


def test_actual_tts_stub_is_excluded_without_consuming_jobs():
    assert registry.is_stub(registry.get_handler('tts_prepare'))
    assert 'tts_prepare' not in registry.available_types(['tts_prepare'])
    assert 'stt' in registry.available_types(['stt'])
