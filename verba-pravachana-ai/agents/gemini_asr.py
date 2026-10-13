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
    "Tamil verse exactly as spoken, in Telugu script. Do not skip, summarize, translate, correct or "
    "explain anything. If a word is unclear, write [?]. Output only the transcript."
)
PHRASE_GAP = 0.5              # word gap (s) that ends a phrase segment
VOCAB_SIZE = 100              # docs: custom vocabulary works best around 100 terms
GAP_MARKER = "[?]"
_CACHE_DIR = os.path.join("audio_input", ".gemini_cache")
_TERMS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "vaishnava_terms.json")

_client = None


def _get_client():
    global _client
    if _client is None:
        from google import genai
        key = os.getenv("GEMINI_API_KEY", "")
        if not key:
            raise RuntimeError("GEMINI_API_KEY is not set")
        # timeout in ms — a hung request would otherwise block the recording
        _client = genai.Client(api_key=key, http_options={"timeout": 180_000})
    return _client


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


def _llm_piece(path: str, use_cache: bool = True, attempts: int = 3) -> str:
    from google.genai import types
    with open(path, "rb") as f:
        audio = f.read()
    tag = hashlib.sha1((LLM_MODEL + LLM_PROMPT).encode()).hexdigest()[:8]
    cache = os.path.join(_CACHE_DIR, f"llm-{tag}-{hashlib.sha1(audio).hexdigest()}.txt")
    if use_cache and os.path.exists(cache):
        with open(cache, encoding="utf-8") as f:
            return f.read()
    client = _get_client()
    for attempt in range(attempts):
        try:
            result = client.models.generate_content(
                model=LLM_MODEL,
                contents=[types.Part.from_bytes(data=audio, mime_type="audio/mpeg"), LLM_PROMPT],
                config=types.GenerateContentConfig(temperature=0),
            )
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


def gemini_stt(path: str, mode: str | None = None, use_cache: bool = True) -> tuple:
    """Transcribe a whole recording in ≤25-minute pieces."""
    from agents.transcription_agent import _to_mp3_16k, _split_audio
    mode = mode or os.getenv("GEMINI_ASR_MODE", "llm")
    piece_seconds = LLM_PIECE_SECONDS if mode == "llm" else PIECE_SECONDS
    print(f"[transcription] Gemini ({LLM_MODEL if mode == 'llm' else MODEL}, verbatim, {mode})...")
    pieces = _split_audio(_to_mp3_16k(path), max_sec=piece_seconds)

    texts, segments, gaps = [], [], 0
    for i, piece in enumerate(pieces):
        offset = i * piece_seconds
        try:
            if mode == "llm":
                text, phrases = _llm_piece(piece, use_cache=use_cache), []
            else:
                text, phrases = _transcribe_piece(piece, mode, offset, use_cache=use_cache)
            texts.append(text)
            segments.extend(phrases)
            print(f"  [gemini piece {i + 1}/{len(pieces)}] {len(text)} chars")
        except Exception as e:
            print(f"  [gemini piece {i + 1}/{len(pieces)}] FAILED after retries: {str(e)[:120]}")
            # Gemini is often briefly overloaded (503) — cover this piece with Sarvam
            # rather than leaving a hole in the transcript
            fallback = _sarvam_fallback(piece)
            if fallback:
                texts.append(fallback)
                print(f"  [gemini piece {i + 1}/{len(pieces)}] covered by Sarvam ({len(fallback)} chars)")
            else:
                gaps += 1
                texts.append(GAP_MARKER)

    full_text = " ".join(t for t in texts if t)
    print(f"[transcription] Gemini done ({len(full_text)} chars, {gaps} gap(s))")
    return full_text, "te", segments, gaps
