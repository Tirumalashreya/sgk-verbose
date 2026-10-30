"""Timestamps are computed on demand by anchoring Gemini's real word-timing
pass (a separate, auxiliary transcription — never shown, only its timing is
used) onto the already-validated notes. These tests cover the pure
alignment/markup math without touching real audio or APIs; one end-to-end
test stubs the timestamp-mode transcription call."""
import os

import agents.notes_timestamp as nt


def test_offset_map_is_identity_with_no_markup():
    notes = "ఇది ఒక సాధారణ వాక్యం."
    pairs = nt.offset_map(notes)
    for target in (0, 5, len(notes)):
        assert nt.to_notes_offset(pairs, target) == target


def test_offset_map_resolves_a_verse_start_to_the_quoted_word_not_the_wrapper():
    notes = 'ముందు వాక్యం.\n**"ఓం నమో నారాయణాయ"** (ॐ नमो नारायणाय)\nతరువాత వాక్యం.'
    pairs = nt.offset_map(notes)
    words, offsets = nt.stripped_words(notes)
    i = words.index("ఓం")
    notes_pos = nt.to_notes_offset(pairs, offsets[i])
    assert notes[notes_pos:notes_pos + 2] == "ఓం"   # not "**" — the wrapper must be skipped


def test_offset_map_resolves_text_right_after_a_verse_correctly():
    notes = '**"ఓం నమో"** (ॐ नमो) తరువాత మాట.'
    pairs = nt.offset_map(notes)
    words, offsets = nt.stripped_words(notes)
    i = words.index("తరువాత")
    notes_pos = nt.to_notes_offset(pairs, offsets[i])
    assert notes[notes_pos:notes_pos + 6] == "తరువాత"


def test_stripped_words_excludes_the_bracketed_original():
    notes = '**"ఓం నమో"** (ॐ नमो) తరువాత మాట.'
    words, _ = nt.stripped_words(notes)
    assert "नमो" not in words and "ॐ" not in words
    assert words[:2] == ["ఓం", "నమో"]


def test_anchor_pieces_finds_the_earliest_match_per_chunk():
    a_tokens = ["ఒకటి", "రెండు", "మూడు", "నాలుగు"]
    a_chunk = [0, 0, 1, 1]
    b_tokens = ["ఒకటి", "రెండు", "మూడు", "నాలుగు"]
    anchors = nt.anchor_pieces(a_tokens, a_chunk, b_tokens)
    assert anchors[0] == 0 and anchors[1] == 2


def test_insert_markers_snaps_to_line_start_and_formats_real_seconds():
    notes = "మొదటి పంక్తి.\nరెండవ పంక్తి."
    second_line_pos = notes.index("రెండవ")
    out = nt.insert_markers(notes, {second_line_pos: 125.4})   # -> 02:05
    assert out.startswith("మొదటి పంక్తి.\n[02:05] రెండవ")


def test_insert_markers_never_splits_a_sentence():
    notes = "ఇది పొడవైన వాక్యం కొనసాగుతుంది ఇంకా ఇంకా."
    mid = notes.index("కొనసాగుతుంది")
    out = nt.insert_markers(notes, {mid: 61.0})
    assert out.startswith("[01:01] ")   # snapped to the line's own start, not mid-sentence


def test_insert_markers_dedupes_same_line_keeps_earliest():
    notes = "ఒకే పంక్తి ఇక్కడ ఉంటుంది."
    out = nt.insert_markers(notes, {0: 180.0, 5: 60.0})   # both land on line start after snapping
    assert out.count("[") == 1


def test_anchor_phrases_to_notes_uses_the_phrase_start_second():
    notes = "మొదటి వాక్యం ఇక్కడ. రెండవ వాక్యం అక్కడ."
    segments = [
        {"start": 12.5, "end": 14.0, "text": "మొదటి వాక్యం"},
        {"start": 40.25, "end": 42.0, "text": "రెండవ వాక్యం"},
    ]
    markers = nt.anchor_phrases_to_notes(segments, notes)
    assert 12.5 in markers.values() and 40.25 in markers.values()


def test_build_returns_none_with_no_audio_on_disk(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    session = {"id": "no-such-session", "notes": "ఏదో నోట్స్", "source_audio_path": None}
    assert nt.build(session) is None


def test_build_returns_none_with_empty_notes(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    session = {"id": "x", "notes": "", "source_audio_path": None}
    assert nt.build(session) is None


def test_available_false_without_audio(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    session = {"id": "none-here", "notes": "ఏదో", "source_audio_path": None}
    assert nt.available(session) is False


def test_build_end_to_end_with_stubbed_gemini_timestamps(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    os.makedirs("audio_input", exist_ok=True)
    source = os.path.join("audio_input", "upload_test.mp3")
    open(source, "wb").write(b"fake")

    import agents.gemini_asr as ga
    def fake_gemini_stt(path, mode=None, use_cache=True):
        segments = [
            {"start": 0.0, "end": 3.0, "text": "మొదటి నిమిషం మాట"},
            {"start": 65.0, "end": 68.0, "text": "రెండవ నిమిషం మాట"},
        ]
        return "", "te", segments, 0
    monkeypatch.setattr(ga, "gemini_stt", fake_gemini_stt)

    session = {
        "id": "upload-session-id",
        "notes": "మొదటి నిమిషం మాట కొనసాగుతుంది.\nరెండవ నిమిషం మాట కూడా కొనసాగుతుంది.",
        "source_audio_path": source,
    }
    assert nt.available(session) is True
    out = nt.build(session)
    assert out is not None
    assert "[00:00]" in out
    assert "[01:05]" in out
