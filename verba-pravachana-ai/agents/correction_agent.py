from graph.state import VerbaState
import re

# Deterministic fixes for Tamil/Sanskrit proper nouns Sarvam consistently misreads.
# Format: (sarvam_pattern, correct_telugu, tamil_or_sanskrit_original)
# The original goes in brackets after the Telugu: "ఆళ్వార్ (ஆழ்வார்)"
#
# There is deliberately no LLM correction pass: the notes must be verbatim, and an
# LLM "correcting" the transcript can silently rewrite or drop what was said.

# Python's \b treats Telugu vowel signs and virama as non-word characters, so it
# finds "boundaries" inside words. Use explicit Telugu-block boundaries instead.
_W = r'(?<![\u0C00-\u0C7F])'   # word start
_E = r'(?![\u0C00-\u0C7F])'    # word end

_TERM_FIXES = [
    # Alwar titles
    (r'తొండలడి\s*పొడి\s*ఆడు', 'తొండరడిప్పొడి ఆళ్వార్ (தொண்டரடிப்பொடி ஆழ்வார்)'),
    (r'తొండరడి\s*పొడి\s*అడు', 'తొండరడిప్పొడి ఆళ్వార్ (தொண்டரடிப்பொடி ஆழ்வார்)'),
    (_W + r'ఆడు' + _E + r'(?=\s+రోజు|\s+సేవ)', 'ఆళ్వార్ (ஆழ்வார்)'),
    (_W + r'అడు' + _E + r'(?=\s+రోజు|\s+సేవ)', 'ఆళ్వార్ (ஆழ்வார்)'),
    # Prabandham names
    (r'తిరుప్పడి\s*అడిచి', 'తిరుపళ్ళియెళుచ్చి (திருப்பள்ளியெழுச்சி)'),
    (r'తిరుమాలై\s*అరియాలై', 'తిరుమాలై అరియాద (திருமாலை அறியாத)'),
    (r'పెరుమాల్\s*పెరియా', 'పెరుమాళ్ళ పెరియ (பெருமாள் பெரிய)'),
    # Common Perumal forms
    (_W + r'పెరుమాల్' + _E, 'పెరుమాళ్ళ (பெருமாள்)'),
    (_W + r'పెరుమాల' + _E + r'(?!ళ)', 'పెరుమాళ్ళ (பெருமாள்)'),
    # Acharya names
    (r'పెరియవార్చాన్\s*పిల్ల' + _E, 'పెరియవాచ్చాన్ పిళ్ళై (பெரியவாச்சான் பிள்ளை)'),
    (r'పెరివాచ్చాన్\s*పిల్లై', 'పెరియవాచ్చాన్ పిళ్ళై (பெரியவாச்சான் பிள்ளை)'),
    # Vipranarayana
    (r'విప్రనారాయణుడు', 'విప్రనారాయణుడు (విప్రనారాయణ)'),
]


def _apply_term_fixes(text: str) -> tuple[str, int]:
    total = 0
    for pattern, replacement in _TERM_FIXES:
        text, n = re.subn(pattern, replacement, text)
        total += n
    return text, total


# The speaker uses "bracket lo" / "bracket open" ... "bracket close" as a
# spoken instruction, not as words meant to appear in the notes — a dictation
# convention, like saying "comma" or "new paragraph". Pure find-and-replace,
# same as the term fixes above: a fixed phrase is recognized and swapped for
# the punctuation it stands for. Nothing in between is read, touched, or
# reasoned about — whatever the speaker says there passes through completely
# unchanged, now sitting inside real parentheses instead of the spoken words
# that used to mark its boundaries. No model sees this text, so there is
# nothing here that can invent or drop anything.
#
# "బ్రాకెట్" is the everyday Telugu spelling of this English loanword (how it
# appears in ordinary Telugu writing) — not yet checked against this
# speaker's own transcribed audio, since no example exists yet. If the ASR
# renders it differently, this simply won't match anything; add the real
# spelling here once a recording that uses it has been seen.
_BRACKET_OPEN = re.compile(_W + r'బ్రాకెట్\s*(లో|ఓపెన్)' + _E)
_BRACKET_CLOSE = re.compile(_W + r'బ్రాకెట్\s*క్లోజ్' + _E)


def _apply_bracket_commands(text: str) -> tuple[str, int]:
    text, n_open = _BRACKET_OPEN.subn('(', text)
    text, n_close = _BRACKET_CLOSE.subn(')', text)
    return text, n_open + n_close


def correction_agent(state: VerbaState) -> VerbaState:
    transcript = state.get("transcript", "") or ""

    if len(transcript.strip()) < 10:
        print("[correction] skipping — no transcript")
        return state

    state["raw_transcript"] = transcript
    fixed, n = _apply_term_fixes(transcript)
    fixed, n_brackets = _apply_bracket_commands(fixed)
    n += n_brackets
    if n_brackets:
        print(f"[correction] converted {n_brackets} spoken bracket instruction(s)")
    if n:
        print(f"[correction] applied {n} term fix(es)")
        state["transcript"] = fixed
    state["current_agent"] = "correction_done"
    return state
