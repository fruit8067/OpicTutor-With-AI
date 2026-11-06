# AI-assisted: 평가 검증 회귀 테스트는 OpenAI Codex의 도움으로 작성했습니다.
# OWNER: grader (contracts.yaml ownership)
import copy
import pytest
from app.schemas.internal import EvaluationLLMOutput
from app.grading.validate import precheck_snapshot,validate_output
from app.grading.rules import contract
from app.llm.chat import LLMOutputError
from app.worker.errors import PermanentJobError


def snapshot():
    kinds=['self_intro','description','routine','past_experience','comparison','roleplay_ask','roleplay_solve','issue']
    functions=['self_introduce','describe','report_routine','narrate_past','compare','ask_information','solve_problem','explain_issue']
    return [dict(order_no=n,question_id=f'Q{n:03d}',question_type=kind,question_text='Tell me about your day.',
        is_scored=n!=1,target_functions=[functions[n-1]],target_time_frames=['past' if n==4 else 'present'],
        context_scope=['personal_familiar'],stt_status='done',stt_text=f'Answer {n}. I enjoy walking because it helps me relax.',
        metrics={'word_count':12},stt_version='fixture') for n,kind in enumerate(kinds,1)]


def output(rows=None):
    rows=rows or snapshot();c=contract();crit=c['evaluation_criteria']
    coverage={}
    for name,field in [('functions','target_functions'),('time_frames','target_time_frames'),('contexts','context_scope')]:
        values=sorted({tag for row in rows if row['is_scored'] for tag in row[field]})
        coverage[name]=[dict(name=value,elicited_order_nos=[r['order_no'] for r in rows if r['is_scored'] and value in r[field]],
            usable_order_nos=[r['order_no'] for r in rows if r['is_scored'] and value in r[field]],gaps=[]) for value in values]
    return dict(status='assessed',assessment_basis='transcript_and_metrics',rubric_version=crit['rubric_version'],prompt_version=crit['prompt_version'],
        im_rubric_version=None,evaluation_scope=dict(submitted_order_nos=list(range(1,9)),scored_order_nos=list(range(2,9)),
            feedback_only_order_nos=[1],usable_order_nos=list(range(2,9)),unusable_items=[]),input_issues=[],base_level='IL',estimated_level='IL',
        im_estimation_status='not_applicable',headline='일상 정보를 전달합니다.',grade_rationale='채점 문항의 짧은 설명을 관찰했습니다.',
        dimension_feedback={key:dict(summary='문장으로 의미를 전합니다.',evidence_order_nos=[2],limitations=['전사 기반 관찰']) for key in c['dimensions']},
        coverage=coverage,fact_evidence=[dict(criterion='functions_tasks',observation='이유를 전달합니다.',status='demonstrated',order_no=n,
            quote='I enjoy walking') for n in [2,3]],sustained_performance=[dict(capability='설명',evidence=[dict(order_no=2,quote='I enjoy walking')],summary='익숙한 정보 전달')],
        breakdown_observations=[],fluency_observations='전사와 지표를 참고했습니다.',why_this_level='일상 과제를 제한적으로 처리합니다.',
        why_not_lower='자기 의미로 문장을 조합합니다.',next_level_gap='관련 사례를 더 전개하는 연습이 필요합니다.',borderline_levels=['NH','IM1'],uncertainty_reasons=['합성 입력'],
        items=[dict(order_no=n,evaluation_role='feedback_only' if n==1 else 'scored',task_fulfillment='fulfilled',
            evidence=['I enjoy walking'],mistakes=[],upgrade_tip='구체적인 사례를 더해 보세요.') for n in range(1,9)],
        feedback_cards=[dict(title='이유 확장',why='설명을 구체화합니다.',before='I enjoy walking',after='I enjoy walking along the river.',
            example_kind='correction',related_order_nos=[n],success_condition='관련 장소나 이유를 설명하기') for n in [2,3,4]],
        additional_tasks_needed=[],limitations=['공식 결과가 아님'],insufficient_reason=None)


def validate(value,rows=None): return validate_output(EvaluationLLMOutput.model_validate(value),rows or snapshot())


def test_valid_output_and_im_provisional():
    result=validate(output())
    assert result.estimated_level=='IL' and result.tier.name=='silver'
    raw=output();raw.update(base_level='IM',estimated_level='IM2',im_estimation_status='provisional',im_rubric_version='project-im-v1',borderline_levels=['IM1','IM3'])
    result=validate(raw)
    assert result.provisional_label and result.tier.name=='gold'


@pytest.mark.parametrize('path,value',[
    (('estimated_level',),'IM2'),(('base_level',),'IM'),(('im_estimation_status',),'provisional'),
    (('fact_evidence',0,'order_no'),1),(('feedback_cards',0,'related_order_nos'),[1]),
    (('items',0,'evaluation_role'),'scored'),(('evaluation_scope','scored_order_nos'),list(range(1,9))),
    (('items',1,'evidence'),['Invented quotation.']),(('feedback_cards',0,'before'),None),
    (('feedback_cards',),output()['feedback_cards'][:2]),(('headline',),'발음 점수 100점'),(('headline',),'85%'),
    (('headline',),'예상 AM'),(('rubric_version',),'old-version'),(('prompt_version',),'old-prompt'),
    (('dimension_feedback','accuracy','evidence_order_nos'),[1]),(('coverage','contexts',0,'elicited_order_nos'),[1]),
    (('sustained_performance',0,'evidence',0,'order_no'),1),
])
def test_invalid_outputs_are_rejected(path,value):
    raw=output();parent=raw
    for part in path[:-1]: parent=parent[part]
    parent[path[-1]]=value
    with pytest.raises(LLMOutputError): validate(raw)


def test_im_withheld_requires_reason():
    raw=output();raw.update(base_level='IM',estimated_level=None,im_estimation_status='insufficient_evidence',borderline_levels=['IM1','IM2'])
    with pytest.raises(LLMOutputError): validate(raw)
    raw['insufficient_reason']='서로 다른 유형의 근거가 부족합니다.'
    assert validate(raw).tier is None


def test_missing_transcripts_cannot_be_fulfilled_or_nl():
    rows=snapshot()
    for row in rows[1:]: row.update(stt_status='failed',stt_text='')
    raw=output(rows)
    with pytest.raises(LLMOutputError): validate(raw,rows)
    raw.update(status='insufficient_evidence',base_level=None,estimated_level=None,insufficient_reason='채점 대상 전사가 없습니다.',
        fact_evidence=[],sustained_performance=[],feedback_cards=[],borderline_levels=[])
    raw['evaluation_scope'].update(usable_order_nos=[],unusable_items=[dict(order_no=n,reason='STT 실패') for n in range(2,9)])
    for d in raw['dimension_feedback'].values(): d['evidence_order_nos']=[]
    for entries in raw['coverage'].values():
        for entry in entries: entry['usable_order_nos']=[]
    for item in raw['items'][1:]: item.update(task_fulfillment='not_assessable',evidence=[])
    assert validate(raw,rows).assessment_status=='insufficient_evidence'


def test_invalid_input_fails_before_llm():
    rows=snapshot();del rows[2]['target_functions']
    with pytest.raises(PermanentJobError,match='EVAL_INPUT_INVALID'): precheck_snapshot(rows)
