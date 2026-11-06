# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성했습니다.
# OWNER: worker-stt (contracts.yaml ownership)
"""m1: 필러 제외 단어 수, 전체/VAD 시간 기반 속도, 발화 사이 1초 이상 쉼을 관측한다.
STT가 지운 필러는 복원되지 않는다. like와 you know는 문맥 판별이 불안정하여 필러로 세지 않는다.
하이픈 단어·숫자는 각각 1토큰이며 어절 앞뒤 구두점만 제거한다. 등급·발음 점수를 산출하지 않는다.
"""
import math
import unicodedata
from app.schemas.internal import WordTS
from app.schemas.api import Metrics

FILLERS_V1={'um','uh','er','ah','hmm','mm','erm'}

def token(value):
    value=value.casefold()
    while value and unicodedata.category(value[0]).startswith('P'): value=value[1:]
    while value and unicodedata.category(value[-1]).startswith('P'): value=value[:-1]
    return value

def compute_metrics(words: list[WordTS], duration_sec: float, speech_segments: list[tuple[float,float]]) -> Metrics:
    if not math.isfinite(duration_sec) or duration_sec<0: raise ValueError('녹음 길이 오류')
    segments=sorted((float(start),float(end)) for start,end in speech_segments)
    previous=0
    for start,end in segments:
        if not math.isfinite(start+end) or start<0 or end<start or end>duration_sec+0.01 or start<previous-0.001:
            raise ValueError('VAD 구간 오류')
        previous=end
    tokens=[]
    for word in words:
        text=word['word'] if isinstance(word,dict) else word.word
        tokens.extend(cleaned for part in text.split() if (cleaned:=token(part)))
    fillers=sum(t in FILLERS_V1 for t in tokens);count=len(tokens)-fillers
    speech=sum(end-start for start,end in segments)
    pauses=sum(start-segments[index-1][1]>=1.0 for index,(start,end) in enumerate(segments) if index)
    return Metrics(duration_sec=round(duration_sec,1),speech_sec=round(speech,1),word_count=count,
        wpm=round(count*60/duration_sec,1) if duration_sec else 0,
        articulation_wpm=round(count*60/speech,1) if speech else None,long_pause_count=pauses,
        observed_filler_per100=round(fillers/count*100,1) if count else None,metrics_version='m1')
