# AI-assisted: 이 테스트는 Claude(Anthropic)의 도움으로 작성되었습니다.
# OWNER: tts-host (contracts.yaml ownership)
"""TTS 파이프라인: 해시·URL·상태, export(--stale/--e2e), import 검사, tts_prepare 핸들러(가짜 db)."""
import json
import threading
import zipfile
from pathlib import Path

import numpy as np
import pytest

from app import db as real_db
from app.config import settings
from app.tts import assets as A
from app.tts import prepare as P
from app.tts.host_lines import HOST_LINES

QUESTIONS = [{"id": "Q000", "status": "pilot", "question": "Tell me about yourself."},
             {"id": "Q001", "status": "pilot", "question": "Describe your home."},
             {"id": "Q013", "status": "todo", "question": "Not yet."}]


@pytest.fixture
def env(tmp_path, monkeypatch):
    tts = tmp_path / "tts"
    build = tmp_path / "build"
    tts.mkdir(); build.mkdir()
    (build / "questions.jsonl").write_text("".join(json.dumps(q) + "\n" for q in QUESTIONS), encoding="utf-8")
    monkeypatch.setattr(settings, "TTS_DIR", tts)
    monkeypatch.setattr(settings, "RAG_BUILD_DIR", build)
    return tts, build


def write_mp3(path: Path, seconds=0.5):
    import av
    path.parent.mkdir(parents=True, exist_ok=True)
    with av.open(str(path), "w", format="mp3") as c:
        s = c.add_stream("mp3", rate=24000)
        s.layout = "mono"
        samples = (0.1 * np.sin(np.arange(int(24000 * seconds)) / 5)).astype(np.float32).reshape(1, -1)
        frame = av.AudioFrame.from_ndarray(samples, format="flt", layout="mono")
        frame.rate = 24000
        for p in s.encode(frame):
            c.mux(p)
        for p in s.encode(None):
            c.mux(p)


def make_voice(root: Path, items: dict[str, str], *, bad_version=False):
    """items: {"question/Q000": text}. root 아래 {settings_version}/... 생성 후 (voice_id, 폴더) 반환."""
    from scripts.import_tts import settings_version
    m = {"engine": "k2-fsa/OmniVoice", "model_revision": "abc", "instruct": "female", "seed": 42, "speed": 0.95,
         "num_step": 32}
    m["settings_version"] = "0000000000" if bad_version else settings_version(m)
    folder = root / m["settings_version"]
    m["items"] = []
    for item_id, text in items.items():
        kind, ref = A.split_item_id(item_id)
        write_mp3(folder / kind / f"{ref}.mp3")
        m["items"].append({"id": item_id, "text_sha1": A.text_hash(text), "seconds": 0.5})
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "manifest.json").write_text(json.dumps(m), encoding="utf-8")
    return m["settings_version"], folder


def test_hash_and_url():
    assert A.text_hash("  hello \n") == A.text_hash("hello")
    assert A.tts_url("ab12/question/Q001.mp3") == "/media/tts/ab12/question/Q001.mp3"
    assert A.tts_url("\\ab\\host\\next.mp3") == "/media/tts/ab/host/next.mp3"
    with pytest.raises(ValueError):
        A.split_item_id("question/../x")
    with pytest.raises(ValueError):
        A.split_item_id("video/Q001")


def test_status_without_voice(env):
    st = A.tts_status()
    assert st["voice_id"] is None and "Q001" in st["missing_pilot"] and "Q013" not in st["missing_pilot"]


def all_items():
    d = {f"question/{q['id']}": q["question"] for q in QUESTIONS if q["status"] == "pilot"}
    d.update({f"host/{k}": t for k, t in HOST_LINES.items()})
    return d


def test_import_activate_and_status(env, tmp_path):
    from scripts.import_tts import main as imp
    tts, _ = env
    src = tmp_path / "zip_src"
    vid, folder = make_voice(src, all_items())
    z = tmp_path / "tts_mp3.zip"
    with zipfile.ZipFile(z, "w") as zf:
        for f in folder.rglob("*"):
            zf.write(f, f.relative_to(src))
    assert imp([str(z), "--activate", "--no-db"]) == 0
    assert A.active_voice_id() == vid
    st = A.tts_status()
    assert st["missing_pilot"] == [] and st["assets"] == len(all_items())


