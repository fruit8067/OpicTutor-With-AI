"""
OpicTutor RAG 코퍼스 빌더
- source/*.yaml(루브릭, 승급 패턴, 문항 뱅크, 대조 세트)을 읽어 build/*.jsonl 로 변환한다.
- 답변마다 clean/stt 두 가지 버전 문서를 만든다(STT 변환은 seed 고정으로 재현 가능).
- 등급별 길이 제약 위반, 누락 등급, 스키마 오류를 검사해 build/report.md 로 남긴다.

AI-assisted: 이 스크립트와 source/ 의 합성 답변은 Claude(Anthropic)의 도움으로 작성되었다.

사용법: python scripts/build_corpus.py   (rag_docs/ 에서 실행)
"""
import glob
import json
import random
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SRC, OUT = ROOT / "source", ROOT / "build"
LEVELS = ["NL", "NM", "NH", "IL", "IM1", "IM2", "IM3", "IH", "AL"]
RANK = {lv: i + 1 for i, lv in enumerate(LEVELS)}
WORD = re.compile(r"[A-Za-z0-9']+")

FILLERS_LOW = ["um", "uh", "um", "uh", "hmm"]
FILLERS_HIGH = ["um", "uh", "like", "you know", "I mean"]


def load(name):
    with open(SRC / name, encoding="utf-8") as f:
        return yaml.safe_load(f)


def to_stt(text: str, level: str, cfg: dict, seed: str) -> str:
    """깔끔한 전사본을 STT 출력처럼 변환: 소문자, 구두점 제거, 필러/반복/재시작 삽입."""
    rng = random.Random(seed)
    words = WORD.findall(text.replace("...", " "))
    fillers = FILLERS_LOW if RANK[level] <= RANK["IM1"] else FILLERS_HIGH
    p_fill = cfg["filler_per100"] / 100
    p_rep = cfg["repeat_per100"] / 100
    p_rst = cfg["restart_per100"] / 100
    out = []
    for i, w in enumerate(words):
        w = w if w == "I" or w.startswith("I'") else w.lower()
        r = rng.random()
        if r < p_fill:
            out.append(rng.choice(fillers))
        elif r < p_fill + p_rst and i >= 2:
            out.extend(words[i - 2 : i])  # 앞 두 단어로 다시 시작
            out[-2:] = [x if x == "I" else x.lower() for x in out[-2:]]
        out.append(w)
        if rng.random() < p_rep:
            out.append(w)  # 같은 단어 반복(말더듬)
    return " ".join(out)


