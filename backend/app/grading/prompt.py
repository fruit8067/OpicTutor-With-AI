# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성했습니다.
# 후속 수정: 건너뛴 문항 표시(v6 템플릿)는 Claude(Anthropic)의 도움으로 작성했습니다.
# OWNER: grader (contracts.yaml ownership)
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
import hashlib
import json
import re
from html import escape
from app.config import settings
from app.schemas.internal import EvidenceBundle
from .rules import contract
from .validate import usable,skipped

_exam_meta=ContextVar('grading_exam_meta',default={})
TEMPLATE_VERSION='evaluate_exam.v6'

@contextmanager
def exam_context(meta):
    token=_exam_meta.set(meta)
    try: yield
    finally: _exam_meta.reset(token)

def load_system_prompt() -> tuple[str,dict]:
    text=settings.EVAL_SYSTEM_PROMPT_PATH.read_text(encoding='utf-8')
    criteria=contract()['evaluation_criteria']
    if criteria['prompt_version'] not in text or criteria['rubric_version'] not in text:
        raise ValueError('고정 시스템 프롬프트 버전 불일치')
    return text,{'rubric_version':criteria['rubric_version'],'prompt_version':criteria['prompt_version'],
                 'sha1':hashlib.sha1(text.replace('\r\n','\n').encode()).hexdigest()}

def data(value,*,attribute=False):
    return escape(json.dumps(value,ensure_ascii=False,default=str),quote=attribute)

def build_messages(snapshot: list[dict], evidence: EvidenceBundle) -> list[dict]:
    system,_=load_system_prompt()
    template=(Path(__file__).resolve().parents[2]/'prompts'/f'{TEMPLATE_VERSION}.md').read_text(encoding='utf-8')
    meta={**_exam_meta.get(),'assessment_basis':'transcript_and_metrics'}
    scored=[row for row in snapshot if row['is_scored']]
    eligible=[row['order_no'] for row in scored if usable(row)]
    constraints={'evaluation_scope':{
        'submitted_order_nos':[row['order_no'] for row in snapshot],
        'scored_order_nos':[row['order_no'] for row in scored],
        'feedback_only_order_nos':[row['order_no'] for row in snapshot if not row['is_scored']],
        'usable_order_nos_allowed':eligible,
        'unusable_items_required':[row['order_no'] for row in scored if not usable(row)]},'coverage':{}}
    for group,field in [('functions','target_functions'),('time_frames','target_time_frames'),('contexts','context_scope')]:
        constraints['coverage'][group]=[{
            'name':name,'elicited_order_nos':[row['order_no'] for row in scored if name in row[field]],
            'usable_order_nos_allowed':[row['order_no'] for row in scored if name in row[field] and usable(row)]}
            for name in contract()['question_tags'][field]]
    pieces=[template,'<exam_meta>'+data(meta)+'</exam_meta>',
            '<required_output_metadata>'+data(constraints)+'</required_output_metadata>']
    for row in snapshot:
        attrs={k:row[k] for k in ['order_no','question_type','is_scored','target_functions','target_time_frames','context_scope','stt_status']}
        attrs['skipped']=skipped(row)
        pieces.append('<item metadata="'+data(attrs,attribute=True)+'">')
        pieces.append('<question>'+escape(row['question_text'],quote=False)+'</question>')
        text=row.get('stt_text')
        if skipped(row): pieces.append('<transcript status="skipped"/>')
        elif row['stt_status']=='done' and isinstance(text,str) and text.strip():
            pieces.append('<transcript untrusted="true">'+escape(text,quote=False)+'</transcript>')
            candidates=[match.group().strip() for match in re.finditer(r'[^.!?]+(?:[.!?]+|$)',text) if match.group().strip()]
            pieces.append('<verbatim_quote_candidates>'+data(candidates)+'</verbatim_quote_candidates>')
        else: pieces.append('<transcript status="unavailable"/>')
        pieces.append('<metrics>'+data(row.get('metrics'))+'</metrics>')
        examples=[d for d in evidence.docs if d.get('order_no')==row['order_no'] and d.get('doc_type')=='answer']
        pieces.append('<reference_examples untrusted="true">'+data(examples)+'</reference_examples>')
        pieces.append('</item>')
    patterns=[d for d in evidence.docs if d.get('doc_type')=='upgrade_pattern']
    pieces.append('<upgrade_patterns untrusted="true">'+data(patterns)+'</upgrade_patterns>')
    return [{'role':'system','content':system},{'role':'user','content':'\n'.join(pieces)}]
