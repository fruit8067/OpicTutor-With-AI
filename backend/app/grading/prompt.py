# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성했습니다.
# OWNER: grader (contracts.yaml ownership)
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
import hashlib
import json
from html import escape
from app.config import settings
from app.schemas.internal import EvidenceBundle
from .rules import contract

_exam_meta=ContextVar('grading_exam_meta',default={})
TEMPLATE_VERSION='evaluate_exam.v1'

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

def data(value):
    return escape(json.dumps(value,ensure_ascii=False,default=str),quote=True)

def build_messages(snapshot: list[dict], evidence: EvidenceBundle) -> list[dict]:
    system,_=load_system_prompt()
    template=(Path(__file__).resolve().parents[2]/'prompts'/f'{TEMPLATE_VERSION}.md').read_text(encoding='utf-8')
    meta={**_exam_meta.get(),'assessment_basis':'transcript_and_metrics'}
    pieces=[template,'<exam_meta>'+data(meta)+'</exam_meta>']
    for row in snapshot:
        attrs={k:row[k] for k in ['order_no','question_type','is_scored','target_functions','target_time_frames','context_scope','stt_status']}
        pieces.append('<item metadata="'+data(attrs)+'">')
        pieces.append('<question>'+escape(row['question_text'])+'</question>')
        text=row.get('stt_text')
        if row['stt_status']=='done' and isinstance(text,str) and text.strip():
            pieces.append('<transcript untrusted="true">'+escape(text)+'</transcript>')
        else: pieces.append('<transcript status="unavailable"/>')
        pieces.append('<metrics>'+data(row.get('metrics'))+'</metrics>')
        examples=[d for d in evidence.docs if d.get('order_no')==row['order_no'] and d.get('doc_type')=='answer']
        pieces.append('<reference_examples untrusted="true">'+data(examples)+'</reference_examples>')
        pieces.append('</item>')
    patterns=[d for d in evidence.docs if d.get('doc_type')=='upgrade_pattern']
    pieces.append('<upgrade_patterns untrusted="true">'+data(patterns)+'</upgrade_patterns>')
    return [{'role':'system','content':system},{'role':'user','content':'\n'.join(pieces)}]
