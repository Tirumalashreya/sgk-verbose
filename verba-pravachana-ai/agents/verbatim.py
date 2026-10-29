"""
Shared helpers for verbatim handling. The shloka detector, formatter and
validator must all agree on what "the transcript" is, so every index they
exchange refers to normalize_ws(transcript).
"""
import re

_WS = re.compile(r"\s+")
# Quotes / punctuation the LLM tends to wrap around extracted verses
_EDGE_PUNCT = "\"'“”‘’«»`*()[]{}.,;:!?।॥-–— "

# Shloka line emitted by the formatter: **"<verse>"** optionally followed by (<devanagari>)
SHLOKA_LINE = re.compile(r'^\*\*"(.+?)"\*\*(?:\s*\(([^)]*)\))?$')


def normalize_ws(text: str) -> str:
    return _WS.sub(" ", text or "").strip()


def clean_verse(text: str) -> str:
    return normalize_ws(text).strip(_EDGE_PUNCT)


def find_all(haystack: str, needle: str) -> list[tuple[int, int]]:
    """All non-overlapping (start, end) spans of needle in haystack."""
    spans = []
    if not needle:
        return spans
    start = haystack.find(needle)
    while start != -1:
        spans.append((start, start + len(needle)))
        start = haystack.find(needle, start + len(needle))
    return spans


def expand_to_words(text: str, start: int, end: int) -> tuple[int, int]:
    """Grow a span to whole words (including attached punctuation) so cutting it
    out never splits a word. `text` must be whitespace-normalized."""
    while start > 0 and text[start - 1] != " ":
        start -= 1
    while end < len(text) and text[end] != " ":
        end += 1
    return start, end


_DEVANAGARI = re.compile(r"[\u0900-\u097F]")


def has_devanagari(text: str) -> bool:
    return bool(_DEVANAGARI.search(text or ""))


# Sound evidence for which language a Telugu-script verse is in. Tamil has no
# visarga, aspirated stops, శ/ష or vocalic ṛ; Tamil verses show its final
# consonants (-న్, -ల్, -ర్, -ళ్), ళ/ఱ and typical endings.
_SKT_STRONG = re.compile(r"ః|[ఖఘఛఝఠఢథధఫభశషఋౠ]|ృ|క్ష|జ్ఞ")
_SKT_WEAK = re.compile(r"(?:స్య|తే|ేయ|ాయ|ామి|తి|ాః)(?=\s|$|[.,।?!])|స్యే|్[కత]\s")
_TAMIL_CUES = re.compile(r"ళ|ఴ|ఱ|(?:న్|ల్|ర్|ళ్|ణ్)(?=\s|$|[.,?!])|ఆనై|ానై|ఏనే|ేనే|ఎంబెరుమాన్|అడియేన్|తిరు|ై(?=వ|ర|ల)")


def verse_script(text: str, llm_language: str = "") -> str:
    """'Sanskrit', 'Tamil' or 'unknown' — only 'Sanskrit' may be shown in Devanagari.
    The LLM's label alone is not trusted: it has called Tamil pasurams Sanskrit."""
    if has_devanagari(text):
        return "Sanskrit"
    strong, weak, tamil = (len(r.findall(text)) for r in (_SKT_STRONG, _SKT_WEAK, _TAMIL_CUES))
    says_sanskrit = "sanskrit" in (llm_language or "").lower()
    if says_sanskrit and tamil == 0 and strong + weak >= 1:
        return "Sanskrit"
    if strong >= 2 and strong > tamil:
        return "Sanskrit"
    if tamil > 0 and strong == 0:
        return "Tamil"
    if "tamil" in (llm_language or "").lower() and strong == 0:
        return "Tamil"
    return "unknown"


def devanagari_to_telugu(text: str) -> str:
    try:
        from indic_transliteration import sanscript
        from indic_transliteration.sanscript import transliterate
        return transliterate(text, sanscript.DEVANAGARI, sanscript.TELUGU)
    except Exception as e:
        print(f"[verbatim] telugu transliteration failed: {e}")
        return ""


def tamil_to_telugu(text: str) -> str:
    """A pasuram transcribed in genuine Tamil script (not spelled phonetically
    in Telugu, which is the more common case this project otherwise handles)
    — a reading line in Telugu script for a Telugu-reading audience."""
    try:
        from indic_transliteration import sanscript
        from indic_transliteration.sanscript import transliterate
        return transliterate(text, sanscript.TAMIL, sanscript.TELUGU)
    except Exception as e:
        print(f"[verbatim] tamil-to-telugu transliteration failed: {e}")
        return ""


def telugu_to_devanagari(text: str) -> str:
    """Script conversion only (same sounds, different script). Returns "" on failure."""
    try:
        from indic_transliteration import sanscript
        from indic_transliteration.sanscript import transliterate
        return transliterate(text, sanscript.TELUGU, sanscript.DEVANAGARI)
    except Exception as e:
        print(f"[verbatim] devanagari transliteration failed: {e}")
        return ""


def telugu_to_iast(text: str) -> str:
    try:
        from indic_transliteration import sanscript
        from indic_transliteration.sanscript import transliterate
        return transliterate(text, sanscript.TELUGU, sanscript.IAST)
    except Exception as e:
        print(f"[verbatim] IAST transliteration failed: {e}")
        return ""
