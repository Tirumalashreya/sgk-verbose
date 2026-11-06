"""
Tests for the deterministic parts of the pipeline: shloka verification,
formatting and validation. LLM calls are stubbed.

Run from verba-pravachana-ai/:  python -m pytest tests
"""
import json
import os
import pytest

from agents import shloka_detect_agent as sda
from agents.correction_agent import _apply_term_fixes
from agents.formatting_agent import format_notes, formatting_agent
from agents.validation_agent import validate
from agents.verbatim import normalize_ws, SHLOKA_LINE

SANSKRIT = "యదా యదా హి ధర్మస్య గ్లానిర్భవతి భారత"
TAMIL = "పచ్చేవామలైహోల్మేని పవడవాయి కమలచ్చంగన్"
FILLER = "ధర్మాన్ని మనం బయట వెతకనవసరం లేదు అని చెప్పారు"


def _transcript(n_filler: int = 30) -> str:
    # No punctuation, like real Sarvam output; Sanskrit verse recited twice
    parts = [FILLER] * n_filler
    parts.insert(3, SANSKRIT)
    parts.insert(12, TAMIL)
    parts.insert(20, SANSKRIT)
    return "  ".join(parts)


def _stub_llm(monkeypatch, shlokas):
    monkeypatch.setattr(sda, "_call", lambda prompt: json.dumps({"shlokas": shlokas}))


def _detect(monkeypatch, transcript, shlokas):
    _stub_llm(monkeypatch, shlokas)
    return sda.shloka_detect_agent({"transcript": transcript})["shlokas"]


# ── shloka verification ───────────────────────────────────────────────────────

def test_rejects_verse_not_verbatim_in_transcript(monkeypatch):
    found = _detect(monkeypatch, _transcript(), [
        {"language": "Sanskrit", "text": "యదా యదా హి ధర్మస్య గ్లానిర్ భవతి భారత", "confidence": 0.9},  # LLM "fixed" spacing
        {"language": "Sanskrit", "text": "పరిత్రాణాయ సాధూనాం", "confidence": 0.9},  # from memory, never spoken
    ])
    assert found == []


def test_accepts_verbatim_verse_and_records_every_occurrence(monkeypatch):
    found = _detect(monkeypatch, _transcript(), [
        {"language": "Sanskrit", "text": f'"{SANSKRIT}"', "confidence": 0.9},  # wrapped in quotes
    ])
    assert len(found) == 1
    s = found[0]
    assert s["text"] == SANSKRIT and s["verified"]
    assert len(s["occurrences"]) == 2
    norm = normalize_ws(_transcript())
    assert norm[s["start_index"]:s["end_index"]] == SANSKRIT


def test_sanskrit_gets_devanagari_tamil_gets_no_original(monkeypatch):
    found = _detect(monkeypatch, _transcript(), [
        {"language": "Sanskrit", "text": SANSKRIT, "confidence": 0.9},
        {"language": "Tamil", "text": TAMIL, "confidence": 0.9},
    ])
    by_lang = {s["language"]: s for s in found}
    assert by_lang["Sanskrit"]["original"].startswith("यदा यदा हि धर्मस्य")
    assert by_lang["Tamil"]["original"] == ""
    assert by_lang["Tamil"]["type"] == "Paasuram"


def test_low_confidence_and_non_verse_languages_filtered(monkeypatch):
    found = _detect(monkeypatch, _transcript(), [
        {"language": "Sanskrit", "text": SANSKRIT, "confidence": 0.3},
        {"language": "Telugu", "text": FILLER, "confidence": 0.95},
    ])
    assert found == []


# ── formatting ────────────────────────────────────────────────────────────────

@pytest.fixture
def detected(monkeypatch):
    return _detect(monkeypatch, _transcript(), [
        {"language": "Sanskrit", "text": SANSKRIT, "confidence": 0.9},
        {"language": "Tamil", "text": TAMIL, "confidence": 0.9},
    ])


def test_notes_reproduce_transcript_exactly(detected):
    transcript = _transcript()
    notes = format_notes(transcript, detected)
    assert validate(transcript, notes, detected) == []


def test_shlokas_on_own_line_at_every_spoken_position(detected):
    notes = format_notes(_transcript(), detected)
    shloka_lines = [l for l in notes.split("\n") if SHLOKA_LINE.match(l)]
    assert len(shloka_lines) == 3  # Sanskrit twice, Tamil once
    assert shloka_lines[0] == f'**"{SANSKRIT}"** ({detected[0]["original"]})'
    assert f'**"{TAMIL}"**' in shloka_lines


