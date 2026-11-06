# AI-assisted: A/B 코어 교차 검증 도구는 OpenAI Codex의 도움으로 작성했습니다.
"""Compose explicit A/B worktree modules in memory; never modify production files.

This is a pre-merge core contract check, not a C implementation or M3/browser exam.
Run with the project's venv Python and --workspace pointing to the worktree parent.
"""
import argparse
import ast
import importlib
import importlib.util
import json
import inspect
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4


def package(name, path):
    spec=importlib.util.spec_from_file_location(name,path/'__init__.py',submodule_search_locations=[str(path)])
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    if '.' in name:
        parent,child=name.rsplit('.',1)
        setattr(sys.modules[parent],child,module)
    spec.loader.exec_module(module)
    return module


def module_file(name, path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    parent,child=name.rsplit('.',1)
    setattr(sys.modules[parent],child,module)
    spec.loader.exec_module(module)
    return module


def check_interfaces():
    import yaml
    from app.schemas import api
    from app.main import app
    contract=yaml.safe_load((Path(__file__).resolve().parents[2]/'agents/contracts.yaml').read_text(encoding='utf-8'))
    errors=[];count=0
    modules={'app.errors','app.db','app.db.dev','app.llm.embeddings','app.llm.chat','app.exam','app.stt','app.grading'}
    def shape(node): return ast.dump(node,include_attributes=False) if node is not None else None
    for label,block in contract['module_interfaces'].items():
        name=label.split(' ')[0]
        if name not in modules: continue
        lines=block.splitlines();i=0
        while i<len(lines):
            line=lines[i].split('#')[0].strip();i+=1
            if not line.startswith('def '): continue
            while line.count('(')>line.count(')'):
                line+=' '+lines[i].split('#')[0].strip();i+=1
            if i<len(lines) and lines[i].strip().startswith('->'):
                line+=' '+lines[i].strip();i+=1
            for header in line.split(';'):
                expected=ast.parse(header.strip()+': pass').body[0]
                target=name+('.job' if expected.name=='handle' else '')
                actual=ast.parse(inspect.getsource(getattr(importlib.import_module(target),expected.name))).body[0]
                count+=1
                if shape(expected.args)!=shape(actual.args) or shape(expected.returns)!=shape(actual.returns):
                    errors.append(target+'.'+expected.name)
    for name,fields in contract['api_schemas'].items():
        if set(fields)!=set(getattr(api,name).model_fields): errors.append('API fields: '+name)
    paths=app.openapi()['paths']
    for endpoint in contract['api']['endpoints']:
        operation=paths.get('/api/v1'+endpoint['path'],{}).get(endpoint['method'].lower())
        if not operation or str(endpoint.get('status',200)) not in operation['responses']:
            errors.append('API route/status: '+endpoint['id'])
    result={'contract_version':contract['contract_version'],'public_signatures':count,
            'api_models':len(contract['api_schemas']),'api_endpoints':len(contract['api']['endpoints']),'differences':errors}
    print(json.dumps(result,ensure_ascii=True),flush=True)
    return int(bool(errors))


def compose_sources(root,emit_manifest=True):
    root=Path(root).resolve()
    sources={role:(root if (root/'backend/app').is_dir() else root/('OpicTutor-'+folder)) for role,folder in
             [('session-api','session'),('data-layer','data'),('grader','grader'),('worker-stt','worker')]}
    for role,path in sources.items():
        if not (path/'backend/app').is_dir(): raise ValueError(f'Missing {role} worktree: {path}')
    sys.path[:0]=[str(p/'backend') for p in sources.values()]+[str(p/'backend/tests') for p in sources.values()]
    package('app',sources['session-api']/'backend/app')
    package('app.db',sources['data-layer']/'backend/app/db')
    llm=importlib.import_module('app.llm')
    llm.__path__=[str(sources[r]/'backend/app/llm') for r in ['grader','data-layer']]
    llm.chat_structured=module_file('app.llm.chat',sources['grader']/'backend/app/llm/chat.py').chat_structured
    llm.embed_texts=module_file('app.llm.embeddings',sources['data-layer']/'backend/app/llm/embeddings.py').embed_texts
    package('app.worker',sources['worker-stt']/'backend/app/worker')
    package('app.stt',sources['worker-stt']/'backend/app/stt')
    package('app.grading',sources['grader']/'backend/app/grading')
    manifest={role:{'path':path.relative_to(root).as_posix(),'commit':subprocess.check_output(
        ['git','rev-parse','HEAD'],cwd=path,text=True).strip(),
        'dirty':bool(subprocess.check_output(['git','status','--porcelain'],cwd=path,text=True).strip())}
        for role,path in sources.items()}
    if emit_manifest:
        print(json.dumps({'verification':'A/B modules in-memory composition; C boundary fixtures only',
                          'sources':manifest},ensure_ascii=True),flush=True)
    return sources


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',type=Path,required=True)
    parser.add_argument('--interfaces-only',action='store_true',help='Compare declared signatures, API fields and routes without DB changes.')
    parser.add_argument('tests',nargs='*',help='Optional pytest paths; defaults to existing A/B module tests.')
    args=parser.parse_args()
    try: sources=compose_sources(args.workspace)
    except ValueError as exc: parser.error(str(exc))
    if args.interfaces_only: return check_interfaces()
    # 프로젝트 테스트의 subprocess도 backend에서 app을 찾도록 기존 실행 조건을 보존한다.
    tests=args.tests or [str(path/'backend/tests') for path in sources.values()]
    tests=[str(Path(path).resolve()) for path in tests]
    os.chdir(sources['grader']/'backend')
    import pytest
    import psycopg
    from psycopg import sql
    from psycopg.conninfo import make_conninfo
    from app.config import settings
    from app.db import pool
    database='opic_ab_check_'+uuid4().hex[:16]
    with psycopg.connect(settings.DATABASE_URL,autocommit=True) as admin:
        admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(database)))
        settings.DATABASE_URL=make_conninfo(settings.DATABASE_URL,dbname=database)
        print(json.dumps({'isolated_test_database':database}),flush=True)
        try:
            extra=Path(__file__).with_name('core_flow_cases.py')
            return pytest.main(['-q',*tests,*([str(extra)] if not args.tests else [])])
        finally:
            if pool._pool is not None: pool._pool.close()
            admin.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(database)))


if __name__=='__main__':
    raise SystemExit(main())
