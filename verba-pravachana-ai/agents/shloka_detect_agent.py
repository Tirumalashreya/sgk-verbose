from graph.state import VerbaState
import json
from google import genai
import os
from dotenv import load_dotenv
load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def shloka_detect_agent(state: VerbaState) -> VerbaState:
    print("[shloka_detect] starting...")
    text=state.get("transcript")
    prompt=build_prompt(state)
    response = client.models.generate_content(model="gemini-2.5-flash-lite", contents=prompt)
    text=response.text
    text = text.replace("```json", "").replace("```", "").strip()
    try:
        result = json.loads(text)
        shlokas = result["shlokas"]
        print(f"[shloka_detect] done — found {len(shlokas)} shlokas")
    except (json.JSONDecodeError, KeyError):
        print(f"[shloka_detect] JSON parse failed, defaulting to empty shlokas")
        shlokas = []
    return {"shlokas": shlokas}
def build_prompt(state):
    transcript = state["transcript"]
    return f"""
    you are an expert spiritual discourse analysis agent.
    your task is to analyse pravachanam transcripts and detect:
    1.sanskrit shlokas
    2.telugu devotional verses
    3.tamil devotional verses
    4.scriptural quotations
    5.explanation given by speaker
    IMPORTANT DETECTION RULES:
    -DETECT SHLOKAS EVEN IF PARTIALLY SPOKEN
    -DETECT TRANSLITERATED SANSKRIT.
    -PRESERVE ORIGINAL WORDING EXACTLY
    -DO NOT AUTOCORRECT SANSKRIT
    -DISTINGUISH NORMAL SPEECH FROM POETIC/SCRIPTURAL METER.
    -TELUGU PADYAMS SHOULD BE CLASSIFIED SEPARATELY
    -TAMIL PASURAMS SHOULD BE CLASSIFIED SEPARATELY
OUTPUT FORMAT STRICTLY JSON
Schema:
{{
  "shlokas": [
    {{
      "language": "Sanskrit/Telugu/Tamil",
      "text": "...",
      "type": "Shloka/Padyam/Paasuram",
      "confidence": 0.0
    }}
  ],

  "explanations": [
    {{
      "text": "..."
    }}
  ]
}}

TRANSCRIPT:
{transcript}
"""

