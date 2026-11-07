# AI-assisted: 이 코드는 Claude(Anthropic)의 도움으로 작성되었습니다.
# 후속 수정: 경로·반입 검증은 OpenAI Codex의 도움으로 작성되었습니다.
# OWNER: tts-host (contracts.yaml ownership)
"""tts_prepare 작업 핸들러 — 세션의 8문항 + 진행자 대사 4개 음성이 정확히 준비됐는지 검사·연결한다.

- attempt: job payload의 prepare_attempt(없으면 sessions.prepare_attempt). 세션이 preparing이 아니거나 attempt가 다르면 종료(늦은 작업 무시).
- 활성 voice 없음 → fail_prepare([NO_ACTIVE_VOICE])
- 항목별: find_tts_asset(kind, ref_id, text_hash(text), voice_id)
    없음 → 활성 manifest에 같은 id가 다른 해시로 있으면 TTS_HASH_MISMATCH, 아니면 TTS_ASSET_MISSING
    등록됐지만 status≠available 이거나 파일이 디스크에 없음 → TTS_FILE_MISSING
- 오류가 하나라도 있으면 fail_prepare(전체 목록), 없으면 complete_prepare(링크 전부). 자동 재생성·대체 문항 없음.
- 파일 I/O만 하므로 Permanent 대상 없음(예외는 워커가 Retryable로 처리).
"""
from __future__ import annotations

import logging

from .assets import active_voice_id, load_manifest, manifest_index, text_hash, tts_dir
from .host_lines import HOST_LINES

log = logging.getLogger(__name__)


def _cancelled(job: dict) -> bool:
    c = job.get("_cancel")
    return c is not None and c.is_set()


def _check(db, idx: dict, voice_id: str, kind: str, ref_id: str, text: str) -> tuple[object | None, str | None]:
    h = text_hash(text)
    asset = db.find_tts_asset(kind=kind, ref_id=ref_id, text_hash=h, voice_id=voice_id)
    if asset is None:
        other = idx.get(f"{kind}/{ref_id}")
        if other is not None and other.get("text_sha1") != h:
            return None, "TTS_HASH_MISMATCH"
        return None, "TTS_ASSET_MISSING"
    base = tts_dir().resolve()
    stored = str(asset.get("file_path", ""))
    from pathlib import PureWindowsPath
    path = (base / stored).resolve()
    if (asset.get("status") != "available" or PureWindowsPath(stored).drive or
            PureWindowsPath(stored).root or not path.is_relative_to(base) or not path.is_file() or path.stat().st_size == 0):
        return None, "TTS_FILE_MISSING"
    return asset["id"], None


def handle(job: dict) -> None:
    from app import db
    session_id = job["target_id"]
    s = db.get_session(session_id)
    if s is None:
        log.info("tts_prepare job=%s: 세션 없음", job.get("id"))
        return
    attempt = (job.get("payload") or {}).get("prepare_attempt") or s.get("prepare_attempt")
    if s.get("status") != "preparing" or int(attempt) != int(s.get("prepare_attempt") or 0):
        log.info("tts_prepare job=%s: 상태 %s / attempt %s≠%s — 건너뜀", job.get("id"), s.get("status"),
                 attempt, s.get("prepare_attempt"))
        return
    attempt = int(attempt)
    voice_id = active_voice_id()
    if voice_id is None:
        if not _cancelled(job):
            db.fail_prepare(session_id, attempt, [{"order_no": None, "host_key": None, "ref_id": "active_voice",
                                                   "error_code": "NO_ACTIVE_VOICE"}])
        return
    idx = manifest_index(load_manifest(voice_id))
    errors, q_links, h_links = [], {}, {}
    for q in db.list_session_questions(session_id):
        aid, err = _check(db, idx, voice_id, "question", q["question_id"], q["question_text"])
        if err:
            errors.append({"order_no": q["order_no"], "host_key": None, "ref_id": q["question_id"], "error_code": err})
        else:
            q_links[q["order_no"]] = aid
    for key, text in HOST_LINES.items():
        aid, err = _check(db, idx, voice_id, "host", key, text)
        if err:
            errors.append({"order_no": None, "host_key": key, "ref_id": key, "error_code": err})
        else:
            h_links[key] = aid
    if _cancelled(job):
        log.warning("tts_prepare job=%s: 잠금 상실 — 저장하지 않음", job.get("id"))
        return
    if errors:
        db.fail_prepare(session_id, attempt, errors)
        log.info("tts_prepare job=%s: prepare_failed (%d건)", job.get("id"), len(errors))
    else:
        db.complete_prepare(session_id, attempt, q_links, h_links)
        log.info("tts_prepare job=%s: ready", job.get("id"))
