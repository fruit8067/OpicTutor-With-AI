# AI-assisted (OpenAI Codex). OWNER: orchestrator.
"""Bounded A/B provider smoke check; no user answers or C implementation.

Default is configuration inspection. --run embeds one tiny input and performs
a structured Pickle ping (at most three requests per provider, including retries).
This proves connectivity/schema compatibility, not grading accuracy.
"""
import argparse
import json
import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel
from verify_core import compose_sources


class Ping(BaseModel):
    ok: bool


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',type=Path,required=True)
    parser.add_argument('--run',action='store_true')
    args=parser.parse_args()
    env_relative=Path('backend/.env') if (args.workspace/'backend/app').is_dir() else Path('OpicTutor-With-AI/backend/.env')
    env_file=args.workspace/env_relative
    # The user maintains this one file. Never copy credentials among worktrees.
    load_dotenv(env_file,override=False)
    compose_sources(args.workspace,emit_manifest=False)
    from app.config import settings
    from app.llm import chat,embeddings
    report={'env_file':env_relative.as_posix(),'env_file_bytes':env_file.stat().st_size if env_file.exists() else None,
            'llm_model':settings.LLM_MODEL,'embedding_model':settings.EMBED_MODEL,'embedding_dimensions':settings.EMBED_DIM,
            'llm_key_present':bool(os.getenv('LLM_API_KEY','').strip() or os.getenv('PICKLE_API_KEY','').strip()),
            'embedding_key_present':bool(settings.EMBED_API_KEY.strip()),'external_requests_before_run':0}
    print(json.dumps(report,ensure_ascii=True),flush=True)
    if not args.run: return 0
    if not report['llm_key_present'] or not report['embedding_key_present']:
        print('Missing provider keys; no requests made. Save the backend/.env file shown above.')
        return 2
    from app import db
    from app.db import pool
    try:
        # Validate LLM config before a potentially billable embedding call.
        chat.llm_options()
        db.init_db()
        vector=embeddings.embed_texts(['Provider connection test.'])[0]
        with chat._track_requests(3) as trace:
            result,usage=chat.chat_structured([{'role':'user','content':'Return only JSON {"ok": true} for this connection check.'}],Ping,timeout=settings.LLM_TIMEOUT_SEC)
        print(json.dumps({'embedding_dimensions_observed':len(vector),'pickle_structured_ping':result.ok,
                          'llm_requests':len(trace.records),'llm_usage':usage},ensure_ascii=True))
        return 0 if result.ok and len(vector)==settings.EMBED_DIM else 1
    except Exception as exc:
        # Provider errors may echo credentials/bodies. Print only the type.
        print(json.dumps({'provider_check':'failed','error_type':type(exc).__name__}))
        return 1
    finally:
        if pool._pool is not None: pool._pool.close()


if __name__=='__main__':
    raise SystemExit(main())
