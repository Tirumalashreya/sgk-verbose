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
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "")
sarvam_client = SarvamAI(api_subscription_key=SARVAM_API_KEY) if SARVAM_API_KEY else None


# Converted audio and its pieces go here, never next to the user's own file
WORK_DIR = os.path.join("audio_input", ".work")


def _work_path(src: str, suffix: str) -> str:
    import hashlib
    os.makedirs(WORK_DIR, exist_ok=True)
    tag = hashlib.sha1(os.path.abspath(src).encode()).hexdigest()[:10]
    return os.path.join(WORK_DIR, f"{tag}{suffix}")


def _to_mp3_16k(src: str) -> str:
    """Convert any audio file to MP3 16kHz mono using ffmpeg. Returns path to converted file."""
    import subprocess
    dst = _work_path(src, "_16k.mp3")
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


_SARVAM_CACHE_DIR = os.path.join("audio_input", ".sarvam_cache")
_SARVAM_FATAL = ("402", "insufficient_quota", "No credits", "401", "403")
GAP_MARKER = "[?]"  # stands in for audio that could not be transcribed


def _sarvam_keyterms() -> list[str]:
    """Up to 50 Vaishnava terms (API limit, 64 chars each) to bias saaras:v4."""
    import json
    path = os.path.join(os.path.dirname(__file__), "..", "data", "vaishnava_terms.json")
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[transcription] could not load keyterms: {e}")
        return []
    terms = [t for t in data.get("telugu", []) + data.get("sanskrit", []) if len(t) <= 64]
    return list(dict.fromkeys(terms))[:50]


def sarvam_settings(model: str | None = None, mode: str | None = None, keyterms: bool | None = None) -> dict:
    """Model/mode/keyterms from arguments, else SARVAM_MODEL / SARVAM_MODE / SARVAM_KEYTERMS."""
    model = model or os.getenv("SARVAM_MODEL", "saaras:v3")
    mode = mode or os.getenv("SARVAM_MODE", "transcribe")
    if keyterms is None:
        keyterms = os.getenv("SARVAM_KEYTERMS", "0") == "1"
    # keyterms are only supported by saaras:v4
    terms = _sarvam_keyterms() if keyterms and model == "saaras:v4" else []
    return {"model": model, "mode": mode, "keyterms": terms}


def _sarvam_cache_path(chunk_path: str, settings: dict) -> str:
    """Cache key is the audio content plus settings, so re-uploads and restarts never pay twice."""
    import hashlib
    with open(chunk_path, "rb") as f:
        digest = hashlib.sha1(f.read()).hexdigest()
    if settings["model"] == "saaras:v3" and settings["mode"] == "transcribe" and not settings["keyterms"]:
        return os.path.join(_SARVAM_CACHE_DIR, f"saaras-v3-{digest}.txt")  # original key format
    kt = hashlib.sha1("|".join(settings["keyterms"]).encode()).hexdigest()[:8] if settings["keyterms"] else "nokt"
    name = f"{settings['model'].replace(':', '-')}-{settings['mode']}-{kt}-{digest}.txt"
    return os.path.join(_SARVAM_CACHE_DIR, name)


def _sarvam_transcribe_chunk(args, attempts: int = 3):
    import time as _time
    i, chunk_path, settings = args if len(args) == 3 else (*args, sarvam_settings())
    cache = _sarvam_cache_path(chunk_path, settings)
    if os.path.exists(cache):
        with open(cache, encoding="utf-8") as f:
            return i, f.read()

    for attempt in range(attempts):
        try:
            with open(chunk_path, "rb") as f:
                extra = {"keyterms": settings["keyterms"]} if settings["keyterms"] else {}
                response = sarvam_client.speech_to_text.transcribe(
                    file=f,
                    model=settings["model"],
                    mode=settings["mode"],
                    # without a timeout one hung request blocks the whole recording
                    request_options={"timeout_in_seconds": 60, "max_retries": 0},
                    **extra,
                )
            break
        except Exception as e:
            if any(code in str(e) for code in _SARVAM_FATAL) or attempt == attempts - 1:
                raise
            print(f"  [sarvam chunk {i}] attempt {attempt + 1} failed, retrying: {str(e)[:100]}")
            _time.sleep(2 * (attempt + 1))

    text = (response.transcript or "").strip()
    os.makedirs(_SARVAM_CACHE_DIR, exist_ok=True)
    with open(cache, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"  [sarvam chunk {i}] {text[:100]}")
    return i, text


