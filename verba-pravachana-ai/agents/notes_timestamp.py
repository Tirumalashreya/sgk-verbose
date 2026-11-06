"""
Builds a timestamped version of a recording's notes: the same notes text,
with a [MM:SS] marker at the start of the paragraph nearest where each
matched phrase was actually spoken. Computed on demand, not during the main
pipeline — the pipeline's dual-listener step (what actually builds the
notes) doesn't track timing at all, confirmed: its "segments" return is
always empty.

How: gemini_asr.py already has a word-level timestamp mode
(gemini-3.5-transcribe, "timestamps") that returns real start/end seconds
per phrase, measured from the audio itself — not used for the notes
themselves because that model drops Sanskrit verses, which is disqualifying
for the actual transcript but irrelevant here, since this pass only
recovers *timing*, never *text*. Each phrase's words are aligned onto the
session's already-validated notes with the same word alignment the
two-listener step uses to merge Sarvam and Gemini; a marker's time is the
real timestamp of whichever phrase matched there — not a guess, not a
minute bucket.

This only works where the original audio is still on disk — None signals
"not available for this recording" rather than guessing.
"""
import os
import re
import glob
import bisect
import difflib
import subprocess

from agents.dual_asr import _key

SHLOKA_MARK = re.compile(r'\*\*"(.+?)"\*\*(?:\s*\(([^)]*)\))?')


def _live_piece_paths(session_id: str) -> list[str]:
    """A live recording's saved per-minute audio, in recording order."""
    pattern = os.path.join("audio_input", f"live_{session_id[:8]}_*")
    files = [f for f in glob.glob(pattern) if not f.endswith(".json")]

    def idx(f):
        return int(os.path.splitext(os.path.basename(f))[0].rsplit("_", 1)[1])

    return [f for f, _ in sorted(((f, idx(f)) for f in files), key=lambda t: t[1])]


def _concat_live_pieces(session_id: str) -> str | None:
    """One audio file spanning the whole recording, so gemini_asr's own
    chunking and offset accounting (gemini_stt already splits long audio and
    accumulates each piece's real position) only has to run once, over the
    whole thing, instead of being reimplemented here per piece."""
    paths = _live_piece_paths(session_id)
    if not paths:
        return None
    out_dir = os.path.join("audio_input", ".work")
    os.makedirs(out_dir, exist_ok=True)
    # .webm, not .m4a: each piece is Opus-in-WebM, and stream-copying Opus
    # straight into an MP4/.m4a container isn't something ffmpeg's muxer
    # supports (confirmed: "Could not find tag for codec opus in container"
    # — it fails but still leaves a 0-byte file behind, which then looked
    # like a valid cached result forever after and crashed every later
    # request that tried to read it). Concatenating into the pieces' own
    # native container works, and costs nothing extra since it's still a
    # stream copy, not a re-encode.
    out_path = os.path.join(out_dir, f"concat_{session_id[:8]}.webm")
    if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
        return out_path
    list_file = out_path + ".txt"
    with open(list_file, "w", encoding="utf-8") as f:
        for p in paths:
            f.write(f"file '{os.path.abspath(p)}'\n")
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", out_path],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True,
        )
    except Exception as e:
        print(f"[notes_timestamp] could not concatenate live pieces: {e}")
        if os.path.exists(out_path):
            os.remove(out_path)   # a failed ffmpeg run can still leave a 0-byte file — don't cache that as success
        return None
    if not os.path.exists(out_path) or os.path.getsize(out_path) == 0:
        return None
    return out_path


def _find_audio(session: dict) -> str | None:
    concatenated = _concat_live_pieces(session["id"])
    if concatenated:
        return concatenated
    audio_path = session.get("source_audio_path")
    if audio_path and os.path.exists(audio_path):
        return audio_path
    return None


def available(session: dict) -> bool:
    """Whether build() has any audio to work with — cheap enough to call
    before offering the option in the UI."""
    return bool(_find_audio(session)) and bool((session.get("notes") or "").strip())


def offset_map(notes: str) -> list[tuple[int, int]]:
    """Breakpoints (stripped_offset, notes_offset). Within each bracket the
    mapping is a constant shift — every span is either untouched prose or a
    verse's verbatim text (group 1), both copied through unchanged; the
    **" / "** (original) wrapper around a verse exists only in `notes` and
    has to be skipped, not just the whole-match span collapsed to a point,
    or a target landing exactly at a verse's first word resolves to the
    wrapper's position instead of the word's."""
    pairs = [(0, 0)]
    stripped_pos = notes_pos = 0
    for m in SHLOKA_MARK.finditer(notes):
        # prose before the markup — shift unchanged
        stripped_pos += m.start() - notes_pos
        notes_pos = m.start()
        pairs.append((stripped_pos, notes_pos))
        # skip the opening **" — notes jumps ahead, stripped doesn't move
        notes_pos = m.start(1)
        pairs.append((stripped_pos, notes_pos))
        # the verse's own text — copied through unchanged
        stripped_pos += len(m.group(1))
        notes_pos = m.end(1)
        pairs.append((stripped_pos, notes_pos))
        # skip the closing "** and optional (original)
        notes_pos = m.end()
        pairs.append((stripped_pos, notes_pos))
    pairs.append((stripped_pos + len(notes) - notes_pos, len(notes)))
    return pairs


