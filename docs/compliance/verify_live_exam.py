# AI-assisted (OpenAI Codex). OWNER: orchestrator.
"""One real synthetic exam through queue/validation/DB, in a disposable database.

Uses the configured provider and its normal <=3-request budget. Existing RAG
vectors are copied locally; no paid reembedding or user recording is performed.
This is a connectivity/contract smoke check, not an accuracy study.
"""
import argparse
import json
from pathlib import Path
from threading import Event
import time
from html import unescape
from uuid import uuid4
from dotenv import load_dotenv
import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo
from pydantic import ValidationError
from verify_core import compose_sources


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',type=Path,required=True)
    parser.add_argument('--level',default='IL')
    parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args()
    env=Path('backend/.env') if (args.workspace/'backend/app').is_dir() else Path('OpicTutor-With-AI/backend/.env')
    load_dotenv(args.workspace/env,override=False)
    sources=compose_sources(args.workspace,emit_manifest=False)
    from app.config import settings
    from app import db
    from app.db import pool,dev
    from app.worker.runner import execute
    from app.grading import service
    from app.grading.prompt import TEMPLATE_VERSION
    from app.grading.validate import normalize
    schema_errors=[];original_chat=service.chat_structured
    quote_diagnostics=[];original_validate=service.validate_output
    def diagnose_quotes(raw,snapshot):
        try: return original_validate(raw,snapshot)
        except Exception:
            texts={row['order_no']:row.get('stt_text') or '' for row in snapshot}
            for item in raw.items:
                for quote in item.evidence:
                    if normalize(quote) not in normalize(texts.get(item.order_no,'')):
                        quote_diagnostics.append({'order_no':item.order_no,'characters':len(quote),
                            'html_entities_present':unescape(quote)!=quote,
                            'valid_after_html_unescape':normalize(unescape(quote)) in normalize(texts.get(item.order_no,'')),
                            'matches_another_answer':any(n!=item.order_no and normalize(quote) in normalize(t) for n,t in texts.items())})
            raise
    service.validate_output=diagnose_quotes
    def diagnose(*a,**kw):
        try: return original_chat(*a,**kw)
        except Exception as exc:
            cause=exc
            while cause is not None:
                if isinstance(cause,ValidationError):
                    schema_errors.extend(e['type'] for e in cause.errors(include_input=False,include_url=False))
                cause=cause.__cause__
            raise
    service.chat_structured=diagnose
    original=settings.DATABASE_URL;database='opic_live_grade_'+uuid4().hex[:16]
    with psycopg.connect(original,autocommit=True,connect_timeout=5) as admin:
        admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(database)))
        try:
            settings.DATABASE_URL=make_conninfo(original,dbname=database);db.init_db()
            with psycopg.connect(original,connect_timeout=5) as src:
                if not src.execute('SELECT count(embedding) FROM rag_docs').fetchone()[0]:
                    raise RuntimeError('Ingest the corpus before running the live exam check')
                with src.cursor().copy('COPY rag_docs TO STDOUT') as outbound:
                    with pool.tx() as cur:
                        with cur.copy('COPY rag_docs FROM STDIN') as inbound:
                            for chunk in outbound: inbound.write(chunk)
            sid,eid=dev.seed_grading_session(level=args.level)
            worker='live-grade-'+uuid4().hex[:8];job=db.claim_job(['evaluate'],worker,60)
            assert job is not None
            start=time.monotonic();outcome=execute(job,worker,60,Event());elapsed=time.monotonic()-start
            e=db.get_evaluation(eid);s=db.get_session(sid)
            with pool.tx() as cur:
                logs=cur.execute('SELECT model,input_tokens,output_tokens,latency_ms,status,error_code FROM ai_requests ORDER BY created_at').fetchall()
            result=e.get('result_json') or {}
            report={'scope':__doc__.splitlines()[0],'synthetic_source_level':args.level,
                    'worker_outcome':outcome,'session_status':s['status'],'evaluation_status':e['status'],
                    'error_code':e.get('error_code'),'error_detail':e.get('error_detail'),
                    'schema_error_types':sorted(set(schema_errors)),
                    'user_template_version':TEMPLATE_VERSION,'invalid_quote_diagnostics':quote_diagnostics,
                    'base_level':e.get('base_level'),'estimated_level':e.get('estimated_level'),
                    'assessment_status':e.get('assessment_status'),'item_count':len(result.get('items',[])),
                    'elapsed_sec':round(elapsed,3),'ai_requests':logs,
                    'sources':{role:{'path':path.relative_to(args.workspace.resolve()).as_posix(),
                                    'note':'explicit role composition'} for role,path in sources.items()},
                    'c_implementation_added':False,'accuracy_study':False}
        finally:
            if pool._pool is not None: pool._pool.close()
            admin.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(database)))
        report['isolated_database_cleaned']=True
        args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(report,ensure_ascii=True))
        return 0 if e['status']=='done' else 1


if __name__=='__main__': raise SystemExit(main())
