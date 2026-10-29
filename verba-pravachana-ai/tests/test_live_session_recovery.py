"""A live recording only lived in server memory — a crash or restart mid-recording
used to split it into two, the same symptom /merge-sessions exists to clean up
after. On startup, a recent in-progress recording is resumed automatically
(reusing the exact "continue" construction the app's own prompt uses); a stale
one is finalized properly instead of left stuck."""
import time
from datetime import datetime, timedelta

import api


def _in_progress(id_, transcript, minutes_ago, pieces_done=2):
    return {"id": id_, "type": "chunk_complete", "title": f"Live Recording {id_}",
            "created_at": (datetime.utcnow() - timedelta(minutes=minutes_ago + 5)).isoformat(),
            "last_piece_at": (datetime.utcnow() - timedelta(minutes=minutes_ago)).isoformat(),
            "transcript": transcript, "raw_transcript": transcript, "notes": transcript,
            "live": True, "live_in_progress": True, "pieces_done": pieces_done}


def _setup(monkeypatch, sessions):
    monkeypatch.setattr(api, "sessions_store", list(sessions))
    monkeypatch.setattr(api, "_live_by_id", {})
    monkeypatch.setattr(api, "_live_recording_session", None)
    monkeypatch.setattr(api, "_broadcast", lambda message: None)
    monkeypatch.setattr(api, "_forget_memory", lambda sources: None)


def test_no_in_progress_session_is_a_no_op(monkeypatch):
    _setup(monkeypatch, [{"id": "x", "live": True}])  # finalized session, no marker
    api._recover_live_sessions()
    assert api._live_recording_session is None
    assert api._live_by_id == {}


def test_recent_in_progress_session_is_resumed(monkeypatch):
    _setup(monkeypatch, [_in_progress("a1", "first part", minutes_ago=3)])
    api._recover_live_sessions()
    assert api._live_recording_session is not None
    assert api._live_recording_session["id"] == "a1"
    assert api._live_recording_session["prefix"]["transcript"] == "first part"
    assert api._live_recording_session["prior_pieces"] == 2
    assert api._live_by_id["a1"] is api._live_recording_session


def test_stale_in_progress_session_is_finalized_instead_of_resumed(monkeypatch):
    _setup(monkeypatch, [_in_progress("old1", "stale content", minutes_ago=60)])
    calls = []
    monkeypatch.setattr(api, "_finalize_live_session", lambda session: calls.append(session["id"]))
    api._recover_live_sessions()
    assert api._live_recording_session is None  # not resumed as the active session
    for _ in range(20):
        if calls:
            break
        time.sleep(0.05)
    assert calls == ["old1"]


def test_only_the_most_recent_in_progress_session_resumes_others_are_closed(monkeypatch):
    _setup(monkeypatch, [_in_progress("older", "a", minutes_ago=10), _in_progress("newer", "b", minutes_ago=1)])
    calls = []
    monkeypatch.setattr(api, "_finalize_live_session", lambda session: calls.append(session["id"]))
    api._recover_live_sessions()
    assert api._live_recording_session["id"] == "newer"
    for _ in range(20):
        if calls:
            break
        time.sleep(0.05)
    assert calls == ["older"]


def test_build_continuation_prefers_pieces_done_over_pieces_recorded():
    earlier = {"id": "z", "transcript": "t", "pieces_done": 3, "pieces_recorded": 99}
    assert api._build_continuation(earlier)["prior_pieces"] == 3


def test_build_continuation_falls_back_to_pieces_recorded_when_never_live():
    earlier = {"id": "z", "pieces_recorded": 4}
    assert api._build_continuation(earlier)["prior_pieces"] == 4
