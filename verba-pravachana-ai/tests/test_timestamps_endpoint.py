"""GET /sessions/{id}/timestamps: cached on the session once built, since
building it re-transcribes the recording's audio; 404 when there's nothing
to anchor against rather than silently returning the plain notes."""
from fastapi.testclient import TestClient

import api
from agents import notes_timestamp as nt


def _client(monkeypatch, sessions):
    monkeypatch.setattr(api, "sessions_store", list(sessions))
    monkeypatch.setattr(api, "_save_sessions", lambda: None)
    return TestClient(api.app)


def test_404_for_an_unknown_session(monkeypatch):
    client = _client(monkeypatch, [])
    res = client.get("/sessions/nope/timestamps")
    assert res.status_code == 404


def test_404_when_no_audio_is_available(monkeypatch):
    session = {"id": "s1", "created_by": "dev", "notes": "ఏదో నోట్స్", "source_audio_path": None}
    client = _client(monkeypatch, [session])
    monkeypatch.setattr(nt, "available", lambda s: False)
    res = client.get("/sessions/s1/timestamps")
    assert res.status_code == 404


def test_returns_cached_notes_timestamped_without_rebuilding(monkeypatch):
    session = {"id": "s1", "created_by": "dev", "notes": "ఏదో", "notes_timestamped": "[00:00] ఏదో", "source_audio_path": None}
    client = _client(monkeypatch, [session])
    called = []
    monkeypatch.setattr(nt, "build", lambda s: called.append(1) or "SHOULD NOT BE USED")
    res = client.get("/sessions/s1/timestamps")
    assert res.status_code == 200
    assert res.json() == {"notes_timestamped": "[00:00] ఏదో"}
    assert not called


def test_builds_and_caches_when_not_already_present(monkeypatch):
    session = {"id": "s1", "created_by": "dev", "notes": "ఏదో నోట్స్", "source_audio_path": None}
    sessions = [session]
    client = _client(monkeypatch, sessions)
    monkeypatch.setattr(nt, "available", lambda s: True)
    monkeypatch.setattr(nt, "build", lambda s: "[00:05] ఏదో నోట్స్")
    res = client.get("/sessions/s1/timestamps")
    assert res.status_code == 200
    assert res.json() == {"notes_timestamped": "[00:05] ఏదో నోట్స్"}
    assert session["notes_timestamped"] == "[00:05] ఏదో నోట్స్"   # cached for next time


def test_force_true_rebuilds_even_when_cached(monkeypatch):
    session = {"id": "s1", "created_by": "dev", "notes": "ఏదో", "notes_timestamped": "[00:00] old", "source_audio_path": None}
    client = _client(monkeypatch, [session])
    monkeypatch.setattr(nt, "available", lambda s: True)
    monkeypatch.setattr(nt, "build", lambda s: "[00:09] new")
    res = client.get("/sessions/s1/timestamps?force=true")
    assert res.json() == {"notes_timestamped": "[00:09] new"}


def test_404_when_build_fails_to_align_anything(monkeypatch):
    session = {"id": "s1", "created_by": "dev", "notes": "ఏదో నోట్స్", "source_audio_path": None}
    client = _client(monkeypatch, [session])
    monkeypatch.setattr(nt, "available", lambda s: True)
    monkeypatch.setattr(nt, "build", lambda s: None)
    res = client.get("/sessions/s1/timestamps")
    assert res.status_code == 404
