from graph.state import VerbaState
import yt_dlp
import os

def listener_agent(state: VerbaState) -> VerbaState:
    # If audio was uploaded directly (live mic mode), skip YouTube download
    if state.get("audio_path"):
        state["current_agent"] = "listening_done"
        return state

    youtube_url = state.get("youtube_url")
    chunk_index = state.get("chunk_index", 0)
    os.makedirs("audio_input", exist_ok=True)
    output_path = f"audio_input/chunk_{chunk_index}.mp3"

    start_sec = chunk_index * 30
    end_sec = start_sec + 30

    try:
        from yt_dlp.utils import download_range_func
        ranges = download_range_func(None, [(start_sec, end_sec)])
    except ImportError:
        ranges = None

    ydl_opts = {
        "format": "bestaudio/best",
        "quiet": True,
        "outtmpl": f"audio_input/chunk_{chunk_index}.%(ext)s",
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "ios", "web"]
            }
        },
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "128",
        }],
    }

    if ranges:
        ydl_opts["download_ranges"] = ranges
        ydl_opts["force_keyframes_at_cuts"] = True

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([youtube_url])

    state["audio_path"] = output_path
    state["current_agent"] = "listening_done"
    return state
