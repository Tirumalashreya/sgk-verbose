"""A minute-piece of a recording in progress should only be transcribed —
shloka detection and topic structuring are wasted work during live preview
(nothing shown mid-recording uses them) and are redone correctly, once, over
the whole transcript when the recording stops. A verse split across two
one-minute pieces also can't be detected correctly from a single piece, so
skipping is a correctness fix, not just an efficiency one."""
import json

from agents import shloka_detect_agent as sda
from agents import knowledge_structurer_agent as ksa
from agents.summary_agent import summary_agent


def test_shloka_detect_skips_a_live_piece_without_calling_the_llm(monkeypatch):
    called = []
    monkeypatch.setattr(sda, "_call", lambda prompt: called.append(1) or json.dumps({"shlokas": []}))
    out = sda.shloka_detect_agent({"transcript": "ఓం నమో నారాయణాయ అని చెప్పారు", "live_piece": True})
    assert out == {"shlokas": []}
    assert not called  # the LLM was never called


def test_shloka_detect_still_runs_for_a_finished_recording(monkeypatch):
    called = []
    monkeypatch.setattr(sda, "_call", lambda prompt: called.append(1) or json.dumps({"shlokas": []}))
    sda.shloka_detect_agent({"transcript": "ఓం నమో నారాయణాయ అని చెప్పారు"})
    assert called  # live_piece not set (or False) — the real pass runs


def test_knowledge_structurer_skips_a_live_piece_without_calling_the_llm(monkeypatch):
    called = []
    monkeypatch.setattr(ksa, "_call", lambda prompt: called.append(1) or "{}")
    out = ksa.knowledge_structurer_agent({"transcript": "కొంత కథ", "live_piece": True})
    assert out == {"segments": []}
    assert not called


def test_knowledge_structurer_still_runs_for_a_finished_recording(monkeypatch):
    called = []
    monkeypatch.setattr(ksa, "_call", lambda prompt: called.append(1) or "{}")
    ksa.knowledge_structurer_agent({"transcript": "కొంత కథ"})
    assert called


def test_summary_already_had_this_pattern_unchanged():
    # Guards the convention these two now follow against drifting apart.
    out = summary_agent({"transcript": "ఏదో టెక్స్ట్", "live_piece": True})
    assert out == {"summary": ""}
