"""PUT /sessions/{id}/notes: a manual edit from the Reading screen's edit
mode — replaces the notes outright (a human override, not re-validated),
and invalidates the cached timestamped version since it no longer matches."""
from fastapi.testclient import TestClient

import api


def _client(monkeypatch, sessions):
    monkeypatch.setattr(api, "sessions_store", list(sessions))
    monkeypatch.setattr(api, "_save_sessions", lambda: None)
    monkeypatch.setattr(api, "_broadcast", lambda message: None)
    return TestClient(api.app)


def test_404_for_an_unknown_session(monkeypatch):
    client = _client(monkeypatch, [])
    res = client.put("/sessions/nope/notes", json={"notes": "x"})
    assert res.status_code == 404


def test_saves_the_edited_text(monkeypatch):
    session = {"id": "s1", "created_by": "dev", "notes": "పాత నోట్స్", "enhanced_notes": "పాత నోట్స్"}
    sessions = [session]
    client = _client(monkeypatch, sessions)
    res = client.put("/sessions/s1/notes", json={"notes": "సరిదిద్దిన నోట్స్"})
    assert res.status_code == 200 and res.json() == {"status": "saved"}
    assert session["notes"] == "సరిదిద్దిన నోట్స్"
    assert session["enhanced_notes"] == "సరిదిద్దిన నోట్స్"
    assert session["edited"] is True


def test_clears_the_cached_timestamped_version(monkeypatch):
    session = {"id": "s1", "created_by": "dev", "notes": "పాత", "notes_timestamped": "[00:00] పాత"}
    client = _client(monkeypatch, [session])
    client.put("/sessions/s1/notes", json={"notes": "కొత్త"})
    assert "notes_timestamped" not in session