def to_notes_offset(pairs: list[tuple[int, int]], target: int) -> int:
    i = bisect.bisect_right([p[0] for p in pairs], target) - 1
    i = max(0, min(i, len(pairs) - 2))
    s0, n0 = pairs[i]
    return n0 + (target - s0)


def stripped_words(notes: str) -> tuple[list[str], list[int]]:
    """Notes with markup reduced to its verbatim text only, tokenized — each
    word's offset is in that stripped text, mapped back via offset_map()."""
    parts, notes_pos = [], 0
    for m in SHLOKA_MARK.finditer(notes):
        parts.append(notes[notes_pos:m.start()])
        parts.append(m.group(1))
        notes_pos = m.end()
    parts.append(notes[notes_pos:])
    stripped = "".join(parts)
    words, offsets = [], []
    for m in re.finditer(r'\S+', stripped):
        words.append(m.group(0))
        offsets.append(m.start())
    return words, offsets


def anchor_pieces(a_tokens: list[str], a_chunk: list[int], b_tokens: list[str]) -> dict[int, int]:
    """For each piece index in a_chunk, the earliest b_tokens word position
    it matches — the same word-alignment the two-listener merge uses."""
    ka = [_key(t) for t in a_tokens]
    kb = [_key(t) for t in b_tokens]
    sm = difflib.SequenceMatcher(a=ka, b=kb, autojunk=False)
    first_b_word: dict[int, int] = {}
    for block in sm.get_matching_blocks():
        for i in range(block.size):
            c = a_chunk[block.a + i]
            if c not in first_b_word:
                first_b_word[c] = block.b + i
    return first_b_word


def _fmt(seconds: float) -> str:
    s = int(round(seconds))
    return f"[{s // 60:02d}:{s % 60:02d}]"


def insert_markers(notes: str, markers_by_notes_offset: dict[int, float]) -> str:
    """markers_by_notes_offset: {position in notes: real audio seconds}. Each
    marker snaps to the start of its nearest line, so it never splits a
    sentence, and a position already claimed by an earlier (earlier in the
    notes, i.e. earlier-spoken) marker is left alone."""
    line_starts = [0] + [m.end() for m in re.finditer(r'\n', notes)]

    def line_start_at_or_before(pos):
        i = bisect.bisect_right(line_starts, pos) - 1
        return line_starts[max(0, i)]

    snapped: dict[int, float] = {}
    for pos in sorted(markers_by_notes_offset):
        line_pos = line_start_at_or_before(pos)
        if line_pos not in snapped:
            snapped[line_pos] = markers_by_notes_offset[pos]

    out = notes
    for pos in sorted(snapped, reverse=True):
        out = out[:pos] + _fmt(snapped[pos]) + " " + out[pos:]
    return out


def anchor_phrases_to_notes(segments: list[dict], notes: str) -> dict[int, float]:
    """segments: Gemini's real {start, end, text} phrases. Returns {position
    in notes: real audio seconds} for each phrase that matched."""
    a_tokens, a_chunk, phrase_start = [], [], {}
    for i, seg in enumerate(segments):
        phrase_start[i] = seg.get("start", 0.0)
        for tok in (seg.get("text") or "").split():
            a_tokens.append(tok)
            a_chunk.append(i)
    if not a_tokens:
        return {}

    pairs = offset_map(notes)
    b_tokens, b_offsets = stripped_words(notes)
    first_b_word = anchor_pieces(a_tokens, a_chunk, b_tokens)
    return {to_notes_offset(pairs, b_offsets[w]): phrase_start[i] for i, w in first_b_word.items()}


def build(session: dict) -> str | None:
    """The full pipeline: find the recording's audio, transcribe it with
    Gemini's real word-timing mode (a separate, auxiliary pass — the result
    is never shown and never touches the notes, only its timing is used),
    align its phrases onto the notes, insert markers. None if there's no
    audio left to anchor against."""
    audio_path = _find_audio(session)
    notes = session.get("notes") or ""
    if not audio_path or not notes.strip():
        return None

    from agents.gemini_asr import gemini_stt
    _, _, segments, _ = gemini_stt(audio_path, mode="timestamps")
    if not segments:
        return None

    markers = anchor_phrases_to_notes(segments, notes)
    if not markers:
        return None
    return insert_markers(notes, markers)
