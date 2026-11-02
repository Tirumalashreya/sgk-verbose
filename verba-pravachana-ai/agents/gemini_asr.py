"""
Gemini 3.5 Transcribe as an ASR provider (the model family behind NotebookLM).

Modes:
  - "llm" (default): a general Gemini model with an explicit verbatim prompt, in
    short pieces. This is the NotebookLM-style approach, and the only mode that
    keeps Sanskrit verses: the dedicated transcribe model drops them.
  - "timestamps": gemini-3.5-transcribe, verbatim + word timings
  - "vocabulary": gemini-3.5-transcribe, verbatim + the Vaishnava terms list

Returns the same shape as the Sarvam provider: (text, language, segments, gap_count).
"""
import hashlib, json, os, time

MODEL = os.getenv("GEMINI_ASR_MODEL", "gemini-3.5-transcribe")
LLM_MODEL = os.getenv("GEMINI_LLM_MODEL", "gemini-3.8-flash")
PIECE_SECONDS = 25 * 60       # API limit is 30 min per request when timestamps are on
LLM_PIECE_SECONDS = 3 * 60    # short pieces keep a general model from skipping or drifting
LLM_PROMPT = (
    "Transcribe this audio exactly, word for word, in Telugu script. The speaker is giving a Telugu "
    "spiritual discourse and recites Sanskrit shlokas and Tamil pasurams. Include every Sanskrit and "
    "Tamil verse exactly as spoken, in Telugu script. Write numbers exactly as spoken, in Telugu "
    "words — never use digits (e.g. write మూడు వందల, not 300). Do not skip, summarize, translate, "
    "correct or explain anything. If a word is unclear, write [?]. Output only the transcript."
)
PHRASE_GAP = 0.5              # word gap (s) that ends a phrase segment
VOCAB_SIZE = 100              # docs: custom vocabulary works best around 100 terms
GAP_MARKER = "[?]"
_CACHE_DIR = os.path.join("audio_input", ".gemini_cache")
_TERMS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "vaishnava_terms.json")

_client = None
_client_lock = __import__("threading").Lock()


def _get_client():
    global _client
    with _client_lock:   # threads racing here created two clients and one was closed mid-request
        return _get_client_locked()


def _get_client_locked():
    global _client
    if _client is None:
        from google import genai
        key = os.getenv("GEMINI_API_KEY", "")
        if not key:
            raise RuntimeError("GEMINI_API_KEY is not set")
        # timeout in ms — a hung request would otherwise block the recording
        _client = genai.Client(api_key=key, http_options={"timeout": 180_000})
    return _client


_vertex_client = None
_vertex_client_lock = __import__("threading").Lock()


def _get_vertex_client():
    """Fallback only — same model, billed through Google Cloud instead of the
    AI Studio API key's prepaid credits. Only reached if the primary client's
    own retries (above) are all exhausted, same slot _sarvam_fallback used to
    sit in."""
    global _vertex_client
    with _vertex_client_lock:
        if _vertex_client is None:
            from google import genai
            project = os.getenv("GOOGLE_CLOUD_PROJECT", "")
            if not project:
                raise RuntimeError("GOOGLE_CLOUD_PROJECT is not set")
            # "global" — gemini-3.8-flash (LLM_MODEL) 404s on regional
            # endpoints like us-central1, confirmed by testing directly; it's
            # only served on the global one.
            _vertex_client = genai.Client(
                vertexai=True, project=project, location="global",
                http_options={"timeout": 180_000},
            )
        return _vertex_client


