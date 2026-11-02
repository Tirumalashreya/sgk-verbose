"""The speaker sometimes marks a verse-source boundary aloud — "first moolam",
"ఒకటో మూలం", "moolam 2", "మూలం వన్" (ASR's Telugu-script spelling of spoken
English "moolam one"), "para 3", number before or after the noun, digit,
ordinal word, or transliterated. From that marker up to the next one (or the
end), everything is one paragraph, regardless of length or pauses. If no
marker is ever spoken, paragraphing is untouched. Each such paragraph also
gets a Telugu-only heading ("మూలం N") in format_headings — a display label
kept separate from the notes text, never embedded in it, since validation's
exact-transcript check would (rightly) reject a word the speaker never said."""
from agents.formatting_agent import format_notes, format_headings, _build_notes
from agents.validation_agent import validate


def test_telugu_ordinal_markers_each_start_their_own_paragraph():
    transcript = (
        "ఒకటో మూలం అని చెప్పి ఈ శ్లోకం గురించి వివరిస్తాను. ఇది చాలా ముఖ్యమైనది. "
        "రెండో మూలం అని చెప్పి వేరే విషయం మాట్లాడతాను. ఇది వేరు కథ."
    )
    notes = format_notes(transcript, [])
    paragraphs = notes.split("\n\n")
    assert len(paragraphs) == 2
    assert paragraphs[0].startswith("ఒకటో మూలం")
    assert paragraphs[1].startswith("రెండో మూలం")


def test_english_and_mixed_digit_forms_are_all_recognized():
    transcript = (
        "first moolam ఇక్కడ మొదలవుతుంది. కొంచెం వివరణ. "
        "moolam 2 ఇక్కడ మొదలవుతుంది. ఇంకొంచెం వివరణ. "
        "para 3 ఇక్కడ మొదలవుతుంది. చివరి వివరణ."
    )
    notes = format_notes(transcript, [])
    paragraphs = notes.split("\n\n")
    assert len(paragraphs) == 3
    assert paragraphs[0].startswith("first moolam")
    assert paragraphs[1].startswith("moolam 2")
    assert paragraphs[2].startswith("para 3")


def test_text_before_the_first_marker_keeps_default_paragraphing():
    transcript = (
        "ఈ రోజు ప్రారంభంలో కొన్ని మాటలు చెప్తాను. ఇది పరిచయం మాత్రమే. "
        "ఒకటో మూలం అని చెప్పి ఈ శ్లోకం గురించి వివరిస్తాను."
    )
    notes = format_notes(transcript, [])
    paragraphs = notes.split("\n\n")
    assert len(paragraphs) == 2
    assert paragraphs[0].startswith("ఈ రోజు ప్రారంభంలో")
    assert paragraphs[1].startswith("ఒకటో మూలం")


def test_no_marker_anywhere_leaves_default_behavior_untouched():
    transcript = "ఇది ఒక సాధారణ వాక్యం. ఇంకొక వాక్యం ఇక్కడ ఉంది."
    with_default = format_notes(transcript, [])
    assert with_default == transcript   # short text, single paragraph, unchanged


def test_marker_paragraphs_still_reconstruct_exactly_no_hallucination():
    transcript = (
        "ఒకటో మూలం అని చెప్పి ఈ శ్లోకం గురించి వివరిస్తాను. "
        "రెండో మూలం అని చెప్పి వేరే విషయం మాట్లాడతాను."
    )
    notes = format_notes(transcript, [])
    errors = validate(transcript, notes, [])
    assert errors == []


def test_telugu_script_spelling_of_spoken_english_numbers_is_recognized():
    """The real bug this was built to fix: a speaker mixing English into
    Telugu says "moolam one" / "moolam two", and ASR writes that phonetically
    in Telugu script (మూలం వన్ / మూలం టు), not as the Latin word "one" and not
    as the native Telugu ordinal "ఒకటో" — a third spelling the first version
    of this feature missed entirely."""
    transcript = (
        "అస్మద్గురుభ్యో నమః ఇవాళ ఏం చెప్పుకుంటున్నామంటే తెలుగు ఇంగ్లీష్ "
        "మూలం వన్ నేను ఇంకా మధ్యలో ఉన్నాను. ఇవాళ దివ్యప్రబంధం చెప్పుకుంటున్నాము. "
        "మూలం టు నా పేరు శ్రేయా."
    )
    notes = format_notes(transcript, [])
    paragraphs = notes.split("\n\n")
    assert len(paragraphs) == 3
    assert paragraphs[1].startswith("మూలం వన్")
    assert paragraphs[2].startswith("మూలం టు")
    headings = format_headings(transcript, [])
    assert headings == {1: "మూలం 1", 2: "మూలం 2"}


def test_headings_are_telugu_only_regardless_of_spoken_language():
    transcript = "first moolam ఇక్కడ మొదలవుతుంది. moolam 2 ఇక్కడ కొనసాగుతుంది."
    headings = format_headings(transcript, [])
    assert headings == {0: "మూలం 1", 1: "మూలం 2"}


def test_headings_absent_when_no_marker_is_spoken():
    transcript = "ఇది ఒక సాధారణ వాక్యం. ఇంకొక వాక్యం ఇక్కడ ఉంది."
    assert format_headings(transcript, []) == {}


def test_plain_next_paragraph_instruction_starts_a_new_paragraph_with_no_heading():
    """"తరువాత పేరా" ("next paragraph") carries no number — a real recording
    used exactly this as a plain paragraph-break instruction. It should split
    the paragraph like a moolam marker, but — unlike a moolam marker — it is
    a dictation command (like correction_agent.py's "bracket lo"), so it must
    not appear in the notes text at all, and never produces a heading."""
    transcript = (
        "భగవానుడొసగగా వీరు పొందినటువంటిది. "
        "తరువాత పేరా. దూత ప్రేషణము అను దాని ద్వారా తమ యొక్క ఆర్తిని తెలిపారు."
    )
    notes, headings, cleaned_transcript = _build_notes(transcript, [])
    paragraphs = notes.split("\n\n")
    assert len(paragraphs) == 2
    assert "తరువాత పేరా" not in notes
    assert paragraphs[1].startswith("దూత ప్రేషణము")
    assert headings == {}
    # Validation compares against the transcript with the same instruction
    # removed — exactly what formatting_agent writes back to state["transcript"]
    # before validation runs, the same way correction_agent.py's fixes do.
    errors = validate(cleaned_transcript, notes, [])
    assert errors == []


def test_next_paragraph_instruction_combines_with_numbered_moolam_markers():
    transcript = (
        "ఒకటో మూలం ఇక్కడ మొదలవుతుంది. "
        "తరువాత పేరా ఇంకో విషయం. "
        "రెండో మూలం ఇక్కడ మొదలవుతుంది."
    )
    notes = format_notes(transcript, [])
    paragraphs = notes.split("\n\n")
    assert len(paragraphs) == 3
    assert paragraphs[0].startswith("ఒకటో మూలం")
    assert "తరువాత పేరా" not in notes
    assert paragraphs[1].startswith("ఇంకో విషయం")
    assert paragraphs[2].startswith("రెండో మూలం")
    assert format_headings(transcript, []) == {0: "మూలం 1", 2: "మూలం 2"}
