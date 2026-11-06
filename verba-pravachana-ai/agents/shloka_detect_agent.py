from graph.state import VerbaState
import json, re
from agents.groq_llm_client import call as _groq_call, parallel_map, STRONG_MODEL
from agents.text_chunker import chunk_text
from agents.verbatim import (normalize_ws, clean_verse, find_all, expand_to_words, verse_script,
                             has_devanagari)
from agents.transliteration_agent import transliterate_to_telugu, transliterate_to_devanagari

_TAMIL_VERSE_MIN_CHARS = 18   # a recited verse runs long; ignore a stray Tamil name/word
from agents import verse_library
from dotenv import load_dotenv
load_dotenv()

_DEVANAGARI = re.compile(r'[ऀ-ॿ]')
_TAMIL      = re.compile(r'[஀-௿]')
_TELUGU     = re.compile(r'[ఀ-౿]')

def _is_valid_shloka(text: str, language: str = "", confidence: float = 0.0) -> bool:
    if not text or len(text) < 5:
        return False
    lang_lower = language.lower()
    is_tamil_or_sanskrit = any(k in lang_lower for k in ("tamil", "sanskrit", "pasuram", "paasuram"))
    if not is_tamil_or_sanskrit:
        return False
    return confidence >= 0.5

def _call(prompt):
    result = _groq_call(prompt, api_key_env="GROQ_API_KEY_SHLOKA", model=STRONG_MODEL)
    return result if result else '{"shlokas": []}'

def _detect_in_chunk(chunk_text_str: str) -> list:
    prompt = _build_prompt(chunk_text_str)
    text = _call(prompt)
    text = re.sub(r'```(?:json)?', '', text).strip()
    try:
        result = json.loads(text)
        if isinstance(result, dict):
            return result.get("shlokas", [])
        elif isinstance(result, list):
            return result
    except (json.JSONDecodeError, TypeError):
        pass
    return []

