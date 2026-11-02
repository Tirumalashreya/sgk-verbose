"""
Assembles the final notes from the transcript using code only — no LLM.

Output rules:
  - Every word comes from the transcript, in order. Nothing added, nothing dropped.
  - Paragraphs are separated by a blank line. No headings.
  - Each verified shloka sits on its own line, at the exact point it was spoken:
        **"<verse as transcribed>"** (<devanagari>)      ← Sanskrit
        **"<verse as transcribed>"**                     ← Tamil
"""
import re
from graph.state import VerbaState
from agents.verbatim import normalize_ws, find_all, expand_to_words, telugu_to_iast

TARGET_PARA_CHARS = 400   # length-based fallback paragraph size
MIN_PARA_CHARS    = 250
MAX_PARA_CHARS    = 900   # even with pause data, never let a paragraph exceed this
PAUSE_SECONDS     = 1.5   # Whisper gap that counts as a natural pause
_SENTENCE_END     = re.compile(r"[.?!।॥]\s")


def _shloka_spans(norm: str, shlokas: list) -> list[tuple[int, int, dict]]:
    """Every occurrence of every verse, longest-first so nested verses don't double-mark."""
    candidates = []
    for s in shlokas:
        for start, end in find_all(norm, s.get("text") or ""):
            start, end = expand_to_words(norm, start, end)
            candidates.append((start, end, {**s, "text": norm[start:end]}))
    candidates.sort(key=lambda c: (c[0], -(c[1] - c[0])))
    spans, last_end = [], -1
    for start, end, s in candidates:
        if start >= last_end:
            spans.append((start, end, s))
            last_end = end
    return spans


def _inside_span(pos: int, spans) -> tuple[int, int] | None:
    for start, end, _ in spans:
        if start < pos < end:
            return start, end
    return None


def _snap(pos: int, norm: str, spans) -> int:
    """Move a break position to a word boundary outside any shloka."""
    span = _inside_span(pos, spans)
    if span:
        pos = span[1]
    nxt = norm.find(" ", pos)
    return len(norm) if nxt == -1 else nxt


def _pause_breaks(norm: str, segments: list) -> list[int]:
    """Map Whisper segment gaps to character positions in the transcript."""
    breaks, cursor = [], 0
    for seg, nxt in zip(segments, segments[1:]):
        tail = normalize_ws(seg.get("text", ""))[-25:]
        if not tail:
            continue
        pos = norm.find(tail, cursor)
        if pos == -1:
            continue  # text changed by term fixes — skip this boundary
        cursor = pos + len(tail)
        if (nxt.get("start", 0) - seg.get("end", 0)) >= PAUSE_SECONDS:
            breaks.append(cursor)
    return breaks


def _length_breaks(norm: str, start: int, end: int, spans) -> list[int]:
    breaks, cur = [], start
    while end - cur > TARGET_PARA_CHARS + MIN_PARA_CHARS:
        window = norm[cur + MIN_PARA_CHARS : cur + TARGET_PARA_CHARS + 150]
        ends = [m.end() for m in _SENTENCE_END.finditer(window)]
        pos = cur + MIN_PARA_CHARS + ends[-1] - 1 if ends else cur + TARGET_PARA_CHARS
        pos = _snap(pos, norm, spans)
        if pos >= end:
            break
        breaks.append(pos)
        cur = pos
    return breaks


def _paragraph_breaks(norm: str, spans, segments: list) -> list[int]:
    pauses = [_snap(b, norm, spans) for b in _pause_breaks(norm, segments)] if segments else []
    # Drop pause breaks that would make tiny paragraphs
    kept, prev = [], 0
    for b in sorted(set(pauses)):
        if MIN_PARA_CHARS <= b - prev and b < len(norm):
            kept.append(b)
            prev = b
    # Fill in long stretches (or everything, when there is no timing data)
    out, prev = [], 0
    for b in kept + [len(norm)]:
        limit = MAX_PARA_CHARS if segments else TARGET_PARA_CHARS + MIN_PARA_CHARS
        if b - prev > limit:
            out.extend(_length_breaks(norm, prev, b, spans))
        if b < len(norm):
            out.append(b)
        prev = b
    return sorted(set(out))


