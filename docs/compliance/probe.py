# AI-assisted: Compliance inspection written with OpenAI Codex.
"""Read-only/static checks and isolated in-memory boundary reproductions."""
import ast
import importlib
import inspect
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'backend'), str(ROOT / 'backend/tests')]
import yaml
from test_grading_validate import snapshot, output, validate
from app.grading import evidence
from unittest.mock import patch

c = yaml.safe_load((ROOT / 'agents/contracts.yaml').read_text(encoding='utf-8'))
def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT).decode('utf-8')
def emit(name, value):
    print(json.dumps({'check':name, 'result':value}, ensure_ascii=True))

def norm(node):
    return ast.dump(node, include_attributes=False) if node is not None else None

emit('audited_commit',git('rev-parse','HEAD').strip())

signature_diffs = []
signature_count = 0
for label, block in c['module_interfaces'].items():
    module_name = label.split(' ')[0]
    if module_name not in ['app.db', 'app.db.dev', 'app.llm.embeddings', 'app.llm.chat',
                           'app.exam', 'app.stt', 'app.grading', 'app.errors']:
        continue
    lines = block.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index].split('#')[0].strip()
        index += 1
        if not line.startswith('def '):
            continue
        while line.count('(') > line.count(')'):
            line += ' ' + lines[index].split('#')[0].strip()
            index += 1
        if index < len(lines) and lines[index].strip().startswith('->'):
            line += ' ' + lines[index].strip()
            index += 1
        for part in line.split(';'):
            expected = ast.parse(part.strip() + ': pass').body[0]
            actual_module = module_name
            if expected.name == 'handle':
                actual_module += '.job'
            try:
                func = getattr(importlib.import_module(actual_module), expected.name)
                actual = ast.parse(inspect.getsource(func)).body[0]
                signature_count += 1
                if norm(expected.args) != norm(actual.args) or norm(expected.returns) != norm(actual.returns):
                    signature_diffs.append({'function':actual_module+'.'+expected.name,
                        'expected':part.strip(), 'actual':str(inspect.signature(func))})
            except (AttributeError, ImportError) as exc:
                signature_diffs.append({'function':actual_module+'.'+expected.name, 'missing':type(exc).__name__})
emit('public_signatures', {'count':signature_count,'differences':signature_diffs})

branches = [('bootstrap','origin/main'),('data-layer','agent/bootstrap'),('session-api','agent/data-layer'),
            ('corpus','agent/session-api'),('grader','agent/corpus'),('worker-stt','agent/grader'),
            ('integrator','agent/worker-stt')]
ownership = importlib.util.spec_from_file_location('ownership',ROOT/'agents/tools/check_ownership.py')
checker = importlib.util.module_from_spec(ownership)
ownership.loader.exec_module(checker)
def errors(role,base,head):
    paths=git('diff','--name-only',base+'...'+head).splitlines()
    bad=[]
    for path in paths:
        owner=next((r['owner'].replace('{agent_id}',role) for r in c['ownership']
                    if checker.matches(path,r['path'].replace('{agent_id}',role))),None)
        if owner!=role: bad.append({'path':path,'owner':owner})
    return {'changed':len(paths),'violations':bad}
emit('ownership', [{'role':role,'default_failed_files':len(errors(role,'origin/main','agent/'+role)['violations']),
                     'pr_delta':errors(role,base,'agent/'+role) if role!='bootstrap' else 'phase0 exception'} for role,base in branches])

schema_expected = re.sub(r'--[^\n]*','', c['db_schema_sql'])
schema_actual = re.sub(r'--[^\n]*','', (ROOT/'backend/migrations/001_init.sql').read_text(encoding='utf-8'))
emit('migration_matches_contract', re.sub(r'\s+','',schema_expected)==re.sub(r'\s+','',schema_actual))

rows=snapshot()
rows[-1].update(stt_status='failed',stt_text='')
raw=output(rows)
raw['evaluation_scope'].update(usable_order_nos=list(range(2,8)),unusable_items=[dict(order_no=8,reason='STT failed')])
for entries in raw['coverage'].values():
    for entry in entries:
        entry['usable_order_nos']=[n for n in entry['usable_order_nos'] if n!=8]
raw['items'][-1].update(task_fulfillment='not_assessable',evidence=[])
for status in ['demonstrated','not_demonstrated']:
    raw['fact_evidence']=[dict(criterion='functions_tasks',observation='Missing transcript',status=status,order_no=8,quote=None)]
    try:
        validate(raw,rows)
        accepted=True
    except Exception as exc:
        accepted=type(exc).__name__
    emit('missing_transcript_fact_'+status, {'accepted':accepted})

