from graph.state import VerbaState
import json, os
from agents.groq_llm_client import call as _groq_call, STRONG_MODEL
from agents.text_chunker import chunk_text
from dotenv import load_dotenv
load_dotenv()


def _transliterate(text: str) -> str:
    from indic_transliteration import sanscript
    from indic_transliteration.sanscript import transliterate
    return transliterate(text, sanscript.TELUGU, sanscript.IAST)


def _call(prompt: str) -> str:
    return _groq_call(prompt, api_key_env="GROQ_API_KEY_NOTES", model=STRONG_MODEL)


def _shloka_list_text(shlokas: list) -> str:
    lines = []
    for i, s in enumerate(shlokas, 1):
        text = (s.get("text") or "").strip()
        original = (s.get("original") or "").strip()
        lang = (s.get("language") or "").strip()
        if text:
            entry = f'{i}. Telugu script: "{text}"'
            if original:
                entry += f'\n   Original {lang} script: "{original}"'
            lines.append(entry)
    return "\n".join(lines)


def notes_generator_agent(state: VerbaState) -> VerbaState:
    transcript = state.get("transcript", "") or ""
    if not transcript.strip():
        state["notes"] = ""
        state["enhanced_notes"] = ""
        state["summary"] = ""
        state["current_agent"] = "notes_generation_done"
        return state

    shlokas = state.get("shlokas") or []
    shloka_context = _shloka_list_text(shlokas)

    print(f"[notes_generator] generating notes via Groq ({len(transcript)} chars, {len(shlokas)} shlokas detected)...")

    chunks = chunk_text(transcript, chunk_size=3000, overlap=200)
    print(f"[notes_generator] processing {len(chunks)} chunk(s)")

    notes_parts = []
    for i, chunk in enumerate(chunks):
        print(f"[notes_generator] chunk {i+1}/{len(chunks)}...")

        shloka_section = ""
        if shloka_context:
            shloka_section = f"""
DETECTED SHLOKAS (from shloka_detect agent):
These verses were identified in the transcript. When they appear, format them like this — TWO lines:
Line 1: **"<Telugu script transliteration>"**
Line 2: *(<original Tamil or Sanskrit script>)*

Detected shlokas:
{shloka_context}
"""

        prompt = f"""You are a faithful scribe for Telugu spiritual discourses.

Your job: present the transcript as clean, readable paragraph notes with proper structure.

FORMATTING RULES:
- Break the content into meaningful paragraphs based on topic/context — each paragraph 3-5 sentences
- Separate paragraphs with a blank line
- Do NOT add headings or titles
- Include EVERY sentence — do not skip or summarise anything
- Do NOT paraphrase — use the exact words from the transcript
- Output in Telugu script only. No English.

EMOTIONAL EXPRESSION RULES:
- Use ! at the end of sentences where the speaker is clearly emphatic, exclaiming, or making a strong point (e.g., repetition for stress, a sudden realisation, or a call to attention)
- Use "..." (double quotes) around key Sanskrit/Telugu terms, important concepts, or words the speaker consciously highlights — e.g., "సద్విద్య", "ఆత్మ", "అద్వితీయం"
- Use ? for rhetorical questions the speaker poses to the audience
- Only add these markers where they are genuinely implied by the spoken rhythm — do NOT invent emotion that is not in the transcript
{shloka_section}
SHLOKA HIGHLIGHTING RULE:
- Any Sanskrit shloka or Tamil pasuram must appear as TWO lines:
  Line 1: **"<Telugu script transliteration as spoken>"**
  Line 2: *(<original Tamil or Sanskrit script if you know it, else omit line 2>)*
- These are Sanskrit/Tamil words embedded mid-sentence — different rhythm from surrounding Telugu
- Even short verse fragments (4+ Sanskrit/Tamil words) must be highlighted this way
- Telugu explanation sentences are NEVER bolded or italicised

TRANSCRIPT:
{chunk}"""
        part = _call(prompt)
        if part:
            notes_parts.append(part)

    state["notes"] = "\n\n".join(notes_parts)
    state["enhanced_notes"] = state["notes"]
    state["transliterated_notes"] = _transliterate(state["notes"])

    summary_prompt = f"""Summarize this Telugu spiritual pravachanam in 2-3 lines.

RULES:
- Write ONLY in Telugu script. No English.
- Base the summary only on what is in the transcript.
- Do NOT add shlokas or quotes from your knowledge.

TRANSCRIPT:
{transcript[:3000]}"""

    state["summary"] = _call(summary_prompt)

    print("[notes_generator] done")
    state["current_agent"] = "notes_generation_done"
    return state
