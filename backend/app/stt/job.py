# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성했습니다.
# OWNER: worker-stt (contracts.yaml ownership)
from pathlib import Path
from uuid import UUID
from app import db
from app.config import settings
from app.worker.errors import RetryableJobError
from .audio import probe_audio
from .engine import transcribe,AudioRejected
from .metrics import compute_metrics

def live(job,answer_id,attempt):
    cancel=job.get('_cancel')
    if cancel and cancel.is_set(): return False
    lease=job.get('_lease_valid')
    if lease and not lease(): return False
    current=db.get_answer(answer_id)
    return current is not None and current['stt_attempt']==attempt

def handle(job: dict) -> None:
    aid=UUID(str(job['target_id']))
    answer=db.get_answer(aid)
    if answer is None: return
    attempt=job.get('payload',{}).get('stt_attempt',answer['stt_attempt'])
    if not live(job,aid,attempt): return
    if not db.mark_stt_processing(aid):
        answer=db.get_answer(aid)
        # 이전 실행이 죽어 processing으로 남은 작업도 같은 attempt의 새 리스에서 재처리한다.
        if answer is None or answer['stt_status']!='processing' or job['attempts']<=1: return
    try:
        path=Path(answer['audio_path'])
        # API는 DB 접수 뒤 파일을 rename한다. 그 짧은 경합은 손상 녹음으로 거부하지 않고 재시도한다.
        if not path.is_file():
            if job['attempts']>=job['max_attempts'] and live(job,aid,attempt): db.fail_stt(aid,'STT_DECODE_ERROR')
            raise RetryableJobError('STT_DECODE_ERROR')
        probe=probe_audio(path)
        if not probe.ok:
            if live(job,aid,attempt): db.reject_stt(aid,probe.reason)
            return
        try: result=transcribe(Path(answer['audio_path']))
        except AudioRejected as exc:
            if live(job,aid,attempt): db.reject_stt(aid,exc.reason)
            return
        metrics=compute_metrics(result.words,result.duration_sec,result.speech_segments)
        if live(job,aid,attempt):
            db.complete_stt(aid,text=result.text,timestamps=[w.model_dump() for w in result.words],
                metrics=metrics.model_dump(),stt_version=f'faster-whisper:{settings.WHISPER_MODEL}:m1')
    except RetryableJobError:
        raise
    except Exception as exc:
        if not live(job,aid,attempt): return
        if job['attempts']>=job['max_attempts']: db.fail_stt(aid,'STT_ENGINE_ERROR')
        raise RetryableJobError('STT_ENGINE_ERROR') from exc
