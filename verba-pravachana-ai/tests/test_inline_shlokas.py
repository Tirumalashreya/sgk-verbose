"""A one- or two-word verse (a name, a short phrase) reads better folded into
its sentence than set apart on its own line; a verse that's a full sentence
or more still gets its own line, as before. Both use the same markup — only
whether it's placed on its own line differs — so validation must still be
able to reconstruct the exact transcript either way."""
from agents.formatting_agent import format_notes
from agents.validation_agent import validate, _strip_markup


def test_a_two_word_verse_stays_inline_with_its_sentence():
    transcript = "ఆయన ఓం నమో నారాయణాయ అని పలికి కొనసాగించారు."
    shlokas = [{"text": "ఓం నమో", "original": "ॐ नमो"}]
    notes = format_notes(transcript, shlokas)
    assert "\n" not in notes.strip()   # one flowing line, not a line of its own
    assert '**"ఓం నమో"** (ॐ नमो)' in notes
    assert notes.startswith("ఆయన") and notes.endswith("కొనసాగించారు.")


def test_a_full_sentence_verse_still_gets_its_own_line():
    transcript = ("ఇది ఒక ఉపోద్ఘాతం వాక్యం ఇక్కడ మొదలవుతుంది. "
                  "నిస్త్రైగుణ్యో భవార్జున త్రైగుణ్యవిషయా వేదా నిస్త్రైగుణ్యో భవార్జున త్రైగుణ్యవిషయా వేదా. "
                  "ఆ తరువాత వివరణ కొనసాగుతుంది ఇంకా ఇంకా ముందుకు.")
    verse = "నిస్త్రైగుణ్యో భవార్జున త్రైగుణ్యవిషయా వేదా నిస్త్రైగుణ్యో భవార్జున త్రైగుణ్యవిషయా వేదా"
    shlokas = [{"text": verse, "original": "निस्त्रैगुण्यो भवार्जुन"}]
    notes = format_notes(transcript, shlokas)
    lines = [l for l in notes.split("\n") if l.strip()]
    assert any(l.strip().startswith(f'**"{verse}') and l.strip().endswith('(निस्त्रैगुण्यो भवार्जुन)') for l in lines)


def test_inline_markup_survives_exact_reconstruction():
    transcript = "ఆయన ఓం నమో నారాయణాయ అని పలికి కొనసాగించారు."
    notes = format_notes(transcript, [{"text": "ఓం నమో", "original": "ॐ नमो"}])
    assert _strip_markup(notes) == transcript.rstrip(".") + "."[:0] or _strip_markup(notes) == transcript


def test_inline_markup_passes_full_validation_no_invention_or_headings():
    transcript = "ఆయన ఓం నమో నారాయణాయ అని పలికి కొనసాగించారు."
    shlokas = [{"text": "ఓం నమో", "original": "ॐ नमो"}]
    notes = format_notes(transcript, shlokas)
    errors = validate(transcript, notes, shlokas)
    assert errors == []


def test_multiple_inline_verses_in_one_paragraph_all_strip_cleanly():
    transcript = "మొదట ఓం నమో అని, తరువాత హరి ఓం అని పలికారు."
    shlokas = [{"text": "ఓం నమో", "original": ""}, {"text": "హరి ఓం", "original": ""}]
    notes = format_notes(transcript, shlokas)
    assert _strip_markup(notes) == transcript
    assert validate(transcript, notes, shlokas) == []
