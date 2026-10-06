from graph.orchestrator import app

YOUTUBE_URL = "https://www.youtube.com/watch?v=u2_I4Wy4BNs"

chunk_index = 0
MAX_CHUNKS = 2

while chunk_index < MAX_CHUNKS:
    print(f"\n--- Processing chunk {chunk_index} ---")

    state = {
        "audio_path": None,
        "youtube_url": YOUTUBE_URL,
        "transcript": None,
        "detected_language": None,
        "shlokas": None,
        "segments": None,
        "summary": None,
        "key_teachings": None,
        "notes": None,
        "enhanced_notes": None,
        "chunk_index": chunk_index,
        "current_agent": None,
        "error": None
    }

    result = app.invoke(state)

    print(f"Chunk {chunk_index} done.")
    print(f"Summary: {result.get('summary', '')[:200]}")
    print(f"Needs manual review: {result.get('needs_manual_review')}")

    # Captions cover the whole video; stop instead of re-transcribing it from audio
    if result.get("caption_text") or result.get("error") == "video_ended":
        break

    chunk_index += 1