def shloka_detect_agent(state: VerbaState) -> VerbaState:
    if state.get("live_piece"):
        # One minute of a recording still in progress: a verse can straddle two
        # pieces, so this only ever sees a false partial view of it. The whole
        # recording is detected once, correctly, when it stops.
        return {"shlokas": []}
    print("[shloka_detect] starting...")
    transcript = state.get("transcript", "") or ""
    norm_transcript = normalize_ws(transcript)
    chunks = chunk_text(transcript, chunk_size=3000, overlap=200)
    print(f"[shloka_detect] processing {len(chunks)} chunk(s)")

    all_raw = []
    seen_texts = set()
    for raw in parallel_map(_detect_in_chunk, chunks):
        for s in raw:
            if not isinstance(s, dict):
                continue
            key = clean_verse(s.get("text", "") or "")
            if key and key not in seen_texts:
                seen_texts.add(key)
                all_raw.append(s)

    shlokas = []
    for s in all_raw:
        text = clean_verse(s.get("text", "") or "")
        lang = s.get("language", "") or ""
        try:
            conf = float(s.get("confidence", 0.0))
        except (TypeError, ValueError):
            conf = 0.0
        passed = _is_valid_shloka(text, lang, conf)
        # Verbatim check: the LLM may only select text, never produce it
        spans = find_all(norm_transcript, text) if passed else []
        if passed and not spans:
            print(f"  shloka REJECTED (not verbatim in transcript): {text[:40]!r}")
            continue
        print(f"  shloka filter: lang={lang!r} conf={conf} passed={passed} occurrences={len(spans)} text={text[:40]!r}")
        if not passed:
            continue
        # LLM boundaries often stop mid-word or before attached punctuation —
        # widen to whole words so the notes never split a word
        a, b = expand_to_words(norm_transcript, *spans[0])
        text = norm_transcript[a:b]
        spans = find_all(norm_transcript, text)
        # Never show a script we are not sure of: a missing second line is
        # better than a Tamil pasuram rendered in Devanagari
        script = verse_script(text, lang)
        if has_devanagari(text):
            # Sarvam already wrote this verse in Devanagari — show Telugu script as the second line
            original = transliterate_to_telugu(text)
        elif script == "Sanskrit":
            # Telugu-script Sanskrit → Devanagari (same sounds, different script)
            original = transliterate_to_devanagari(text)
        else:
            # Tamil: Telugu→Tamil script is lossy; unknown: don't guess
            original = ""
        if script != "unknown" and script.lower() not in lang.lower():
            print(f"  shloka relabelled {lang!r} → {script!r} from its sounds: {text[:40]!r}")
        shlokas.append({
            "language": script if script != "unknown" else lang,
            "llm_language": lang,
            "script_certain": script != "unknown",
            "type": "Shloka" if script == "Sanskrit" else "Paasuram" if script == "Tamil" else (s.get("type") or "Shloka"),
            "text": text,
            "original": original,
            "confidence": conf,
            "verified": True,
            "start_index": spans[0][0],
            "end_index": spans[0][1],
            "occurrences": [list(sp) for sp in spans],
        })

    shlokas = _verify_with_library(norm_transcript, shlokas)
    native = _native_tamil_candidates(norm_transcript, [sp for s in shlokas for sp in s["occurrences"]])
    if native:
        print(f"  {len(native)} verse(s) found written in real Tamil script (missed the LLM pass — "
              f"its prompt assumes Tamil is spelled phonetically in Telugu, which this wasn't)")
    shlokas = sorted(shlokas + native, key=lambda s: s["start_index"])

    # Detect inline Sri Vaishnava Tamil & Sanskrit terms outside full verses
    from agents.inline_terms import detect_inline_terms
    inline = detect_inline_terms(norm_transcript, shlokas)
    if inline:
        print(f"  {len(inline)} inline term(s) tagged (Tamil/Sanskrit vocabulary outside recited verses)")
        shlokas = sorted(shlokas + inline, key=lambda s: s["start_index"])

    print(f"[shloka_detect] done — {len(all_raw)} detected, {len(shlokas)} verified")
    return {"shlokas": shlokas}


_REALIGN_PAD_WORDS = 4   # how far past the LLM's own guessed edges to look
_REALIGN_MIN_SCORE = 70  # below this, keep the LLM's original span rather than risk a worse one


def _realign_to_library(norm_transcript: str, start: int, end: int, lib_text: str) -> tuple[int, int]:
    """The LLM has to judge where Tamil/Sanskrit words end and Telugu
    narration begins by meaning alone (both are written in the same Telugu
    script here) — real recordings showed it drawing that line one word off,
    on either edge, independently. Once a verse is confirmed against the
    library, use the library's own (correct) wording to re-find the exact
    boundary by sound, instead of trusting the LLM's guessed edges: search
    every word-aligned substring in a small window around the original span
    and keep whichever one sounds most like the verified line. Falls back to
    the original span untouched if nothing in the window sounds close
    enough — never guesses past what it can verify."""
    from rapidfuzz import fuzz
    words = [(m.start(), m.end()) for m in re.finditer(r"\S+", norm_transcript)]
    in_range = [i for i, (a, b) in enumerate(words) if b > start and a < end]
    if not in_range:
        return start, end
    lo = max(0, in_range[0] - _REALIGN_PAD_WORDS)
    hi = min(len(words) - 1, in_range[-1] + _REALIGN_PAD_WORDS)
    lib_skel = verse_library.skeleton(lib_text, "tamil")
    best = None
    for i in range(lo, hi + 1):
        for j in range(i, hi + 1):
            cand = norm_transcript[words[i][0]:words[j][1]]
            score = fuzz.ratio(verse_library.skeleton(cand), lib_skel)
            if best is None or score > best[0]:
                best = (score, words[i][0], words[j][1])
    if best is None or best[0] < _REALIGN_MIN_SCORE:
        return start, end
    return best[1], best[2]


