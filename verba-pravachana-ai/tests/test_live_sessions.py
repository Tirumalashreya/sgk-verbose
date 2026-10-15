"""Continue-a-recording and merge-recordings: one pravachanam, one set of notes."""
import asyncio

import pytest

import api


@pytest.fixture
def store(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(api, "sessions_store", [])
    monkeypatch.setattr(api, "_live_by_id", {})
    monkeypatch.setattr(api, "_live_recording_session", None)
    monkeypatch.setattr(api, "_broadcast", lambda message: None)
    monkeypatch.setattr(api, "_forget_memory", lambda sources: None)
    # The text steps just echo the transcript as notes
    monkeypatch.setattr(api, "_run_text_steps",
                        lambda transcript, i, source: {"notes": transcript, "segments": [], "shlokas": []})
    return api


def _earlier(id_, transcript, created, pieces=1):
    return {"id": id_, "type": "chunk_complete", "title": f"Live Recording {id_}", "created_at": created,
            "transcript": transcript, "raw_transcript": transcript, "notes": transcript,
            "pieces_recorded": pieces, "live": True}


def test_continue_appends_to_the_same_notes(store):
    store.sessions_store.append(_earlier("a1", "first part", "2026-10-15T09:46:00", pieces=2))
    res = asyncio.run(store.start_live(store.StartLiveRequest(continue_id="a1")))
    assert res["continued"] == "a1"
    session = store._live_recording_session
    session["pieces"].append({"transcript": "second part", "notes": "second part"})
    # what run_live_piece does after a piece is transcribed
    done = [p for p in [session["prefix"]] + session["pieces"] if p]
    session["transcript"] = "\n".join(p["transcript"] for p in done)
    store._finalize_live_session(session)
    assert len(store.sessions_store) == 1
    final = store.sessions_store[0]
    assert final["id"] == "a1" and final["created_at"] == "2026-10-15T09:46:00"
    assert final["transcript"] == "first part\nsecond part"
    assert final["pieces_recorded"] == 3


def test_continue_reopens_a_recording_still_in_memory(store):
    asyncio.run(store.start_live())
    first = store._live_recording_session
    asyncio.run(store.stop_session())
    res = asyncio.run(store.start_live(store.StartLiveRequest(continue_id=first["id"])))
    assert res["continued"] == first["id"]
    assert store._live_recording_session is first and first["stopped"] is False


def test_unknown_continue_id_starts_new_notes(store):
    res = asyncio.run(store.start_live(store.StartLiveRequest(continue_id="nope")))
    assert "continued" not in res and store._live_recording_session["id"] != "nope"


def test_merge_joins_in_recorded_order_and_keeps_the_first(store):
    store.sessions_store.extend([
        _earlier("c3", "third", "2026-10-15T09:51:00", pieces=2),
        _earlier("a1", "first", "2026-10-15T09:46:00"),
        {"id": "other", "title": "upload", "created_at": "2026-10-14T10:00:00", "transcript": "x"},
        _earlier("b2", "second", "2026-10-15T09:49:00"),
    ])
    store._merge_sessions(sorted((s for s in store.sessions_store if s["id"] in {"a1", "b2", "c3"}),
                                 key=lambda s: s["created_at"]))
    ids = [s["id"] for s in store.sessions_store]
    assert ids == ["a1", "other"]
    merged = store.sessions_store[0]
    assert merged["transcript"] == "first\nsecond\nthird"
    assert merged["title"] == "Live Recording a1" and merged["pieces_recorded"] == 4
