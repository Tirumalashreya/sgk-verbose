"""One Sarvam chunk failing (after its own retries) must not discard every
other chunk — that turned one transient error into losing the whole listener
for the duration of the recording (seen on a real 2-hour upload)."""
import agents.dual_asr as dual_asr
import agents.transcription_agent as ta
import agents.gemini_asr as gemini_asr


def _stub_common(monkeypatch, chunks):
    monkeypatch.setattr(ta, "_to_mp3_16k", lambda path: path)
    monkeypatch.setattr(ta, "_split_audio", lambda path, max_sec: chunks)
    monkeypatch.setattr(ta, "sarvam_settings", lambda *a, **k: {"model": "saaras:v4", "mode": "verbatim", "keyterms": []})
    monkeypatch.setattr(gemini_asr, "gemini_stt", lambda path, mode: ("word " * len(chunks), "te", [], 0))
    # No real audio to judge disputes against in this test — any dispute is just "?"
    monkeypatch.setattr(dual_asr, "_judge_chunk", lambda audio_path, items, model: {})


def test_one_failed_chunk_keeps_the_rest_as_the_sarvam_side(monkeypatch):
    chunks = ["c0", "c1", "c2", "c3"]
    _stub_common(monkeypatch, chunks)

    def fake_transcribe(args, attempts=3):
        i, chunk_path, settings = args
        if i == 2:
            raise RuntimeError("transient 503")
        return i, f"word{i}"
    monkeypatch.setattr(ta, "_sarvam_transcribe_chunk", fake_transcribe)

    text, lang, segs, gaps, report = dual_asr.dual_stt("fake.mp3")
    # Both listeners present — the single chunk failure did not knock Sarvam out entirely
    assert set(report["listeners"]) == {"sarvam", "gemini"}
    assert "sarvam" not in (report.get("errors") or {})


def test_every_chunk_failing_still_falls_back_to_gemini_only(monkeypatch):
    chunks = ["c0", "c1"]
    _stub_common(monkeypatch, chunks)

    def always_fails(args, attempts=3):
        raise RuntimeError("quota exceeded")
    monkeypatch.setattr(ta, "_sarvam_transcribe_chunk", always_fails)

    text, lang, segs, gaps, report = dual_asr.dual_stt("fake.mp3")
    assert report["listeners"] == ["gemini"]
    assert "sarvam" in report["errors"]
    assert text.strip()  # Gemini's text still comes through