def _sarvam_stt(path: str, settings: dict | None = None) -> tuple:
    """Transcribe using Sarvam AI (saaras:v3 by default) — parallel sub-chunk calls.
    Returns (text, language, segments, gap_count)."""
    settings = settings or sarvam_settings()
    print(f"[transcription] Sarvam AI ({settings['model']}, {settings['mode']}, "
          f"{len(settings['keyterms'])} keyterms)...")
    mp3_path = _to_mp3_16k(path)
    chunks = _split_audio(mp3_path, max_sec=28)

    # Probe with first chunk — bail out immediately on quota/auth errors
    try:
        _sarvam_transcribe_chunk((0, chunks[0], settings))
    except Exception as e:
        msg = str(e)
        if any(code in msg for code in _SARVAM_FATAL):
            print(f"[transcription] Sarvam quota/auth error — skipping: {msg[:120]}")
            raise

    # No overall deadline: a long recording simply takes longer. (A batch-wide
    # timeout used to cut off everything after the first ~60s of API time and
    # silently return a partial transcript.)
    results, failed = {}, []
    with ThreadPoolExecutor(max_workers=min(5, len(chunks))) as ex:
        futures = {ex.submit(_sarvam_transcribe_chunk, (i, c, settings)): i for i, c in enumerate(chunks)}
        for fut in as_completed(futures):
            i = futures[fut]
            try:
                results[i] = fut.result()[1]
            except Exception as e:
                failed.append(i)
                print(f"  [sarvam chunk {i}] FAILED after retries: {str(e)[:120]}")
            done = len(results) + len(failed)
            if done % 25 == 0 or done == len(chunks):
                print(f"[transcription] Sarvam progress {done}/{len(chunks)}")

    # Failed pieces stay visible in the transcript instead of silently vanishing
    pieces = [results[i] if i in results else GAP_MARKER for i in range(len(chunks))]
    full_text = " ".join(p for p in pieces if p)
    print(f"[transcription] Sarvam done ({len(full_text)} chars, {len(failed)} gap(s))")
    return full_text, "te", [], len(failed)


def _whisper_chunk(path: str):
    """Send one file to Groq Whisper, rotating across all available keys on error."""
    import time as _time
    import re as _re

    if os.path.getsize(path) < 1000:
        print(f"[transcription] skipping tiny file {path}")
        return None

    if not _WHISPER_KEYS:
        raise RuntimeError("No Groq Whisper key set (GROQ_API_KEY_WHISPER) — cannot fall back to Whisper")
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

    base = _work_path(path, f"_{max_sec}s")
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

    # Providers in preference order (ASR_PROVIDER picks the first); each falls
    # through to the next on failure or an empty result, Whisper last
    providers = []
    if os.getenv("ASR_PROVIDER", "sarvam").lower() == "gemini" and os.getenv("GEMINI_API_KEY"):
        from agents.gemini_asr import gemini_stt
        providers.append(("Gemini", gemini_stt))
    if SARVAM_API_KEY:
        providers.append(("Sarvam", _sarvam_stt))

    for name, stt in providers:
        try:
            text, lang, segments, gaps = stt(path)
            if text.strip() and text.replace(GAP_MARKER, "").strip():
                state["transcription_gaps"] = gaps
                state["transcript"] = text
                state["detected_language"] = lang
                state["transcript_segments"] = segments
                state["asr_provider"] = name.lower()
                state["current_agent"] = "transcription_done"
                return state
            print(f"[transcription] {name} returned empty — trying next provider")
        except Exception as e:
            print(f"[transcription] {name} failed ({e}) — trying next provider")

    # Fallback: Groq Whisper
    text, lang, segments = _whisper_stt(path)
    state["asr_provider"] = "whisper"
    print(f"[transcription] Whisper done ({len(text)} chars): {text[:300]}")
    state["transcript"] = text
    state["detected_language"] = lang
    state["transcript_segments"] = segments
    state["current_agent"] = "transcription_done"
    return state
