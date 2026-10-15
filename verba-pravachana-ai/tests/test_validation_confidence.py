from agents.validation_agent import validation_agent, CONFIDENCE_FLOOR


def _state(transcript, notes, **extra):
    return {"transcript": transcript, "notes": notes, "shlokas": [], **extra}


def test_low_confidence_flags_for_review_without_failing_other_checks():
    text = "ఇది ఒక పరీక్ష వాక్యం."
    out = validation_agent(_state(text, text, asr_confidence=0.4))
    types = [e["type"] for e in out["validation_errors"]]
    assert "low_asr_confidence" in types
    assert out["needs_manual_review"] is True


def test_confidence_at_or_above_floor_is_not_flagged():
    text = "ఇది ఒక పరీక్ష వాక్యం."
    out = validation_agent(_state(text, text, asr_confidence=CONFIDENCE_FLOOR))
    assert "low_asr_confidence" not in [e["type"] for e in out["validation_errors"]]
    assert out["validation_passed"] is True


def test_missing_confidence_is_not_flagged():
    text = "ఇది ఒక పరీక్ష వాక్యం."
    out = validation_agent(_state(text, text))
    assert "low_asr_confidence" not in [e["type"] for e in out["validation_errors"]]
