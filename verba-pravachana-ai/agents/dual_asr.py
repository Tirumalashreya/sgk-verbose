"""
Two-listener transcription: Sarvam (exact words) and Gemini (verses, names,
punctuation) each transcribe the same audio independently; disagreements are
settled by a judge that hears the audio and may only pick A or B.

  listener A  Sarvam saaras:v4 verbatim, 28 s pieces   — transcribes, nothing else
  listener B  Gemini (GEMINI_LLM_MODEL), 3 min pieces   — transcribes, nothing else
  comparer    code: word alignment                      — never chooses
  judge       Gemini with the 28 s audio of each disputed stretch — answers only
              "A", "B" or "?"; anything else counts as "?"

Agreed words, and spelling/spacing-only differences, are taken from B (it
carries punctuation). A "?" keeps B's words and is recorded, with both
versions, in the returned uncertain list for a reviewer.

Returns (text, language, segments, gap_count, report) — report has agreement,
judge decisions and uncertain spots.
"""
import difflib, hashlib, json, os, re
from concurrent.futures import ThreadPoolExecutor

SARVAM_PIECE_SECONDS = 28
_PUNCT = re.compile(r"[.,;:!?।॥\"'“”‘’()\[\]{}…—–-]+")
_FOLD = [("ం", "మ్"), ("ఁ", ""), ("ా", "ఆ"), ("ీ", "ఈ"), ("ూ", "ఊ"), ("ే", "ఏ"), ("ో", "ఓ"), ("ై", "ఐ"),
         ("ౌ", "ఔ"), ("ళ", "ల"), ("ణ", "న"), ("శ", "స"), ("ష", "స"), ("ఱ", "ర")]
_CACHE_DIR = os.path.join("audio_input", ".judge_cache")
JUDGE_PROMPT = (
    "You will hear a short clip from a Telugu spiritual discourse (with Sanskrit and Tamil verses). "
    "Two transcribers disagree about some phrases in it. For each numbered item, decide which "
    "version, A or B, matches what is actually spoken in the clip. The surrounding words are given "
    "for context. Answer ONLY with JSON mapping item numbers to \"A\", \"B\" or \"?\" (use \"?\" if "
    "neither matches or you are unsure), for example {\"1\": \"A\", \"2\": \"?\"}. Do not write any "
    "other text and never propose new words.\n\nItems:\n"
)


def _key(token: str) -> str:
    return _PUNCT.sub("", token)


def _fold(s: str) -> str:
    for a, b in _FOLD:
        s = s.replace(a, b)
    return re.sub(r"(.)\1+", r"\1", s.replace("్", ""))


def _same_words(a: list[str], b: list[str]) -> bool:
    """Same words up to spelling variants or word joining (no judge needed)."""
    from rapidfuzz.distance import Levenshtein
    if not (a and b):
        return False
    fa, fb = _fold("".join(map(_key, a))), _fold("".join(map(_key, b)))
    if fa == fb:
        return True
    # Near-matches only count for long stretches (verse spellings); in a short
    # word one letter can change the meaning (అడిగాడు "he asked" / అడిగారు "they asked")
    return min(len(fa), len(fb)) >= 12 and Levenshtein.normalized_similarity(fa, fb) >= 0.9


def _slots_line_up(a: list[str], b: list[str]) -> bool:
    """True when each word pair plausibly fills the same slot (not shifted by a join)."""
    from rapidfuzz.distance import Levenshtein
    return all(Levenshtein.normalized_similarity(_fold(_key(x)), _fold(_key(y))) >= 0.5 for x, y in zip(a, b))


def align(a_tokens: list[str], a_chunk: list[int], b_tokens: list[str]) -> list[dict]:
    """Ops over B's tokens: keep spans, and disputes carrying the Sarvam chunk they fall in."""
    ka = [_key(t) for t in a_tokens]
    kb = [_key(t) for t in b_tokens]
    ops = []

    def add(a1, a2, b1, b2):
        if _same_words(a_tokens[a1:a2], b_tokens[b1:b2]):
            ops.append({"keep": b_tokens[b1:b2]})
        else:
            chunk = a_chunk[min(a1, len(a_chunk) - 1)] if a_chunk else 0
            ops.append({"a": a_tokens[a1:a2], "b": b_tokens[b1:b2], "chunk": chunk,
                        "before": " ".join(b_tokens[max(0, b1 - 5):b1]), "after": " ".join(b_tokens[b2:b2 + 5])})

    for op, a1, a2, b1, b2 in difflib.SequenceMatcher(a=ka, b=kb, autojunk=False).get_opcodes():
        if op == "equal":
            ops.append({"keep": b_tokens[b1:b2]})
        elif op == "replace" and a2 - a1 == b2 - b1 and _slots_line_up(a_tokens[a1:a2], b_tokens[b1:b2]):
            # Same number of words, word for word: judge each word on its own, so
            # one real difference can't hide inside a stretch that is mostly spelling
            for i in range(a2 - a1):
                add(a1 + i, a1 + i + 1, b1 + i, b1 + i + 1)
        else:
            add(a1, a2, b1, b2)
    return ops


