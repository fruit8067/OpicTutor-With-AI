# AI-assisted: 합성 평가 계획 검증은 OpenAI Codex의 도움으로 작성했습니다.
# OWNER: grader (contracts.yaml ownership)
import json
import pytest
from scripts.eval_exam import cases,make_snapshot,metrics
from app.config import settings
from app.grading.validate import precheck_snapshot
from types import SimpleNamespace
from scripts import eval_exam
import sys


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


def test_optional_warmup_examples_have_documented_fallback_but_scored_answers_do_not():
    answers={(row['question_id'],row['level']):row for row in
        (json.loads(line) for line in (settings.RAG_BUILD_DIR/'answers.jsonl').read_text(encoding='utf-8').splitlines())
        if row['text_style']=='stt' and row['question_id']!='Q000'}
    case=cases()[0]
    rows,_=make_snapshot(case,answers)
    assert rows[0]['is_scored'] is False and rows[0]['stt_version']=='synthetic-fixed-warmup:v1'
    assert rows[0]['stt_text'].startswith('My name is Alex.')
    missing=rows[1]['question_id']
    answers.pop((missing,case['levels'][0]))
    with pytest.raises(ValueError,match=missing): make_snapshot(case,answers)


@pytest.mark.parametrize('quota',[False,True])
def test_school_credit_mode_checkpoints_unknown_cost_and_stops_provider_limits(monkeypatch,quota):
    reports=[];calls=[]
    monkeypatch.setattr(sys,'argv',['eval_exam','--limit','2','--school-credit-usd','10','--embedding-usd-per-million','.13','--yes'])
    monkeypatch.setattr(eval_exam,'llm_options',lambda:{'model':'pickle-general'})
    monkeypatch.setattr(settings,'EMBED_API_KEY','fixture-no-network')
    monkeypatch.setattr(eval_exam,'write_report',lambda payload,label,**kw:reports.append(json.loads(json.dumps(payload))))
    class LimitError(Exception): code='insufficient_quota'
    def evaluate(*args,**kwargs):
        calls.append(1)
        if quota: raise LimitError('must not store arbitrary provider text')
        return SimpleNamespace(estimated_level='NL',base_level='NL',assessment_status='assessed',im_estimation_status='not_applicable'),dict(
            total_input_tokens=10,total_output_tokens=5,llm_calls=1)
    monkeypatch.setattr(eval_exam,'evaluate_exam',evaluate)
    assert eval_exam.main()==int(quota)
    latest=reports[-1]
    assert len(calls)==(1 if quota else 2)
    assert latest['metadata']['run_status']==('stopped_provider_limit' if quota else 'completed')
    assert latest['metrics']['avg_estimated_cost_usd'] is None
    assert latest['metadata']['upper_cost_usd'] is None and latest['metadata']['school_credit_usd']==10
    assert 'arbitrary provider text' not in json.dumps(latest)
    assert len(reports)>=3


def test_resume_keeps_model_failures_and_provider_pause_history_without_reusing_incompatible_results(tmp_path):
    metadata={'system_prompt_sha1':'same','user_template_sha256':'same','user_template_version':'v5',
              'corpus_version':'corpus','model':'pickle-general','planned_exams':3}
    prepared=[({'id':name,'expected':'IL','trap':None},[],['Q000',name]) for name in ['a','b','c']]
    records=[{'id':name,'repeat':1,'expected':'IL','trap':None,'excluded_contrast_set_ids':['Q000',name],
              'status':'error' if name=='a' else 'done','llm_calls':2} for name in ['a','b']]
    paused={'id':'c','repeat':1,'status':'error','llm_calls':1}
    path=tmp_path/'stopped.json'
    original={'metadata':{**metadata,'run_status':'stopped_provider_limit'},'records':records+[paused]}
    path.write_text(json.dumps(original),encoding='utf-8')
    current=metadata.copy()
    recovered=eval_exam.resume_records(path,current,prepared,1)
    assert recovered==records and recovered[0]['status']=='error'
    assert current['provider_pause_records']==[paused]
    assert json.loads(path.read_text(encoding='utf-8'))==original
    with pytest.raises(ValueError,match='corpus_version'):
        eval_exam.resume_records(path,{**metadata,'corpus_version':'changed'},prepared,1)
    changed=[prepared[1],prepared[0],prepared[2]]
    with pytest.raises(ValueError,match='시험 순서'):
        eval_exam.resume_records(path,metadata.copy(),changed,1)
