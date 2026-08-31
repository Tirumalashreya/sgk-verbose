from graph.state import VerbaState
import json, re
from agents.groq_llm_client import call as _groq_call, STRONG_MODEL
from agents.text_chunker import chunk_text
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
    chunks = chunk_text(transcript, chunk_size=3000, overlap=200)
    print(f"[shloka_detect] processing {len(chunks)} chunk(s)")

    all_raw = []
    seen_texts = set()
    for i, chunk in enumerate(chunks):
        raw = _detect_in_chunk(chunk)
        for s in raw:
            key = (s.get("text", "") or "")[:60]
            if key not in seen_texts:
                seen_texts.add(key)
                all_raw.append(s)

    shlokas = []
    for s in all_raw:
        text = s.get("text", "")
        lang = s.get("language", "")
        conf = float(s.get("confidence", 0.0))
        passed = _is_valid_shloka(text, lang, conf)
        print(f"  shloka filter: lang={lang!r} conf={conf} passed={passed} text={text[:40]!r}")
        if passed:
            shlokas.append(s)

    print(f"[shloka_detect] done — {len(all_raw)} detected, {len(shlokas)} passed filter")
    return {"shlokas": shlokas}


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

HOW TO IDENTIFY WHERE A SHLOKA ENDS (CRITICAL):
- The shloka ends at the last Sanskrit/Tamil word before Telugu explanation resumes
- Telugu explanation markers that signal the verse is OVER: కదండీ, అంటే, అని, అంటారు, చేస్తున్నారు, చెప్పారు, వెళ్ళారు, అయ్యా, రోజు, గనుక, మనం, మనకి, మనకు, ఆయన, వాళ్ళు
- STOP the shloka text the moment you see Telugu conversational words — do NOT include them

EXAMPLE — correct boundary:
  Transcript: "పచ్చేవామలైహోల్మేని పవడవాయి కమలచ్చంగన్ అచ్యుతా అమరర్యేరే ఆ ఎర్రం కొడుందే అన్నం తొండలడి పొడి ఆడు రోజు సేవకాలం చేస్తున్నారు"
  CORRECT shloka text: "పచ్చేవామలైహోల్మేని పవడవాయి కమలచ్చంగన్ అచ్యుతా అమరర్యేరే ఆ ఎర్రం కొడుందే"
  WRONG (includes Telugu): "పచ్చేవామలైహోల్మేని ... అన్నం తొండలడి పొడి ఆడు రోజు సేవకాలం చేస్తున్నారు"

RULES:
- Text must appear word-for-word in the transcript (Telugu script transliteration of the verse)
- Do NOT add anything from your training knowledge
- Cut off the shloka BEFORE Telugu explanation begins
- If nothing qualifies, return empty array

Return ONLY JSON:
{{"shlokas": [{{"language": "Tamil", "text": "<verse only — no Telugu explanation>", "original": "<verse in original Tamil/Devanagari script>", "type": "Paasuram", "confidence": 0.9}}]}}

For "original" field:
- If Tamil pasuram: write it in Tamil script (தமிழ்)
- If Sanskrit shloka: write it in Devanagari script (देवनागरी)

TRANSCRIPT:
{transcript}"""
