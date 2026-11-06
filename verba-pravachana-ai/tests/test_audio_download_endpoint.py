"""
Tests for GET /sessions/{session_id}/audio
Ensures user isolation, file delivery, and 404 handling.
"""
import os
import tempfile
from fastapi.testclient import TestClient

import api
from agents import notes_timestamp as nt


def _client(monkeypatch, sessions):
    monkeypatch.setattr(api, "sessions_store", list(sessions))
    monkeypatch.setattr(api, "_save_sessions", lambda: None)
    return TestClient(api.app)


def test_404_for_unknown_session(monkeypatch):
    client = _client(monkeypatch, [])
    res = client.get("/sessions/nonexistent/audio")
    assert res.status_code == 404


def test_404_for_different_user_session(monkeypatch):
    # Session belongs to 'other_user', while default test client authenticates as 'dev'
    session = {"id": "s1", "created_by": "other_user", "title": "Secret", "source_audio_path": "/tmp/dummy.webm"}
    client = _client(monkeypatch, [session])
    res = client.get("/sessions/s1/audio")
    assert res.status_code == 404


def test_returns_audio_file_for_owner(monkeypatch):
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f:
        f.write(b"RIFFdummy_audio_bytes")
        tmp_path = f.name

    try:
        session = {"id": "s1", "created_by": "dev", "title": "Pravachanam 1", "source_audio_path": tmp_path}
        client = _client(monkeypatch, [session])
        monkeypatch.setattr(nt, "_find_audio", lambda s: tmp_path)
        
        res = client.get("/sessions/s1/audio")
        assert res.status_code == 200
        assert res.headers["content-type"].startswith("audio/")
        assert res.content == b"RIFFdummy_audio_bytes"
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