def test_reimport_same_folder_registers_only(env, tmp_path):
    from scripts.import_tts import main as imp
    tts, _ = env
    vid, folder = make_voice(tmp_path / "s", all_items())
    assert imp([str(folder), "--activate", "--no-db"]) == 0
    assert imp([str(tts / vid), "--activate", "--no-db"]) == 0   # 같은 폴더 재등록: SameFileError 없음
    assert A.tts_status()["missing_pilot"] == []


def test_import_rejects_bad(env, tmp_path):
    from scripts.import_tts import main as imp
    vid, folder = make_voice(tmp_path / "a", all_items(), bad_version=True)
    assert imp([str(folder), "--no-db"]) == 1           # settings_version 재계산 불일치
    vid, folder = make_voice(tmp_path / "b", all_items())
    (folder / "host" / "next.mp3").unlink()
    assert imp([str(folder), "--no-db"]) == 1           # 파일 누락
    assert A.active_voice_id() is None


def test_export_stale_and_e2e(env, tmp_path):
    from scripts import export_tts_jobs as E
    from scripts.import_tts import main as imp
    tts, build = env
    items = all_items()
    items["question/Q001"] = "OLD sentence"              # 문장 변경 → stale
    vid, folder = make_voice(tmp_path / "v", items)
    assert imp([str(folder), "--activate", "--no-db"]) == 0
    out = tmp_path / "jobs.jsonl"
    E.main(["--stale", "--out", str(out)])
    ids = [json.loads(l)["id"] for l in out.read_text().splitlines()]
    assert ids == ["question/Q001"]


def test_export_e2e_uses_real_corpus(tmp_path, monkeypatch):
    from scripts import export_tts_jobs as E
    real_build = Path(E.__file__).resolve().parents[2] / "rag_docs" / "build"
    rows = E.e2e_jobs(real_build)
    assert len(rows) == 16 and {r["level"] for r in rows} == {"IM2", "IL"}
    assert sorted(r["order_no"] for r in rows if r["level"] == "IL") == list(range(1, 9))
    assert all(r["kind"] == "e2e_answer" and "/" not in r["ref_id"] and len(r["text_sha1"]) == 40 for r in rows)


class FakeDB:
    def __init__(self, assets, status="preparing", attempt=1):
        self.assets, self.s = assets, {"status": status, "prepare_attempt": attempt}
        self.failed, self.completed = None, None

    def get_session(self, sid): return self.s
    def list_session_questions(self, sid):
        return [{"order_no": 1, "question_id": "Q000", "question_text": "Tell me about yourself."},
                {"order_no": 2, "question_id": "Q001", "question_text": "Describe your home."}]
    def find_tts_asset(self, *, kind, ref_id, text_hash, voice_id):
        return self.assets.get((kind, ref_id, text_hash, voice_id))
    def fail_prepare(self, sid, attempt, errors): self.failed = errors; return True
    def complete_prepare(self, sid, attempt, q, h): self.completed = (q, h); return True


def registered(vid, items, status="available"):
    out = {}
    for item_id, text in items.items():
        kind, ref = A.split_item_id(item_id)
        out[(kind, ref, A.text_hash(text), vid)] = {"id": f"id-{item_id}", "status": status,
                                                   "file_path": A.asset_rel_path(vid, kind, ref)}
    return out


@pytest.fixture
def active(env, tmp_path):
    from scripts.import_tts import main as imp
    vid, folder = make_voice(tmp_path / "v", all_items())
    assert imp([str(folder), "--activate", "--no-db"]) == 0
    return vid


def patch_db(monkeypatch, fake):
    for n in ("get_session", "list_session_questions", "find_tts_asset", "fail_prepare", "complete_prepare"):
        monkeypatch.setattr(real_db, n, getattr(fake, n))


JOB = {"id": "j", "target_id": "s", "payload": {"prepare_attempt": 1}}


def test_prepare_ready(active, monkeypatch):
    f = FakeDB(registered(active, all_items()))
    patch_db(monkeypatch, f)
    P.handle(JOB)
    assert f.failed is None and set(f.completed[0]) == {1, 2} and set(f.completed[1]) == set(HOST_LINES)


