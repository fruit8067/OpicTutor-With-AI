# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성했습니다.
# OWNER: worker-stt (contracts.yaml ownership)
from pathlib import Path
import math
import av
import numpy as np
from app.schemas.internal import AudioProbe

SAMPLE_RATE=16000
MAX_SECONDS=126

def decode_audio(path: Path) -> np.ndarray:
    frames=[];size=0
    with av.open(str(path)) as container:
        if not container.streams.audio: raise ValueError('audio stream missing')
        resampler=av.AudioResampler(format='fltp',layout='mono',rate=SAMPLE_RATE)
        for frame in container.decode(audio=0):
            for converted in resampler.resample(frame):
                samples=converted.to_ndarray().reshape(-1)
                frames.append(samples);size+=len(samples)
            if size>=SAMPLE_RATE*MAX_SECONDS: break
        else:
            for converted in resampler.resample(None): frames.append(converted.to_ndarray().reshape(-1))
    audio=np.concatenate(frames).astype(np.float32) if frames else np.empty(0,dtype=np.float32)
    if not np.isfinite(audio).all(): raise ValueError('non-finite audio')
    return audio

def probe_audio(path: Path) -> AudioProbe:
    try: audio=decode_audio(path)
    except (OSError,ValueError,av.error.FFmpegError):
        return AudioProbe(duration_sec=0,sample_rate=SAMPLE_RATE,rms_dbfs=-120,ok=False,reason='corrupt')
    duration=len(audio)/SAMPLE_RATE
    rms=float(np.sqrt(np.mean(audio.astype(np.float64)**2))) if len(audio) else 0
    dbfs=max(-120,20*math.log10(rms)) if rms>0 else -120
    reason='too_short' if duration<2 else 'too_long' if duration>125 else None
    return AudioProbe(duration_sec=duration,sample_rate=SAMPLE_RATE,rms_dbfs=round(dbfs,1),ok=reason is None,reason=reason)
