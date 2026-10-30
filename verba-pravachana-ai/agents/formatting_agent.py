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
        before = norm[cur:s_start].strip()
        if before:
            pending.append(before)
        if _is_inline_shloka(s):
            pending.append(_shloka_line(s))   # same markup — just not given its own line
        else:
            flush()
            lines.append(_shloka_line(s))
        cur = s_end
    after = norm[cur:end].strip()
    if after:
        pending.append(after)
    flush()
    return "\n".join(lines)


def format_notes(transcript: str, shlokas: list, segments: list | None = None) -> str:
    norm = normalize_ws(transcript)
    if not norm:
        return ""
    spans = _shloka_spans(norm, shlokas or [])
    bounds = [0] + _paragraph_breaks(norm, spans, segments or []) + [len(norm)]
    paragraphs = [_render_paragraph(norm, a, b, spans) for a, b in zip(bounds, bounds[1:])]
    return "\n\n".join(p for p in paragraphs if p)


def formatting_agent(state: VerbaState) -> VerbaState:
    transcript = state.get("transcript") or ""
    shlokas = state.get("shlokas") or []
    notes = format_notes(transcript, shlokas, state.get("transcript_segments") or [])
    print(f"[formatting] {len(notes)} chars, {notes.count(chr(10) * 2) + 1 if notes else 0} paragraph(s), {len(shlokas)} shloka(s)")
    state["notes"] = notes
    state["enhanced_notes"] = notes
    state["transliterated_notes"] = telugu_to_iast(notes) if notes else ""
    state["current_agent"] = "formatting_done"
    return state