def test_prepare_missing_mismatch_file(active, monkeypatch, env):
    tts, _ = env
    items = all_items()
    reg = registered(active, items)
    reg.pop(("question", "Q000", A.text_hash(items["question/Q000"]), active))     # 등록 없음 → MISSING
    f = FakeDB(reg)
    patch_db(monkeypatch, f)
    (tts / active / "host" / "next.mp3").unlink()                                   # 파일 없음 → FILE_MISSING
    f.list_session_questions = lambda sid: [
        {"order_no": 1, "question_id": "Q000", "question_text": "Tell me about yourself."},
        {"order_no": 2, "question_id": "Q001", "question_text": "Describe your NEW home."}]  # 문장 바뀜 → MISMATCH
    monkeypatch.setattr(real_db, "list_session_questions", f.list_session_questions)
    P.handle(JOB)
    codes = {(e["ref_id"], e["error_code"]) for e in f.failed}
    assert codes == {("Q000", "TTS_ASSET_MISSING"), ("Q001", "TTS_HASH_MISMATCH"), ("next", "TTS_FILE_MISSING")}
    assert f.completed is None


def test_prepare_no_voice_and_stale_attempt(env, monkeypatch):
    f = FakeDB({})
    patch_db(monkeypatch, f)
    P.handle(JOB)
    assert f.failed[0]["error_code"] == "NO_ACTIVE_VOICE"
    f2 = FakeDB({}, attempt=2)
    patch_db(monkeypatch, f2)
    P.handle(JOB)                                                                   # 늦은 작업(attempt 1) 무시
    assert f2.failed is None and f2.completed is None
    f3 = FakeDB({}, status="cancelled")
    patch_db(monkeypatch, f3)
    P.handle(JOB)
    assert f3.failed is None


def test_prepare_cancel_flag(active, monkeypatch):
    f = FakeDB(registered(active, all_items()))
    patch_db(monkeypatch, f)
    ev = threading.Event(); ev.set()
    P.handle({**JOB, "_cancel": ev})
    assert f.completed is None and f.failed is None


# AI-assisted: 경로 회귀 검증은 OpenAI Codex의 도움으로 작성했습니다.
@pytest.mark.parametrize("name", ["question/..\\escape", "question/C:escape", "host/../next", "e2e_answer/IL_01/escape"])
def test_item_paths_cannot_escape(name):
    with pytest.raises(ValueError):
        A.split_item_id(name)


@pytest.mark.parametrize("name", ["../escape.mp3", "..\\escape.mp3", "C:/escape.mp3", "/escape.mp3"])
def test_zip_paths_cannot_escape(tmp_path, name):
    from scripts.import_tts import find_root
    archive = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr(name, b"invalid")
    unpack = tmp_path / "unpack"
    unpack.mkdir()
    with pytest.raises(SystemExit, match="안전하지 않은"):
        find_root(archive, unpack)
    assert list(unpack.iterdir()) == []


def test_prepare_rejects_external_file(active, monkeypatch, env, tmp_path):
    external = tmp_path / "outside.mp3"
    write_mp3(external)
    reg = registered(active, all_items())
    reg[("question", "Q000", A.text_hash(all_items()["question/Q000"]), active)]["file_path"] = str(external)
    fake = FakeDB(reg)
    patch_db(monkeypatch, fake)
    P.handle(JOB)
    assert fake.completed is None
    assert fake.failed[0]["error_code"] == "TTS_FILE_MISSING"


# AI-assisted (OpenAI Codex). F0/F6: an old session must keep its original audio.
def test_changed_text_keeps_old_asset(env, tmp_path):
    from scripts.import_tts import main as imp
    import hashlib
    vid, first = make_voice(tmp_path / "first", {"question/Q001": "Original question."})
    assert imp([str(first), "--no-db"]) == 0
    tts, _ = env
    old_item = A.manifest_index(A.load_manifest(vid))["question/Q001"]
    old_file = tts / old_item.get("file_path", A.asset_rel_path(vid, "question", "Q001"))
    digest = hashlib.sha256(old_file.read_bytes()).hexdigest()
    _, second = make_voice(tmp_path / "second", {"question/Q001": "Updated question."})
    write_mp3(second / "question/Q001.mp3", seconds=1.5)
    assert imp([str(second), "--no-db"]) == 0
    assert hashlib.sha256(old_file.read_bytes()).hexdigest() == digest
