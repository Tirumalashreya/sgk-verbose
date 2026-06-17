from graph.state import VerbaState
import json
from google import genai
import os
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor
load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def _call(prompt):
    return client.models.generate_content(model="gemini-2.5-flash-lite", contents=prompt).text.strip()

def notes_generator_agent(state: VerbaState) -> VerbaState:
    print("[notes_generator] starting — running 3 Gemini calls in parallel...")
    with ThreadPoolExecutor(max_workers=3) as executor:
        f1 = executor.submit(_call, build_prompt_exact(state))
        f2 = executor.submit(_call, build_prompt_enhanced(state))
        f3 = executor.submit(_call, build_prompt_summary(state))
        state["notes"] = f1.result()
        state["enhanced_notes"] = f2.result()
        state["summary"] = f3.result()

    print("[notes_generator] done — notes, enhanced notes, summary ready")
    state["current_agent"] = "notes_generation_done"
    return state
    
    
def build_prompt_exact(state):
    segments = state.get("segments", [])
    segments_json = json.dumps(segments, ensure_ascii=False, indent=2)
    return f"""You are a faithful scribe for Telugu spiritual discourses.
Your job is to reproduce the pravachanam as exact notes — line by line, segment by segment.
DO NOT add your own words, explanations, or interpretations. Stay 100% faithful to what was said.
For every segment with label "shloka", wrap it exactly like this:
[SHLOKA BOX START]
<shloka text here>
[SHLOKA BOX END]
For all other segments, write them as clean notes preserving the original meaning.
SEGMENTS:
{segments_json}"""

def build_prompt_enhanced(state):
    segments = state.get("segments", [])
    shlokas = state.get("shlokas", [])
    segments_json = json.dumps(segments, ensure_ascii=False, indent=2)
    shlokas_json = json.dumps(shlokas, ensure_ascii=False, indent=2)
    return f"""You are an expert in Telugu spiritual discourses, Sanskrit scriptures, and Vedantic philosophy.
Generate AI-enhanced notes from this pravachanam. For each segment:
- For "teaching" segments: explain the teaching in simple terms and add deeper context
- For "philosophy" segments: elaborate on the philosophical concept with examples
- For "story" segments: retell the story clearly and state the moral or message
- For "devotional" segments: preserve as-is with a brief meaning
- For "shloka" segments: wrap in a box AND add the meaning, scripture source, and significance:
[SHLOKA BOX START]
<shloka text>
Meaning: <meaning in simple Telugu/English>
Source: <scripture name if known>
Significance: <why Guru Garu quoted this here>
[SHLOKA BOX END]
SEGMENTS:
{segments_json}
DETECTED SHLOKAS WITH SOURCES:
{shlokas_json}"""

def build_prompt_summary(state):
    transcript = state.get("transcript", "")
    return f"""You are summarizing a Telugu spiritual pravachanam for a devotee.
Write a concise 2-3 line summary of the entire session — what was the main topic, what key message did the Guru convey, and what is the devotee's key takeaway.
Keep it simple, warm, and faithful to the spirit of the discourse.
TRANSCRIPT:
{transcript}"""