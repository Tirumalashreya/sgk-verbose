from graph.state import VerbaState
import json, re
from agents.groq_llm_client import call as _groq_call, parallel_map, FAST_MODEL
from agents.text_chunker import chunk_text
from dotenv import load_dotenv
load_dotenv()

def _call(prompt):
    return _groq_call(prompt, api_key_env="GROQ_API_KEY_STRUCTURER", model=FAST_MODEL)

def _structure_chunk(chunk_text_str: str) -> list:
    prompt = _build_prompt(chunk_text_str)
    text = _call(prompt)
    text = re.sub(r'```(?:json)?', '', text).strip()
    if not text:
        return []
    start = text.find('{')
    if start != -1:
        depth, end = 0, start
        for i, ch in enumerate(text[start:], start):
            if ch == '{': depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    end = i
                    break
        text = text[start:end + 1]
    try:
        result = json.loads(text)
        if isinstance(result, dict):
            return result.get("segments", [])
    except (json.JSONDecodeError, TypeError):
        pass
    return []

def knowledge_structurer_agent(state: VerbaState) -> VerbaState:
    if state.get("live_piece"):
        # Same reason as shloka_detect_agent: this piece's segments are never
        # shown during the live preview and get fully redone at finalize time.
        return {"segments": []}
    print("[knowledge_structurer] starting...")
    transcript = state.get("transcript", "") or ""
    chunks = chunk_text(transcript, chunk_size=1500, overlap=150)
    print(f"[knowledge_structurer] processing {len(chunks)} chunk(s)")

    all_segments = []
    for segs in parallel_map(_structure_chunk, chunks):
        all_segments.extend(segs)

    print(f"[knowledge_structurer] done — {len(all_segments)} segments")
    return {"segments": all_segments}

def _build_prompt(transcript: str) -> str:
    return f"""You are a discourse analysis expert. Read this Telugu spiritual pravachanam transcript and classify each segment.
Labels: teaching, story, shloka, philosophy, devotional.
RULES:
- "text" field: keep the original text exactly as-is (Telugu/Sanskrit/Tamil)
- "summary" field: write the one-line summary in Telugu script only — no English
Return strictly as JSON.
Output schema:
{{
  "segments": [
    {{
      "text": "...",
      "label": "teaching/story/shloka/philosophy/devotional",
      "summary": "ఒక లైన్ సారాంశం తెలుగులో"
    }}
  ]
}}
TRANSCRIPT:
{transcript}"""
