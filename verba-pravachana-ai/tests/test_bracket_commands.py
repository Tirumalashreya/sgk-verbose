"""The speaker says "bracket lo" / "bracket open" ... "bracket close" as a
spoken instruction, not words meant to appear in the notes. This must be
pure find-and-replace — the cue phrase swapped for punctuation, everything
else byte-for-byte untouched — never an LLM rewrite, so there is nothing
here that could invent or drop what was actually said."""
from agents.correction_agent import _apply_bracket_commands, correction_agent


def test_bracket_lo_opens_a_bracket():
    out, n = _apply_bracket_commands("ఇది బ్రాకెట్ లో ముఖ్యమైనది బ్రాకెట్ క్లోజ్ అని చెప్పారు")
    assert out == "ఇది (ముఖ్యమైనది) అని చెప్పారు"
    assert n == 2


def test_bracket_open_also_opens_a_bracket():
    out, n = _apply_bracket_commands("బ్రాకెట్ ఓపెన్ ఇది ముఖ్యం బ్రాకెట్ క్లోజ్")
    assert out == "(ఇది ముఖ్యం)"
    assert n == 2


def test_content_between_the_cues_is_preserved_exactly():
    # Nothing in between is read or reasoned about — it must survive verbatim,
    # including an otherwise-unrelated word that happens to contain similar sounds.
    inner = "ఇది చాలా పొడవైన వాక్యం, సంఖ్యలు మరియు పేర్లు కూడా ఉన్నాయి రామానుజులు"
    out, n = _apply_bracket_commands(f"ఆయన బ్రాకెట్ లో {inner} బ్రాకెట్ క్లోజ్ అన్నారు")
    assert inner in out
    assert out == f"ఆయన ({inner}) అన్నారు"


def test_text_without_any_bracket_cue_is_completely_unchanged():
    text = "ఇది సాధారణ వాక్యం బ్రాకెట్ అనే మాట లేకుండా."
    out, n = _apply_bracket_commands(text)
    assert out == text and n == 0


def test_unclosed_bracket_auto_closes_at_sentence_end():
    out, n = _apply_bracket_commands("ఇది బ్రాకెట్ లో ముగింపు లేదు")
    assert out == "ఇది (ముగింపు లేదు)"
    assert n >= 2


def test_unclosed_bracket_auto_closes_before_ani_clause():
    out, n = _apply_bracket_commands("ఈ విషయాన్ని బ్రాకెట్ లో గుర్తుంచుకోవాలి అని చెప్పారు. ఆ తరువాత")
    assert out == "ఈ విషయాన్ని (గుర్తుంచుకోవాలి) అని చెప్పారు. ఆ తరువాత"
    assert n >= 2


def test_plural_and_descriptive_bracket_phrases():
    out1, _ = _apply_bracket_commands("బ్రాకెట్లలో ముఖ్యమైన విషయం బ్రాకెట్ ఎండ్")
    assert out1 == "(ముఖ్యమైన విషయం)"

    out2, _ = _apply_bracket_commands("దీనిని బ్రాకెట్ లో ఉంచండి రహస్యం బ్రాకెట్ ముగింపు")
    assert out2 == "దీనిని (రహస్యం)"

    out3, _ = _apply_bracket_commands("స్టార్ట్ బ్రాకెట్ వేదం ఎండ్ బ్రాకెట్")
    assert out3 == "(వేదం)"


def test_the_word_bracket_alone_with_no_cue_word_after_it_is_left_alone():
    # Guards against over-matching: "బ్రాకెట్" must be followed by లో/ఓపెన్/క్లోజ్ to count.
    text = "బ్రాకెట్ అనేది ఒక పదం."
    out, n = _apply_bracket_commands(text)
    assert out == text and n == 0


def test_correction_agent_applies_bracket_commands_and_keeps_raw_transcript():
    transcript = "ఒక వాక్యం బ్రాకెట్ లో ఇంకో వాక్యం బ్రాకెట్ క్లోజ్ ముగింపు." + " " * 1  # pad past the 10-char skip guard
    state = correction_agent({"transcript": transcript})
    assert state["raw_transcript"] == transcript   # the untouched original is always kept
    assert "(" in state["transcript"] and ")" in state["transcript"]
    assert "బ్రాకెట్" not in state["transcript"]
