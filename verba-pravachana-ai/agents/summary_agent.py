"""
2-3 line Telugu summary. This is the only LLM-written text shown to readers,
and it is always displayed as a summary — never mixed into the verbatim notes.
"""
import os
from graph.state import VerbaState
from agents.groq_llm_client import call as _groq_call, STRONG_MODEL
from dotenv import load_dotenv
load_dotenv()


def summary_agent(state: VerbaState) -> VerbaState:
    transcript = state.get("transcript", "") or ""
    # Optional extra — the notes are the full verbatim transcript either way
    if not transcript.strip() or os.getenv("GENERATE_SUMMARY", "1") == "0" or state.get("live_piece"):
        return {"summary": ""}

    prompt = f"""Summarize this Telugu spiritual pravachanam in 2-3 lines.

RULES:
- Write ONLY in Telugu script. No English.
- Base the summary only on what is in the transcript.
- Do NOT add shlokas or quotes from your knowledge.
- Write numbers in Telugu words, never digits.

TRANSCRIPT:
{transcript[:3000]}"""

    summary = _groq_call(prompt, api_key_env="GROQ_API_KEY_NOTES", model=STRONG_MODEL)
    print(f"[summary] done ({len(summary)} chars)")
    return {"summary": summary}
