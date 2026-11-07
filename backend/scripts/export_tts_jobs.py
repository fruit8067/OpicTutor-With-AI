# AI-assisted: 이 스크립트는 Claude(Anthropic)의 도움으로 작성되었습니다.
# 후속 수정: 버전별 로컬 경로 호환은 OpenAI Codex의 도움으로 작성되었습니다.
# OWNER: tts-host (contracts.yaml ownership)
"""Colab(OmniVoice)에 보낼 TTS 작업 목록 만들기 → backend/static/tts/jobs.jsonl

한 줄: {"id": "question/Q001", "kind": "question", "ref_id": "Q001", "text": "...", "text_sha1": "<sha1(strip utf-8)>"}
- 기본: questions.jsonl의 pilot 전부(Q000 포함) + HOST_LINES 4개
- --stale: 활성 voice의 manifest와 text_sha1을 비교해 바뀌었거나 없는 항목만 (파일이 디스크에 없는 항목 포함)
- --e2e: integrator 자동 완주용 "가짜 수험생 음성"(실제 사람 목소리 아님). default 시나리오 슬롯 순서대로
         IM2·IL 등급 clean 답변 8개씩(kind e2e_answer, ref_id "{level}_{order:02d}"). 1번 자기소개는 대조 세트가 없어
         등급별 고정 합성 문장을 쓴다. 진행자와 다른 목소리로 만들어야 한다(노트북 11번 셀).
사용법 (backend/에서): python -m scripts.export_tts_jobs [--stale] [--e2e] [--out PATH]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.config import settings
from app.tts.assets import active_voice_id, manifest_asset_path, load_manifest, manifest_index, pilot_questions, text_hash, tts_dir
from app.tts.host_lines import HOST_LINES

E2E_LEVELS = ("IM2", "IL")
E2E_SELF_INTRO = {
    "IL": "Hi, my name is Minji. I am a university student in Busan. I live with my parents. I like music.",
    "IM2": "Hi, my name is Minji. I'm a third-year computer science student in Busan. I live with my family near "
           "campus, so I usually walk to school. In my free time I listen to music because it helps me relax.",
}


def job(kind: str, ref_id: str, text: str, **extra) -> dict:
    text = text.strip()
    return {"id": f"{kind}/{ref_id}", "kind": kind, "ref_id": ref_id, "text": text, "text_sha1": text_hash(text), **extra}


def base_jobs() -> list[dict]:
    rows = [job("question", q["id"], q["question"]) for q in sorted(pilot_questions(), key=lambda q: q["id"])]
    rows += [job("host", k, t) for k, t in HOST_LINES.items()]
    return rows


def e2e_jobs(build_dir: Path) -> list[dict]:
    sc = json.loads((build_dir / "scenarios.json").read_text(encoding="utf-8"))
    default = next(s for s in sc["scenarios"] if s["scenario_id"] == "default")
    answers: dict[tuple[str, str], str] = {}
    for line in (build_dir / "answers.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            a = json.loads(line)
            if a.get("text_style") == "clean":
                answers[(a["question_id"], a["level"])] = a["answer_text"]
    out = []
    for level in E2E_LEVELS:
        for slot in sorted(default["slots"], key=lambda s: s["order_no"]):
            n = slot["order_no"]
            if slot["question_types"] == ["self_intro"]:
                out.append(job("e2e_answer", f"{level}_{n:02d}", E2E_SELF_INTRO[level], level=level, order_no=n,
                               question_id=slot["pool"][0]))
                continue
            qid = next((q for q in slot["pool"] if (q, level) in answers), None)
            if qid is None:
                raise SystemExit(f"e2e: {n}번 슬롯에 {level} clean 답변이 있는 문항이 없음")
            out.append(job("e2e_answer", f"{level}_{n:02d}", answers[(qid, level)], level=level, order_no=n,
                           question_id=qid))
    return out


def stale_only(rows: list[dict]) -> list[dict]:
    vid = active_voice_id()
    if vid is None:
        return rows
    idx = manifest_index(load_manifest(vid))
    keep = []
    for r in rows:
        it = idx.get(r["id"])
        path = manifest_asset_path(vid, r["kind"], r["ref_id"], it) if it else None
        if it is None or it.get("text_sha1") != r["text_sha1"] or path is None or not path.is_file():
            keep.append(r)
    return keep


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stale", action="store_true", help="활성 음성에 없거나 문장이 바뀐 항목만")
    ap.add_argument("--e2e", action="store_true", help="자동 완주 테스트용 가짜 수험생 답변 음성 추가")
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args(argv)
    rows = base_jobs()
    if a.e2e:
        rows += e2e_jobs(Path(settings.RAG_BUILD_DIR))
    if a.stale:
        rows = stale_only(rows)
    ids = [r["id"] for r in rows]
    if len(ids) != len(set(ids)):
        raise SystemExit("jobs에 중복 id")
    out = a.out or (tts_dir() / "jobs.jsonl")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    by = {}
    for r in rows:
        by[r["kind"]] = by.get(r["kind"], 0) + 1
    print(f"{out}: {len(rows)}개 ({', '.join(f'{k} {v}' for k, v in by.items()) or '없음'}), "
          f"총 {sum(len(r['text']) for r in rows)}자")
    print("Colab의 colab/omnivoice_tts.ipynb 4번 셀에서 이 파일을 업로드하세요." if rows else "생성할 항목이 없습니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