def stale_doc(qid):
    return dict(id=qid+'-IM2-stt',doc_type='answer',level='IM2',contrast_set_id=qid,
                text='old version reference',text_style='stt',corpus_version='old-v1')
with patch.object(evidence.db,'current_corpus_version',return_value='current-v2'), \
     patch.object(evidence.db,'get_contrast_set',side_effect=lambda qid,**kwargs:[stale_doc(qid)]), \
     patch.object(evidence.db,'get_rag_docs',return_value=[]), \
     patch.object(evidence.db,'search_similar_answers',return_value=[stale_doc('OLD')]), \
     patch.object(evidence,'embed_texts',return_value=[[1.0]]), \
     patch.object(evidence,'token_count',return_value=100):
    bundle=evidence.build_evidence(snapshot())
    emit('fallback_corpus_version',{'reported':bundle.corpus_version,'retrieved':bundle.retrieved_doc_ids,
                                   'actual_doc_version':'old-v1'})

tracked=git('ls-files').splitlines()
added=git('log','--format=','--name-only','--diff-filter=A','origin/main..HEAD').splitlines()
def prohibited(path):
    return bool(re.search(r'(^|/)(\.env($|\.)|data/)|\.(wav|webm|mp3|mp4|pt|bin|safetensors)$',path,re.I)) and not path.endswith('.env.example')
emit('prohibited_tracked_paths',sorted(set(p for p in tracked+added if prohibited(p))))
emit('prompt_unchanged',not git('diff','origin/main','--','docs/prompts/opic_evaluation_system.md').strip())
emit('policy_files', {p:(ROOT/p).exists() for p in ['.gitattributes','.github/workflows/ownership.yml','docs/REVIEW.md']})
emit('handoff_sections', {p.stem:re.findall(r'^## (.+)',p.read_text(encoding='utf-8'),re.M) for p in sorted((ROOT/'docs/handoff').glob('*.md'))})

import httpx
import os
import hashlib
from app.llm import chat
from app.grading import service
from app.schemas.internal import EvaluationLLMOutput, EvidenceBundle
real_openai=chat.OpenAI
environment={'LLM_BASE_URL':'https://pickle.example.invalid/v1','LLM_MODEL':'pickle-audit','LLM_API_KEY':'audit-no-network'}
def make_client(handler):
    return lambda **kwargs:real_openai(**kwargs,http_client=httpx.Client(transport=httpx.MockTransport(handler)))
with patch.dict(os.environ,environment), patch.object(chat,'OpenAI',make_client(lambda request:httpx.Response(408,json={'error':{'message':'timeout'}}))):
    try: chat.chat_structured([],EvaluationLLMOutput,timeout=1)
    except Exception as exc: emit('http_408_error_mapping',type(exc).__name__)

posts=[];logs=[]
def fallback_http(request):
    posts.append(str(request.url))
    if len(posts)==1:
        return httpx.Response(400,json={'error':{'message':'response_format json_schema not supported'}})
    return httpx.Response(200,json={'id':'audit','object':'chat.completion','created':0,'model':'pickle-audit',
        'choices':[{'index':0,'message':{'role':'assistant','content':json.dumps(output())},'finish_reason':'stop'}],
        'usage':{'prompt_tokens':100,'completion_tokens':50,'total_tokens':150}})
with patch.dict(os.environ,environment), patch.object(chat,'OpenAI',make_client(fallback_http)), \
     patch.object(service,'build_evidence',return_value=EvidenceBundle(corpus_version='fixture')), \
     patch.object(service.db,'log_ai_request',side_effect=lambda **kwargs:logs.append(kwargs)), \
     patch.object(service,'token_count',return_value=100):
    result,meta=service.evaluate_exam(snapshot())
    emit('json_fallback_request_accounting',{'http_requests':len(posts),'ai_request_rows':len(logs),'reported_llm_calls':meta['llm_calls']})

from app import db
from app.db.pool import tx
text=' Question with whitespace?\n'
expected_hash=hashlib.sha1(text.strip().encode('utf-8')).hexdigest()
if db.ping():
    with tx() as cur:
        cur.execute("SELECT encode(digest(%s,'sha1'),'hex')=%s AS accepts_host_hash",(text,expected_hash))
        emit('prepare_hash_predicate',cur.fetchone())
else: emit('prepare_hash_predicate','DB unavailable')
