"""A pasuram the ASR wrote in real Tamil script (not spelled phonetically in
Telugu, which the LLM detector's prompt assumes) used to sit in the transcript
correctly transcribed and simply never get flagged. Catching it needs no
model — a long run of genuine Tamil Unicode already is the verse."""
import agents.shloka_detect_agent as sda
from agents.verbatim import tamil_to_telugu, normalize_ws
from agents.transliteration_agent import transliterate_to_telugu

TAMIL_VERSE = "அவனுருவம் இவ்வுருவுகள். அவனுருவம் இவ்வுருவுகள். உளநலனெனில். உளநலனெனில்."


def _mostly_telugu(text: str) -> bool:
    # indic_transliteration doesn't map every Tamil-specific phoneme (e.g. the
    # dental ன has no distinct Telugu letter) — a handful of untransliterated
    # characters can remain. "mostly converted" is the honest bar, not "every
    # character", and it's also a clear signal that conversion ran at all.
    letters = [c for c in text if c.strip() and c not in ".,!?"]
    telugu = [c for c in letters if 0x0C00 <= ord(c) <= 0x0C7F]
    return bool(letters) and len(telugu) / len(letters) >= 0.8


def test_tamil_to_telugu_produces_telugu_script():
    out = tamil_to_telugu(TAMIL_VERSE)
    assert out != TAMIL_VERSE and _mostly_telugu(out)


def test_transliterate_to_telugu_dispatches_tamil_source():
    assert transliterate_to_telugu(TAMIL_VERSE, source="tamil") == tamil_to_telugu(TAMIL_VERSE)


def test_finds_a_native_tamil_verse_with_no_prior_detections():
    transcript = f"ఇంకో పాశురంలోకి వెళ్దామా? {TAMIL_VERSE} దానికి అర్థాన్ని చెప్తున్నారు."
    norm = normalize_ws(transcript)
    found = sda._native_tamil_candidates(norm, [])
    assert len(found) == 1
    s = found[0]
    assert s["text"] == TAMIL_VERSE.strip(" .") or TAMIL_VERSE.strip() in s["text"]
    assert s["language"] == "Tamil" and s["type"] == "Paasuram"
    assert s["original"]  # the Telugu reading line is filled in
    assert _mostly_telugu(s["original"])


def test_ignores_a_short_tamil_name_not_a_recited_verse():
    transcript = "అతను ராமానுజన் అని చెప్పారు."   # a short Tamil-origin name, not a verse
    norm = normalize_ws(transcript)
    assert sda._native_tamil_candidates(norm, []) == []


def test_skips_a_span_already_taken_by_an_earlier_detection():
    transcript = f"ఈ శ్లోకం: {TAMIL_VERSE} ముగిసింది."
    norm = normalize_ws(transcript)
    start = norm.find(TAMIL_VERSE.split()[0])
    end = start + len(TAMIL_VERSE)
    assert sda._native_tamil_candidates(norm, [(start, end)]) == []


def test_end_to_end_via_shloka_detect_agent_with_an_empty_llm_pass(monkeypatch):
    monkeypatch.setattr(sda, "_call", lambda prompt: '{"shlokas": []}')
    transcript = f"ఇంకో పాశురంలోకి వెళ్దామా? {TAMIL_VERSE} దానికి అర్థాన్ని చెప్తున్నారు."
    out = sda.shloka_detect_agent({"transcript": transcript})["shlokas"]
    assert len(out) == 1
    assert out[0]["language"] == "Tamil" and out[0]["found_by"] == "native_script"