def test_paragraphs_without_punctuation_use_length_fallback(detected):
    notes = format_notes(_transcript(60), detected)
    paragraphs = notes.split("\n\n")
    assert len(paragraphs) > 3
    for p in paragraphs[:-1]:
        assert 200 <= len(p) <= 900


def test_paragraph_break_never_splits_a_shloka():
    long_verse = " ".join([SANSKRIT] * 8)  # ~300 chars, straddles the 400-char target
    transcript = " ".join([FILLER] * 6 + [long_verse] + [FILLER] * 20)
    shlokas = [{"text": long_verse, "original": ""}]
    notes = format_notes(transcript, shlokas)
    assert f'**"{long_verse}"**' in notes.split("\n")
    assert validate(transcript, notes, shlokas) == []


def test_whisper_pauses_drive_paragraph_breaks():
    sentences = [f"{FILLER} {i}" for i in range(24)]
    transcript = " ".join(sentences)
    segments, t = [], 0.0
    for i, text in enumerate(sentences):
        segments.append({"start": t, "end": t + 3, "text": text})
        t += 3 + (2.0 if i % 6 == 5 else 0.2)  # long pause after every 6th sentence
    notes = format_notes(transcript, [], segments)
    paragraphs = notes.split("\n\n")
    assert len(paragraphs) == 4
    assert all(p.endswith(f"{FILLER} {i}") for p, i in zip(paragraphs, (5, 11, 17, 23)))


def test_formatting_agent_sets_frontend_fields(detected):
    state = formatting_agent({"transcript": _transcript(), "shlokas": detected})
    assert state["notes"] and state["enhanced_notes"] == state["notes"]
    assert state["transliterated_notes"].startswith("dharmānni")


def test_empty_transcript():
    assert format_notes("", []) == ""
    assert validate("", "", []) == []


# ── validation ────────────────────────────────────────────────────────────────

def test_validation_flags_invented_words():
    errors = validate(FILLER, FILLER + " శ్రీమన్నారాయణుడు", [])
    assert [e["type"] for e in errors] == ["no_invention"]


def test_validation_flags_headings():
    for heading in ("# ధర్మం", "**ధర్మం**", "1. ధర్మం", "THE MEANING OF DHARMA HERE"):
        errors = validate(FILLER, f"{heading}\n{FILLER}", [])
        assert "no_headings" in [e["type"] for e in errors], heading


def test_validation_flags_dropped_text():
    transcript = " ".join([FILLER] * 10)
    errors = validate(transcript, FILLER, [])
    assert "completeness" in [e["type"] for e in errors]


def test_validation_flags_reordered_text():
    a, b = "మొదటి వాక్యం", "రెండవ వాక్యం"
    errors = validate(f"{a} {b}", f"{b}\n\n{a}", [])
    assert [e["type"] for e in errors] == ["not_verbatim"]


def test_validation_flags_unverified_shloka():
    errors = validate(FILLER, FILLER, [{"text": "పరిత్రాణాయ సాధూనాం"}])
    assert [e["type"] for e in errors] == ["verbatim_shlokas"]


# ── term fixes ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("text, expected", [
    ("పెరుమాల్ చెప్పారు", "పెరుమాళ్ళ (பெருமாள்) చెప్పారు"),
    ("తొండలడి పొడి ఆడు రోజు", "తొండరడిప్పొడి ఆళ్వార్ (தொண்டரடிப்பொடி ஆழ்வார்) రోజు"),
    ("ఆడు సేవ", "ఆళ్వార్ (ஆழ்வார்) సేవ"),
    # Must not fire inside longer words (\b used to split at vowel signs)
    ("పెరుమాలు వచ్చారు", "పెరుమాలు వచ్చారు"),
    ("పెరియవార్చాన్ పిల్లై", "పెరియవార్చాన్ పిల్లై"),
    ("వాడు రోజు", "వాడు రోజు"),
])
def test_term_fixes_respect_telugu_word_boundaries(text, expected):
    assert _apply_term_fixes(text)[0] == expected


# ── Sarvam transcription ──────────────────────────────────────────────────────

