# AI-assisted: 이 코드는 Claude(Anthropic)의 도움으로 작성되었습니다.
# OWNER: tts-host (contracts.yaml ownership)
"""TTS 자산 공통 함수.

- text_hash: sha1(text.strip().encode('utf-8')).hexdigest()  — DB·jobs.jsonl·manifest 모두 같은 규칙
- cache_key: "{kind}:{ref_id}:{text_hash}:{voice_id}"
- 파일 배치: {TTS_DIR}/{voice_id}/{kind}/{ref_id}.mp3, {TTS_DIR}/{voice_id}/manifest.json, {TTS_DIR}/active_voice.json
- tts_status()는 DB 없이 파일(활성 manifest + questions.jsonl pilot)만으로 계산한다(/health가 DB 장애와 섞이지 않게).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from app.config import settings

from .host_lines import HOST_LINES

KINDS = ("question", "host", "e2e_answer")


def text_hash(text: str) -> str:
    return hashlib.sha1((text or "").strip().encode("utf-8")).hexdigest()


def cache_key(kind: str, ref_id: str, text_sha1: str, voice_id: str) -> str:
    return f"{kind}:{ref_id}:{text_sha1}:{voice_id}"


def tts_dir() -> Path:
    return Path(settings.TTS_DIR)


def active_voice_id() -> str | None:
    p = tts_dir() / "active_voice.json"
    try:
        vid = json.loads(p.read_text(encoding="utf-8")).get("voice_id")
    except (OSError, ValueError, AttributeError):
        return None
    return vid if isinstance(vid, str) and vid.strip() else None


def asset_rel_path(voice_id: str, kind: str, ref_id: str) -> str:
    """TTS_DIR 기준 상대 경로(DB tts_assets.file_path에 저장하는 값)."""
    return f"{voice_id}/{kind}/{ref_id}.mp3"


def tts_url(file_path: str) -> str:
    return "/media/tts/" + str(file_path).replace("\\", "/").lstrip("/")


def split_item_id(item_id: str) -> tuple[str, str]:
    """'question/Q001' → ('question', 'Q001')."""
    kind, sep, ref = str(item_id).partition("/")
    if not sep or kind not in KINDS or not ref or "/" in ref or ref in (".", ".."):
        raise ValueError(f"잘못된 item id: {item_id!r}")
    return kind, ref


def load_manifest(voice_id: str) -> dict | None:
    p = tts_dir() / voice_id / "manifest.json"
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def manifest_index(manifest: dict | None) -> dict[str, dict]:
    return {it["id"]: it for it in (manifest or {}).get("items", []) if isinstance(it, dict) and "id" in it}


def pilot_questions() -> list[dict]:
    p = Path(settings.RAG_BUILD_DIR) / "questions.jsonl"
    try:
        rows = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    except (OSError, ValueError):
        return []
    return [r for r in rows if r.get("status") == "pilot"]


def tts_status() -> dict:
    """{voice_id, assets, missing_pilot}. missing_pilot = 활성 음성에 (같은 문장 해시로) 없는 pilot 문항 id + 진행자 대사 키."""
    vid = active_voice_id()
    pilot = pilot_questions()
    if vid is None:
        return {"voice_id": None, "assets": 0,
                "missing_pilot": [q["id"] for q in pilot] + [f"host/{k}" for k in HOST_LINES]}
    idx = manifest_index(load_manifest(vid))
    present = {}
    for item_id, it in idx.items():
        try:
            kind, ref = split_item_id(item_id)
        except ValueError:
            continue
        if (tts_dir() / asset_rel_path(vid, kind, ref)).is_file():
            present[item_id] = it.get("text_sha1")
    missing = [q["id"] for q in pilot if present.get(f"question/{q['id']}") != text_hash(q.get("question", ""))]
    missing += [f"host/{k}" for k, t in HOST_LINES.items() if present.get(f"host/{k}") != text_hash(t)]
    return {"voice_id": vid, "assets": len(present), "missing_pilot": missing}
