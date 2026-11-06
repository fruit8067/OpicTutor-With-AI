"""
블라인드 교차 평가: 생성에 쓰지 않은 모델(JUDGE_MODEL)이 등급을 모르는 상태로 각 답변을 채점한다.
- 입력: build/answers.jsonl 의 clean 답변 (등급 라벨은 프롬프트에서 제거, 순서 섞음)
- 판정: |예측 - 의도| <= 1 이면 pass, 정확히 같으면 exact
- 출력: build/cross_validation.jsonl + 콘솔 요약(혼동 행렬), fail 목록은 수정·재생성 대상

AI-assisted: Claude(Anthropic)의 도움으로 작성.
사용법: python scripts/cross_validate.py [--only Q013,Q014]
"""
import argparse
import json
import random
import re
from collections import Counter
from pathlib import Path

from llm import judge

ROOT = Path(__file__).resolve().parent.parent
LEVELS = ["NL", "NM", "NH", "IL", "IM1", "IM2", "IM3", "IH", "AL"]
RANK = {lv: i for i, lv in enumerate(LEVELS)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    args = ap.parse_args()
    only = set(filter(None, args.only.split(",")))

    rubrics = "\n\n".join(json.loads(l)["text"] for l in open(ROOT / "build/rubrics.jsonl", encoding="utf-8"))
    docs = [json.loads(l) for l in open(ROOT / "build/answers.jsonl", encoding="utf-8")]
    docs = [d for d in docs if d["text_style"] == "clean" and (not only or d["question_id"] in only)]
    random.Random(0).shuffle(docs)

    system = ("You are a certified OPIc rater. Rate ONE spoken answer (transcript) using the rubric. "
              "Consider task completion, text type, tense control, connectors, fluency and comprehensibility. "
              'Reply ONLY JSON: {"level": "<NL|NM|NH|IL|IM1|IM2|IM3|IH|AL>", "reason": "<한국어 한 문장>"}\n\n'
              f"# Rubric\n{rubrics}")
    results, conf = [], Counter()
    with open(ROOT / "build/cross_validation.jsonl", "w", encoding="utf-8") as f:
        for d in docs:
            raw = judge(system, f"Question: {d['question']}\nAnswer: {d['answer_text']}", max_tokens=300)
            m = re.search(r"\{.*\}", raw, re.S)
            pred = json.loads(m.group(0)) if m else {"level": "?", "reason": raw}
            gap = abs(RANK.get(pred["level"], 99) - RANK[d["level"]])
            r = {"id": d["id"], "intended": d["level"], "predicted": pred["level"], "gap": gap,
                 "verdict": "exact" if gap == 0 else "pass" if gap == 1 else "fail", "judge_reason": pred.get("reason")}
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            results.append(r)
            conf[(d["level"], pred["level"])] += 1
            print(r["verdict"], r["id"], "→", r["predicted"])

    n = len(results)
    ex = sum(r["verdict"] == "exact" for r in results)
    ok = sum(r["verdict"] != "fail" for r in results)
    print(f"\nexact {ex}/{n} ({ex/n:.0%}), within±1 {ok}/{n} ({ok/n:.0%})")
    print("\n의도\\예측 " + " ".join(f"{p:>4}" for p in LEVELS))
    for t in LEVELS:
        print(f"{t:9} " + " ".join(f"{conf[(t, p)]:4}" for p in LEVELS))
    print("\nfail:", [r["id"] for r in results if r["verdict"] == "fail"])


if __name__ == "__main__":
    main()
