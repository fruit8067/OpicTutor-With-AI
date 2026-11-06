# AI-assisted: 출력 검증은 OpenAI Codex의 도움으로 작성했습니다.
# OWNER: grader (contracts.yaml ownership)
"""서버 스냅샷과 출력 계약을 대조한다. 등급이나 인용을 조용히 보정하지 않는다."""
import re
import unicodedata
from app.schemas.internal import EvaluationLLMOutput
from app.schemas.api import EvaluationResult
from app.llm.chat import LLMOutputError
from app.worker.errors import PermanentJobError
from .rules import contract
from .tiers import tier_of

FORBIDDEN_PATTERNS=(r'발음\s*점수',r'합격\s*보장',r'\d+\s?%',r'\bAM\b',r'Advanced\s+Mid',r'100\s*점')

def usable(row):
    return row.get('stt_status')=='done' and isinstance(row.get('stt_text'),str) and bool(row['stt_text'].strip())

def normalize(value):
    text=unicodedata.normalize('NFKC',value).casefold()
    return ' '.join(''.join(' ' if unicodedata.category(c).startswith('P') else c for c in text).split())

def precheck_snapshot(snapshot: list[dict]) -> None:
    c=contract()
    def invalid():
        raise PermanentJobError('EVAL_INPUT_INVALID')
    if not isinstance(snapshot,list) or len(snapshot)!=8: invalid()
    if any(not isinstance(row,dict) for row in snapshot): invalid()
    if [r.get('order_no') for r in snapshot]!=list(range(1,9)): invalid()
    if len({r.get('question_id') for r in snapshot})!=8: invalid()
    for row in snapshot:
        if type(row.get('is_scored')) is not bool or row['is_scored'] is not (row['order_no']!=1): invalid()
        if row.get('question_type') not in c['question_types']: invalid()
        if (row['question_type']=='self_intro') != (row['order_no']==1): invalid()
        if not isinstance(row.get('question_text'),str) or not row['question_text'].strip(): invalid()
        if row.get('stt_status') not in c['answer_stt_status']: invalid()
        if row.get('stt_text') is not None and not isinstance(row['stt_text'],str): invalid()
        for field in ['target_functions','target_time_frames','context_scope']:
            values=row.get(field)
            if not isinstance(values,list) or not values or any(not isinstance(v,str) or v not in c['question_tags'][field] for v in values):
                invalid()

