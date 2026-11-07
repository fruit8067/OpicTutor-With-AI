# AI-assisted: 이 코드는 Claude(Anthropic)의 도움으로 작성되었습니다.
# 후속 수정: 경로·반입 검증은 OpenAI Codex의 도움으로 작성되었습니다.
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
import re
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
    return vid if isinstance(vid, str) and re.fullmatch(r"[0-9a-f]{10}", vid) else None


def asset_rel_path(voice_id: str, kind: str, ref_id: str, text_sha1: str | None = None) -> str:
    """TTS_DIR 기준 상대 경로(DB tts_assets.file_path에 저장하는 값)."""
    if text_sha1 is not None:
        if not re.fullmatch(r"[0-9a-f]{40}", text_sha1): raise ValueError("text_sha1 형식 오류")
        return f"{voice_id}/{kind}/{ref_id}/{text_sha1}.mp3"
    return f"{voice_id}/{kind}/{ref_id}.mp3"


def tts_url(file_path: str) -> str:
    return "/media/tts/" + str(file_path).replace("\\", "/").lstrip("/")


def split_item_id(item_id: str) -> tuple[str, str]:
    """'question/Q001' → ('question', 'Q001')."""
    kind, sep, ref = str(item_id).partition("/")
    if not sep or kind not in KINDS or not re.fullmatch(r"[A-Za-z0-9_-]+", ref):
        raise ValueError(f"잘못된 item id: {item_id!r}")
    return kind, ref


def load_manifest(voice_id: str) -> dict | None:
    p = tts_dir() / voice_id / "manifest.json"
    try:
        manifest = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict) or not isinstance(manifest.get("items"), list): return None
        if manifest.get("settings_version") != voice_id: return None
        return manifest
    except (OSError, ValueError):
        return None


def manifest_index(manifest: dict | None) -> dict[str, dict]:
    if not isinstance(manifest, dict) or not isinstance(manifest.get("items"), list): return {}
    result = {}
    for item in manifest["items"]:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str): return {}
        if item["id"] in result: return {}
        try: split_item_id(item["id"])
        except ValueError: return {}
        result[item["id"]] = item
    return result


def manifest_asset_path(voice_id: str, kind: str, ref_id: str, item: dict) -> Path | None:
    """v8 로컬 file_path와 v7 평면 경로를 함께 읽는다."""
    try:
        legacy = asset_rel_path(voice_id, kind, ref_id)
        expected = asset_rel_path(voice_id, kind, ref_id, item["text_sha1"])
        relative = item.get("file_path", legacy)
        if relative not in (legacy, expected): return None
        path = (tts_dir() / relative).resolve()
        if not path.is_relative_to(tts_dir().resolve()): return None
        return path
    except (KeyError, TypeError, ValueError): return None


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
        path = manifest_asset_path(vid, kind, ref, it)
        if path is not None and path.is_file() and path.stat().st_size > 0:
            present[item_id] = it.get("text_sha1")
    missing = [q["id"] for q in pilot if present.get(f"question/{q['id']}") != text_hash(q.get("question", ""))]
    missing += [f"host/{k}" for k, t in HOST_LINES.items() if present.get(f"host/{k}") != text_hash(t)]
    return {"voice_id": vid, "assets": len(present), "missing_pilot": missing}
