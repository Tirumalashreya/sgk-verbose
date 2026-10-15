"""
Script conversion for verses — one-to-one character mapping only, via
indic_transliteration. No interpretation, no filling in meaning. On failure,
returns the original text unchanged rather than guessing.

This wraps the conversion functions in verbatim.py (shared with the shloka
detector, which already calls them to attach a Devanagari/Tamil original to
each verified verse) under the name/signature this project's spec asks for.
"""
from agents.verbatim import devanagari_to_telugu, telugu_to_devanagari, telugu_to_iast


def transliterate_to_telugu(text: str, source: str = "devanagari") -> str:
    """Convert a Sanskrit (Devanagari) or already-Telugu-script verse to Telugu
    script. `source` is "devanagari" (default) or "telugu" (pass-through)."""
    if not text:
        return text
    if source == "telugu":
        return text
    result = devanagari_to_telugu(text)
    return result or text  # never fail silently into an empty verse


def transliterate_to_devanagari(text: str) -> str:
    result = telugu_to_devanagari(text)
    return result or text


def transliterate_to_roman(text: str) -> str:
    """IAST, for the Roman-script reading view."""
    result = telugu_to_iast(text)
    return result or text
