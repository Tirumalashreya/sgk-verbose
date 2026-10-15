from agents.transliteration_agent import (
    transliterate_to_telugu, transliterate_to_devanagari, transliterate_to_roman,
)


def test_devanagari_converts_to_telugu_script():
    out = transliterate_to_telugu("कृष्ण")
    assert out and out != "కృష్ణ"[:0]  # non-empty
    assert all(0x0C00 <= ord(c) <= 0x0C7F for c in out if c.strip())


def test_telugu_source_is_passthrough():
    assert transliterate_to_telugu("కృష్ణ", source="telugu") == "కృష్ణ"


def test_empty_input_returns_empty():
    assert transliterate_to_telugu("") == ""
    assert transliterate_to_devanagari("") == ""
    assert transliterate_to_roman("") == ""


def test_telugu_to_devanagari_round_trips_to_devanagari_block():
    out = transliterate_to_devanagari("కృష్ణ")
    assert out and all(0x0900 <= ord(c) <= 0x097F for c in out if c.strip())


def test_failure_falls_back_to_original_text(monkeypatch):
    import agents.transliteration_agent as ta
    monkeypatch.setattr(ta, "devanagari_to_telugu", lambda text: "")
    assert transliterate_to_telugu("कृष्ण") == "कृष्ण"