# The speaker sometimes marks a verse-source boundary aloud — "first moolam",
# "ఒకటో మూలం", "moolam 2", "మూలం వన్" (ASR's Telugu-script spelling of spoken
# English "moolam one"), "para 3", number before or after the noun, digit,
# ordinal word, or Telugu-transliterated English word. When any such marker
# is heard, everything from it up to the next one (or the end) becomes its
# own single paragraph, in place of the usual pause/length-based splitting —
# a spoken structural cue, not a guess. If none is heard anywhere, this
# never fires and paragraphing runs exactly as before. The number is also
# kept (see _NUM_VALUE) so a Telugu heading like "మూలం 1" can be shown for it.
_EN_NUM_VALUE = {
    "first": 1, "1st": 1, "one": 1, "second": 2, "2nd": 2, "two": 2,
    "third": 3, "3rd": 3, "three": 3, "fourth": 4, "4th": 4, "four": 4,
    "fifth": 5, "5th": 5, "five": 5, "sixth": 6, "6th": 6, "six": 6,
    "seventh": 7, "7th": 7, "seven": 7, "eighth": 8, "8th": 8, "eight": 8,
    "ninth": 9, "9th": 9, "nine": 9, "tenth": 10, "10th": 10, "ten": 10,
    "eleventh": 11, "11th": 11, "eleven": 11, "twelfth": 12, "12th": 12, "twelve": 12,
    "thirteenth": 13, "13th": 13, "thirteen": 13, "fourteenth": 14, "14th": 14, "fourteen": 14,
    "fifteenth": 15, "15th": 15, "fifteen": 15, "sixteenth": 16, "16th": 16, "sixteen": 16,
    "seventeenth": 17, "17th": 17, "seventeen": 17, "eighteenth": 18, "18th": 18, "eighteen": 18,
    "nineteenth": 19, "19th": 19, "nineteen": 19, "twentieth": 20, "20th": 20, "twenty": 20,
}
_TE_ORDINAL_VALUE = {
    "ఒకటో": 1, "రెండో": 2, "మూడో": 3, "నాలుగో": 4, "ఐదో": 5, "ఆరో": 6, "ఏడో": 7,
    "ఎనిమిదో": 8, "తొమ్మిదో": 9, "పదో": 10, "పదకొండో": 11, "పన్నెండో": 12,
    "పదమూడో": 13, "పధ్నాలుగో": 14, "పదిహేనో": 15, "పదహారో": 16, "పదిహేడో": 17,
    "పద్దెనిమిదో": 18, "పందొమ్మిదో": 19, "ఇరవయ్యో": 20,
}
# ASR writes a spoken-English number in Telugu script when it's mixed into
# otherwise-Telugu speech (same reason correction_agent.py's bracket command
# spells "bracket" as బ్రాకెట్) — this is a different, separate spelling from
# both the Latin English word and the native Telugu ordinal above, and real
# recordings showed it's the common case, not the rare one. Spellings vary
# (టు vs టూ for "two"), so common variants are included where likely.
_TE_EN_NUM_VALUE = {
    "వన్": 1, "ఫస్ట్": 1, "టు": 2, "టూ": 2, "సెకండ్": 2, "త్రీ": 3, "థర్డ్": 3,
    "ఫోర్": 4, "ఫోర్త్": 4, "ఫైవ్": 5, "ఫిఫ్త్": 5, "సిక్స్": 6, "సిక్స్త్": 6,
    "సెవెన్": 7, "సెవెంత్": 7, "ఎయిట్": 8, "ఐట్": 8, "నైన్": 9, "నైన్త్": 9,
    "టెన్": 10, "టెంత్": 10, "ఎలెవన్": 11, "ట్వెల్వ్": 12, "థర్టీన్": 13,
    "ఫోర్టీన్": 14, "ఫిఫ్టీన్": 15, "సిక్స్టీన్": 16, "సెవెంటీన్": 17,
    "సెవెన్టీన్": 17, "ఎయిటీన్": 18, "నైన్టీన్": 19, "ట్వెంటీ": 20, "ట్వంటీ": 20,
}
_MOOLAM_NUM_WORDS = "|".join({*_EN_NUM_VALUE, *_TE_ORDINAL_VALUE, *_TE_EN_NUM_VALUE})
_MOOLAM_NUM = rf"(?:\d{{1,2}}|{_MOOLAM_NUM_WORDS})"
_MOOLAM_NOUN = r"(?:మూలం|మూలము|moolam|mulam|పేరా|పారా|para)"
# Plain \b fails on Telugu: vowel signs (ో, ి, etc.) are combining marks, not
# \w, so \b lands mid-syllable instead of at the word edge. correction_agent.py
# hit this same issue and fixed it with a Telugu-block-aware lookaround —
# reused here rather than reinventing it.
_TE_W = r'(?<![\wఀ-౿])'
_TE_E = r'(?![\wఀ-౿])'
_MOOLAM_MARK = re.compile(
    rf"{_TE_W}(?:(?P<num_a>{_MOOLAM_NUM})\s*{_MOOLAM_NOUN}|{_MOOLAM_NOUN}\s*(?P<num_b>{_MOOLAM_NUM})){_TE_E}",
    re.IGNORECASE,
)


