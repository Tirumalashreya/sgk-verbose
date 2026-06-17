from graph.state import VerbaState
import json
from google import genai
import os
from dotenv import load_dotenv
load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def knowledge_structurer_agent(state: VerbaState) -> VerbaState:
    print("[knowledge_structurer] starting...")
    text=state.get("transcript")
    prompt = build_prompt(state)
    response = client.models.generate_content(model="gemini-2.5-flash-lite", contents=prompt)
    text = response.text or ""
    print(f"[knowledge_structurer] raw response: {text[:300]}")
    text = text.replace("```json", "").replace("```", "").strip()
    if not text:
        state["segments"] = []
        state["current_agent"] = "knowledge_structuring_done"
        return state
    try:
        result = json.loads(text)
        segments = result["segments"]
    except (json.JSONDecodeError, KeyError):
        print(f"[knowledge_structurer] JSON parse failed, defaulting to empty segments")
        segments = []
    print(f"[knowledge_structurer] done — {len(segments)} segments")
    return {"segments": segments}
def build_prompt(state):
    transcript = state["transcript"]
    return f""" you are a discourse analysis expert. Read this Telugu pravachanam transcript and classify each segment with a label. Labels are: teaching, story, shloka, philosophy, devotional. Return strictly as JSON.
  Output schema:
  {{
    "segments": [
      {{
        "text": "...",
        "label": "teaching/story/shloka/philosophy/devotional",
        "summary": "one line summary"
      }}
    ] 
  }}
  TRANSCRIPT:
{transcript}"""