import pytest
from agents.inline_terms import detect_inline_terms
from agents.formatting_agent import format_notes
from agents.validation_agent import validate, _strip_markup
from agents.verbatim import normalize_ws

def test_inline_tamil_terms_detection():
    transcript = "స్వామి వారు ఈ రోజు అడియేన్ అని చెప్పారు మరియు నమ్మాళ్వార్ తిరువడిగళే శరణం అన్నారు."
    norm = normalize_ws(transcript)
    
    # Run inline terms detection
    inline = detect_inline_terms(norm, existing_shlokas=[])
    assert len(inline) >= 3
    
    # Check that 'అడియేన్' is detected as Tamil inline term
    adiyen = next((t for t in inline if t["text"] == "అడియేన్"), None)
    assert adiyen is not None
    assert adiyen["original"] == "அடியேன்"
    assert adiyen["is_inline"] is True
    assert adiyen["language"] == "Tamil"

def test_inline_sanskrit_terms_detection():
    transcript = "విశిష్టాద్వైతం సిద్ధాంతంలో పరమాత్మ జీవాత్మ సంబంధం గురించి శ్రీభాష్యం చెబుతుంది."
    norm = normalize_ws(transcript)
    
    inline = detect_inline_terms(norm, existing_shlokas=[])
    bhashyam = next((t for t in inline if t["text"] == "శ్రీభాష్యం"), None)
    assert bhashyam is not None
    assert bhashyam["original"] == "श्रीभाष्यम्"
    assert bhashyam["is_inline"] is True
    assert bhashyam["language"] == "Sanskrit"

def test_formatting_keeps_inline_terms_inside_sentence():
    transcript = "స్వామి వారు అడియేన్ అని ప్రారంభించారు."
    norm = normalize_ws(transcript)
    
    shlokas = detect_inline_terms(norm, existing_shlokas=[])
    notes = format_notes(norm, shlokas)
    
    # Must be on a single line with inline markup, NOT split across multiple lines
    assert '\n' not in notes
    assert '**"అడియేన్"** (அடியேன்)' in notes
    
    # Stripping markup must equal the exact original transcript
    assert _strip_markup(notes) == norm
    assert validate(norm, notes, shlokas) == []

def test_inline_terms_do_not_overlap_with_recited_verses():
    # Transcript where 'అడియేన్' appears both inside a verse line and in narration
    verse_text = "ఆరావముదే అడియేన్ ఉడలం నిన్పాల్ అన్బాయే"
    transcript = f"స్వామి వారు అడియేన్ అంటూ {verse_text} అని పాడారు."
    norm = normalize_ws(transcript)
    
    v_start = norm.find(verse_text)
    v_end = v_start + len(verse_text)
    
    full_verse = {
        "language": "Tamil",
        "type": "Paasuram",
        "text": verse_text,
        "start_index": v_start,
        "end_index": v_end,
        "occurrences": [[v_start, v_end]],
    }
    
    inline = detect_inline_terms(norm, existing_shlokas=[full_verse])
    
    # Only the first 'అడియేన్' (outside the verse) should be tagged as an inline term
    assert len(inline) == 1
    assert inline[0]["start_index"] < v_start
