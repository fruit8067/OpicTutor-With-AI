# AI-assisted: 기존 코퍼스 빌더와 계약 연결은 OpenAI Codex의 도움으로 작성했습니다.
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
    from corpus_v3 import main as build_v3
    return build_v3()


if __name__ == "__main__":
    sys.exit(main())
