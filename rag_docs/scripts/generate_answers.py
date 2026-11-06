"""
question_bank.yaml 의 status: todo 문항에 대해 9등급 대조 답변을 생성해
source/contrast_sets_gen_XX.yaml 로 저장한다. (파일럿 세트와 같은 형식)

- 프롬프트에 루브릭 + 등급별 제약표 + 파일럿 대조 세트 2개(few-shot)를 넣는다.
- 생성 후 build_corpus.py 의 길이 검사, check_monotonic.py, cross_validate.py 를 반드시 통과시킨다.

AI-assisted: Claude(Anthropic)의 도움으로 작성.
사용법: python scripts/generate_answers.py --limit 6
"""
import argparse
import glob
import re
from pathlib import Path

import yaml

from llm import gen

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "source"
LEVELS = ["NL", "NM", "NH", "IL", "IM1", "IM2", "IM3", "IH", "AL"]

SYSTEM = """You write calibrated OPIc sample answers for a Korean test-prep RAG corpus.
For ONE question, write 9 answers, one per level: NL, NM, NH, IL, IM1, IM2, IM3, IH, AL.
Rules:
- Speaker is a Korean university student. Keep the same persona and facts across levels so only the language quality differs.
- Obey each level's word range, sentence level, tense control and error rate in the constraint table EXACTLY.
- Lower levels must contain realistic Korean-learner errors (missing articles, 3rd-person -s, present-for-past, missing plurals, 'listen music').
- IM2 overuses simple connectors (so, because, actually); IH/AL use advanced discourse markers and keep tense control.
- Do NOT copy any published model answer. Write originally.
- rationale and upgrade_tip are in Korean, one sentence each. AL upgrade_tip is null.
- Output ONLY YAML in the exact format of the examples (top key = question id). Use double quotes for text; escape inner double quotes."""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=6)
    args = ap.parse_args()

    rub = (SRC / "rubrics.yaml").read_text(encoding="utf-8")
    cons = (SRC / "level_constraints.yaml").read_text(encoding="utf-8")
    pilot = yaml.safe_load((SRC / "contrast_sets_01.yaml").read_text(encoding="utf-8"))
    shots = yaml.safe_dump({k: pilot[k] for k in ("Q001", "Q003")}, allow_unicode=True, sort_keys=False, width=1000)

    done = set()
    for p in glob.glob(str(SRC / "contrast_sets_*.yaml")):
        done |= set(yaml.safe_load(open(p, encoding="utf-8")) or {})
    todo = [q for q in yaml.safe_load((SRC / "question_bank.yaml").read_text(encoding="utf-8"))["questions"]
            if q["status"] == "todo" and q["id"] not in done][: args.limit]

    n = len(glob.glob(str(SRC / "contrast_sets_gen_*.yaml"))) + 1
    out = {}
    for q in todo:
        user = (f"# Rubric\n{rub}\n\n# Constraint table\n{cons}\n\n# Examples\n{shots}\n\n"
                f"# Target\nid: {q['id']}\nquestion_type: {q['question_type']}\nquestion: {q['question']}")
        raw = gen(SYSTEM, user, max_tokens=6000)
        raw = re.sub(r"^```(yaml)?|```$", "", raw.strip(), flags=re.M)
        try:
            data = yaml.safe_load(raw)
            assert set(data[q["id"]]) == set(LEVELS)
            out.update(data)
            print("ok", q["id"])
        except Exception as e:  # noqa: BLE001
            print("FAIL", q["id"], e)
            (SRC / f"_failed_{q['id']}.txt").write_text(raw, encoding="utf-8")

    if out:
        path = SRC / f"contrast_sets_gen_{n:02d}.yaml"
        header = "# 등급 대조 세트 (source_tier C, LLM 생성 — cross_validate 통과 전에는 검수 대기)\n"
        path.write_text(header + yaml.safe_dump(out, allow_unicode=True, sort_keys=False, width=1000), encoding="utf-8")
        print("saved", path)


if __name__ == "__main__":
    main()
