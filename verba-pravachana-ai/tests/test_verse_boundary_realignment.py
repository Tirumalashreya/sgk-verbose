"""A Tamil pasuram spelled phonetically in Telugu script has no hard
script-change signal to anchor on (unlike real Tamil Unicode or a Sanskrit
visarga) — the LLM has to judge, by meaning alone, where the verse ends and
the speaker's own Telugu narration begins. Real recordings showed it getting
that judgment wrong by exactly one neighbouring word, independently on either
edge. Once the candidate is confirmed against the verse library, the
library's own (correct) wording lets the boundary be re-found by sound
instead of trusted as the LLM guessed it — these are the two real cases that
were wrong, taken verbatim from an actual recording."""
from agents.shloka_detect_agent import _verify_with_library


def _one_shloka(context: str, wrong_text: str) -> dict:
    idx = context.find(wrong_text)
    return {
        "language": "Tamil", "llm_language": "Tamil", "script_certain": False, "type": "Paasuram",
        "text": wrong_text, "confidence": 0.9,
        "start_index": idx, "end_index": idx + len(wrong_text),
        "occurrences": [[idx, idx + len(wrong_text)]],
    }


def test_trailing_narration_word_is_dropped_from_the_pasuram():
    # The LLM over-extended into "గోపాలకుల" — the first word of the speaker's
    # own explanation right after the verse, not part of it.
    context = "అంటే లేదా ఆనాయర్ వలియ తలైవనాయ్ గోపాలకుల యందు బలిష్టుడైనటువంటి"
    s = _one_shloka(context, "వలియ తలైవనాయ్ గోపాలకుల")
    out = _verify_with_library(context, [s])[0]
    assert out["text"] == "వలియ తలైవనాయ్"
    assert "గోపాలకుల" not in out["text"]
    assert out["reference"]["number"] == 2826


def test_leading_and_trailing_narration_words_are_both_dropped():
    # "కూడా" ("also") leaked in from "పిమ్మట కూడా" before the verse, and
    # "మల్లెమొగ్గ" leaked in from the speaker's own description right after.
    context = "దొంగ అంటిని పిమ్మట కూడా తళవేళ్ మురువల్ పిన్నైక్కాయ్ మల్లెమొగ్గ వంటి చిరునవ్వు"
    s = _one_shloka(context, "కూడా తళవేళ్ మురువల్ పిన్నైక్కాయ్ మల్లెమొగ్గ")
    out = _verify_with_library(context, [s])[0]
    assert out["text"] == "తళవేళ్ మురువల్ పిన్నైక్కాయ్"
    assert "కూడా" not in out["text"] and "మల్లెమొగ్గ" not in out["text"]


def test_an_already_correct_boundary_is_left_exactly_as_is():
    # No narration bleeding in on either side — must stay byte-for-byte the same.
    context = "ఈ రోజు వలియ తలైవనాయ్ అని చెప్పారు"
    s = _one_shloka(context, "వలియ తలైవనాయ్")
    out = _verify_with_library(context, [s])[0]
    assert out["text"] == "వలియ తలైవనాయ్"
    assert out["start_index"] == s["start_index"] and out["end_index"] == s["end_index"]


def test_library_self_found_pasuram_is_realigned_too():
    # Same bug, different code path: find_pasurams() (library's own scan for
    # verses the LLM missed entirely) does its own window-sliding skeleton
    # match, with the same word-edge drift — a real example from a recording,
    # where the speaker repeated the verse's own opening word right before
    # reciting it ("...ఇమయోర్ [పలరుమ్ ఇమయోర్ పలరుమ్ మునివరుమ్] బ్రహ్మాదులు...").
    from agents.verse_library import find_pasurams
    context = "పడువారు ఎవరు అనినా? ఇమయోర్ పలరుమ్ ఇమయోర్ పలరుమ్ మునివరుమ్ బ్రహ్మాదులు సనకాదులును"
    found = find_pasurams(context)
    assert found, "library didn't find the pasuram at all — check the fixture itself"
    out = _verify_with_library(context, [])
    texts = [s["text"] for s in out]
    assert "ఇమయోర్ పలరుమ్ మునివరుమ్" in texts
    assert "బ్రహ్మాదులు" not in out[0]["text"]


def test_a_candidate_with_no_library_match_is_never_realigned():
    # No verse_library match at all — boundary must be untouched, nothing to verify against.
    context = "ఈ రోజు పూర్తిగా కల్పితమైన పదబంధం ఇక్కడ ఉంది అని చెప్పారు"
    s = _one_shloka(context, "పూర్తిగా కల్పితమైన పదబంధం")
    out = _verify_with_library(context, [s])[0]
    assert out["text"] == "పూర్తిగా కల్పితమైన పదబంధం"
    assert out.get("reference") is None
