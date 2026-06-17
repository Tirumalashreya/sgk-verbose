import whisper
from graph.state import VerbaState

import torch
device = "mps" if torch.backends.mps.is_available() else "cpu"
print(f"[transcription] loading whisper model on {device}...")
model = whisper.load_model("small", device=device)
print(f"[transcription] model loaded on {device}")

def transcription_agent(state: VerbaState) -> VerbaState:
    path = state["audio_path"]
    print(f"[transcription] starting transcription of {path}...")
    result = model.transcribe(path, language="te")
    print(f"[transcription] done!")

    transcript = result["text"]
    print(f"[transcription] raw transcript (first 300 chars): {transcript[:300]}")

    state["transcript"] = transcript
    state["detected_language"] = result["language"]
    state["current_agent"] = "transcription_done"

    return state