def _judge_chunk(audio_path: str, items: list[dict], model: str) -> dict:
    """Ask Gemini, with the chunk's audio, to pick A or B for each item."""
    lines = [f'{i}. …{it["before"]} [A: {" ".join(it["a"]) or "(nothing)"} | B: {" ".join(it["b"]) or "(nothing)"}] {it["after"]}…'
             for i, it in enumerate(items, 1)]
    prompt = JUDGE_PROMPT + "\n".join(lines)
    with open(audio_path, "rb") as f:
        audio = f.read()
    cache = os.path.join(_CACHE_DIR, hashlib.sha1(audio + prompt.encode() + model.encode()).hexdigest() + ".json")
    if os.path.exists(cache) and os.path.getsize(cache) > 0:
        with open(cache, encoding="utf-8") as f:
            return json.load(f)
    from google.genai import types
    from agents.gemini_asr import _get_client
    raw = {}
    try:
        r = _get_client().models.generate_content(
            model=model, contents=[types.Part.from_bytes(data=audio, mime_type="audio/mpeg"), prompt],
            config=types.GenerateContentConfig(temperature=0, response_mime_type="application/json"))
        raw = json.loads(r.text or "{}")
    except Exception as e:
        print(f"  [judge] chunk failed, leaving its disputes unresolved: {str(e)[:100]}")
        return {}
    # The judge may only answer A, B or ? — anything else is treated as ?
    answers = {str(k): (v if v in ("A", "B") else "?") for k, v in raw.items() if isinstance(v, str)}
    os.makedirs(_CACHE_DIR, exist_ok=True)
    with open(cache, "w", encoding="utf-8") as f:
        json.dump(answers, f)
    return answers


def merge(ops: list[dict], decisions: dict[int, str]) -> tuple[list[str], list[dict]]:
    """Build the final token list; decisions maps dispute index → A/B/?."""
    out, uncertain, d = [], [], 0
    for op in ops:
        if "keep" in op:
            out.extend(op["keep"])
            continue
        choice = decisions.get(d, "?")
        out.extend(op["a"] if choice == "A" else op["b"])
        if choice == "?":
            uncertain.append({"sarvam": " ".join(op["a"]), "gemini": " ".join(op["b"]),
                              "context": f'{op["before"]} … {op["after"]}', "chunk": op["chunk"]})
        d += 1
    return out, uncertain


def dual_stt(path: str) -> tuple:
    from agents import transcription_agent as ta
    from agents import gemini_asr as g
    print("[transcription] two listeners: Sarvam V4 verbatim + Gemini...")
    mp3 = ta._to_mp3_16k(path)
    chunks = ta._split_audio(mp3, max_sec=SARVAM_PIECE_SECONDS)
    settings = ta.sarvam_settings("saaras:v4", "verbatim", True)

    def sarvam_side():
        with ThreadPoolExecutor(max_workers=min(5, len(chunks))) as ex:
            return list(ex.map(lambda ic: ta._sarvam_transcribe_chunk((ic[0], ic[1], settings))[1], enumerate(chunks)))

    with ThreadPoolExecutor(max_workers=2) as ex:
        fa, fb = ex.submit(sarvam_side), ex.submit(g.gemini_stt, path, "llm")
        errors = {}
        try:
            a_texts = fa.result()
        except Exception as e:
            a_texts, errors["sarvam"] = None, str(e)[:150]
        try:
            b_text, _, _, b_gaps = fb.result()
        except Exception as e:
            b_text, b_gaps, errors["gemini"] = None, 0, str(e)[:150]

    # One listener down: carry on with the other, and say so
    if a_texts is None and b_text is None:
        raise RuntimeError(f"both listeners failed: {errors}")
    if a_texts is None or b_text is None:
        only = "Gemini" if a_texts is None else "Sarvam"
        print(f"[transcription] single listener only ({only}); other failed: {errors}")
        text = b_text if a_texts is None else " ".join(t for t in a_texts if t)
        return text, "te", [], b_gaps if a_texts is None else 0, {"listeners": [only.lower()], "errors": errors}

    a_tokens, a_chunk = [], []
    for i, t in enumerate(a_texts):
        for tok in t.split():
            a_tokens.append(tok)
            a_chunk.append(i)
    b_tokens = b_text.split()
    ops = align(a_tokens, a_chunk, b_tokens)
    disputes = [op for op in ops if "keep" not in op]
    agreed = sum(len(op["keep"]) for op in ops if "keep" in op)
    print(f"[transcription] listeners agree on {agreed}/{len(b_tokens)} words; {len(disputes)} dispute(s) for the judge")

    # One judge call per Sarvam chunk that has disputes, in parallel
    by_chunk = {}
    for idx, op in enumerate(disputes):
        by_chunk.setdefault(op["chunk"], []).append(idx)
    decisions = {}

    def judge(item):
        chunk, idxs = item
        answers = _judge_chunk(chunks[chunk], [disputes[i] for i in idxs], g.LLM_MODEL)
        return {i: answers.get(str(n), "?") for n, i in enumerate(idxs, 1)}

    with ThreadPoolExecutor(max_workers=5) as ex:
        for part in ex.map(judge, by_chunk.items()):
            decisions.update(part)

    tokens, uncertain = merge(ops, decisions)
    counts = {c: list(decisions.values()).count(c) for c in ("A", "B", "?")}
    print(f"[transcription] judge: Sarvam {counts['A']}, Gemini {counts['B']}, unresolved {counts['?']}")
    report = {"listeners": ["sarvam", "gemini"], "agreement": round(agreed / max(len(b_tokens), 1), 3),
              "disputes": len(disputes), "judge": counts, "uncertain": uncertain}
    # No segments: Sarvam's 28 s pieces run back to back, so they carry no pause information
    return " ".join(tokens), "te", [], b_gaps, report
