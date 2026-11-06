# AI-assisted (OpenAI Codex). OWNER: orchestrator.
"""Run the owned grader CLI with explicit pre-merge A/B module composition.

Examples (repo root, activated venv):
  python docs/compliance/run_eval.py --workspace .. --limit 4 --school-credit-usd 10 --embedding-usd-per-million .13 --yes
"""
import argparse
import importlib.util
from pathlib import Path
import sys
from dotenv import load_dotenv
from verify_core import compose_sources


def main():
    parser=argparse.ArgumentParser(description=__doc__,add_help=False)
    parser.add_argument('--workspace',type=Path,required=True)
    args,remaining=parser.parse_known_args()
    relative=Path('backend/.env') if (args.workspace/'backend/app').is_dir() else Path('OpicTutor-With-AI/backend/.env')
    load_dotenv(args.workspace/relative,override=False)
    sources=compose_sources(args.workspace)
    path=sources['grader']/'backend/scripts/eval_exam.py'
    spec=importlib.util.spec_from_file_location('owned_eval_cli',path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module;spec.loader.exec_module(module)
    sys.argv=['eval_exam',*remaining]
    return module.main()


if __name__=='__main__': raise SystemExit(main())
