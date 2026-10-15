"""
Shared Vaishnava term list (names, places, Sanskrit/Tamil terms) from
data/vaishnava_terms.json. Used to bias Sarvam's keyterm list and to score
how much of a transcript's vocabulary matches known terms — a cheap signal
for "does this transcript look right", not a measure of word-for-word
correctness (only a human, or the two-listener/judge cross-check, can tell
that).
"""
import json
import os

_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "vaishnava_terms.json")
_cache: list[str] | None = None


def load_terms() -> list[str]:
    """Every term string in the dictionary, Telugu and Sanskrit, deduplicated."""
    global _cache
    if _cache is not None:
        return _cache
    try:
        with open(_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[term_dictionary] could not load {_PATH}: {e}")
        _cache = []
        return _cache
    terms: list[str] = []
    for key in ("telugu", "sanskrit", "tamil", "tamil_pasuram_phrases", "discourse_markers"):
        terms.extend(data.get(key, []))
    _cache = list(dict.fromkeys(t for t in terms if t))
    return _cache


def sarvam_keyterms(limit: int = 50, max_len: int = 64) -> list[str]:
    """Telugu + Sanskrit terms short enough for Sarvam's keyterm bias (API limits)."""
    return [t for t in load_terms() if len(t) <= max_len][:limit]


def term_fidelity(transcript: str) -> float:
    """Fraction of the dictionary's terms that appear somewhere in the transcript,
    scaled by how many distinct terms show up relative to the transcript's length.
    This is a rough "does this look like a Vaishnava discourse" score, used only
    as an extra signal — never to pick or reject transcript text."""
    terms = load_terms()
    if not terms or not transcript.strip():
        return 0.0
    hits = sum(1 for t in terms if t in transcript)
    # Normalise against a plausible hit count for a real discourse rather than
    # against len(terms), so a short clip isn't unfairly scored near zero.
    expected = max(3, len(transcript) // 400)
    return round(min(1.0, hits / expected), 3)
