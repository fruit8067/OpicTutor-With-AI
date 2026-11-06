# AI-assisted: 관측 지표 테스트는 OpenAI Codex의 도움으로 작성했습니다.
# OWNER: worker-stt (contracts.yaml ownership)
import pytest
from app.stt.metrics import compute_metrics
from app.schemas.internal import WordTS


def words(*texts): return [WordTS(word=text,start=0,end=0.1) for text in texts]


def test_fillers_hyphens_numbers_and_pause_boundary():
    result=compute_metrics(words('Um,','I','uh','like','well-known','2026','you','know.'),10,[(0.5,2),(3,6),(6.9,7.9)])
    assert result.word_count==6 and result.observed_filler_per100==33.3
    assert result.speech_sec==5.5 and result.wpm==36 and result.articulation_wpm==65.5
    assert result.long_pause_count==1 and result.metrics_version=='m1'


def test_silence_and_only_fillers_do_not_divide_by_zero():
    result=compute_metrics(words('um','hmm'),3,[])
    assert result.word_count==0 and result.observed_filler_per100 is None and result.articulation_wpm is None
    assert result.wpm==0 and result.long_pause_count==0


@pytest.mark.parametrize('duration,segments',[(-1,[]),(3,[(2,1)]),(3,[(0,4)]),(3,[(0,2),(1,3)])])
def test_invalid_vad_intervals_are_not_silently_scored(duration,segments):
    with pytest.raises(ValueError): compute_metrics([],duration,segments)
