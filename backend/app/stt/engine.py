# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성했습니다.
# OWNER: worker-stt (contracts.yaml ownership)
from pathlib import Path
from threading import Lock
import json
import math
import os
import numpy as np
from faster_whisper import WhisperModel
from faster_whisper.vad import get_speech_timestamps
from app.config import settings
from app.schemas.internal import SttResult,WordTS
from .audio import decode_audio,SAMPLE_RATE

_model=None
_lock=Lock()

class AudioRejected(Exception):
    def __init__(self,reason):
        self.reason=reason
        super().__init__(reason)

def load_model() -> None:
    global _model
    with _lock:
        if _model is None:
            _model=WhisperModel(settings.WHISPER_MODEL,device=settings.WHISPER_DEVICE,
                compute_type=settings.WHISPER_COMPUTE_TYPE,cpu_threads=min(4,os.cpu_count() or 4),
                download_root=str(settings.DATA_DIR/'models'))

def is_loaded() -> bool: return _model is not None

def transcribe(path: Path) -> SttResult:
    audio=decode_audio(path);duration=len(audio)/SAMPLE_RATE
    rms=float(np.sqrt(np.mean(audio.astype(np.float64)**2))) if len(audio) else 0
    if rms==0 or 20*math.log10(rms)<-50: raise AudioRejected('silence')
    speech=get_speech_timestamps(audio,sampling_rate=SAMPLE_RATE)
    intervals=[(segment['start']/SAMPLE_RATE,segment['end']/SAMPLE_RATE) for segment in speech]
    if sum(end-start for start,end in intervals)<0.5: raise AudioRejected('silence')
    load_model()
    segments,info=_model.transcribe(audio,language='en',word_timestamps=True,vad_filter=False,beam_size=5,
        condition_on_previous_text=False,initial_prompt='Um, uh, so, I mean, like... Hmm, well.')
    text=[];words=[]
    for segment in segments:
        text.append(segment.text.strip())
        for word in segment.words or []:
            words.append(WordTS(word=word.word.strip(),start=word.start,end=word.end))
    if not words or not any(word.word.strip() for word in words): raise AudioRejected('no_speech')
    return SttResult(text=' '.join(text),words=words,duration_sec=duration,speech_segments=intervals)

def main():
    import argparse
    from .audio import probe_audio
    from .metrics import compute_metrics
    p=argparse.ArgumentParser(description='로컬 STT 수동 확인: 전사·지표는 이 명령에서만 출력')
    p.add_argument('path',type=Path);args=p.parse_args()
    probe=probe_audio(args.path)
    if not probe.ok:
        print(json.dumps(probe.model_dump(),ensure_ascii=False));return 1
    try: result=transcribe(args.path)
    except AudioRejected as exc:
        print(json.dumps({'rejected':exc.reason}));return 1
    print(json.dumps({'text':result.text,'metrics':compute_metrics(result.words,result.duration_sec,result.speech_segments).model_dump()},
                     ensure_ascii=False,indent=2))
    return 0

if __name__=='__main__': raise SystemExit(main())
