"""The speaker says "ఇన్వర్టెడ్ కామాస్" ("inverted commas") ... "ఇన్వర్టెడ్ కామాస్
ముగింపు" ("...ending") as a spoken instruction to quote something, not words
meant to appear in the notes — the same convention as the bracket command.
Real recording: bare "ఇన్వర్టెడ్ కామాస్" opens (no "లో"/"ఓపెన్" was said), and
"ముగింపు" (not "క్లోజ్") closes it. Pure find-and-replace, never an LLM
rewrite — nothing here can invent or drop what was actually said."""
from agents.correction_agent import _apply_quote_commands, correction_agent


def test_bare_inverted_commas_opens_and_mugimpu_closes_a_real_example():
    # The exact spoken form from a real recording.
    text = "తెలిపిన అనంతరము ఇన్వర్టెడ్ కామాస్ వీరిని ఈ రీతిగా విడిచిపెట్టేసినామే అని ఇన్వర్టెడ్ కామాస్ ముగింపు వెనుకబడినందుకు"
    out, n = _apply_quote_commands(text)
    assert out == 'తెలిపిన అనంతరము " వీరిని ఈ రీతిగా విడిచిపెట్టేసినామే అని " వెనుకబడినందుకు'
    assert n == 2


def test_inverted_commas_lo_and_klose_also_work():
    out, n = _apply_quote_commands("ఇది ఇన్వర్టెడ్ కామాస్ లో ముఖ్యమైనది ఇన్వర్టెడ్ కామాస్ క్లోజ్ అని చెప్పారు")
    assert out == 'ఇది " ముఖ్యమైనది " అని చెప్పారు'
    assert n == 2


def test_quote_open_and_unquote_english_loanword_forms():
    out, n = _apply_quote_commands("అతను కోట్ ఓపెన్ నేను వస్తాను అన్ కోట్ అన్నాడు")
    assert out == 'అతను " నేను వస్తాను " అన్నాడు'
    assert n == 2


def test_content_between_the_cues_is_preserved_exactly():
    inner = "ఇది చాలా పొడవైన వాక్యం, సంఖ్యలు మరియు పేర్లు కూడా ఉన్నాయి రామానుజులు"
    out, n = _apply_quote_commands(f"ఆయన ఇన్వర్టెడ్ కామాస్ {inner} ఇన్వర్టెడ్ కామాస్ ముగింపు అన్నారు")
    assert inner in out
    assert out == f'ఆయన " {inner} " అన్నారు'


def test_text_without_any_quote_cue_is_completely_unchanged():
    text = "ఇది సాధారణ వాక్యం కోట్ అనే మాట లేకుండా, కోట అంటే ఊరు."
    out, n = _apply_quote_commands(text)
    assert out == text and n == 0


def test_bare_kot_alone_is_never_matched_its_an_ordinary_word_too():
    # "కోట్"/"కోట" (fort) is an everyday Telugu word — must never trigger alone.
    text = "గోల్కొండ కోట్ చాలా ప్రసిద్ధమైనది."
    out, n = _apply_quote_commands(text)
    assert out == text and n == 0


def test_correction_agent_applies_quote_commands_and_keeps_raw_transcript():
    transcript = "ఒక వాక్యం ఇన్వర్టెడ్ కామాస్ ఇంకో వాక్యం ఇన్వర్టెడ్ కామాస్ ముగింపు చివరి." + " " * 1
    state = correction_agent({"transcript": transcript})
    assert state["raw_transcript"] == transcript
    assert state["transcript"].count('"') == 2
    assert "ఇన్వర్టెడ్" not in state["transcript"]