def _verify_with_library(norm_transcript: str, shlokas: list) -> list:
    """Attach the verified Tamil original to pasurams found in the Divya
    Prabandham, and add pasurams the LLM missed. The spoken text itself is
    never changed — the source text only fills the second line."""
    for s in shlokas:
        if s["language"] == "Sanskrit" and s.get("script_certain"):
            continue
        m = verse_library.match_verse(s["text"])
        if m:
            print(f"  shloka matched to Divya Prabandham #{m['number']} (score {m['score']}): {s['text'][:40]!r}")
            new_start, new_end = _realign_to_library(norm_transcript, s["start_index"], s["end_index"], m["lines"][0])
            if (new_start, new_end) != (s["start_index"], s["end_index"]):
                new_text = norm_transcript[new_start:new_end]
                print(f"  boundary corrected to match the verified line: {new_text!r}")
                s["text"] = new_text
                s["start_index"], s["end_index"] = new_start, new_end
                s["occurrences"] = [[new_start, new_end]]
            s.update({"language": "Tamil", "type": "Paasuram", "script_certain": True,
                      "original": verse_library.original_line(m), "reference": verse_library.reference(m)})

    taken = [(a, b) for s in shlokas for a, b in s["occurrences"]]
    for m in verse_library.find_pasurams(norm_transcript):
        if any(a < m["end"] and m["start"] < b for a, b in taken):
            continue
        # find_pasurams's own window-sliding match has the same edge-drift as
        # the LLM candidates above (it's matching skeleton n-grams, not whole
        # words) — re-tighten the same way.
        new_start, new_end = _realign_to_library(norm_transcript, m["start"], m["end"], m["lines"][0])
        text = norm_transcript[new_start:new_end]
        spans = find_all(norm_transcript, text)
        if not spans:
            continue
        print(f"  pasuram found by library (missed by LLM): #{m['number']} score {m['score']}: {text[:40]!r}")
        shlokas.append({
            "language": "Tamil", "llm_language": None, "script_certain": True, "type": "Paasuram",
            "text": text, "original": verse_library.original_line(m), "reference": verse_library.reference(m),
            "confidence": m["score"] / 100, "verified": True, "found_by": "library",
            "start_index": spans[0][0], "end_index": spans[0][1], "occurrences": [list(sp) for sp in spans],
        })
        taken.extend(spans)
    return sorted(shlokas, key=lambda s: s["start_index"])


def _native_tamil_candidates(norm_transcript: str, taken: list) -> list:
    """Spoken Tamil that the ASR wrote in real Tamil script, not spelled out
    phonetically in Telugu, never matches what the LLM prompt above assumes
    ("both are written in Telugu script here") — so a genuine pasuram can sit
    in the transcript, correctly transcribed, and simply never get looked at.
    Catching it needs no model: a long run of real Tamil Unicode already IS
    the verse. We only verify it (a Divya Prabandham match when there is one)
    and give it a Telugu reading line — the same courtesy every other verse
    in these notes gets."""
    taken = list(taken)
    out = []
    for m in re.finditer(r'[஀-௿][஀-௿\s.,?!।॥]*[஀-௿]', norm_transcript):
        a, b = expand_to_words(norm_transcript, m.start(), m.end())
        text = norm_transcript[a:b]
        if len(text) < _TAMIL_VERSE_MIN_CHARS or any(x < b and a < y for x, y in taken):
            continue
        spans = find_all(norm_transcript, text)
        if not spans:
            continue
        lib = verse_library.match_verse(text)
        out.append({
            "language": "Tamil", "llm_language": None, "script_certain": True, "type": "Paasuram",
            "text": text,
            "original": transliterate_to_telugu(text, source="tamil"),
            "reference": verse_library.reference(lib) if lib else None,
            "confidence": max(0.95, lib["score"] / 100) if lib else 0.95,
            "verified": True, "found_by": "native_script",
            "start_index": spans[0][0], "end_index": spans[0][1], "occurrences": [list(sp) for sp in spans],
        })
        taken.extend(spans)
    return out