# "తరువాత పేరా" ("next paragraph") — unlike the moolam/para markers above, this
# carries no number, so it starts a new paragraph without a heading. A real
# recording showed the speaker using exactly this as a plain paragraph-break
# instruction, with no moolam/number anywhere near it. Unlike those markers,
# the instruction itself is a dictation command like correction_agent.py's
# "bracket lo" — it marks where to break, but is never meant to be read back
# as part of the notes, so it (and any punctuation the ASR tacked onto it,
# e.g. a trailing period) is dropped from the rendered text entirely.
_NEXT_PARA_MARK = re.compile(
    rf"{_TE_W}(?:(?:తరువాత|తర్వాత|కొత్త|న్యూ)\s*(?:పేరా|పారా)|next\s*para(?:graph)?)[.,]?{_TE_E}",
    re.IGNORECASE,
)


def _moolam_number(token: str) -> int | None:
    if token.isdigit():
        return int(token)
    return _EN_NUM_VALUE.get(token.lower()) or _TE_ORDINAL_VALUE.get(token) or _TE_EN_NUM_VALUE.get(token)


def _moolam_markers(norm: str, spans) -> list[tuple[int, int]]:
    """(position, number) for every moolam/para marker — position is a
    paragraph-START point, so (unlike _snap, which is built for paragraph-END
    points and jumps forward to the next space) this only nudges past a
    shloka span when the marker would otherwise land inside one, never past
    the marker itself."""
    out = []
    for m in _MOOLAM_MARK.finditer(norm):
        num = _moolam_number(m.group("num_a") or m.group("num_b"))
        if num is None:
            continue
        pos = m.start()
        span = _inside_span(pos, spans)
        if span:
            pos = span[1]
        out.append((pos, num))
    # A later marker's start might have been nudged onto an earlier one's
    # position (both landing right after the same shloka) — keep the first.
    seen, dedup = set(), []
    for pos, num in sorted(out):
        if pos not in seen:
            seen.add(pos)
            dedup.append((pos, num))
    return dedup


def _next_para_markers(norm: str, spans) -> list[int]:
    """Positions of a plain "next paragraph" instruction — same paragraph-START
    nudging as _moolam_markers, just with no number attached."""
    out = []
    for m in _NEXT_PARA_MARK.finditer(norm):
        pos = m.start()
        span = _inside_span(pos, spans)
        if span:
            pos = span[1]
        out.append(pos)
    return sorted(set(out))


def _strip_next_para(text: str) -> str:
    """Remove the "next paragraph" instruction from rendered text — it only
    ever marks a break point (handled by _next_para_markers), it is never
    meant to appear in the notes themselves."""
    return normalize_ws(_NEXT_PARA_MARK.sub(" ", text))


def _shloka_line(s: dict) -> str:
    line = f'**"{s["text"]}"**'
    if s.get("original"):
        line += f' ({s["original"]})'
    return line


INLINE_WORD_LIMIT = 2   # a verse this short (a name, a single phrase) reads better folded
                        # into its sentence than set apart as its own line


def _is_inline_shloka(s: dict) -> bool:
    return len((s.get("text") or "").split()) <= INLINE_WORD_LIMIT


