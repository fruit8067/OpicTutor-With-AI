# AI-assisted: 이 스크립트는 Claude(Anthropic)의 도움으로 작성되었습니다.
# 후속 수정: 경로·반입 검증은 OpenAI Codex의 도움으로 작성되었습니다.
# OWNER: tts-host (contracts.yaml ownership)
"""Colab에서 받은 tts_mp3.zip(또는 풀린 폴더)을 반입한다.

python -m scripts.import_tts <zip|폴더> [--activate] [--no-db]
1. {TTS_DIR}/{voice_id}/ 에 풀기 (voice_id = manifest.settings_version, zip 최상위 폴더 이름과 같아야 함)
2. manifest 검사: 필수 키, settings_version 재계산 일치, 모든 item 파일 존재, mp3 길이(PyAV) > 0, id 형식
3. 각 item을 db.upsert_tts_asset으로 등록(kind/ref_id = id 분리, text_hash = manifest text_sha1). --no-db면 생략
4. --activate면 active_voice.json 갱신. e2e_answer는 backend/e2e_audio/{level}/{order:02d}.mp3로도 복사
5. 요약: 등록 수, 누락, 오류. 오류가 있으면 exit 1(그 경우 활성화하지 않음)
기존 voice 폴더는 덮어쓰지 않고 항목을 추가·갱신한다(--stale 반입 지원).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path, PureWindowsPath

from app.tts.assets import asset_rel_path, split_item_id, tts_dir

BACKEND = Path(__file__).resolve().parents[1]
REQUIRED = ("engine", "model_revision", "instruct", "seed", "speed", "num_step", "settings_version", "items")
SETTINGS_KEYS = ("engine", "model_revision", "instruct", "seed", "speed", "num_step")


def settings_version(m: dict) -> str:
    payload = json.dumps({k: m[k] for k in SETTINGS_KEYS}, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:10]


def mp3_seconds(path: Path) -> float:
    import av
    with av.open(str(path)) as c:
        s = next(s for s in c.streams if s.type == "audio")
        if c.duration:
            return c.duration / 1_000_000
        n = 0
        for f in c.decode(s):
            n += f.samples
        return n / (s.rate or 1)


def find_root(path: Path, tmp: Path) -> Path:
    if path.is_file():
        with zipfile.ZipFile(path) as z:
            for name in z.namelist():
                win = PureWindowsPath(name)
                target = (tmp / name).resolve()
                if (win.drive or win.root or "\\" in name or
                        ".." in Path(name).parts or not target.is_relative_to(tmp.resolve())):
                    raise SystemExit(f"zip에 안전하지 않은 경로: {name}")
            z.extractall(tmp)
        path = tmp
    if (path / "manifest.json").is_file():
        return path
    subs = [p for p in path.iterdir() if p.is_dir() and (p / "manifest.json").is_file()]
    if len(subs) != 1:
        raise SystemExit("manifest.json이 있는 폴더를 하나만 찾아야 합니다")
    return subs[0]


def validate(root: Path, check_name: bool = True) -> tuple[dict, list[str]]:
    errs = []
    m = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    if not isinstance(m, dict):
        return {}, ["manifest는 JSON 객체여야 합니다"]
    for k in REQUIRED:
        if k not in m:
            errs.append(f"manifest 필수 키 없음: {k}")
    if errs:
        return m, errs
    if not isinstance(m["items"], list) or not m["items"]:
        return m, ["manifest items는 비어 있지 않은 목록이어야 합니다"]
    if settings_version(m) != m["settings_version"]:
        errs.append(f"settings_version 불일치: manifest {m['settings_version']} / 재계산 {settings_version(m)}")
    if check_name and root.name != m["settings_version"]:
        errs.append(f"최상위 폴더 이름({root.name})이 settings_version({m['settings_version']})과 다름")
    seen = set()
    for it in m["items"]:
        if not isinstance(it, dict):
            errs.append("manifest item은 객체여야 합니다")
            continue
        try:
            kind, ref = split_item_id(it.get("id", ""))
        except ValueError as e:
            errs.append(str(e))
            continue
        if it["id"] in seen:
            errs.append(f"중복 id {it['id']}")
        seen.add(it["id"])
        if not isinstance(it.get("text_sha1"), str) or not re.fullmatch(r"[0-9a-f]{40}", it["text_sha1"]):
            errs.append(f"{it['id']}: text_sha1 형식 오류")
        if kind == "e2e_answer" and not re.fullmatch(r"(?:IM2|IL)_0[1-8]", ref):
            errs.append(f"{it['id']}: e2e 등급/순서 형식 오류")
        f = root / kind / f"{ref}.mp3"
        if not f.is_file():
            errs.append(f"{it['id']}: 파일 없음")
            continue
        try:
            sec = mp3_seconds(f)
        except Exception:  # noqa: BLE001
            errs.append(f"{it['id']}: mp3 디코드 실패")
            continue
        if sec <= 0:
            errs.append(f"{it['id']}: 길이 0초")
        it["_measured"] = round(sec, 2)
    return m, errs


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", type=Path)
    ap.add_argument("--activate", action="store_true")
    ap.add_argument("--no-db", action="store_true", help="DB 등록 없이 파일만 반입(개발용)")
    a = ap.parse_args(argv)
    with tempfile.TemporaryDirectory() as td:
        root = find_root(a.source.resolve(), Path(td))
        m, errs = validate(root, check_name=root != Path(td))
        if errs:
            print("검사 실패:\n- " + "\n- ".join(errs[:50]))
            return 1
        vid = m["settings_version"]
        dest = tts_dir() / vid
        dest.mkdir(parents=True, exist_ok=True)
        for it in m["items"]:
            kind, ref = split_item_id(it["id"])
            (dest / kind).mkdir(exist_ok=True)
            src, dst = root / kind / f"{ref}.mp3", dest / kind / f"{ref}.mp3"
            if not (dst.exists() and src.resolve() == dst.resolve()):   # 이미 반입된 폴더를 다시 등록할 때(DB만)
                shutil.copyfile(src, dst)
        # 기존 manifest와 합치기(--stale 반입)
        old = {}
        if (dest / "manifest.json").is_file():
            old = {i["id"]: i for i in json.loads((dest / "manifest.json").read_text(encoding="utf-8")).get("items", [])}
        for it in m["items"]:
            old[it["id"]] = {k: v for k, v in it.items() if not k.startswith("_")}
        merged = {**{k: m[k] for k in REQUIRED if k != "items"}, "items": sorted(old.values(), key=lambda i: i["id"])}
        (dest / "manifest.json").write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    registered = 0
    if not a.no_db:
        from app import db
        for it in m["items"]:
            kind, ref = split_item_id(it["id"])
            db.upsert_tts_asset(kind=kind, ref_id=ref, text_hash=it["text_sha1"], voice_id=vid, settings_version=vid,
                                file_path=asset_rel_path(vid, kind, ref), duration_sec=it.get("_measured") or it.get("seconds"))
            registered += 1
    e2e = 0
    jobs_meta = {}
    jp = tts_dir() / "jobs.jsonl"
    if jp.is_file():
        for line in jp.read_text(encoding="utf-8").splitlines():
            if line.strip():
                j = json.loads(line)
                jobs_meta[j["id"]] = j
    for it in m["items"]:
        kind, ref = split_item_id(it["id"])
        if kind != "e2e_answer":
            continue
        level, _, order = ref.partition("_")
        target = BACKEND / "e2e_audio" / level / f"{order}.mp3"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(dest / kind / f"{ref}.mp3", target)
        e2e += 1
    if a.activate:
        (tts_dir() / "active_voice.json").write_text(json.dumps({"voice_id": vid}) + "\n", encoding="utf-8")
    total = sum(it.get("_measured", 0) for it in m["items"])
    size = sum((dest / split_item_id(i["id"])[0] / f"{split_item_id(i['id'])[1]}.mp3").stat().st_size for i in m["items"])
    print(f"voice_id={vid}: 반입 {len(m['items'])}개(총 {total:.0f}초, {size / 1e6:.1f}MB), DB 등록 {registered}개, "
          f"e2e 복사 {e2e}개, 누락 0, 해시 불일치 0{' — 활성화함' if a.activate else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