def _build_prompt(transcript: str) -> str:
    return f"""You detect Sanskrit shlokas and Tamil pasurams in Telugu spiritual discourse transcripts.

The speaker alternates between:
1. RECITING a Sanskrit shloka or Tamil pasuram (the verse itself)
2. EXPLAINING it in Telugu (narration, story, meaning)

Your job: extract ONLY the actual verse text — NOT the Telugu explanation that follows.

HOW TO IDENTIFY WHERE A SHLOKA STARTS:
- Speaker shifts from Telugu to Sanskrit/Tamil words mid-sentence
- Compound words with Sanskrit endings: -చ, -స్య, -ణ, -స్చ, -ణాం, -మ్
- Tamil pasuram words: పోల్, మేని, పవళ, కమల, అచ్చుత, అమరర్, కొళుందే, తిరు-

TELLING TAMIL FROM SANSKRIT (both are written in Telugu script here — label carefully):
- Tamil: words ending in a consonant (-న్, -ల్, -ర్, -ళ్, -ణ్), ళ / ఱ, endings like -ఆనై, -ఏనే, -ఆరే,
  doubled consonants (త్త, ట్ట, క్క, ప్ప), Divya Desam / Alwar names (తిరువల్లిక్కేణి, తిరువరంగం, ఎంబెరుమాన్, అడియేన్)
- Sanskrit: visarga ః, aspirated letters (ఖ ఘ థ ధ భ), శ / ష, endings like -స్య, -తే, -ాయ
- Example Tamil pasuram line (Tiruppavai): "మార్గళి త్తింగళ్ మది నిఱైంద నన్నాళాల్" → language "Tamil"
- A Tamil pasuram is NEVER "Sanskrit", even if it contains Sanskrit-derived words

HOW TO IDENTIFY WHERE A SHLOKA ENDS (CRITICAL):
- The shloka ends at the last Sanskrit/Tamil word before Telugu explanation resumes
- Telugu explanation markers that signal the verse is OVER: కదండీ, అంటే, అని, అంటారు, చేస్తున్నారు, చెప్పారు, వెళ్ళారు, అయ్యా, రోజు, గనుక, మనం, మనకి, మనకు, ఆయన, వాళ్ళు
- STOP the shloka text the moment you see Telugu conversational words — do NOT include them

EXAMPLE — correct boundary:
  Transcript: "పచ్చేవామలైహోల్మేని పవడవాయి కమలచ్చంగన్ అచ్యుతా అమరర్యేరే ఆ ఎర్రం కొడుందే అన్నం తొండలడి పొడి ఆడు రోజు సేవకాలం చేస్తున్నారు"
  CORRECT shloka text: "పచ్చేవామలైహోల్మేని పవడవాయి కమలచ్చంగన్ అచ్యుతా అమరర్యేరే ఆ ఎర్రం కొడుందే"
  WRONG (includes Telugu): "పచ్చేవామలైహోల్మేని ... అన్నం తొండలడి పొడి ఆడు రోజు సేవకాలం చేస్తున్నారు"

RULES:
- Copy the verse EXACTLY as it appears in the transcript — same spelling, same words, same spacing
- Do NOT correct, normalize, complete, or "fix" the verse, even if you know the canonical version
- Any text that is not an exact substring of the transcript will be discarded
- Do NOT add anything from your training knowledge
- Cut off the shloka BEFORE Telugu explanation begins
- If nothing qualifies, return empty array

Return ONLY JSON:
{{"shlokas": [{{"language": "Tamil", "text": "<verse only, copied exactly from the transcript>", "type": "Paasuram", "confidence": 0.9}}]}}

"language" must be "Sanskrit" or "Tamil". "type" must be "Shloka" (Sanskrit) or "Paasuram" (Tamil).

TRANSCRIPT:
{transcript}"""
