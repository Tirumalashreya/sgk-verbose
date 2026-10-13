"""
Google Cloud Speech-to-Text v2, model chirp_3, as an ASR provider.

Synchronous recognize accepts at most 60 s of audio, so the recording is cut
into 55 s pieces sent in parallel (cached by content, like Sarvam). Word time
offsets come back too, giving the formatter real pause-based paragraphs.

Needs GOOGLE_APPLICATION_CREDENTIALS (service account with the "Cloud Speech
Client" role) and GOOGLE_CLOUD_PROJECT, on a project with billing enabled.
Returns (text, language, segments, gap_count) like the other providers.
"""
import hashlib, json, os, time
from concurrent.futures import ThreadPoolExecutor, as_completed

MODEL = os.getenv("GOOGLE_ASR_MODEL", "chirp_3")
LOCATION = os.getenv("GOOGLE_ASR_LOCATION", "us")
PIECE_SECONDS = 55
PHRASE_GAP = 0.5
GAP_MARKER = "[?]"
_CACHE_DIR = os.path.join("audio_input", ".google_cache")

_client = None


def _get_client():
    global _client
    if _client is None:
        from google.cloud.speech_v2 import SpeechClient
        from google.api_core.client_options import ClientOptions
        cred = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
        if cred and not os.path.isabs(cred):
            # .env paths are relative to the backend folder
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.join(os.path.dirname(__file__), "..", cred)
        endpoint = "speech.googleapis.com" if LOCATION == "global" else f"{LOCATION}-speech.googleapis.com"
        _client = SpeechClient(client_options=ClientOptions(api_endpoint=endpoint))
    return _client


def _seconds(duration) -> float:
    return duration.total_seconds() if hasattr(duration, "total_seconds") else float(duration or 0)


def _transcribe_piece(args, attempts: int = 3) -> tuple[int, str, list[dict]]:
    i, path, offset = args
    with open(path, "rb") as f:
        audio = f.read()
    cache = os.path.join(_CACHE_DIR, f"{MODEL}-{hashlib.sha1(audio).hexdigest()}.json")
    if os.path.exists(cache):
        with open(cache, encoding="utf-8") as f:
            saved = json.load(f)
        return i, saved["text"], [dict(w, start=w["start"] + offset, end=w["end"] + offset) for w in saved["words"]]

    from google.cloud.speech_v2.types import cloud_speech as cs
    project = os.getenv("GOOGLE_CLOUD_PROJECT", "")
    config = cs.RecognitionConfig(
        auto_decoding_config=cs.AutoDetectDecodingConfig(),
        language_codes=["te-IN"],
        model=MODEL,
        features=cs.RecognitionFeatures(enable_automatic_punctuation=True, enable_word_time_offsets=True),
    )
    request = cs.RecognizeRequest(recognizer=f"projects/{project}/locations/{LOCATION}/recognizers/_",
                                  config=config, content=audio)
    for attempt in range(attempts):
        try:
            response = _get_client().recognize(request=request, timeout=90)
            break
        except Exception as e:
            if attempt == attempts - 1 or "PermissionDenied" in type(e).__name__:
                raise
            print(f"  [google piece {i}] attempt {attempt + 1} failed, retrying: {str(e)[:100]}")
            time.sleep(3 * (attempt + 1))

    texts, words = [], []
    for result in response.results:
        if not result.alternatives:
            continue
        alt = result.alternatives[0]
        texts.append(alt.transcript.strip())
        for w in alt.words:
            words.append({"start": _seconds(w.start_offset), "end": _seconds(w.end_offset), "text": w.word})
    text = " ".join(t for t in texts if t)
    os.makedirs(_CACHE_DIR, exist_ok=True)
    with open(cache, "w", encoding="utf-8") as f:
        json.dump({"text": text, "words": words}, f, ensure_ascii=False)
    return i, text, [dict(w, start=w["start"] + offset, end=w["end"] + offset) for w in words]


def _phrases(words: list[dict]) -> list[dict]:
    """Group words into phrase segments at short pauses, for pause-based paragraphs."""
    phrases, group = [], []
    for w in words:
        if group and w["start"] - group[-1]["end"] >= PHRASE_GAP:
            phrases.append({"start": group[0]["start"], "end": group[-1]["end"], "text": " ".join(x["text"] for x in group)})
            group = []
        group.append(w)
    if group:
        phrases.append({"start": group[0]["start"], "end": group[-1]["end"], "text": " ".join(x["text"] for x in group)})
    return phrases


def chirp_stt(path: str) -> tuple:
    from agents.transcription_agent import _to_mp3_16k, _split_audio
    print(f"[transcription] Google {MODEL} ({LOCATION})...")
    pieces = _split_audio(_to_mp3_16k(path), max_sec=PIECE_SECONDS)
    results, failed = {}, []
    with ThreadPoolExecutor(max_workers=min(5, len(pieces))) as ex:
        futures = {ex.submit(_transcribe_piece, (i, p, i * PIECE_SECONDS)): i for i, p in enumerate(pieces)}
        for fut in as_completed(futures):
            i = futures[fut]
            try:
                _, text, words = fut.result()
                results[i] = (text, words)
            except Exception as e:
                failed.append(i)
                print(f"  [google piece {i}] FAILED: {str(e)[:120]}")
    texts = [results[i][0] if i in results else GAP_MARKER for i in range(len(pieces))]
    words = [w for i in range(len(pieces)) if i in results for w in results[i][1]]
    full_text = " ".join(t for t in texts if t)
    print(f"[transcription] Google done ({len(full_text)} chars, {len(failed)} gap(s))")
    return full_text, "te", _phrases(words), len(failed)
