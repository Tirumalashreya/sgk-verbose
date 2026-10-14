"""Command-line run: one YouTube video (or a local audio file) → one set of notes."""
import sys
from graph.orchestrator import app

source = sys.argv[1] if len(sys.argv) > 1 else "https://www.youtube.com/watch?v=u2_I4Wy4BNs"
state = {"chunk_index": 0}
state["youtube_url" if source.startswith("http") else "audio_path"] = source

result = app.invoke(state)
print(f"Title: {result.get('video_title') or source}")
print(f"Transcript: {len(result.get('transcript') or '')} chars, notes: {len(result.get('notes') or '')} chars")
print(f"Summary: {(result.get('summary') or '')[:200]}")
print(f"Needs manual review: {result.get('needs_manual_review')}")
