from graph.state import VerbaState
import json, re
from agents.groq_llm_client import call as _groq_call, parallel_map, STRONG_MODEL
from agents.text_chunker import chunk_text
from agents.verbatim import (normalize_ws, clean_verse, find_all, expand_to_words, verse_script,
                             has_devanagari)
from agents.transliteration_agent import transliterate_to_telugu, transliterate_to_devanagari
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
    print(f"[shloka_detect] done — {len(all_raw)} detected, {len(shlokas)} verified")
    return {"shlokas": shlokas}


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
            s.update({"language": "Tamil", "type": "Paasuram", "script_certain": True,
                      "original": verse_library.original_line(m), "reference": verse_library.reference(m)})

    taken = [(a, b) for s in shlokas for a, b in s["occurrences"]]
    for m in verse_library.find_pasurams(norm_transcript):
        if any(a < m["end"] and m["start"] < b for a, b in taken):
            continue
        text = norm_transcript[m["start"]:m["end"]]
        spans = find_all(norm_transcript, text)
        print(f"  pasuram found by library (missed by LLM): #{m['number']} score {m['score']}: {text[:40]!r}")
        shlokas.append({
            "language": "Tamil", "llm_language": None, "script_certain": True, "type": "Paasuram",
            "text": text, "original": verse_library.original_line(m), "reference": verse_library.reference(m),
            "confidence": m["score"] / 100, "verified": True, "found_by": "library",
            "start_index": spans[0][0], "end_index": spans[0][1], "occurrences": [list(sp) for sp in spans],
        })
        taken.extend(spans)
    return sorted(shlokas, key=lambda s: s["start_index"])


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
