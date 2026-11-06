# AI-assisted: 합성 평가 계획 검증은 OpenAI Codex의 도움으로 작성했습니다.
# OWNER: grader (contracts.yaml ownership)
import json
from scripts.eval_exam import cases,make_snapshot,metrics
from app.config import settings
from app.grading.validate import precheck_snapshot


def test_full_eval_plan_has_five_traps_and_excludes_every_used_set():
    answers={(row['question_id'],row['level']):row for row in
        (json.loads(line) for line in (settings.RAG_BUILD_DIR/'answers.jsonl').read_text(encoding='utf-8').splitlines()) if row['text_style']=='stt'}
    plan=cases(traps=True)
    assert len(plan)==40 and len({c['trap'] for c in plan if c['trap']})==5
    for case in plan:
        snapshot,excluded=make_snapshot(case,answers)
        precheck_snapshot(snapshot)
        assert {row['question_id'] for row in snapshot}==set(excluded)
        if case['trap']=='no_future': assert not any('future' in r['target_time_frames'] for r in snapshot[1:])
        if case['trap']=='all_missing': assert all(not r['stt_text'] for r in snapshot[1:])


def test_metrics_do_not_hide_failed_or_withheld_predictions():
    result=metrics([
        dict(id='a',expected='IL',estimated_level='IL',base_level='IL',status='done',latency_ms=1,estimated_cost_usd=0),
        dict(id='b',expected='IL',status='error'),
        dict(id='c',expected='IM2',estimated_level=None,base_level='IM',status='done',latency_ms=1,estimated_cost_usd=0)])
    assert result['within_one']==1/3 and result['exact']==1/3
    assert result['base_agreement']==2/3 and result['im_withheld_rate']==1
