"""sessions.json was a single flat file, rewritten whole on every save — no
partial-write safety, and nothing stopped two saves at once from
interleaving. SQLite replaces the storage, but sessions_store itself stays a
plain in-memory list, exactly as every endpoint already expects — only
_load_sessions/_save_sessions changed underneath it."""
import json


def test_existing_sessions_json_is_migrated_into_the_database(monkeypatch, tmp_path):
    import api
    monkeypatch.chdir(tmp_path)
    (tmp_path / "sessions.json").write_text(json.dumps([
        {"id": "a1", "title": "First", "created_at": "2026-01-01", "transcript": "t1", "notes": "n1"},
        {"id": "a2", "title": "Second", "created_at": "2026-01-02", "transcript": "t2", "notes": "n2"},
    ]), encoding="utf-8")
    loaded = api._load_sessions()
    assert {s["id"] for s in loaded} == {"a1", "a2"}
    assert (tmp_path / "sessions.db").exists()


def test_migration_only_happens_once_a_later_json_edit_is_ignored(monkeypatch, tmp_path):
    import api
    monkeypatch.chdir(tmp_path)
    (tmp_path / "sessions.json").write_text(json.dumps([
        {"id": "b1", "title": "Original", "transcript": "t", "notes": "n"},
    ]), encoding="utf-8")
    api._load_sessions()   # first load migrates b1 into the (now-created) database

    # Someone (or a stray process) rewrites the old json file afterwards —
    # the database must not be clobbered by it on the next load.
    (tmp_path / "sessions.json").write_text(json.dumps([
        {"id": "c1", "title": "Should be ignored", "transcript": "t", "notes": "n"},
    ]), encoding="utf-8")
    loaded = api._load_sessions()
    assert [s["id"] for s in loaded] == ["b1"]


def test_save_sessions_persists_an_append(monkeypatch, tmp_path):
    import api
    monkeypatch.chdir(tmp_path)
    api.sessions_store = [{"id": "x1", "title": "X", "created_at": "2026-01-01",
                           "transcript": "t", "notes": "n"}]
    api._save_sessions()
    reloaded = api._load_sessions()
    assert [s["id"] for s in reloaded] == ["x1"]


def test_save_sessions_removes_a_deleted_session(monkeypatch, tmp_path):
    import api
    monkeypatch.chdir(tmp_path)
    api.sessions_store = [
        {"id": "y1", "title": "Keep", "created_at": "2026-01-01", "transcript": "t", "notes": "n"},
        {"id": "y2", "title": "Delete me", "created_at": "2026-01-02", "transcript": "t", "notes": "n"},
    ]
    api._save_sessions()
    api.sessions_store = [s for s in api.sessions_store if s["id"] != "y2"]
    api._save_sessions()
    reloaded = api._load_sessions()
    assert [s["id"] for s in reloaded] == ["y1"]


def test_save_sessions_persists_an_edit_to_an_existing_session(monkeypatch, tmp_path):
    import api
    monkeypatch.chdir(tmp_path)
    api.sessions_store = [{"id": "z1", "title": "Before", "created_at": "2026-01-01",
                           "transcript": "t", "notes": "n"}]
    api._save_sessions()
    api.sessions_store[0]["notes"] = "edited notes"
    api._save_sessions()
    reloaded = api._load_sessions()
    assert reloaded[0]["notes"] == "edited notes"


def test_sessions_with_no_transcript_or_notes_are_still_dropped_on_load(monkeypatch, tmp_path):
    import api
    monkeypatch.chdir(tmp_path)
    api.sessions_store = [
        {"id": "empty", "title": "Nothing captured", "transcript": "", "notes": ""},
        {"id": "real", "title": "Real", "transcript": "ప్రవచనం", "notes": "ప్రవచనం"},
    ]
    api._save_sessions()
    reloaded = api._load_sessions()
    assert [s["id"] for s in reloaded] == ["real"]
