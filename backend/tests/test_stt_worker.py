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


def _stub_handler(conn, job):
    raise NotImplementedError('TODO')


def test_stub_handler_is_excluded_without_consuming_jobs(monkeypatch):
    # tts-host 병합 후 실제 stub이 없어졌으므로 가짜 stub으로 제외 규칙을 확인한다.
    real=registry.get_handler
    monkeypatch.setattr(registry,'get_handler',lambda kind:_stub_handler if kind=='tts_prepare' else real(kind))
    assert registry.is_stub(_stub_handler)
    assert registry.available_types(['tts_prepare','stt'])==['stt']


def test_merged_handlers_are_all_available():
    # 병합된 실제 핸들러(tts_prepare·stt)는 stub으로 오인하지 않는다.
    assert not registry.is_stub(registry.get_handler('tts_prepare'))
    assert registry.available_types(['tts_prepare','stt'])==['tts_prepare','stt']