def validate_output(raw: EvaluationLLMOutput, snapshot: list[dict]) -> EvaluationResult:
    precheck_snapshot(snapshot)
    if not isinstance(raw,EvaluationLLMOutput):
        try: raw=EvaluationLLMOutput.model_validate(raw)
        except Exception as exc: raise LLMOutputError('output: schema mismatch') from exc
    c=contract();criteria=c['evaluation_criteria'];errors=[]
    rows={r['order_no']:r for r in snapshot};all_orders=set(rows)
    scored={n for n,r in rows.items() if r['is_scored']}
    warmup=all_orders-scored
    available={n for n in scored if usable(rows[n])}
    missing=scored-available
    evidence_quotes=set()
    def require(condition,label):
        if not condition: errors.append(label)
    def exact_list(values,expected,label):
        require(len(values)==len(set(values)) and set(values)==expected,label)
    def scoped(values,allowed,label):
        require(len(values)==len(set(values)) and set(values)<=allowed,label)
    def quote(order,text,label,grade_evidence=True):
        if order not in rows or (grade_evidence and order not in scored):
            errors.append(label+': order');return
        if not isinstance(text,str) or not normalize(text) or normalize(text) not in normalize(rows[order].get('stt_text') or ''):
            errors.append(label+': quote');return
        if grade_evidence:
            require(order in available,label+': unavailable')
            evidence_quotes.add((order,normalize(text)))

    require(raw.assessment_basis==criteria['assessment_basis'],'assessment_basis')
    require(raw.rubric_version==criteria['rubric_version'],'rubric_version')
    require(raw.prompt_version==criteria['prompt_version'],'prompt_version')
    scope=raw.evaluation_scope
    exact_list(scope.submitted_order_nos,all_orders,'evaluation_scope.submitted')
    exact_list(scope.scored_order_nos,scored,'evaluation_scope.scored')
    exact_list(scope.feedback_only_order_nos,warmup,'evaluation_scope.feedback_only')
    scoped(scope.usable_order_nos,available,'evaluation_scope.usable')
    unusable=[i.order_no for i in scope.unusable_items]
    scoped(unusable,scored,'evaluation_scope.unusable')
    require(not(set(unusable)&set(scope.usable_order_nos)),'evaluation_scope.overlap')
    require(missing<=set(unusable),'evaluation_scope.missing')
    require(all(i.reason.strip() for i in scope.unusable_items),'evaluation_scope.reason')

    base=raw.base_level;level=raw.estimated_level
    if raw.status=='insufficient_evidence':
        require(base is None and level is None,'insufficient_evidence.levels')
    else:
        require(base in c['base_levels'],'assessed.base_level')
    if not available:
        require(raw.status=='insufficient_evidence','all_inputs_unavailable')
    if base=='IM':
        require(level in ('IM1','IM2','IM3',None),'IM.estimated_level')
        expected='provisional' if level is not None else 'insufficient_evidence'
        require(raw.im_estimation_status==expected,'IM.status')
        if level is not None:
            require(raw.im_rubric_version==criteria['im_rubric_version'],'IM.rubric_version')
    else:
        require(level==base,'base_estimated_consistency')
        require(raw.im_estimation_status=='not_applicable','non_IM.status')
        require(raw.im_rubric_version is None,'non_IM.rubric_version')
    if raw.status=='insufficient_evidence' or (base=='IM' and level is None):
        require(isinstance(raw.insufficient_reason,str) and bool(raw.insufficient_reason.strip()),'insufficient_reason')
    if level is not None:
        require(all(abs(c['levels'].index(l)-c['levels'].index(level))==1 for l in raw.borderline_levels),'borderline.adjacent')
    elif base=='IM':
        require(set(raw.borderline_levels)<={'IM1','IM2','IM3'},'borderline.IM')

    for dimension in raw.dimension_feedback.model_dump().values():
        scoped(dimension['evidence_order_nos'],available,'dimension_feedback.orders')
    for name,entries in raw.coverage.model_dump().items():
        field={'functions':'target_functions','time_frames':'target_time_frames','contexts':'context_scope'}[name]
        require(len({e['name'] for e in entries})==len(entries),'coverage.duplicate_name')
        for entry in entries:
            require(entry['name'] in c['question_tags'][field],'coverage.vocabulary')
            expected={n for n in scored if entry['name'] in rows[n][field]}
            exact_list(entry['elicited_order_nos'],expected,'coverage.elicited')
            scoped(entry['usable_order_nos'],expected&available,'coverage.usable')
    for fact in raw.fact_evidence:
        require(fact.order_no is None or fact.order_no in scored,'fact_evidence.order')
        if fact.order_no in missing:
            require(fact.status=='not_observed','fact_evidence.unavailable')
        if fact.order_no is None or fact.status=='not_observed':
            require(fact.quote is None,'fact_evidence.null_quote')
        elif fact.quote is not None:
            quote(fact.order_no,fact.quote,'fact_evidence')
    for entry in raw.sustained_performance:
        for ref in entry.evidence: quote(ref.order_no,ref.quote,'sustained_performance')
    for entry in raw.breakdown_observations:
        for ref in entry.evidence: quote(ref.order_no,ref.quote,'breakdown_observations')
    exact_list([item.order_no for item in raw.items],all_orders,'items.orders')
    for item in raw.items:
        if item.order_no not in rows: continue
        row=rows[item.order_no]
        require(item.evaluation_role==('scored' if row['is_scored'] else 'feedback_only'),'items.role')
        if not usable(row):
            require(item.task_fulfillment=='not_assessable','items.not_assessable')
        for text in item.evidence: quote(item.order_no,text,'items.evidence',grade_evidence=row['is_scored'])
        for mistake in item.mistakes: quote(item.order_no,mistake.quote,'items.mistake',grade_evidence=row['is_scored'])
    minimum=3 if raw.status=='assessed' else 0
    require(minimum<=len(raw.feedback_cards)<=5,'feedback_cards.count')
    for card in raw.feedback_cards:
        scoped(card.related_order_nos,scored,'feedback_cards.orders')
        if card.before is None:
            require(card.example_kind=='practice','feedback_cards.practice')
        else:
            found=any(n in available and normalize(card.before) and normalize(card.before) in normalize(rows[n].get('stt_text') or '')
                      for n in card.related_order_nos)
            require(found,'feedback_cards.before')
    if base=='IM' and level is not None:
        require(len(evidence_quotes)>=2 and len({rows[n]['question_type'] for n,_ in evidence_quotes})>=2,'IM.minimum_evidence')
    narratives=[raw.headline,raw.grade_rationale,raw.fluency_observations,raw.why_this_level,raw.why_not_lower,raw.next_level_gap]
    for text in narratives:
        require(not any(re.search(pattern,text,re.I) for pattern in FORBIDDEN_PATTERNS),'forbidden_narrative')
    if errors:
        failure=LLMOutputError('; '.join(dict.fromkeys(errors)))
        # These are code-defined labels only, never quotes or provider bodies.
        failure.validation_errors=list(dict.fromkeys(errors))
        raise failure
    payload=raw.model_dump()
    payload['assessment_status']=payload.pop('status')
    payload['tier']=tier_of(level)
    payload['provisional_label']=c['policies']['im_provisional_label'] if base=='IM' and level is not None else None
    payload['disclaimer']=c['policies']['disclaimer']
    return EvaluationResult.model_validate(payload)
