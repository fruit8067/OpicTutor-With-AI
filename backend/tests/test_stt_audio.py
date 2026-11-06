# AI-assisted: 로컬 오디오 검사 테스트는 OpenAI Codex의 도움으로 작성했습니다.
# OWNER: worker-stt (contracts.yaml ownership)
from pathlib import Path
import wave
import pytest
from app.stt.audio import probe_audio
from app.stt.engine import transcribe,AudioRejected


def wav(path,seconds,rate=16000):
    with wave.open(str(path),'wb') as out:
        out.setnchannels(1);out.setsampwidth(2);out.setframerate(rate);out.writeframes(b'\0'*(round(seconds*rate)*2))
    return path


@pytest.mark.parametrize('seconds,reason',[(1.5,'too_short'),(2,None),(3,None),(125,None),(126,'too_long')])
def test_real_wav_duration_limits(tmp_path,seconds,reason):
    result=probe_audio(wav(tmp_path/'audio.wav',seconds))
    assert result.reason==reason and result.ok==(reason is None) and result.sample_rate==16000


def test_corrupt_file_and_silence_are_rejected_locally(tmp_path):
    corrupt=tmp_path/'corrupt.webm';corrupt.write_bytes(b'not an audio file')
    assert probe_audio(corrupt).reason=='corrupt'
    silent=wav(tmp_path/'silence.wav',3,rate=22050)
    assert probe_audio(silent).rms_dbfs==-120
    with pytest.raises(AudioRejected,match='silence'): transcribe(silent)