def _vocabulary() -> list[str]:
    try:
        with open(_TERMS_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return (data.get("telugu", []) + data.get("sanskrit", []))[:VOCAB_SIZE]
    except Exception as e:
        print(f"[gemini_asr] could not load terms: {e}")
        return []


def _config(mode: str) -> dict:
    cfg = {"language_codes": ["te-IN"]}
    if mode == "vocabulary":
        cfg["mode"] = {"type": "verbatim"}
        cfg["custom_vocabulary"] = _vocabulary()
    else:
        cfg["mode"] = {"type": "verbatim", "timestamp_granularities": ["word"]}
    return {"transcription_config": cfg}


def _seconds(offset) -> float:
    return float(str(offset or "0").rstrip("s") or 0)


def _phrases(text: str, words: list[dict], offset: float) -> list[dict]:
    """Group words into phrases at short pauses. Phrase text is an exact slice
    of the transcript (annotation indices are UTF-8 byte offsets), so the
    formatter can find each phrase's end in the transcript verbatim."""
    raw = text.encode("utf-8")
    phrases, group = [], []

    def flush():
        if group:
            a, b = group[0]["start_index"], group[-1]["end_index"]
            phrases.append({
                "start": round(offset + _seconds(group[0]["start_offset"]), 2),
                "end": round(offset + _seconds(group[-1]["end_offset"]), 2),
                "text": raw[a:b].decode("utf-8", errors="ignore"),
            })
            group.clear()

    for w in words:
        if group and _seconds(w["start_offset"]) - _seconds(group[-1]["end_offset"]) >= PHRASE_GAP:
            flush()
        group.append(w)
    flush()
    return phrases


def _transcribe_piece(path: str, mode: str, offset: float, attempts: int = 3,
                      use_cache: bool = True) -> tuple[str, list[dict]]:
    with open(path, "rb") as f:
        digest = hashlib.sha1(f.read()).hexdigest()
    vocab_tag = hashlib.sha1("|".join(_vocabulary()).encode()).hexdigest()[:8] if mode == "vocabulary" else ""
    cache = os.path.join(_CACHE_DIR, f"{MODEL}-{mode}{vocab_tag}-{digest}.json")
    if use_cache and os.path.exists(cache):
        with open(cache, encoding="utf-8") as f:
            saved = json.load(f)
        return saved["text"], [dict(p, start=p["start"] + offset, end=p["end"] + offset) for p in saved["phrases"]]

    client = _get_client()
    for attempt in range(attempts):
        uploaded = None
        try:
            uploaded = client.files.upload(file=path)
            result = client.interactions.create(
                model=MODEL,
                input=[{"type": "audio", "uri": uploaded.uri, "mime_type": uploaded.mime_type}],
                generation_config=_config(mode),
            )
            break
        except Exception as e:
            if attempt == attempts - 1:
                raise
            print(f"[gemini_asr] attempt {attempt + 1} failed, retrying: {str(e)[:120]}")
            time.sleep(5 * (attempt + 1))
        finally:
            if uploaded is not None:
                try:
                    client.files.delete(name=uploaded.name)
                except Exception:
                    pass

    text = (result.output_text or "").strip()
    words = []
    for step in result.steps or []:
        for content in getattr(step, "content", None) or []:
            for a in getattr(content, "annotations", None) or []:
                d = a.model_dump(exclude_none=True) if hasattr(a, "model_dump") else dict(a)
                if d.get("type") == "word_info" and "start_index" in d:
                    words.append(d)
    phrases = _phrases(result.output_text or "", words, 0.0)

    if use_cache:
        os.makedirs(_CACHE_DIR, exist_ok=True)
        with open(cache, "w", encoding="utf-8") as f:
            json.dump({"text": text, "phrases": phrases}, f, ensure_ascii=False)
    return text, [dict(p, start=p["start"] + offset, end=p["end"] + offset) for p in phrases]


def _llm_piece(path: str, client=None, use_cache: bool = True, attempts: int = 3) -> str:
    from google.genai import types
    with open(path, "rb") as f:
        audio = f.read()
    tag = hashlib.sha1((LLM_MODEL + LLM_PROMPT).encode()).hexdigest()[:8]
    cache = os.path.join(_CACHE_DIR, f"llm-{tag}-{hashlib.sha1(audio).hexdigest()}.txt")
    if use_cache and os.path.exists(cache) and os.path.getsize(cache) > 0:
        with open(cache, encoding="utf-8") as f:
            return f.read()
    client = client or _get_client()
    for attempt in range(attempts):
        try:
            result = client.models.generate_content(
                model=LLM_MODEL,
                contents=[types.Part.from_bytes(data=audio, mime_type="audio/mpeg"), LLM_PROMPT],
                config=types.GenerateContentConfig(temperature=0),
            )
            if not (result.text or "").strip():
                # An empty reply is a failure, not "nothing was said" — accepting it
                # silently dropped 3 minutes of a test recording
                raise RuntimeError("empty transcription returned")
            break
        except Exception as e:
            if attempt == attempts - 1:
                raise
            print(f"[gemini_asr] attempt {attempt + 1} failed, retrying: {str(e)[:120]}")
            time.sleep(5 * (attempt + 1))
    text = " ".join((result.text or "").split())
    if use_cache:
        os.makedirs(_CACHE_DIR, exist_ok=True)
        with open(cache, "w", encoding="utf-8") as f:
            f.write(text)
    return text


def _sarvam_fallback(piece: str) -> str:
    from agents import transcription_agent as ta
    if not ta.SARVAM_API_KEY:
        return ""
    try:
        text, _, _, gaps = ta._sarvam_stt(piece)
        return text if text.replace(GAP_MARKER, "").strip() else ""
    except Exception as e:
        print(f"[gemini_asr] Sarvam fallback failed too: {str(e)[:120]}")
        return ""


def _vertex_fallback(piece: str) -> str:
    """Same prompt, same model, same Gemini — just through Google Cloud
    billing instead of the AI Studio key, for when that key's own credits run
    out. Only reached after the primary client's retries are all exhausted."""
    if not os.getenv("GOOGLE_CLOUD_PROJECT"):
        return ""
    from google.genai import types
    try:
        client = _get_vertex_client()
        with open(piece, "rb") as f:
            audio = f.read()
        result = client.models.generate_content(
            model=LLM_MODEL,
            contents=[types.Part.from_bytes(data=audio, mime_type="audio/mpeg"), LLM_PROMPT],
            config=types.GenerateContentConfig(temperature=0),
        )
        text = " ".join((result.text or "").split())
        return text
    except Exception as e:
        print(f"[gemini_asr] Vertex AI fallback failed too: {str(e)[:150]}")
        return ""


PARALLEL_PIECES = int(os.getenv("GEMINI_MAX_PARALLEL", "4"))  # pieces are independent audio
                                                                # chunks, so an upload no longer
                                                                # waits on them one at a time — a
                                                                # live recording was always this
                                                                # fast in practice because each
                                                                # minute transcribes in the
                                                                # background while the next minute
                                                                # is still being recorded; an
                                                                # upload has no such overlap to
                                                                # hide behind, so it needs this
                                                                # explicitly


def _process_one_piece(i: int, piece: str, total: int, mode: str, piece_seconds: int,
                        use_cache: bool, digest: str | None = None) -> tuple[int, str, list[dict], bool]:
    """One piece, independently — returns (index, text, phrases, was_a_gap) so the
    caller can reassemble results in order after running these concurrently.

    For "llm" mode, pieces alternate which account does the work (AI Studio
    key vs Vertex AI/Google Cloud billing) — two separate rate-limit pools,
    so running several pieces at once no longer piles every request onto one
    pool's per-minute limit. Whichever one wasn't tried first still backs up
    the other if it fails.

    All pieces get submitted to the thread pool up front — with max_workers
    capping how many actually run at once, most of them sit queued, not yet
    doing any real work. Checking cancellation again right here (not just
    before submission) means a queued piece a worker hasn't picked up yet
    still skips its API call once cancelled, instead of every one of them
    firing off regardless because submission itself was already done."""
    from agents import cancellation
    if cancellation.is_cancelled(digest):
        return i, "", [], False
    offset = i * piece_seconds
    vertex_available = bool(os.getenv("GOOGLE_CLOUD_PROJECT"))
    use_vertex_first = mode == "llm" and vertex_available and i % 2 == 1
    try:
        if mode == "llm":
            client = _get_vertex_client() if use_vertex_first else _get_client()
            text, phrases = _llm_piece(piece, client=client, use_cache=use_cache), []
        else:
            text, phrases = _transcribe_piece(piece, mode, offset, use_cache=use_cache)
        if not text.strip():
            raise RuntimeError("empty transcription returned")
        label = "Vertex AI" if use_vertex_first else "AI Studio"
        print(f"  [gemini piece {i + 1}/{total}] {len(text)} chars ({label})")
        return i, text, phrases, False
    except Exception as e:
        print(f"  [gemini piece {i + 1}/{total}] FAILED after retries: {str(e)[:120]}")
        # Whichever pool handled this piece just exhausted its own retries —
        # try the other one before giving up, so one pool's limit or billing
        # issue doesn't leave a hole in the transcript.
        if use_vertex_first:
            source = "AI Studio"
            try:
                fallback = _llm_piece(piece, client=_get_client(), use_cache=use_cache)
            except Exception as e2:
                print(f"[gemini_asr] AI Studio fallback failed too: {str(e2)[:150]}")
                fallback = ""
        else:
            source = "Vertex AI"
            fallback = _vertex_fallback(piece)
        if not fallback:
            fallback = _sarvam_fallback(piece)
            source = "Sarvam"
        if fallback:
            print(f"  [gemini piece {i + 1}/{total}] covered by {source} ({len(fallback)} chars)")
            return i, fallback, [], False
        return i, GAP_MARKER, [], True


def gemini_stt(path: str, mode: str | None = None, use_cache: bool = True, digest: str | None = None) -> tuple:
    """Transcribe a whole recording in ≤25-minute pieces, several at once —
    pieces don't depend on each other, so there's no reason to wait on them
    one at a time. `digest` (the upload's content hash) lets a user-cancelled
    upload stop dispatching further pieces — already in-flight API calls still
    finish, but nothing new starts."""
    from agents.transcription_agent import _to_mp3_16k, _split_audio
    from agents import cancellation
    mode = mode or os.getenv("GEMINI_ASR_MODE", "llm")
    piece_seconds = LLM_PIECE_SECONDS if mode == "llm" else PIECE_SECONDS
    print(f"[transcription] Gemini ({LLM_MODEL if mode == 'llm' else MODEL}, verbatim, {mode})...")
    pieces = _split_audio(_to_mp3_16k(path), max_sec=piece_seconds)

    workers = max(1, min(PARALLEL_PIECES, len(pieces)))
    results = []
    if workers == 1:
        for i, p in enumerate(pieces):
            if cancellation.is_cancelled(digest):
                print(f"[gemini_asr] cancelled — stopping after {i}/{len(pieces)} piece(s)")
                break
            results.append(_process_one_piece(i, p, len(pieces), mode, piece_seconds, use_cache, digest))
    else:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futures = []
            for i, p in enumerate(pieces):
                if cancellation.is_cancelled(digest):
                    print(f"[gemini_asr] cancelled — not starting remaining piece(s)")
                    break
                futures.append(ex.submit(_process_one_piece, i, p, len(pieces), mode, piece_seconds, use_cache, digest))
            results = [f.result() for f in futures]

    if cancellation.is_cancelled(digest):
        print("[transcription] Gemini cancelled by user")
        return "", "te", [], 0

    results.sort(key=lambda r: r[0])
    texts = [r[1] for r in results]
    segments = [p for r in results for p in r[2]]
    gaps = sum(1 for r in results if r[3])

    full_text = " ".join(t for t in texts if t)
    print(f"[transcription] Gemini done ({len(full_text)} chars, {gaps} gap(s))")
    return full_text, "te", segments, gaps