def main():
    OUT.mkdir(exist_ok=True)
    rub = load("rubrics.yaml")
    cons = load("level_constraints.yaml")
    qbank = {q["id"]: q for q in load("question_bank.yaml")["questions"]}
    sets = {}
    for p in sorted(glob.glob(str(SRC / "contrast_sets_*.yaml"))):
        sets.update(yaml.safe_load(open(p, encoding="utf-8")))

    problems, stats = [], []

    # 1) 루브릭
    with open(OUT / "rubrics.jsonl", "w", encoding="utf-8") as f:
        for r in rub["levels"]:
            body = "\n".join(
                f"{k}: {', '.join(v) if isinstance(v, list) else v}"
                for k, v in r.items() if k not in ("level", "level_rank", "source_tier")
            )
            doc = {"id": f"RUBRIC-{r['level']}", "doc_type": "rubric", "level": r["level"],
                   "level_rank": r["level_rank"], "source_tier": r["source_tier"],
                   "text": f"[OPIc {r['level']} 등급 기준]\n{body}",
                   "license": "paraphrased_from_ACTFL_2024_with_attribution" if r["source_tier"] == "A" else "project_defined"}
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")

    # 2) 승급 패턴
    with open(OUT / "upgrade_patterns.jsonl", "w", encoding="utf-8") as f:
        for u in rub["upgrade_patterns"]:
            text = (f"[{u['from']} → {u['to']} 승급 패턴]\n핵심 변화: {u['key_shift']}\n실천:\n- "
                    + "\n- ".join(u["actions"])
                    + f"\nBefore: {u['example_before']}\nAfter: {u['example_after']}")
            doc = {"id": f"UPGRADE-{u['from']}-{u['to']}", "doc_type": "upgrade_pattern",
                   "from_level": u["from"], "to_level": u["to"], "level_rank": RANK[u["from"]],
                   "source_tier": "B", "text": text, "license": "self_authored"}
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")

    # 3) 문항 메타
    with open(OUT / "questions.jsonl", "w", encoding="utf-8") as f:
        for q in qbank.values():
            f.write(json.dumps({**q, "doc_type": "question", "text": q["question"]}, ensure_ascii=False) + "\n")

    # 4) 답변 (clean + stt)
    n = 0
    with open(OUT / "answers.jsonl", "w", encoding="utf-8") as f:
        for qid, levels in sets.items():
            q = qbank.get(qid)
            if not q:
                problems.append(f"{qid}: question_bank 에 없음")
                continue
            missing = [lv for lv in LEVELS if lv not in levels]
            if missing:
                problems.append(f"{qid}: 누락 등급 {missing}")
            for lv, a in levels.items():
                for key in ("text", "rationale"):
                    if not a.get(key):
                        problems.append(f"{qid}-{lv}: {key} 비어 있음")
                wc = len(WORD.findall(a["text"]))
                lo, hi = cons[lv]["words"]
                if not lo <= wc <= hi:
                    problems.append(f"{qid}-{lv}: 단어 수 {wc} (기준 {lo}~{hi})")
                stats.append((qid, lv, wc))
                c = cons[lv]
                base = {
                    "doc_type": "answer", "level": lv, "level_rank": RANK[lv],
                    "question_id": qid, "question_type": q["question_type"], "topic": q["topic"],
                    "survey": q["survey"], "question": q["question"],
                    "word_count": wc, "est_seconds": round(wc / (1.3 if RANK[lv] <= 4 else 2.0)),
                    "features": {k: c[k] for k in ("sentence_level", "tense", "error_rate")},
                    "rationale": a["rationale"], "upgrade_tip": a.get("upgrade_tip"),
                    "next_level": LEVELS[RANK[lv]] if RANK[lv] < 9 else None,
                    "contrast_set_id": qid, "source_tier": "C",
                    "verified_by": ["author_review"], "license": "self_generated",
                }
                for style in ("clean", "stt"):
                    txt = a["text"] if style == "clean" else to_stt(a["text"], lv, c["stt"], f"{qid}-{lv}")
                    doc = {"id": f"{qid}-{lv}-{style}", **base, "text_style": style, "answer_text": txt,
                           # 임베딩 대상 텍스트: 답변 + 등급 근거를 한 청크로
                           "text": f"[Q] {q['question']}\n[A·{lv}] {txt}\n[근거] {a['rationale']}"}
                    f.write(json.dumps(doc, ensure_ascii=False) + "\n")
                    n += 1

    # 리포트
    by_lv = {lv: [w for _, l, w in stats if l == lv] for lv in LEVELS}
    lines = ["# Build report", "", f"- 대조 세트: {len(sets)}개 / 답변 문서: {n}개 (clean+stt)",
             f"- 루브릭: {len(rub['levels'])}개 / 승급 패턴: {len(rub['upgrade_patterns'])}개 / 문항: {len(qbank)}개", "",
             "| 등급 | 답변 수 | 평균 단어 | 최소 | 최대 | 기준 |", "|---|---|---|---|---|---|"]
    for lv in LEVELS:
        ws = by_lv[lv]
        if ws:
            lines.append(f"| {lv} | {len(ws)} | {sum(ws)/len(ws):.0f} | {min(ws)} | {max(ws)} | {cons[lv]['words'][0]}~{cons[lv]['words'][1]} |")
    lines += ["", "## 문제", *(f"- {p}" for p in problems)] if problems else ["", "## 문제", "- 없음"]
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
