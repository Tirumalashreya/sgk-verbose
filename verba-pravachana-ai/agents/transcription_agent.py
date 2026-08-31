from graph.state import VerbaState
from groq import Groq
from sarvamai import SarvamAI
from concurrent.futures import ThreadPoolExecutor, as_completed
import os, subprocess, requests
from dotenv import load_dotenv
load_dotenv()

# Set Google credentials path relative to this file's location
_cred_path = os.path.join(os.path.dirname(__file__), "..", os.getenv("GOOGLE_APPLICATION_CREDENTIALS", ""))
if os.path.exists(_cred_path):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.abspath(_cred_path)

_WHISPER_KEYS = [k for k in [
    os.getenv("GROQ_API_KEY_WHISPER"),
    os.getenv("GROQ_API_KEY_WHISPER2"),
] if k]
groq_client = Groq(api_key=_WHISPER_KEYS[0])
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "")
sarvam_client = SarvamAI(api_subscription_key=SARVAM_API_KEY) if SARVAM_API_KEY else None


def _to_mp3_16k(src: str) -> str:
    """Convert any audio file to MP3 16kHz mono using ffmpeg. Returns path to converted file."""
    import subprocess, tempfile
    dst = src.rsplit(".", 1)[0] + "_16k.mp3"
    subprocess.run(
        ["ffmpeg", "-y", "-i", src, "-ar", "16000", "-ac", "1", "-q:a", "4", dst],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True
    )
    return dst


def _google_stt(path: str) -> str:
    from google.cloud import speech
    client = speech.SpeechClient()

    # Convert to MP3 16kHz mono regardless of input format
    mp3_path = _to_mp3_16k(path)
    with open(mp3_path, "rb") as f:
        audio_bytes = f.read()

    audio = speech.RecognitionAudio(content=audio_bytes)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.MP3,
        sample_rate_hertz=16000,
        audio_channel_count=1,
        language_code="te-IN",
        alternative_language_codes=["ta-IN", "sa-IN"],
        enable_automatic_punctuation=True,
        model="latest_long",
    )

    print("[transcription] sending to Google STT (te-IN + ta-IN + sa-IN)...")
    response = client.recognize(config=config, audio=audio)

    lines = []
    for result in response.results:
        alt = result.alternatives[0]
        lines.append(alt.transcript)
        print(f"  [{alt.confidence:.2f}] {alt.transcript[:100]}")

    return "\n".join(lines)


def _sarvam_transcribe_chunk(args):
    i, chunk_path = args
    with open(chunk_path, "rb") as f:
        response = sarvam_client.speech_to_text.transcribe(
            file=f,
            model="saaras:v3",
            mode="transcribe",
        )
    text = (response.transcript or "").strip()
    print(f"  [sarvam chunk {i}] {text[:100]}")
    return i, text


def _sarvam_stt(path: str) -> tuple:
    """Transcribe using Sarvam AI saaras:v3 — parallel sub-chunk calls."""
    print("[transcription] Sarvam AI (saaras:v3)...")
    mp3_path = _to_mp3_16k(path)
    chunks = _split_audio(mp3_path, max_sec=28)

    # Probe with first chunk — bail out immediately on quota/auth errors
    try:
        _sarvam_transcribe_chunk((0, chunks[0]))
    except Exception as e:
        msg = str(e)
        if any(code in msg for code in ["402", "insufficient_quota", "No credits", "401", "403"]):
            print(f"[transcription] Sarvam quota/auth error — skipping: {msg[:120]}")
            raise

    results = {}
    try:
        with ThreadPoolExecutor(max_workers=min(5, len(chunks))) as ex:
            for i, text in ex.map(_sarvam_transcribe_chunk, enumerate(chunks), timeout=60):
                results[i] = text
    except Exception as e:
        print(f"[transcription] Sarvam partial failure: {e} — using {len(results)}/{len(chunks)} chunks")

    full_text = " ".join(results[i] for i in sorted(results) if results[i])
    print(f"[transcription] Sarvam done ({len(full_text)} chars)")
    return full_text, "te", []