def _render_paragraph(norm: str, start: int, end: int, spans) -> str:
    lines, cur = [], start
    pending = []   # prose + any short (inline) verses, joined into one flowing line
    def flush():
        if pending:
            lines.append(" ".join(pending))
            pending.clear()
    for s_start, s_end, s in spans:
        if s_end <= start or s_start >= end:
            continue
        before = _strip_next_para(norm[cur:s_start])
        if before:
            pending.append(before)
        if _is_inline_shloka(s):
            pending.append(_shloka_line(s))   # same markup — just not given its own line
        else:
            flush()
            lines.append(_shloka_line(s))
        cur = s_end
    after = _strip_next_para(norm[cur:end])
    if after:
        pending.append(after)
    flush()
    return "\n".join(lines)


def _build_notes(transcript: str, shlokas: list, segments: list | None = None) -> tuple[str, dict[int, str], str]:
    """Shared by format_notes and format_headings so the two can never drift
    out of sync with each other — headings are keyed to the paragraph index
    they'd land on in notes.split("\\n\\n"), after empty paragraphs are
    dropped, exactly as the caller will see them. Also returns the transcript
    with any "next paragraph" instruction removed — notes no longer contain
    that phrase, so this is what validation must compare against instead of
    the raw transcript, the same way correction_agent.py's own text fixes
    become the new baseline."""
    norm = normalize_ws(transcript)
    if not norm:
        return "", {}, norm
    spans = _shloka_spans(norm, shlokas or [])
    markers = _moolam_markers(norm, spans)
    num_at = dict(markers)
    # A numbered moolam/para marker and a plain "next paragraph" instruction
    # both force a break; only the numbered ones get a heading.
    marker_positions = sorted({pos for pos, _ in markers} | set(_next_para_markers(norm, spans)))
    if marker_positions:
        # Default pause/length splitting only for whatever came before the
        # first marker; from each marker on, the paragraph runs undivided
        # until the next one (or the end) — exactly what was spoken as the
        # boundary, not a guess.
        pre_bounds = _paragraph_breaks(norm[:marker_positions[0]], spans, segments or []) if marker_positions[0] > 0 else []
        bounds = sorted({0, *pre_bounds, *marker_positions, len(norm)})
    else:
        bounds = [0] + _paragraph_breaks(norm, spans, segments or []) + [len(norm)]
    paragraphs = [(a, _render_paragraph(norm, a, b, spans)) for a, b in zip(bounds, bounds[1:])]
    kept = [(a, p) for a, p in paragraphs if p]
    notes = "\n\n".join(p for _, p in kept)
    headings = {i: f"మూలం {num_at[a]}" for i, (a, _) in enumerate(kept) if a in num_at}
    cleaned_transcript = _strip_next_para(norm)
    return notes, headings, cleaned_transcript


def format_notes(transcript: str, shlokas: list, segments: list | None = None) -> str:
    notes, _, _ = _build_notes(transcript, shlokas, segments)
    return notes


def format_headings(transcript: str, shlokas: list, segments: list | None = None) -> dict[int, str]:
    """{paragraph index -> "మూలం N"} for every paragraph that starts with a
    moolam/para marker — a display-only label, never embedded into the notes
    text itself (validation's exact-transcript-reconstruction check would
    reject it, and rightly so: it's not a word the speaker said)."""
    _, headings, _ = _build_notes(transcript, shlokas, segments)
    return headings


def formatting_agent(state: VerbaState) -> VerbaState:
    transcript = state.get("transcript") or ""
    shlokas = state.get("shlokas") or []
    notes, headings, cleaned_transcript = _build_notes(transcript, shlokas, state.get("transcript_segments") or [])
    print(f"[formatting] {len(notes)} chars, {notes.count(chr(10) * 2) + 1 if notes else 0} paragraph(s), {len(shlokas)} shloka(s), {len(headings)} moolam heading(s)")
    state["notes"] = notes
    state["enhanced_notes"] = notes
    state["transliterated_notes"] = telugu_to_iast(notes) if notes else ""
    state["notes_headings"] = headings
    # Validation compares notes against state["transcript"] next — update it
    # to match, the same way correction_agent.py's own text fixes already do.
    state["transcript"] = cleaned_transcript
    state["current_agent"] = "formatting_done"
    return state
