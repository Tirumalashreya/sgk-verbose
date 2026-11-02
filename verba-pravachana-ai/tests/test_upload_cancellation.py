"""A big upload can take minutes — the UI needs a real way to discard it
mid-flight, not just a disabled Cancel button. `agents/cancellation.py` holds
the shared cancelled-digest set; gemini_asr.py's piece loop and
transcription_agent.py's provider loop both check it."""
from agents import cancellation


def test_cancel_marks_and_clear_unmarks():
    cancellation.cancel("abc123")
    assert cancellation.is_cancelled("abc123")
    cancellation.clear("abc123")
    assert not cancellation.is_cancelled("abc123")


def test_is_cancelled_false_for_none_or_unknown_digest():
    assert not cancellation.is_cancelled(None)
    assert not cancellation.is_cancelled("never-seen-this-one")


def test_gemini_stt_stops_dispatching_once_cancelled(monkeypatch):
    from agents import gemini_asr as g, transcription_agent as ta
    monkeypatch.setattr(ta, "_to_mp3_16k", lambda p: p)
    monkeypatch.setattr(ta, "_split_audio", lambda p, max_sec: ["p0", "p1", "p2", "p3"])
    monkeypatch.setattr(g, "PARALLEL_PIECES", 1)   # sequential path — deterministic to test

    calls = []

    def piece(path, client=None, use_cache=True):
        calls.append(path)
        if path == "p1":
            cancellation.cancel("test-digest-1")
        return f"text-{path}"

    monkeypatch.setattr(g, "_llm_piece", piece)
    try:
        text, lang, segments, gaps = g.gemini_stt("x.mp3", "llm", digest="test-digest-1")
        assert text == ""   # cancelled result is treated as empty, not partial
        assert calls == ["p0", "p1"]   # p2 and p3 never dispatched
    finally:
        cancellation.clear("test-digest-1")


def test_process_one_piece_skips_immediately_if_already_cancelled(monkeypatch):
    # A ThreadPoolExecutor submits every piece up front — with a cap on
    # concurrency, most of them just sit queued. This is what makes a queued
    # (not-yet-started) piece bail out the moment a free worker picks it up,
    # instead of firing its API call regardless because submission already
    # happened before the cancel request arrived.
    from agents import gemini_asr as g
    cancellation.cancel("test-digest-3")
    called = []
    monkeypatch.setattr(g, "_llm_piece", lambda *a, **k: called.append(1) or "should not run")
    try:
        result = g._process_one_piece(5, "piece.mp3", 10, "llm", 180, True, digest="test-digest-3")
        assert result == (5, "", [], False)
        assert called == []   # the real API call never happened
    finally:
        cancellation.clear("test-digest-3")


def test_transcription_agent_raises_cancelled_not_generic_failure(monkeypatch):
    from agents import transcription_agent as ta, cancellation as c
    monkeypatch.setattr(ta, "SARVAM_API_KEY", "")
    monkeypatch.setenv("ASR_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key-for-test")

    def fake_gemini_stt(path, digest=None):
        return "", "te", [], 0   # what a cancelled gemini_stt returns

    import agents.gemini_asr as gem
    monkeypatch.setattr(gem, "gemini_stt", fake_gemini_stt)
    c.cancel("test-digest-2")
    try:
        import pytest
        with pytest.raises(c.UploadCancelled):
            ta.transcription_agent({"audio_path": "x.mp3", "chunk_index": 0, "digest": "test-digest-2"})
    finally:
        c.clear("test-digest-2")
