"""
Finds known Tamil pasurams in a Telugu-script transcript and returns the
verified Tamil original for each one.

Both sides are reduced to a "sound skeleton": romanized, with the distinctions
Tamil script does not write (k/g, t/d, p/b, aspiration, long/short vowels,
doubled consonants, the three n's, l/ḷ/ḻ, r/ṟ) folded together. A transcript
window that is close enough to a pasuram line is a match.

The library is built by scripts/build_verse_library.py (Project Madurai text).
Without it, find_pasurams() simply returns nothing.
"""
import json, os, re
from functools import lru_cache

LIBRARY = os.path.join(os.path.dirname(__file__), "..", "data", "verse_library", "divya_prabandham.json")
MIN_SCORE = 82        # partial_ratio on skeletons; unrelated lines score ~40–60
MIN_LINE_SKELETON = 14
MIN_MATCH_SKELETON = 20   # shorter matches happen by chance among 4,000 pasurams

# Tamil-origin words used all the time in Telugu Vaishnava talks. Their Tamil
# letters (ళ, final -ర్...) are not evidence that a pasuram is being recited.
_EVERYDAY_TAMIL_WORDS = re.compile(r"ఆళ్వా[రర్]\S*|పెరుమా[ళల]\S*|తిరుమల\S*|తిరుపతి\S*|తిరునక్షత్ర\S*")
NGRAM = 5

_FOLD = [("ḻ", "l"), ("ḷ", "l"), ("ṟ", "r"), ("ṉ", "n"), ("ṇ", "n"), ("ñ", "n"), ("ṅ", "n"), ("ṃ", "n"),
         ("ḥ", ""), ("ś", "s"), ("ṣ", "s"), ("ā", "a"), ("ī", "i"), ("ū", "u"), ("ē", "e"), ("ō", "o"),
         ("ṛ", "ri"), ("ṭ", "t"), ("ḍ", "t"), ("kh", "k"), ("gh", "k"), ("ch", "c"), ("jh", "c"), ("th", "t"),
         ("dh", "t"), ("ph", "p"), ("bh", "p"), ("g", "k"), ("j", "c"), ("d", "t"), ("b", "p")]


def skeleton(text: str, script: str = "telugu") -> str:
    from indic_transliteration import sanscript
    from indic_transliteration.sanscript import transliterate
    src = sanscript.TAMIL if script == "tamil" else sanscript.TELUGU
    s = transliterate(text, src, sanscript.IAST).lower()
    for a, b in _FOLD:
        s = s.replace(a, b)
    s = re.sub(r"[^a-z]", "", s)
    return re.sub(r"(.)\1+", r"\1", s)


@lru_cache(maxsize=1)
def _index():
    if not os.path.exists(LIBRARY):
        return None
    with open(LIBRARY, encoding="utf-8") as f:
        verses = json.load(f)["verses"]
    lines, grams = [], {}
    for v in verses:
        for li, text in enumerate(v["lines"]):
            sk = skeleton(text, "tamil")
            if len(sk) < MIN_LINE_SKELETON:
                continue
            lid = len(lines)
            lines.append({"verse": v, "line": li, "text": text, "skel": sk})
            for g in {sk[i:i + NGRAM] for i in range(len(sk) - NGRAM + 1)}:
                grams.setdefault(g, []).append(lid)
    return lines, grams


