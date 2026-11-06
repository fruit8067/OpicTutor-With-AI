# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성되었습니다.
# OWNER: session-api (contracts.yaml ownership)
import json
import hashlib
import pytest
from app.exam import build_question_set, list_scenarios
from app.exam.scenarios import coverage_for
from app.config import settings
from app.errors import AppError


@pytest.fixture
def corpus(tmp_path,monkeypatch):
    kinds=['self_intro','description','routine','past_experience','comparison','roleplay_ask','roleplay_solve','issue']
    rows=[];slots=[]
    for n,kind in enumerate(kinds,1):
        pool=[]
        for variant in range(2):
            qid=f'Q{n}-{variant}';pool.append(qid)
            rows.append(dict(id=qid,status='pilot',question_type=kind,question=f'Question {n} variant {variant}',
                is_scored=n!=1,target_functions=['self_introduce' if n==1 else 'describe'],
                target_time_frames=['present'],context_scope=['personal_familiar']))
        slots.append(dict(order_no=n,question_types=[kind],is_scored=n!=1,pool=pool))
    scenarios={'version':'fixture','scenarios':[dict(scenario_id='default',label='예시',description='검증용',slots=slots,
        coverage={'functions':['describe'],'time_frames':['present'],'contexts':['personal_familiar'],'warnings':['fixture warning']})]}
    (tmp_path/'questions.jsonl').write_text('\n'.join(json.dumps(q) for q in rows),encoding='utf-8')
    (tmp_path/'scenarios.json').write_text(json.dumps(scenarios),encoding='utf-8')
    monkeypatch.setattr(settings,'RAG_BUILD_DIR',tmp_path)
    return tmp_path,rows,scenarios


def test_determinism_tags_and_coverage(corpus):
    first=build_question_set('default','same-seed')
    assert first==build_question_set('default','same-seed')
    assert len({q.question_id for q in first})==8
    assert [q.is_scored for q in first]==[False]+[True]*7
    assert first[0].question_version==hashlib.sha1(first[0].question_text.encode()).hexdigest()[:12]
    assert list_scenarios()[0].question_count==8
    coverage=coverage_for('default',first)
    assert coverage['functions']==['describe'] and 'fixture warning' in coverage['warnings']
    assert 'self_introduce' not in coverage['functions']


def test_missing_tags_and_missing_files_fail_explicitly(corpus):
    path,rows,_=corpus
    del rows[0]['target_functions']
    (path/'questions.jsonl').write_text('\n'.join(json.dumps(q) for q in rows),encoding='utf-8')
    with pytest.raises(AppError,match='SCENARIO_UNAVAILABLE'): build_question_set('default','seed')
    (path/'scenarios.json').unlink()
    with pytest.raises(AppError,match='SCENARIO_UNAVAILABLE'): list_scenarios()


def test_overlapping_pools_use_complete_assignment(corpus):
    path,rows,data=corpus
    # 같은 유형인 두 슬롯에 겹치는 pool이 있어도 완성 가능한 배정을 찾는다.
    data['scenarios'][0]['slots'][2].update(question_types=['description'],pool=['Q2-0'])
    data['scenarios'][0]['slots'][1]['pool']=['Q2-0','Q2-1']
    (path/'scenarios.json').write_text(json.dumps(data),encoding='utf-8')
    for seed in range(10):
        selected=build_question_set('default',str(seed))
        assert selected[1].question_id=='Q2-1' and selected[2].question_id=='Q2-0'
    data['scenarios'][0]['slots'][1]['pool']=['Q2-0']
    (path/'scenarios.json').write_text(json.dumps(data),encoding='utf-8')
    with pytest.raises(AppError): build_question_set('default','seed')
