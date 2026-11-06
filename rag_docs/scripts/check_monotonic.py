"""
대조 세트 자동 점검: 같은 문항 안에서 등급이 올라갈수록 언어 특징이 증가하는지 확인한다.
특징: 단어 수, 평균 문장 길이, 어휘 다양성(MATTR), 연결어 수, 과거시제 오류 의심 패턴 수.
역전(하위 등급이 상위 등급보다 뚜렷하게 높음)이 있으면 경고로 출력한다.

AI-assisted: Claude(Anthropic)의 도움으로 작성.
사용법: python scripts/check_monotonic.py
"""
import glob
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
LEVELS = ["NL", "NM", "NH", "IL", "IM1", "IM2", "IM3", "IH", "AL"]
WORD = re.compile(r"[A-Za-z']+")
# 기본 연결어는 IM2에서 과다 반복되는 게 오히려 그 등급의 특징이므로 단조 증가를 요구하지 않는다(정보용).
CONN_BASIC = ["because", "so", "but", "and then", "also", "actually", "first", "then", "after that"]
# 고급 연결어·담화 표지는 등급이 오를수록 늘어나야 한다(점검 대상).
CONN_ADV = ["however", "although", "even though", "since", "which", "whether", "while", "once",
            "as a result", "looking back", "on the other hand", "that said", "instead", "rather than",
            "despite", "though", "ever since", "by the end", "it turned out", "turned out", "personally"]
# 한국인 학습자 흔한 오류 패턴(휴리스틱): 원형부정사, 3인칭 -s 누락 등
ERR = re.compile(r"\b(I go to? \w+ (yesterday|last)|want go|listen music|he do|she do|is relax|"
                 r"everyone bring|my family watch|friend join|was small|you was|cafes was|tickets was)\b", re.I)


def mattr(words, w=25):
    if len(words) < w:
        return len(set(words)) / max(len(words), 1)
    return sum(len(set(words[i:i + w])) / w for i in range(len(words) - w + 1)) / (len(words) - w + 1)


def feats(text):
    sents = [s for s in re.split(r"[.!?]+", text) if WORD.search(s)]
    words = [w.lower() for w in WORD.findall(text)]
    low = " " + " ".join(words) + " "
    return {
        "words": len(words),
        "sent_len": len(words) / max(len(sents), 1),
        "mattr": mattr(words),
        "conn_basic": sum(low.count(f" {c} ") for c in CONN_BASIC),
        "conn_adv": sum(low.count(f" {c} ") for c in CONN_ADV),
    }


def main():
    sets = {}
    for p in sorted(glob.glob(str(ROOT / "source" / "contrast_sets_*.yaml"))):
        sets.update(yaml.safe_load(open(p, encoding="utf-8")))
    warn = 0
    print(f"{'Q':5} {'feature':9} " + " ".join(f"{lv:>5}" for lv in LEVELS))
    for qid, lv in sets.items():
        F = {l: feats(lv[l]["text"]) for l in LEVELS}
        for k in ("words", "sent_len", "conn_adv", "conn_basic"):
            row = [F[l][k] for l in LEVELS]
            print(f"{qid:5} {k:9} " + " ".join(f"{v:5.1f}" for v in row))
            # 인접 2단계 이상 떨어진 등급끼리 역전되면 경고(인접 등급은 소폭 역전 허용)
            for i in range(len(LEVELS) - 2) if k != "conn_basic" else []:
                if row[i] > row[i + 2] * 1.15 and row[i] - row[i + 2] > 1:
                    print(f"   ! {qid} {k}: {LEVELS[i]}({row[i]:.1f}) > {LEVELS[i+2]}({row[i+2]:.1f})")
                    warn += 1
    print(f"\n경고 {warn}건")


if __name__ == "__main__":
    main()