def find_pasurams(norm_transcript: str) -> list[dict]:
    """Matches as dicts: start/end (char span in norm_transcript, whole words),
    number, lines (Tamil), score. Overlapping hits on one pasuram are merged."""
    idx = _index()
    if idx is None:
        return []
    from rapidfuzz import fuzz
    lines, grams = idx

    # Transcript skeleton, remembering which word each skeleton char came from
    words = [(m.start(), m.end()) for m in re.finditer(r"\S+", norm_transcript)]
    sk_chars, sk_word = [], []
    for wi, (a, b) in enumerate(words):
        for ch in skeleton(norm_transcript[a:b]):
            sk_chars.append(ch)
            sk_word.append(wi)
    T = "".join(sk_chars)
    if len(T) < MIN_LINE_SKELETON:
        return []

    hits = []
    window, step = 48, 8
    for start in range(0, max(1, len(T) - window // 2), step):
        w = T[start:start + window]
        counts = {}
        for i in range(len(w) - NGRAM + 1):
            for lid in grams.get(w[i:i + NGRAM], ()):
                counts[lid] = counts.get(lid, 0) + 1
        for lid, c in sorted(counts.items(), key=lambda kv: -kv[1])[:5]:
            if c < 4:
                break
            line = lines[lid]
            al = fuzz.partial_ratio_alignment(line["skel"], w, score_cutoff=MIN_SCORE)
            if al is None:
                continue
            a, b = start + al.dest_start, start + al.dest_end
            if b - a < MIN_LINE_SKELETON:
                continue
            hits.append({"lid": lid, "score": al.score, "w0": sk_word[a], "w1": sk_word[b - 1]})

    # Merge hits on the same pasuram that touch or overlap (in words)
    merged = []
    for h in sorted(hits, key=lambda h: (lines[h["lid"]]["verse"]["number"], h["w0"])):
        num = lines[h["lid"]]["verse"]["number"]
        if merged and merged[-1]["number"] == num and h["w0"] <= merged[-1]["w1"] + 3:
            m = merged[-1]
            m["w1"] = max(m["w1"], h["w1"])
            m["score"] = max(m["score"], h["score"])
            m["line_ids"].add(lines[h["lid"]]["line"])
        else:
            merged.append({"number": num, "w0": h["w0"], "w1": h["w1"], "score": h["score"],
                           "line_ids": {lines[h["lid"]]["line"]}, "verse": lines[h["lid"]]["verse"]})

    # Where two pasurams claim the same words, keep the better-scoring one
    from agents.verbatim import _TAMIL_CUES
    merged.sort(key=lambda m: -m["score"])
    taken, out = set(), []
    for m in merged:
        span = set(range(m["w0"], m["w1"] + 1))
        if span & taken:
            continue
        heard = norm_transcript[words[m["w0"]][0]:words[m["w1"]][1]]
        # Ordinary Telugu sentences sometimes sound like a pasuram line; a real
        # quote carries Tamil word shapes (final -న్/-ల్/-ర్, ళ, -ై endings...)
        if len(skeleton(heard)) < MIN_MATCH_SKELETON or not _TAMIL_CUES.search(_EVERYDAY_TAMIL_WORDS.sub(" ", heard)):
            continue
        taken |= span
        v = m["verse"]
        out.append({
            "start": words[m["w0"]][0],
            "end": words[m["w1"]][1],
            "number": m["number"],
            "lines": [v["lines"][i] for i in sorted(m["line_ids"])],
            "score": round(m["score"]),
        })
    return sorted(out, key=lambda m: m["start"])


def match_verse(text: str, min_score: int = MIN_SCORE, min_skeleton: int = 12) -> dict | None:
    """Best pasuram match for one candidate verse (already flagged by the LLM),
    so a shorter phrase is accepted than in the open search above."""
    idx = _index()
    if idx is None:
        return None
    from rapidfuzz import fuzz
    lines, grams = idx
    sk = skeleton(text)
    if len(sk) < min_skeleton:
        return None
    counts = {}
    for i in range(len(sk) - NGRAM + 1):
        for lid in grams.get(sk[i:i + NGRAM], ()):
            counts[lid] = counts.get(lid, 0) + 1
    best = None
    for lid, _ in sorted(counts.items(), key=lambda kv: -kv[1])[:20]:
        score = fuzz.partial_ratio(lines[lid]["skel"], sk)
        if score >= min_score and (best is None or score > best[0]):
            best = (score, lid)
    if best is None:
        return None
    line = lines[best[1]]
    return {"number": line["verse"]["number"], "lines": [line["text"]], "score": round(best[0])}


def reference(match: dict) -> dict:
    return {"collection": "Nalayira Divya Prabandham", "number": match["number"],
            "source": "Project Madurai", "score": match["score"]}


def original_line(match: dict) -> str:
    """Tamil source text for the notes' second line (no parentheses: the notes
    use them to delimit this field)."""
    text = " / ".join(match["lines"]).replace("(", "").replace(")", "")
    return f"{text} · நாலாயிர திவ்ய பிரபந்தம் {match['number']}"
