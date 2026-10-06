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


def devanagari_to_telugu(text: str) -> str:
    try:
        from indic_transliteration import sanscript
        from indic_transliteration.sanscript import transliterate
        return transliterate(text, sanscript.DEVANAGARI, sanscript.TELUGU)
    except Exception as e:
        print(f"[verbatim] telugu transliteration failed: {e}")
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