def _whisper_chunk(path: str):
    """Send one file to Groq Whisper, rotating across all available keys on error."""
    import time as _time
    import re as _re

    if os.path.getsize(path) < 1000:
        print(f"[transcription] skipping tiny file {path}")
        return None

    attempts = len(_WHISPER_KEYS) * 3  # 3 tries per key
    for attempt in range(attempts):
        key = _WHISPER_KEYS[attempt % len(_WHISPER_KEYS)]
        client = Groq(api_key=key)
        try:
            with open(path, "rb") as f:
                result = client.audio.transcriptions.create(
                    file=(os.path.basename(path), f),
                    model="whisper-large-v3",
                    language="te",
                    response_format="verbose_json"
                )
            return result
        except Exception as e:
            msg = str(e)
            m = _re.search(r'try again in ([\d.]+)s', msg)
            wait = float(m.group(1)) + 2 if m else 15
            key_num = (attempt % len(_WHISPER_KEYS)) + 1
            print(f"[transcription] Whisper key {key_num} error (attempt {attempt+1}/{attempts}), retrying in {wait:.0f}s: {msg[:100]}")
            _time.sleep(wait)
    raise RuntimeError("Groq Whisper failed after all attempts")


def _split_audio(path: str, max_sec: int = 300) -> list:
    """Split audio into max_sec chunks using ffmpeg. Returns list of chunk paths."""
    import subprocess, json as _json
    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", path],
        capture_output=True, text=True
    )
    duration = float(probe.stdout.strip() or 0)
    if duration <= max_sec:
        return [path]

    base = path.rsplit(".", 1)[0]
    ext  = path.rsplit(".", 1)[1]
    chunks, start, i = [], 0, 0
    while start < duration:
        out = f"{base}_part{i}.{ext}"
        subprocess.run(
            ["ffmpeg", "-y", "-i", path, "-ss", str(start),
             "-t", str(max_sec), "-c", "copy", out],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        if os.path.exists(out) and os.path.getsize(out) > 1000:
            chunks.append(out)
        start += max_sec
        i += 1
    print(f"[transcription] split into {len(chunks)} chunks of ≤{max_sec}s")
    return chunks


def _whisper_stt(path: str):
    print("[transcription] falling back to Groq Whisper...")
    mp3_path = _to_mp3_16k(path)
    chunks = _split_audio(mp3_path, max_sec=300)

    all_text, all_segs, lang = [], [], "te"
    offset = 0.0
    for chunk_path in chunks:
        result = _whisper_chunk(chunk_path)
        if result is None:
            continue
        all_text.append(result.text.strip())
        lang = result.language or lang
        segs = getattr(result, "segments", []) or []
        for seg in segs:
            start = (seg.get("start") if isinstance(seg, dict) else getattr(seg, "start", 0)) + offset
            end   = (seg.get("end")   if isinstance(seg, dict) else getattr(seg, "end",   0)) + offset
            text  = (seg.get("text")  if isinstance(seg, dict) else getattr(seg, "text",  "")).strip()
            print(f"  [{start:.1f}s → {end:.1f}s] {text}")
            all_segs.append({"start": start, "end": end, "text": text})
        chunk_dur = float(subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", chunk_path],
            capture_output=True, text=True
        ).stdout.strip() or 0)
        offset += chunk_dur

    return " ".join(all_text), lang, all_segs


def transcription_agent(state: VerbaState) -> VerbaState:
    chunk_index = state.get("chunk_index", 0)

    # YouTube captions already fetched by listener — use directly
    if state.get("caption_text"):
        text = state["caption_text"]
        print(f"[transcription] chunk {chunk_index} — using YouTube captions ({len(text)} chars)")
        print(f"[transcription] preview: {text[:300]}")
        state["transcript"] = text
        state["detected_language"] = "te"
        state["transcript_segments"] = []
        state["current_agent"] = "transcription_done"
        return state

    # Video ended signal from listener — nothing to transcribe
    if state.get("error") == "video_ended" or not state.get("audio_path"):
        print(f"[transcription] chunk {chunk_index} — skipping (video ended)")
        state["transcript"] = ""
        state["current_agent"] = "transcription_done"
        return state

    path = state["audio_path"]
    print(f"[transcription] chunk {chunk_index} — {path}")

    # Try Sarvam AI first
    if SARVAM_API_KEY:
        try:
            text, lang, segments = _sarvam_stt(path)
            if text.strip():
                state["transcript"] = text
                state["detected_language"] = lang
                state["transcript_segments"] = segments
                state["current_agent"] = "transcription_done"
                return state
            else:
                print("[transcription] Sarvam returned empty — falling back to Whisper")
        except Exception as e:
            print(f"[transcription] Sarvam failed ({e}) — falling back to Whisper")

    # Fallback: Groq Whisper
    text, lang, segments = _whisper_stt(path)
    print(f"[transcription] Whisper done ({len(text)} chars): {text[:300]}")
    state["transcript"] = text
    state["detected_language"] = lang
    state["transcript_segments"] = segments
    state["current_agent"] = "transcription_done"
    return state
