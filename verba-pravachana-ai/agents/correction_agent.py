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
# common way to say "end this", and plural/extended phrases like "బ్రాకెట్లలో",
# "బ్రాకెట్ లో ఉంచండి", "స్టార్ట్/ఎండ్ బ్రాకెట్".
_BRACKET_OPEN = re.compile(
    _W + r'(?:'
         r'బ్రాకెట్(?:లలో|\s*లో)(?:\s*(?:ఉంచండి|పెట్టండి|రాయండి))?'
         r'|బ్రాకెట్\s*(?:ఓపెన్|స్టార్ట్)'
         r'|(?:ఓపెన్|స్టార్ట్)\s*(?:ది\s*)?బ్రాకెట్'
         r')' + _E,
    re.IGNORECASE
)
_BRACKET_CLOSE = re.compile(
    _W + r'(?:'
         r'బ్రాకెట్\s*(?:క్లోజ్|స్టాప్|ఎండ్|ముగింపు)'
         r'|(?:క్లోజ్|స్టాప్|ఎండ్)\s*(?:ది\s*)?బ్రాకెట్'
         r')' + _E,
    re.IGNORECASE
)


def _snap_punctuation_spacing(text: str) -> str:
    """Snaps inner whitespace around brackets and quotes for book-quality typography."""
    text = re.sub(r'\(\s+', '(', text)
    text = re.sub(r'\s+\)', ')', text)
    text = re.sub(r'“\s+', '“', text)
    text = re.sub(r'\s+”', '”', text)
    text = re.sub(r'"\s+([^"\n]+?)\s+"', r'"\1"', text)
    text = re.sub(r'([^\s(\[{“"])(\(|“)', r'\1 \2', text)
    text = re.sub(r'(\)|”)([^\s)\]}”",.:;!?।॥])', r'\1 \2', text)
    # Remove any space between close bracket/quote and following punctuation
    text = re.sub(r'([”\)])\s+([.,!?:;।॥])', r'\1\2', text)
    return text.strip()


def _auto_close_unmatched(text: str, open_ch: str, close_ch: str) -> tuple[str, int]:
    """Auto-seals unclosed brackets or quotes before 'అని' clauses or sentence boundaries."""
    diff = text.count(open_ch) - text.count(close_ch)
    if diff <= 0:
        return text, 0
    added = 0
    for _ in range(diff):
        stack = []
        for i, ch in enumerate(text):
            if ch == open_ch:
                stack.append(i)
            elif ch == close_ch:
                if stack:
                    stack.pop()
        if not stack:
            break
        target_open = stack[-1]
        sub = text[target_open + 1:]
        ani_match = re.search(r'\s+(?:అని\s*(?:చెప్పారు|అన్నారు|వివరించారు|తెలిపారు|పలికారు|భాష్యం|వ్రాశారు|పేర్కొన్నారు)|అని(?=[\s.,!?।॥]|$))', sub)
        sent_match = re.search(r'[.!?।॥]|\n|$', sub)

        if ani_match and (not sent_match or ani_match.start() < sent_match.start()):
            insert_pos = target_open + 1 + ani_match.start()
        elif sent_match and sent_match.start() > 0:
            insert_pos = target_open + 1 + sent_match.start()
        else:
            insert_pos = len(text)

        next_text = text[insert_pos:]
        sep = '' if re.match(r'^[.,!?:;।॥\s]', next_text) else ' '
        text = text[:insert_pos].rstrip() + close_ch + sep + next_text.lstrip()
        added += 1

    return text.strip(), added


def _apply_bracket_commands(text: str) -> tuple[str, int]:
    text, n_close = _BRACKET_CLOSE.subn(')', text)
    text, n_open = _BRACKET_OPEN.subn('(', text)
    text, n_auto = _auto_close_unmatched(text, '(', ')')
    if n_open or n_close or n_auto:
        text = _snap_punctuation_spacing(text)
    return text, n_open + n_close + n_auto


# Same convention as the bracket command, for "put this in quotes" — covers
# "ఇన్వర్టెడ్ కామాస్", "కామాస్", "కొటేషన్స్", "కొటేషన్", "డబుల్ కోట్స్", and
# english loanword forms like "కోట్ ఓపెన్" / "అన్ కోట్". Emits book-quality
# curly quotes (“...”) and snaps whitespace.
_COMMAS = r'(?:ఇన్వర్టెడ్\s*కామాస్|కామాస్|కొటేషన్స్|కొటేషన్|డబుల్\s*కోట్స్)'
_QUOTE_CLOSE = re.compile(
    _W + rf'(?:'
         rf'{_COMMAS}\s*(?:ముగింపు|క్లోజ్|ఎండ్|స్టాప్)'
         r'|(?:క్లోజ్|స్టాప్|ఎండ్)\s*(?:ది\s*)?(?:కోట్|కొటేషన్స్|కొటేషన్|కామాస్)'
         r'|కోట్\s*(?:క్లోజ్|స్టాప్|ఎండ్|ముగింపు)'
         r'|అన్\s*కోట్'
         r')' + _E,
    re.IGNORECASE
)
_QUOTE_OPEN = re.compile(
    _W + rf'(?:'
         rf'{_COMMAS}(?:\s*(?:లో(?:\s*(?:ఉంచండి|పెట్టండి|రాయండి))?|ఓపెన్|స్టార్ట్))?'
         r'|(?:ఓపెన్|స్టార్ట్)\s*(?:ది\s*)?(?:కోట్|కొటేషన్స్|కొటేషన్)'
         r'|కోట్\s*(?:ఓపెన్|స్టార్ట్)'
         r')' + _E,
    re.IGNORECASE
)


def _apply_quote_commands(text: str) -> tuple[str, int]:
    text, n_close = _QUOTE_CLOSE.subn('”', text)
    text, n_open = _QUOTE_OPEN.subn('“', text)
    text, n_auto = _auto_close_unmatched(text, '“', '”')
    if n_open or n_close or n_auto:
        text = _snap_punctuation_spacing(text)
    return text, n_open + n_close + n_auto


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
