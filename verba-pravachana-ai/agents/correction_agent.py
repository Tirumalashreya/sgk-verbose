from graph.state import VerbaState
import json, os, re
from agents.groq_llm_client import call as _groq_call, STRONG_MODEL

# Deterministic fixes for Tamil/Sanskrit proper nouns Sarvam consistently misreads.
# Format: (sarvam_pattern, correct_telugu, tamil_or_sanskrit_original)
# The original goes in brackets after the Telugu: "ఆళ్వార్ (ஆழ்வார்)"
_TERM_FIXES = [
    # Alwar titles
    (r'తొండలడి\s*పొడి\s*ఆడు', 'తొండరడిప్పొడి ఆళ్వార్ (தொண்டரடிப்பொடி ஆழ்வார்)'),
    (r'తొండరడి\s*పొడి\s*అడు', 'తొండరడిప్పొడి ఆళ్వార్ (தொண்டரடிப்பொடி ஆழ்வார்)'),
    (r'\bఆడు\b(?=\s+రోజు|\s+సేవ)', 'ఆళ్వార్ (ஆழ்வார்)'),
    (r'\bఅడు\b(?=\s+రోజు|\s+సేవ)', 'ఆళ్వార్ (ஆழ்வார்)'),
    # Prabandham names
    (r'తిరుప్పడి\s*అడిచి', 'తిరుపళ్ళియెళుచ్చి (திருப்பள்ளியெழுச்சி)'),
    (r'తిరుమాలై\s*అరియాలై', 'తిరుమాలై అరియాద (திருமாலை அறியாத)'),
    (r'పెరుమాల్\s*పెరియా', 'పెరుమాళ్ళ పెరియ (பெருமாள் பெரிய)'),
    # Common Perumal forms
    (r'\bపెరుమాల్\b', 'పెరుమాళ్ళ (பெருமாள்)'),
    (r'\bపెరుమాల\b(?!ళ)', 'పెరుమాళ్ళ (பெருமாள்)'),
    # Acharya names
    (r'పెరియవార్చాన్\s*పిల్ల\b', 'పెరియవాచ్చాన్ పిళ్ళై (பெரியவாச்சான் பிள்ளை)'),
    (r'పెరివాచ్చాన్\s*పిల్లై', 'పెరియవాచ్చాన్ పిళ్ళై (பெரியவாச்சான் பிள்ளை)'),
    # Vipranarayana
    (r'విప్రనారాయణుడు', 'విప్రనారాయణుడు (విప్రనారాయణ)'),
]


def _apply_term_fixes(text: str) -> str:
    for pattern, replacement in _TERM_FIXES:
        text = re.sub(pattern, replacement, text)
    return text

def _call(prompt):
    return _groq_call(prompt, api_key_env="GROQ_API_KEY_CORRECTION", model=STRONG_MODEL)
from dotenv import load_dotenv
load_dotenv()

_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "vaishnava_terms.json")

def _load_terms():
    try:
        with open(_DATA_PATH, encoding="utf-8") as f:
            data = json.load(f)
        terms = []
        for key in ("telugu", "tamil", "sanskrit"):
            terms.extend(data.get(key, []))
        return terms
    except Exception as e:
        print(f"[correction] could not load terms: {e}")
        return []

_TERMS = _load_terms()
_TERMS_TEXT = "\n".join(_TERMS[:200])


def correction_agent(state: VerbaState) -> VerbaState:
    transcript = state.get("transcript", "")

    if not transcript or len(transcript.strip()) < 10:
        print("[correction] skipping — no transcript")
        return state

    # Always apply deterministic Tamil/Sanskrit term fixes (no LLM, no rate limits)
    fixed = _apply_term_fixes(transcript)
    if fixed != transcript:
        print(f"[correction] applied {sum(1 for a,b in zip(transcript,fixed) if a!=b)} term fixes")
        transcript = fixed
        state["transcript"] = transcript

    # Skip LLM correction for long transcripts — Sarvam quality is good enough
    if len(transcript) > 5000:
        print(f"[correction] skipping LLM correction — transcript too long ({len(transcript)} chars)")
        return state

    print(f"[correction] correcting transcript ({len(transcript)} chars)...")

    prompt = f"""You are correcting ASR transcription errors in a Sri Vaishnava spiritual discourse.
The speaker alternates between Telugu explanation, Tamil pasurams, and Sanskrit shlokas.

KNOWN CORRECT TERMS — use these exact spellings when the ASR has mangled them:
{_TERMS_TEXT}

RULES:
1. Preserve EVERY sentence — do not skip, summarize, or paraphrase anything
2. Correct only clear ASR mistakes: wrong phonetics, garbled words, obvious errors
3. Telugu must remain Telugu, Tamil must remain Tamil, Sanskrit must remain Sanskrit
4. Do NOT translate between languages
5. Preserve all line breaks and paragraph structure
6. If unsure whether something is an error, leave it as-is
7. Return ONLY the corrected transcript — no explanations, no labels

RAW TRANSCRIPT:
{transcript}"""

    corrected = _call(prompt)

    if corrected and len(corrected) > 10:
        print(f"[correction] done ({len(transcript)} → {len(corrected)} chars)")
        state["transcript"] = corrected
    else:
        print("[correction] correction returned empty — keeping original transcript")

    return state
