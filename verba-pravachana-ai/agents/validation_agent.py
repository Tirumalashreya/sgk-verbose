"""
Checks the formatted notes against the transcript. Never retries — the
formatter is deterministic, so a failure is flagged for manual review instead.
"""
import re
from collections import Counter
from graph.state import VerbaState
from agents.verbatim import normalize_ws, SHLOKA_LINE

MIN_COVERAGE = 0.5
_BOLD_LINE   = re.compile(r"^\*{1,2}.+\*{1,2}$")
_NUMBERED    = re.compile(r"^\d+[.)]\s")
_ALL_CAPS    = re.compile(r"^(?:[A-Z][A-Z'’-]*\s+){4,}[A-Z][A-Z'’-]*$")


def _strip_markup(notes: str) -> str:
    """Notes text with shloka markup removed — should equal the transcript."""
    words = []
    for line in notes.split("\n"):
        line = line.strip()
        if not line:
            continue
        m = SHLOKA_LINE.match(line)
        words.append(m.group(1) if m else line)
    return normalize_ws(" ".join(words))


def validate(transcript: str, notes: str, shlokas: list) -> list[dict]:
    errors = []
    norm_transcript = normalize_ws(transcript)
    if not norm_transcript:
        return errors

    stripped = _strip_markup(notes or "")
    t_words, n_words = norm_transcript.split(" "), stripped.split(" ") if stripped else []

    # 1. No invention — every word in the notes must come from the transcript
    invented = Counter(n_words) - Counter(t_words)
    if invented:
        sample = ", ".join(list(invented)[:10])
        errors.append({"type": "no_invention",
                       "message": f"{sum(invented.values())} word(s) not in transcript: {sample}"})

    # 2. Verbatim shlokas
    for s in shlokas or []:
        text = normalize_ws(s.get("text", ""))
        if text and text not in norm_transcript:
            errors.append({"type": "verbatim_shlokas",
                           "message": f"shloka not found verbatim in transcript: {text[:60]}"})

    # 3. No headings / structural elements
    for line in (notes or "").split("\n"):
        line = line.strip()
        if not line or SHLOKA_LINE.match(line):
            continue
        if line.startswith("#") or _NUMBERED.match(line) or _BOLD_LINE.match(line) or _ALL_CAPS.match(line):
            errors.append({"type": "no_headings", "message": f"structural line: {line[:60]}"})

    # 4. Completeness
    coverage = len(n_words) / len(t_words)
    if coverage < MIN_COVERAGE:
        errors.append({"type": "completeness",
                       "message": f"notes contain {coverage:.0%} of transcript words (min {MIN_COVERAGE:.0%})"})

    # 5. Exact reconstruction — catches dropped or reordered text that 1 and 4 allow
    if stripped != norm_transcript and not errors:
        errors.append({"type": "not_verbatim",
                       "message": "notes text does not reproduce the transcript word-for-word"})
    return errors


CONFIDENCE_FLOOR = 0.6


def validation_agent(state: VerbaState) -> VerbaState:
    errors = validate(state.get("transcript") or "", state.get("notes") or "", state.get("shlokas") or [])
    gaps = state.get("transcription_gaps") or 0
    if gaps:
        errors.append({"type": "asr_gap",
                       "message": f"{gaps} audio piece(s) could not be transcribed — marked [?] in the transcript"})
    confidence = state.get("asr_confidence")
    if confidence is not None and confidence < CONFIDENCE_FLOOR:
        errors.append({"type": "low_asr_confidence",
                       "message": f"term-dictionary confidence {confidence:.0%} is below {CONFIDENCE_FLOOR:.0%} — worth a listen"})
    state["validation_passed"] = not errors
    state["validation_errors"] = errors
    state["needs_manual_review"] = bool(errors)
    if errors:
        print(f"[validation] FAILED — flagged for manual review: {[e['type'] for e in errors]}")
        for e in errors:
            print(f"  [{e['type']}] {e['message']}")
    else:
        print("[validation] passed")
    state["current_agent"] = "validation_done"
    return state