def test_sarvam_retries_caches_and_marks_gaps(monkeypatch, tmp_path):
    import types
    from agents import transcription_agent as ta

    parts = []
    for i in range(12):
        p = tmp_path / f"part{i}.mp3"
        p.write_bytes(f"audio-{i}".encode() * 200)
        parts.append(str(p))
    calls = {}

    def transcribe(file, **_):
        name = os.path.basename(file.name)
        calls[name] = calls.get(name, 0) + 1
        if name == "part3.mp3" and calls[name] == 1:
            raise RuntimeError("503 temporarily unavailable")  # recovers on retry
        if name == "part7.mp3":
            raise RuntimeError("500 internal error")           # never recovers
        return types.SimpleNamespace(transcript=f"text{name[4:-4]}")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(ta, "sarvam_client", types.SimpleNamespace(speech_to_text=types.SimpleNamespace(transcribe=transcribe)))
    monkeypatch.setattr(ta, "_to_mp3_16k", lambda p: p)
    monkeypatch.setattr(ta, "_split_audio", lambda p, max_sec: parts)
    monkeypatch.setattr("time.sleep", lambda s: None)

    text, _, _, gaps = ta._sarvam_stt("x.mp3")
    expected = " ".join("[?]" if i == 7 else f"text{i}" for i in range(12))
    assert text == expected and gaps == 1
    assert calls["part3.mp3"] == 2 and calls["part7.mp3"] == 3

    # Second run: every successful piece comes from the cache, only the gap is retried
    before = dict(calls)
    assert ta._sarvam_stt("x.mp3")[0] == expected
    assert {k: calls[k] - before[k] for k in calls if calls[k] != before[k]} == {"part7.mp3": 3}


# ── upload de-duplication ─────────────────────────────────────────────────────

