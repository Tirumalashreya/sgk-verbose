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
# Covers the open/close said in either word order, plus "stop" as another
# common way to say "end this".
_BRACKET_OPEN = re.compile(_W + r'(?:బ్రాకెట్\s*(?:లో|ఓపెన్)|ఓపెన్\s*బ్రాకెట్)' + _E)
_BRACKET_CLOSE = re.compile(_W + r'(?:బ్రాకెట్\s*(?:క్లోజ్|స్టాప్)|క్లోజ్\s*బ్రాకెట్)' + _E)


def _apply_bracket_commands(text: str) -> tuple[str, int]:
    text, n_open = _BRACKET_OPEN.subn('(', text)
    text, n_close = _BRACKET_CLOSE.subn(')', text)
    return text, n_open + n_close


# Same convention as the bracket command, for "put this in quotes" — a real
# recording used exactly "ఇన్వర్టెడ్ కామాస్ ... అని ఇన్వర్టెడ్ కామాస్ ముగింపు"
# (bare "inverted commas" to open, "... ముగింపు" — "ending" — to close, not
# "క్లోజ్"). Covers the other ways this is commonly said too — "కామాస్" alone
# (dropping "ఇన్వర్టెడ్"), "స్టాప్" as another way to say "end this", and
# either word order. The close patterns are matched first since they're
# strict extensions of the open phrase ("కామాస్" + a closing word) — matching
# open first would swallow the shared prefix and leave the closing word
# stranded as plain text. "కోట్" ("quote") is never matched bare — it's also
# an ordinary Telugu word (fort), so only the unambiguous multi-word commands
# are recognized.
_COMMAS = r'(?:ఇన్వర్టెడ్\s*కామాస్|కామాస్)'
_QUOTE_CLOSE = re.compile(
    _W + rf'(?:{_COMMAS}\s*(?:ముగింపు|క్లోజ్|ఎండ్|స్టాప్)'
         r'|అన్\s*కోట్'
         r'|కోట్\s*(?:క్లోజ్|స్టాప్)|క్లోజ్\s*కోట్)' + _E
)
_QUOTE_OPEN = re.compile(
    _W + rf'(?:{_COMMAS}(?:\s*(?:లో|ఓపెన్))?'
         r'|కోట్\s*ఓపెన్|ఓపెన్\s*కోట్)' + _E
)


def _apply_quote_commands(text: str) -> tuple[str, int]:
    text, n_close = _QUOTE_CLOSE.subn('"', text)
    text, n_open = _QUOTE_OPEN.subn('"', text)
    return text, n_open + n_close


# The dictionary above only catches Tamil names already known to be
# misread. Separately, the ASR sometimes writes a stray word straight in
# Tamil script (its own script, not a Telugu misspelling) — any run of Tamil
# Unicode characters, not just known names. For a Telugu-reading audience
# that is unreadable as-is, so give it a Telugu-script reading the same way
# verified Tamil pasurams already get one (transliteration_agent.py /
# verbatim.py's tamil_to_telugu — a one-to-one script mapping, not a guess
# at meaning), and keep the original right after it in brackets so nothing
# is lost or silently rewritten.
_TAMIL_RUN = re.compile(r'[஀-௿](?:[஀-௿\s]*[஀-௿])?')


def _apply_tamil_transliteration(text: str) -> tuple[str, int]:
    from agents.verbatim import tamil_to_telugu
    count = 0

    def repl(m):
        nonlocal count
        original = m.group(0)
        telugu = tamil_to_telugu(original)
        if not telugu:
            return original  # transliteration failed — leave the original untouched, never drop it
        count += 1
        return f"{telugu} ({original})"

    text = _TAMIL_RUN.sub(repl, text)
    return text, count


def correction_agent(state: VerbaState) -> VerbaState:
    transcript = state.get("transcript", "") or ""

    if len(transcript.strip()) < 10:
        print("[correction] skipping — no transcript")
        return state

    state["raw_transcript"] = transcript
    fixed, n_tamil = _apply_tamil_transliteration(transcript)
    fixed, n = _apply_term_fixes(fixed)
    fixed, n_brackets = _apply_bracket_commands(fixed)
    fixed, n_quotes = _apply_quote_commands(fixed)
    n += n_brackets + n_quotes + n_tamil
    if n_tamil:
        print(f"[correction] transliterated {n_tamil} raw Tamil-script fragment(s)")
    if n_brackets:
        print(f"[correction] converted {n_brackets} spoken bracket instruction(s)")
    if n_quotes:
        print(f"[correction] converted {n_quotes} spoken quote instruction(s)")
    if n:
        print(f"[correction] applied {n} term fix(es)")
        state["transcript"] = fixed
    state["current_agent"] = "correction_done"
    return state
