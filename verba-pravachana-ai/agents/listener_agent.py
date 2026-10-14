from graph.state import VerbaState
import yt_dlp
import os
import glob
import shutil

# yt-dlp needs a JS runtime for YouTube. Override with YTDLP_NODE_PATH, else use node on PATH.
_NODE_PATH = os.getenv("YTDLP_NODE_PATH") or shutil.which("node")
_JS_RUNTIMES = {"node": {"path": _NODE_PATH} if _NODE_PATH else {}}

def listener_agent(state: VerbaState) -> VerbaState:
    if state.get("audio_path"):
        state["current_agent"] = "listening_done"
        return state

    youtube_url = state.get("youtube_url")
    chunk_index = state.get("chunk_index", 0)
    os.makedirs("audio_input", exist_ok=True)

    # ── Step 1: get video metadata (duration + title) ──────────────────────
    info_opts = {
        "quiet": True,
        "noplaylist": True,
        "js_runtimes": _JS_RUNTIMES,
    }
    with yt_dlp.YoutubeDL(info_opts) as ydl:
        info = ydl.extract_info(youtube_url, download=False)
    duration   = info.get("duration") or 0
    video_title = info.get("title", "")
    print(f"[listener] url={youtube_url[:60]} title={video_title!r} duration={duration} type={info.get('_type','video')}")
    if video_title and not state.get("video_title"):
        state["video_title"] = video_title

    # ── Step 2: YouTube captions (Telugu or Tamil), if the video has them ───
    caption_base = "audio_input/captions"
    cap_opts = {
        "quiet": True,
        "noplaylist": True,
        "writeautomaticsub": True,
        "writesubtitles": True,
        "subtitleslangs": ["te", "ta", "te-IN", "ta-IN"],
        "subtitlesformat": "vtt",
        "skip_download": True,
        "outtmpl": caption_base,
        "js_runtimes": _JS_RUNTIMES,
    }
    for old in glob.glob(f"{caption_base}*.vtt"):
        os.remove(old)
    try:
        with yt_dlp.YoutubeDL(cap_opts) as ydl:
            ydl.download([youtube_url])
    except Exception as e:
        print(f"[listener] subtitle download failed ({e.__class__.__name__}), falling back to audio")
    vtt_files = glob.glob(f"{caption_base}*.vtt")
    if vtt_files:
        caption_text = _parse_vtt(vtt_files[0])
        print(f"[listener] found YouTube captions ({len(caption_text)} chars) — skipping transcription")
        state["audio_path"] = None
        state["caption_text"] = caption_text
        state["current_agent"] = "captions_ready"
        return state
    print("[listener] no YouTube captions available — downloading the audio")

    # ── Step 3: the whole audio, once — transcription splits long audio itself ──
    video_id = info.get("id") or "video"
    ydl_opts = {
        "format": "bestaudio/best",
        "quiet": True,
        "noplaylist": True,
        "outtmpl": f"audio_input/yt_{video_id}.%(ext)s",
        "extractor_args": {"youtube": {"player_client": ["android", "web"]}},
        "js_runtimes": _JS_RUNTIMES,
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "128"}],
    }
    output_path = f"audio_input/yt_{video_id}.mp3"
    if not os.path.exists(output_path):
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([youtube_url])
    if not os.path.exists(output_path) or os.path.getsize(output_path) < 5000:
        raise RuntimeError("could not download the video's audio")

    print(f"[listener] downloaded full audio ({duration}s, {os.path.getsize(output_path)//1024}KB)")
    state["audio_path"] = output_path
    state["current_agent"] = "listening_done"
    return state


def _parse_vtt(path: str) -> str:
    """Extract plain text from a .vtt subtitle file, deduplicating lines."""
    seen = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # Skip header, timestamps, empty lines
            if not line or line.startswith("WEBVTT") or "-->" in line or line.isdigit():
                continue
            # Remove HTML tags like <c> </c>
            import re
            line = re.sub(r"<[^>]+>", "", line).strip()
            if line and (not seen or seen[-1] != line):
                seen.append(line)
    return "\n".join(seen)