def test_identical_upload_while_processing_is_not_queued_again(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    import api

    monkeypatch.chdir(tmp_path)
    ran = []
    # Simulate a pipeline that is still running: record the call, never release the hash
    monkeypatch.setattr(api, "run_pipeline_from_audio", lambda *a: ran.append(a))
    monkeypatch.setattr(api, "_active_upload_hashes", set())
    client = TestClient(api.app)
    audio = b"same audio bytes" * 100

    first = client.post("/upload-audio", files={"file": ("talk.mp3", audio)}).json()
    second = client.post("/upload-audio", files={"file": ("talk.mp3", audio)}).json()
    other = client.post("/upload-audio", files={"file": ("other.mp3", audio + b"x")}).json()

    assert first["status"] == "processing" and other["status"] == "processing"
    assert second == {"status": "duplicate"}
    assert len(ran) == 2


def test_upload_hash_released_when_pipeline_finishes(monkeypatch):
    import api
    monkeypatch.setattr(api, "_run_pipeline_from_audio", lambda *a: (_ for _ in ()).throw(RuntimeError("boom")))
    api._active_upload_hashes.add("abc")
    with pytest.raises(RuntimeError):
        api.run_pipeline_from_audio("x.mp3", 0, 0, "abc")
    assert "abc" not in api._active_upload_hashes


# ── regressions from the first real 2-hour run ────────────────────────────────

def test_verse_cut_mid_word_or_before_punctuation_is_widened(monkeypatch):
    transcript = f"{FILLER} తం తమేవైతి కౌంతేయః. మరణించిన {FILLER} చెప్పారు గోవు పవిత్రమైన {FILLER}"
    found = _detect(monkeypatch, transcript, [
        {"language": "Sanskrit", "text": "తం తమేవైతి కౌంతేయ", "confidence": 0.9},   # stops before ః.
        {"language": "Sanskrit", "text": "పారు గోవు పవిత్రమైన", "confidence": 0.9},  # starts inside చెప్పారు
    ])
    assert [s["text"] for s in found] == ["తం తమేవైతి కౌంతేయః.", "చెప్పారు గోవు పవిత్రమైన"]
    notes = format_notes(transcript, found)
    assert validate(transcript, notes, found) == []


def test_formatter_widens_spans_even_for_unexpanded_input():
    transcript = f"{FILLER} తం తమేవైతి కౌంతేయః. {FILLER}"
    shlokas = [{"text": "తం తమేవైతి కౌంతేయ", "original": ""}]
    assert validate(transcript, format_notes(transcript, shlokas), shlokas) == []


def test_devanagari_verse_gets_telugu_second_line(monkeypatch):
    transcript = f"{FILLER} ॐ हरये नमः। {FILLER}"
    found = _detect(monkeypatch, transcript, [{"language": "Sanskrit", "text": "ॐ हरये नमः।", "confidence": 0.9}])
    assert found[0]["original"] == "ఓం హరయే నమః।"
    assert '**"ॐ हरये नमः।"** (ఓం హరయే నమః।)' in format_notes(transcript, found).split("\n")


# ── Groq key rotation ─────────────────────────────────────────────────────────

def test_groq_switches_key_immediately_on_rate_limit(monkeypatch):
    from agents import groq_llm_client as g
    for env, val in {"GROQ_API_KEY_STRUCTURER": "k1", "GROQ_API_KEY_SPARE1": "k2", "GROQ_API_KEY_SPARE2": "k1",
                     "GROQ_API_KEY_SHLOKA": "", "GROQ_API_KEY_NOTES": ""}.items():
        monkeypatch.setenv(env, val)
    monkeypatch.setattr(g, "_cooldown_until", {})
    monkeypatch.setattr(g, "_rotation", __import__("itertools").count())
    sleeps, used = [], []
    monkeypatch.setattr(g.time, "sleep", sleeps.append)

    def fake(key, *a):
        used.append(key)
        if key == "k1":
            raise RuntimeError("429 Rate limit reached ... Please try again in 1m3.5s")
        return "ok"
    monkeypatch.setattr(g, "_request", fake)

    assert g.call("p", "GROQ_API_KEY_STRUCTURER") == "ok"
    assert used == ["k1", "k2"] and sleeps == []          # no sleeping while another key works
    assert g.call("p", "GROQ_API_KEY_STRUCTURER") == "ok"
    assert used[2:] == ["k2"]                              # k1 still cooling down → skipped


def test_groq_waits_only_when_every_key_is_limited(monkeypatch):
    from agents import groq_llm_client as g
    for env in g._KEY_ENVS:
        monkeypatch.setenv(env, "")
    monkeypatch.setenv("GROQ_API_KEY_NOTES", "only")
    monkeypatch.setattr(g, "_cooldown_until", {})
    sleeps, calls = [], []
    monkeypatch.setattr(g.time, "sleep", lambda s: (sleeps.append(s), g._cooldown_until.clear()))

    def fake(key, *a):
        calls.append(key)
        if len(calls) == 1:
            raise RuntimeError("429 Please try again in 7.2s")
        return "ok"
    monkeypatch.setattr(g, "_request", fake)
    assert g.call("p", "GROQ_API_KEY_NOTES") == "ok"
    assert len(sleeps) == 1 and 7 < sleeps[0] <= 9


def test_parallel_map_keeps_order_spreads_keys_and_caps_workers(monkeypatch):
    import threading, time as _t
    from agents import groq_llm_client as g
    for env, val in zip(g._KEY_ENVS, ["a", "b", "c", "a", ""]):  # 3 distinct keys
        monkeypatch.setenv(env, val)
    monkeypatch.setattr(g, "_cooldown_until", {})
    monkeypatch.setattr(g, "_rotation", __import__("itertools").count())
    lock, live, peak, first_keys = threading.Lock(), [0], [0], []

    def fake(key, prompt, *a):
        with lock:
            live[0] += 1; peak[0] = max(peak[0], live[0]); first_keys.append(key)
        _t.sleep(0.05)
        with lock:
            live[0] -= 1
        return prompt.upper()
    monkeypatch.setattr(g, "_request", fake)

    items = [f"p{i}" for i in range(12)]
    out = g.parallel_map(lambda p: g.call(p, "GROQ_API_KEY_STRUCTURER"), items)
    assert out == [p.upper() for p in items]          # input order preserved
    assert peak[0] == 3                                # one in-flight call per distinct key
    assert {k: first_keys.count(k) for k in "abc"} == {"a": 4, "b": 4, "c": 4}  # evenly spread


def test_parallel_map_single_key_runs_sequentially(monkeypatch):
    from agents import groq_llm_client as g
    for env in g._KEY_ENVS:
        monkeypatch.setenv(env, "")
    monkeypatch.setenv("GROQ_API_KEY_NOTES", "only")
    assert g.parallel_map(lambda x: x * 2, [1, 2, 3]) == [2, 4, 6]


# ── memory ────────────────────────────────────────────────────────────────────

def test_memory_rerun_replaces_segments_instead_of_duplicating(monkeypatch, tmp_path):
    import chromadb
    from chromadb.utils.embedding_functions import EmbeddingFunction
    from agents import memory_agent as m

    class Fake(EmbeddingFunction):  # no model download in tests
        def __init__(self): pass
        def __call__(self, input): return [[float(len(t)), 1.0] for t in input]
        @staticmethod
        def name(): return "fake"
        def get_config(self): return {}
        @staticmethod
        def build_from_config(config): return Fake()

    real = chromadb.PersistentClient
    class Client:
        def __init__(self, path): self.c = real(path=str(tmp_path / path))
        def get_or_create_collection(self, name): return self.c.get_or_create_collection(name, embedding_function=Fake())
    monkeypatch.setattr(m.chromadb, "PersistentClient", Client)

    seg = lambda t: {"text": t, "label": "teaching", "summary": ""}
    m.memory_agent({"audio_path": "a.mp3", "chunk_index": 1, "segments": [seg("x"), seg("y")]})
    m.memory_agent({"audio_path": "a.mp3", "chunk_index": 2, "segments": [seg("z")]})
    m.memory_agent({"audio_path": "a.mp3", "chunk_index": 1, "segments": [seg("x2"), seg("y2"), seg("w2")]})

    col = Client("chroma_db").get_or_create_collection("notes_collection")
    docs = sorted(col.get()["documents"])
    assert docs == ["w2", "x2", "y2", "z"]   # chunk 1 replaced, chunk 2 untouched


# ── Gemini ASR ────────────────────────────────────────────────────────────────

def test_gemini_phrases_slice_transcript_by_byte_offsets():
    from agents.gemini_asr import _phrases
    text = "మొదటి ప్రశ్న ఏంటి? శ్రేయస్సు ఏది"
    raw = text.encode("utf-8")
    words, cursor = [], 0
    timing = [(0.0, 0.4), (0.4, 0.9), (0.9, 1.2), (2.0, 2.6), (2.6, 2.9)]  # pause before శ్రేయస్సు
    for w, (s, e) in zip(text.replace("?", "").split(), timing):
        a = raw.index(w.encode(), cursor); b = a + len(w.encode()); cursor = b
        words.append({"start_index": a, "end_index": b, "start_offset": f"{s}s", "end_offset": f"{e}s", "text": w})
    ph = _phrases(text, words, offset=100.0)
    assert [p["text"] for p in ph] == ["మొదటి ప్రశ్న ఏంటి", "శ్రేయస్సు ఏది"]
    assert ph[1]["start"] == 102.0 and ph[0]["end"] == 101.2


def test_gemini_failed_piece_is_covered_by_sarvam(monkeypatch):
    from agents import gemini_asr as g, transcription_agent as ta
    monkeypatch.setattr(ta, "_to_mp3_16k", lambda p: p)
    monkeypatch.setattr(ta, "_split_audio", lambda p, max_sec: ["p0", "p1", "p2"])
    def piece(path, client=None, use_cache=True):
        if path == "p1":
            raise RuntimeError("503 UNAVAILABLE high demand")
        return f"gemini-{path}"
    monkeypatch.setattr(g, "_llm_piece", piece)
    monkeypatch.setattr(g, "_sarvam_fallback", lambda p: f"sarvam-{p}")
    text, _, _, gaps = g.gemini_stt("x.mp3", "llm")
    assert text == "gemini-p0 sarvam-p1 gemini-p2" and gaps == 0

    monkeypatch.setattr(g, "_sarvam_fallback", lambda p: "")
    text, _, _, gaps = g.gemini_stt("x.mp3", "llm")
    assert text == "gemini-p0 [?] gemini-p2" and gaps == 1


# ── verse script (Tamil vs Sanskrit) ──────────────────────────────────────────

@pytest.mark.parametrize("text, llm, expected", [
    ("నవ్యతీతాః పితామహః", "Sanskrit", "Sanskrit"),          # visarga
    ("నచ పునరావర్తతే", "Sanskrit", "Sanskrit"),             # grammatical ending only
    ("తం తమేవైతి కౌంతేయ", "Sanskrit", "Sanskrit"),
    ("ॐ हरये नमः।", "Sanskrit", "Sanskrit"),               # already Devanagari
    ("విసిత్తిరత్తేర్వలైవ", "Sanskrit", "Tamil"),           # LLM mislabel seen in a real run
    ("ఇందిరన్ సిరువంతేర్మున్ నింద్రాని తిరువల్లికే", "Tamil", "Tamil"),
    ("మార్గళి త్తింగళ్ మది నిఱైంద నన్నాళాల్", "Sanskrit", "Tamil"),
])
def test_verse_script(text, llm, expected):
    from agents.verbatim import verse_script
    assert verse_script(text, llm) == expected


def test_tamil_verse_labelled_sanskrit_gets_no_devanagari(monkeypatch, tmp_path):
    from agents import verse_library as vl
    monkeypatch.setattr(vl, "LIBRARY", str(tmp_path / "missing.json"))  # without the verse library
    vl._index.cache_clear()
    transcript = f"{FILLER} విసిత్తిరత్తేర్వలైవ అంటారు {FILLER}"
    found = _detect(monkeypatch, transcript, [{"language": "Sanskrit", "text": "విసిత్తిరత్తేర్వలైవ", "confidence": 0.9}])
    assert found[0]["language"] == "Tamil" and found[0]["type"] == "Paasuram"
    assert found[0]["original"] == "" and found[0]["llm_language"] == "Sanskrit"


# ── Divya Prabandham library ──────────────────────────────────────────────────

@pytest.fixture
def tiny_library(monkeypatch, tmp_path):
    from agents import verse_library as vl
    lib = {"verses": [
        {"number": 1073, "lines": ["அந்தகன் சிறுவன் அரசர்-தம் அரசற்கு", "இந்திரன் சிறுவன் தேர் முன் நின்றானை"]},
        {"number": 3523, "lines": ["சித்திரத் தேர் வலவா திருச் சக்கரத்தாய் அருளாய்"]},
        {"number": 474, "lines": ["மார்கழித் திங்கள் மதி நிறைந்த நன்னாளால்"]},
    ]}
    path = tmp_path / "dp.json"
    path.write_text(json.dumps(lib, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(vl, "LIBRARY", str(path))
    vl._index.cache_clear()
    yield vl
    vl._index.cache_clear()


def test_library_finds_pasuram_heard_in_telugu_script(tiny_library):
    transcript = f"{FILLER} భగవంతుడు ఎంత గొప్పవాడండి? ఇందిరన్ సిరువంతేర్మున్ నింద్రాని తిరువల్లికే. {FILLER}"
    matches = tiny_library.find_pasurams(normalize_ws(transcript))
    assert [m["number"] for m in matches] == [1073]
    heard = normalize_ws(transcript)[matches[0]["start"]:matches[0]["end"]]
    assert "ఇందిరన్" in heard and "సిరువంతేర్మున్" in heard


def test_library_ignores_plain_telugu(tiny_library):
    assert tiny_library.find_pasurams(normalize_ws(" ".join([FILLER] * 30))) == []


def test_library_verifies_short_llm_verse(tiny_library):
    m = tiny_library.match_verse("విసిత్తిరత్తేర్వలైవ")
    assert m and m["number"] == 3523
    assert "(" not in tiny_library.original_line(m) and "3523" in tiny_library.original_line(m)


def test_shloka_step_adds_missed_pasuram_and_keeps_notes_verbatim(monkeypatch, tiny_library):
    transcript = f"{FILLER} ఇందిరన్ సిరువంతేర్మున్ నింద్రాని తిరువల్లికే {FILLER} విసిత్తిరత్తేర్వలైవ అంటారు {FILLER}"
    found = _detect(monkeypatch, transcript, [{"language": "Sanskrit", "text": "విసిత్తిరత్తేర్వలైవ", "confidence": 0.9}])
    refs = {s["reference"]["number"]: s.get("found_by", "llm") for s in found if s.get("reference")}
    assert refs == {1073: "library", 3523: "llm"}
    assert all(s["language"] == "Tamil" for s in found)
    notes = format_notes(transcript, found)
    assert "சித்திரத் தேர் வலவா" in notes
    assert validate(transcript, notes, found) == []


def test_without_library_nothing_changes(monkeypatch, tmp_path):
    from agents import verse_library as vl
    monkeypatch.setattr(vl, "LIBRARY", str(tmp_path / "missing.json"))
    vl._index.cache_clear()
    assert vl.find_pasurams("ఇందిరన్ సిరువంతేర్మున్ నింద్రాని") == [] and vl.match_verse("విసిత్తిరత్తేర్వలైవ") is None
    vl._index.cache_clear()


def test_gemini_empty_piece_is_a_gap_not_silence(monkeypatch):
    from agents import gemini_asr as g, transcription_agent as ta
    monkeypatch.setattr(ta, "_to_mp3_16k", lambda p: p)
    monkeypatch.setattr(ta, "_split_audio", lambda p, max_sec: ["p0", "p1", "p2"])
    monkeypatch.setattr(g, "_llm_piece", lambda path, client=None, use_cache=True: "" if path == "p1" else f"text-{path}")
    monkeypatch.setattr(g, "_sarvam_fallback", lambda p: "")
    text, _, _, gaps = g.gemini_stt("x.mp3", "llm")
    assert text == "text-p0 [?] text-p2" and gaps == 1


def test_everyday_tamil_words_are_not_pasuram_evidence():
    # "ఆళ్వార్" has a Tamil letter but is ordinary Telugu discourse vocabulary
    from agents.verbatim import _TAMIL_CUES
    from agents.verse_library import _EVERYDAY_TAMIL_WORDS
    plain = "అవతరించినటువంటి ఆళ్వార్లున్నారు పెరుమాళ్ళ సేవ"
    assert _TAMIL_CUES.search(plain)                                   # the raw cue fires...
    assert not _TAMIL_CUES.search(_EVERYDAY_TAMIL_WORDS.sub(" ", plain))  # ...but not after removing loanwords
    assert _TAMIL_CUES.search(_EVERYDAY_TAMIL_WORDS.sub(" ", "ఇందిరన్ సిరువంతేర్మున్ నింద్రాని"))


def test_groq_retries_a_cut_off_reply(monkeypatch):
    from agents import groq_llm_client as g
    for env in g._KEY_ENVS:
        monkeypatch.setenv(env, "")
    monkeypatch.setenv("GROQ_API_KEY_STRUCTURER", "k1")
    monkeypatch.setattr(g, "_cooldown_until", {})
    replies = iter([g._BadReply("cut off"), "good"])
    def fake(*a):
        r = next(replies)
        if isinstance(r, Exception):
            raise r
        return r
    monkeypatch.setattr(g, "_request", fake)
    monkeypatch.setattr(g.time, "sleep", lambda s: None)
    assert g.call("p", "GROQ_API_KEY_STRUCTURER") == "good"


# ── two listeners ─────────────────────────────────────────────────────────────

def test_dual_alignment_keeps_agreement_and_routes_real_disputes():
    from agents.dual_asr import align, merge
    a = "ఇది ప్రశ్న ఆరు ప్రశ్నలు అడిగాడు సౌనకాదులకు".split()          # Sarvam
    b = "ఇది ప్రశ్న. ఆరు ప్రశ్నలు అడిగారు శౌనకాదులకు".split()        # Gemini
    ops = align(a, [0] * len(a), b)
    disputes = [op for op in ops if "keep" not in op]
    # punctuation and the సౌ/శౌ spelling variant need no judge; అడిగాడు/అడిగారు is a real dispute
    assert len(disputes) == 1 and disputes[0]["a"] == ["అడిగాడు"] and disputes[0]["b"] == ["అడిగారు"]
    tokens, uncertain = merge(ops, {0: "A"})
    assert " ".join(tokens) == "ఇది ప్రశ్న. ఆరు ప్రశ్నలు అడిగాడు శౌనకాదులకు" and uncertain == []
    tokens, uncertain = merge(ops, {0: "?"})
    assert "అడిగారు" in tokens and uncertain[0]["sarvam"] == "అడిగాడు"


def test_dual_judge_may_only_answer_a_b_or_unsure(monkeypatch, tmp_path):
    import types as _t
    from agents import dual_asr as d, gemini_asr as g
    monkeypatch.chdir(tmp_path)
    clip = tmp_path / "c.mp3"; clip.write_bytes(b"audio")
    reply = _t.SimpleNamespace(text='{"1": "A", "2": "B", "3": "మూడు వందల", "4": "?"}')
    client = _t.SimpleNamespace(models=_t.SimpleNamespace(generate_content=lambda **k: reply))
    monkeypatch.setattr(g, "_get_client", lambda: client)
    items = [{"a": ["x"], "b": ["y"], "before": "", "after": ""}] * 4
    assert d._judge_chunk(str(clip), items, "m") == {"1": "A", "2": "B", "3": "?", "4": "?"}


def test_dual_alignment_does_not_pair_words_shifted_by_a_join():
    from agents.dual_asr import align
    a = "ధర్మము ఎవనిని శరణుజొచ్చెను ఎందుకు చెప్తారు కలియుగం".split()
    b = "ధర్మము ఎవరిని శరణు జొచ్చెను? ఎందుచేత? కలియుగం".split()
    disputes = [op for op in align(a, [0] * len(a), b) if "keep" not in op]
    assert len(disputes) == 1                       # one phrase-level dispute, not 4 nonsense pairs
    assert disputes[0]["a"][0] == "ఎవనిని" and disputes[0]["b"][-1] == "ఎందుచేత?"


# ── one recording → one set of notes ──────────────────────────────────────────

@pytest.fixture
def api_env(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    import api
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(api, "sessions_store", [])
    monkeypatch.setattr(api, "_active_upload_hashes", set())
    monkeypatch.setattr(api, "_live_recording_sessions", {})
    monkeypatch.setattr(api, "_last_stopped_sessions", {})
    monkeypatch.setattr(api, "_last_stopped_at", {})
    monkeypatch.setattr(api, "_save_chunk_result", lambda *a: None)
    text_runs = []

    class SyncThread:                      # run "background" finalize immediately
        def __init__(self, target, args=(), daemon=None): self.t, self.a = target, args
        def start(self): self.t(*self.a)
    monkeypatch.setattr(api.threading, "Thread", SyncThread)

    def fake_graph(state, chunk_index):
        minute = open(state["audio_path"], "rb").read().decode()
        return {"transcript": minute, "notes": minute, "shlokas": [], "segments": []}
    monkeypatch.setattr(api, "_run_graph", fake_graph)

    def fake_text_steps(transcript, chunk_index, source):
        text_runs.append(transcript)
        return {"notes": transcript, "summary": "one summary", "shlokas": [], "segments": [{"text": "s"}]}
    monkeypatch.setattr(api, "_run_text_steps", fake_text_steps)
    return api, TestClient(api.app), text_runs


def test_mic_recording_becomes_one_session_with_notes_built_once(api_env):
    api, client, text_runs = api_env
    client.post("/start-live")
    for minute in ("మొదటి నిమిషం", "రెండవ నిమిషం", "మూడవ నిమిషం"):
        client.post("/upload-audio", files={"file": ("chunk.webm", minute.encode())}, data={"live": "1"})
    assert len(api.sessions_store) == 1                     # preview: still one session
    client.post("/stop-session")
    assert len(api.sessions_store) == 1
    s = api.sessions_store[0]
    assert s["transcript"] == "మొదటి నిమిషం\nరెండవ నిమిషం\nమూడవ నిమిషం"
    assert text_runs == [s["transcript"]]                    # text steps ran once, over everything
    assert s["summary"] == "one summary" and s["pieces_recorded"] == 3
    assert "pieces" not in s and "pending" not in s


def test_recording_finalizes_only_after_its_last_piece(api_env, monkeypatch):
    api, client, text_runs = api_env
    client.post("/start-live")
    session = api._live_recording_sessions["dev"]
    session["pending"] = 1                                   # a minute still being processed
    client.post("/stop-session")
    assert text_runs == []                                   # not yet
    session["pieces"].append({"transcript": "చివరి నిమిషం"}); session["transcript"] = "చివరి నిమిషం"
    with api._live_lock:
        session["pending"] -= 1
    api._finalize_live_session(session)
    assert text_runs == ["చివరి నిమిషం"]


def test_recording_with_no_speech_saves_nothing(api_env):
    api, client, text_runs = api_env
    client.post("/start-live")
    client.post("/stop-session")
    assert api.sessions_store == [] and text_runs == []


def test_uploaded_file_is_one_session(api_env):
    api, client, _ = api_env
    client.post("/upload-audio", files={"file": ("talk.mp3", "మొత్తం ప్రవచనం".encode())})
    assert len(api.sessions_store) == 1 and api.sessions_store[0]["title"] == "talk"


def test_empty_sessions_are_dropped_on_load(monkeypatch, tmp_path):
    import api
    monkeypatch.chdir(tmp_path)
    (tmp_path / "sessions.json").write_text(json.dumps([
        {"id": "empty-1", "title": "Live Recording", "transcript": "", "notes": ""},
        {"id": "real-1", "title": "real", "transcript": "ప్రవచనం", "notes": "ప్రవచనం"}]), encoding="utf-8")
    assert [s["title"] for s in api._load_sessions()] == ["real"]
