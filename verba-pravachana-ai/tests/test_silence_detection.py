"""Tests that pure digital silence (<= -80 dB) or empty stubs are detected
and skipped before calling Gemini, preventing hallucinations from silent audio."""
import os
import subprocess
from agents import gemini_asr


def test_is_silence_detects_nonexistent_or_tiny_files(tmp_path):
    assert gemini_asr._is_silence(str(tmp_path / "nonexistent.mp3")) is True
    tiny = tmp_path / "tiny.mp3"
    tiny.write_bytes(b"123")
    assert gemini_asr._is_silence(str(tiny)) is True


def test_is_silence_detects_pure_digital_silence(tmp_path):
    # Generate 1 second of pure digital silence (-91 dB) with ffmpeg
    silent_file = str(tmp_path / "silence.mp3")
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono", "-t", "1", "-q:a", "9", silent_file],
        capture_output=True, check=True
    )
    assert os.path.exists(silent_file)
    assert gemini_asr._is_silence(silent_file) is True


def test_is_silence_allows_actual_tone(tmp_path):
    # Generate 1 second of an audible 440 Hz sine wave with ffmpeg
    tone_file = str(tmp_path / "tone.mp3")
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=16000", "-t", "1", "-q:a", "9", tone_file],
        capture_output=True, check=True
    )
    assert os.path.exists(tone_file)
    assert gemini_asr._is_silence(tone_file) is False


def test_llm_piece_skips_silent_audio_without_calling_gemini(tmp_path, monkeypatch):
    silent_file = str(tmp_path / "silence.mp3")
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono", "-t", "1", "-q:a", "9", silent_file],
        capture_output=True, check=True
    )
    called = []
    class FakeClient:
        class models:
            @staticmethod
            def generate_content(*args, **kwargs):
                called.append(1)
                raise RuntimeError("Should never be called for silent audio")

    result = gemini_asr._llm_piece(silent_file, client=FakeClient())
    assert result == ""
    assert not called
