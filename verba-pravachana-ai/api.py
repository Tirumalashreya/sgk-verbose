from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import threading
import os
import uuid
from datetime import datetime
from graph.orchestrator import app as langgraph_app
from agents.rag_agent import rag_agent

app = FastAPI()


# ── Sidecar helpers ────────────────────────────────────────────────────────────
def _chunk_result_path(audio_path: str) -> str:
    return audio_path.rsplit(".", 1)[0] + ".result.json"


def _save_chunk_result(audio_path: str, result: dict):
    try:
        with open(_chunk_result_path(audio_path), "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[pipeline] could not save chunk result sidecar: {e}")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass


SESSIONS_FILE = "sessions.json"

def _load_sessions():
    try:
        with open(SESSIONS_FILE) as f:
            sessions = json.load(f)
    except Exception:
        return []
    # A session with no transcript and no notes is a leftover of a recording
    # that captured nothing (e.g. Stop pressed straight away) — never show it
    return [x for x in sessions if (x.get("transcript") or "").strip() or (x.get("notes") or "").strip()]

def _save_sessions():
    try:
        with open(SESSIONS_FILE, "w") as f:
            json.dump(sessions_store, f, ensure_ascii=False)
    except Exception as e:
        print(f"[sessions] save failed: {e}")

import json


def _review_fields(result: dict, chunk_index: int) -> dict:
    """Validation outcome for one chunk, in the shape stored on sessions."""
    return {
        "needs_manual_review": bool(result.get("needs_manual_review")),
        "validation_errors": [{**e, "chunk_index": chunk_index} for e in (result.get("validation_errors") or [])],
    }


def _merge_review(session: dict, result: dict, chunk_index: int):
    """Fold one chunk's validation outcome into a multi-chunk session."""
    review = _review_fields(result, chunk_index)
    session["needs_manual_review"] = bool(session.get("needs_manual_review")) or review["needs_manual_review"]
    session["validation_errors"] = (session.get("validation_errors") or []) + review["validation_errors"]


manager = ConnectionManager()
event_loop: asyncio.AbstractEventLoop | None = None
stop_event = threading.Event()
sessions_store: list[dict] = _load_sessions()
_pipeline_thread: threading.Thread | None = None
_live_session_id: int = 0
_pipeline_semaphore = threading.Semaphore(1)  # one pipeline at a time — Ollama is single-threaded
_live_recording_session: dict | None = None   # the mic recording currently being captured
_live_lock = threading.Lock()                 # guards each live session's "pending" piece count
_live_by_id: dict[str, dict] = {}            # mic recordings made since start-up, by id (for "continue")
_active_upload_hashes: set[str] = set()  # uploads queued or processing — identical re-uploads are ignored
RESUME_WINDOW_MINUTES = 15  # how long a crash/restart may leave a live session resumable — matches the
                            # app's own "continue the previous recording?" window, for the same reason


@app.on_event("startup")
async def startup():
    global event_loop
    event_loop = asyncio.get_event_loop()
    _recover_live_sessions()


def _recover_live_sessions():
    """A live recording's continuity (which id the next minute-piece belongs to)
    only lived in memory — a crash or restart used to silently split it into two
    recordings, the same bug /merge-sessions exists to clean up after. Every
    minute already lands durably in sessions.json via _save_live_preview; the
    only thing missing was restoring *which* saved session is still being
    recorded into. Reuses the exact "continue" construction /start-live already
    uses for the Continue prompt — recovery is just that, triggered here instead
    of by the app."""
    global _live_recording_session
    now = datetime.utcnow()
    in_progress = [s for s in sessions_store if s.get("live_in_progress")]
    if not in_progress:
        return
    # Only one recording can really be "the one still in progress" — the most
    # recently updated marker is it; any others are leftovers from an earlier
    # crash and get closed out properly instead of left stuck.
    in_progress.sort(key=lambda s: s.get("last_piece_at") or s.get("created_at") or "", reverse=True)
    newest, *rest = in_progress
    age_minutes = (now - datetime.fromisoformat(newest.get("last_piece_at") or newest.get("created_at"))).total_seconds() / 60
    if age_minutes <= RESUME_WINDOW_MINUTES:
        _live_recording_session = _build_continuation(newest)
        _live_by_id[newest["id"]] = _live_recording_session
        print(f"[live] resumed in-progress recording {newest['id'][:8]} after restart ({age_minutes:.1f} min old)")
    else:
        rest = [newest] + rest  # too old to still count as "the same recording in progress"
    for s in rest:
        print(f"[live] finalizing orphaned in-progress recording {s['id'][:8]}")
        threading.Thread(target=_finalize_live_session, args=(_build_continuation(s),), daemon=True).start()


def _build_continuation(earlier: dict) -> dict:
    """The in-memory shape for a live session that continues an earlier
    (possibly unfinished) one: its saved text becomes a fixed prefix, and new
    minute-pieces are appended after it."""
    session = {
        **{k: earlier.get(k) for k in ("id", "type", "title", "created_at", "notes", "enhanced_notes",
                                        "transliterated_notes", "summary", "asr_provider")},
        "transcript": earlier.get("transcript") or "",
        "raw_transcript": earlier.get("raw_transcript") or earlier.get("transcript") or "",
        "shlokas": earlier.get("shlokas") or [], "segments": earlier.get("segments") or [],
        "prefix": {k: earlier.get(k) for k in ("transcript", "raw_transcript", "notes",
                                                "transliterated_notes", "shlokas")},
        "prior_pieces": int(earlier.get("pieces_done") or earlier.get("pieces_recorded") or 0),
        "pieces": [], "pending": 0, "stopped": False, "live": True,
        "live_in_progress": True, "last_piece_at": datetime.utcnow().isoformat(),
    }
    return session


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


class SessionRequest(BaseModel):
    youtube_url: str


@app.post("/start-session")
async def start_session(data: SessionRequest, background_tasks: BackgroundTasks):
    global _pipeline_thread
    # Stop any currently running pipeline
    stop_event.set()
    if _pipeline_thread and _pipeline_thread.is_alive():
        _pipeline_thread.join(timeout=3)
    stop_event.clear()
    background_tasks.add_task(run_pipeline, data.youtube_url)
    return {"status": "started", "youtube_url": data.youtube_url}


@app.post("/stop-session")
async def stop_session():
    """Stop a YouTube run or a mic recording. A recording's notes are rebuilt
    once over the whole transcript as soon as its last piece is processed."""
    global _live_session_id, _live_recording_session
    stop_event.set()
    _live_session_id += 1
    session, _live_recording_session = _live_recording_session, None
    if session is not None:
        with _live_lock:
            session["stopped"] = True
            session["stopped_at"] = datetime.utcnow().isoformat()
            ready = session["pending"] == 0
        for stored in sessions_store:          # so the app can offer "continue" right away
            if stored.get("id") == session["id"]:
                stored["stopped_at"] = session["stopped_at"]
        if ready:
            threading.Thread(target=_finalize_live_session, args=(session,), daemon=True).start()
    return {"status": "stopped"}


class StartLiveRequest(BaseModel):
    continue_id: str | None = None   # add to this earlier recording instead of starting new notes


@app.post("/start-live")
async def start_live(data: StartLiveRequest | None = None):
    global _live_recording_session, _live_session_id
    _live_session_id += 1
    continue_id = data.continue_id if data else None
    if continue_id in _live_by_id:
        # Still in memory (maybe still finishing): reopen it; its next stop rebuilds the notes over everything
        session = _live_by_id[continue_id]
        with _live_lock:
            session["stopped"] = False
        _live_recording_session = session
        return {"status": "ok", "continued": continue_id}
    earlier = next((s for s in sessions_store if continue_id and s.get("id") == continue_id), None)
    if earlier is not None:
        # Continue: same notes, same id; the new minutes are appended to its transcript
        _live_recording_session = _build_continuation(earlier)
        _live_by_id[earlier["id"]] = _live_recording_session
        return {"status": "ok", "continued": earlier["id"]}
    _live_recording_session = {
        "id": str(uuid.uuid4()),
        "type": "chunk_complete",
        "title": "Live Recording – " + datetime.now().strftime("%d %b %Y, %H:%M"),
        "created_at": datetime.utcnow().isoformat(),
        "transcript": "", "notes": "", "enhanced_notes": "", "transliterated_notes": "",
        "summary": "", "shlokas": [], "segments": [],
        "pieces": [],          # per-minute results, in recording order (preview only)
        "pending": 0,          # pieces uploaded but not yet processed
        "stopped": False,
        "live": True,
        "live_in_progress": True,      # cleared once finalized — lets a restart find and resume this
        "last_piece_at": datetime.utcnow().isoformat(),
        "pieces_done": 0,              # real minute-pieces processed, for an accurate resume after a restart
    }
    _live_by_id[_live_recording_session["id"]] = _live_recording_session
    return {"status": "ok"}


class SearchRequest(BaseModel):
    query: str


@app.post("/search")
async def search(data: SearchRequest):
    result = rag_agent(data.query)
    return {"result": result}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/sessions")
async def get_sessions():
    return {"sessions": sessions_store}


@app.get("/sessions/{session_id}/timestamps")
async def get_timestamps(session_id: str, force: bool = False):
    """Notes with [MM:SS] markers, anchored to the real audio — computed
    once per session and cached on it (notes_timestamped), since building
    it re-transcribes the recording's audio. 404 if there's no audio left
    on disk to anchor against; the app checks this before offering the
    option, so a 404 here means the option shouldn't have been shown."""
    from fastapi import HTTPException
    session = next((s for s in sessions_store if s.get("id") == session_id), None)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if not force and session.get("notes_timestamped"):
        return {"notes_timestamped": session["notes_timestamped"]}

    from agents import notes_timestamp as nt
    if not nt.available(session):
        raise HTTPException(status_code=404, detail="No audio left on disk to build timestamps from")

    def _build_locked():
        with _pipeline_semaphore:   # don't contend with an active recording's own transcription
            return nt.build(session)
    out = await asyncio.get_event_loop().run_in_executor(None, _build_locked)
    if out is None:
        raise HTTPException(status_code=404, detail="Could not align any audio to this recording's notes")
    session["notes_timestamped"] = out
    _save_sessions()
    return {"notes_timestamped": out}


class UpdateNotesRequest(BaseModel):
    notes: str


@app.put("/sessions/{session_id}/notes")
async def update_notes(session_id: str, data: UpdateNotesRequest):
    """A manual correction from the Reading screen's edit mode. Replaces the
    notes text outright — no re-validation, this is a human overriding the
    pipeline's output on purpose. Clears any cached timestamped version,
    since it was built from the text before this edit and would no longer
    line up; the next request for it rebuilds fresh."""
    from fastapi import HTTPException
    session = next((s for s in sessions_store if s.get("id") == session_id), None)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    session["notes"] = data.notes
    session["enhanced_notes"] = data.notes
    session["edited"] = True
    session.pop("notes_timestamped", None)
    _save_sessions()
    _broadcast({"type": "chunk_complete", "chunk_index": session.get("chunk_index", 0),
                "title": session.get("title"), "notes": data.notes})
    return {"status": "saved"}


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    global sessions_store
    original_len = len(sessions_store)
    sessions_store = [s for s in sessions_store if str(s.get("id", "")) != session_id]
    if len(sessions_store) == original_len:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Session not found")
    _save_sessions()
    return {"status": "deleted"}


class ReprocessRequest(BaseModel):
    chunk_index: int


@app.post("/reprocess")
async def reprocess(data: ReprocessRequest, background_tasks: BackgroundTasks):
    """Re-run LLM agents (shloka detect + structurer + notes) on a saved transcript. Skips Sarvam."""
    # Find the sidecar file for this chunk
    sidecar_candidates = [
        f"audio_input/live_chunk_{data.chunk_index}.mp3",
        f"audio_input/live_chunk_{data.chunk_index}.webm",
        f"audio_input/live_chunk_{data.chunk_index}.m4a",
        f"audio_input/live_chunk_{data.chunk_index}.wav",
    ]
    audio_path = None
    for c in sidecar_candidates:
        if os.path.exists(c.rsplit(".", 1)[0] + ".result.json"):
            audio_path = c
            break
    if audio_path is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"No sidecar found for chunk {data.chunk_index}")
    sidecar_path = audio_path.rsplit(".", 1)[0] + ".result.json"
    with open(sidecar_path, encoding="utf-8") as f:
        saved = json.load(f)
    transcript = saved.get("transcript", "")
    if not transcript:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Sidecar has no transcript")
    background_tasks.add_task(_run_reprocess, data.chunk_index, audio_path, transcript)
    return {"status": "reprocessing", "chunk_index": data.chunk_index, "transcript_chars": len(transcript)}


def _run_text_steps(transcript: str, chunk_index: int, source: str) -> dict:
    """Every step after transcription, run once over a whole transcript."""
    from agents.shloka_detect_agent import shloka_detect_agent
    from agents.knowledge_structurer_agent import knowledge_structurer_agent
    from agents.summary_agent import summary_agent
    from agents.formatting_agent import formatting_agent
    from agents.validation_agent import validation_agent
    from agents.memory_agent import memory_agent
    state = _new_state(audio_path=source, transcript=transcript, chunk_index=chunk_index)
    for step in (shloka_detect_agent, knowledge_structurer_agent, summary_agent,
                 formatting_agent, validation_agent, memory_agent):
        state = {**state, **step(state)}
    return state


def _run_reprocess(chunk_index: int, audio_path: str, transcript: str):
    print(f"[reprocess] starting for chunk {chunk_index} ({len(transcript)} chars)...")
    state = _run_text_steps(transcript, chunk_index, audio_path)
    chunk = _session_from_result({**state, "transcript": transcript}, None, chunk_index)
    _save_chunk_result(audio_path, chunk)

    # Update existing session if present, otherwise append
    global sessions_store
    for i, s in enumerate(sessions_store):
        if s.get("chunk_index") == chunk_index:
            sessions_store[i] = {**s, **chunk, "id": s["id"], "title": s.get("title") or chunk["title"]}
            break
    else:
        sessions_store.append(chunk)
    _save_sessions()
    _broadcast(chunk)
    print(f"[reprocess] done for chunk {chunk_index}")


def _new_state(**values) -> dict:
    base = {"audio_path": None, "youtube_url": None, "transcript": None, "detected_language": None,
            "shlokas": None, "segments": None, "summary": None, "key_teachings": None, "notes": None,
            "enhanced_notes": None, "chunk_index": 0, "current_agent": None, "error": None}
    return {**base, **values}


def _broadcast(message: dict):
    if event_loop:
        asyncio.run_coroutine_threadsafe(manager.broadcast(message), event_loop)


_AGENT_LABELS = {
    "listener": "Downloading Audio", "transcription": "Transcribing Audio", "correction": "Correcting Transcript",
    "shloka_detector": "Detecting Shlokas", "knowledge_structurer": "Structuring Knowledge", "summary": "Summarising",
    "formatting": "Formatting Notes", "validation": "Verifying Notes", "memory": "Saving to Memory",
}


def _run_graph(state: dict, chunk_index: int) -> dict:
    """Run the whole pipeline once, broadcasting progress after each step."""
    result = {}
    for event in langgraph_app.stream(state):
        for node, output in event.items():
            result.update(output)
            _broadcast({"type": "agent_progress", "agent": node, "label": _AGENT_LABELS.get(node, node),
                        "chunk_index": chunk_index})
            if node == "transcription" and output.get("transcript"):
                _broadcast({"type": "stage_result", "chunk_index": chunk_index, "stage": "transcription",
                            "transcript": output["transcript"]})
            elif node == "shloka_detector":
                _broadcast({"type": "stage_result", "chunk_index": chunk_index, "stage": "shlokas",
                            "shlokas": output.get("shlokas") or []})
            elif node == "formatting":
                _broadcast({"type": "stage_result", "chunk_index": chunk_index, "stage": "notes",
                            "notes": output.get("notes") or "", "enhanced_notes": output.get("enhanced_notes") or "",
                            "transliterated_notes": output.get("transliterated_notes") or ""})
    return result


def _session_from_result(result: dict, title: str | None, chunk_index: int, **extra) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "type": "chunk_complete",
        "chunk_index": chunk_index,
        "title": title or result.get("video_title") or "Pravachanam",
        "created_at": datetime.utcnow().isoformat(),
        "summary": result.get("summary"),
        "notes": result.get("notes"),
        "enhanced_notes": result.get("enhanced_notes"),
        "transliterated_notes": result.get("transliterated_notes"),
        "shlokas": result.get("shlokas") or [],
        "segments": result.get("segments") or [],
        "transcript": result.get("transcript"),
        "raw_transcript": result.get("raw_transcript"),
        "asr_provider": result.get("asr_provider"),
        "asr_report": result.get("asr_report"),
        "youtube_url": result.get("youtube_url"),
        "source_audio_path": result.get("audio_path"),   # for timestamp backfill — None if YouTube captions were used
        **_review_fields(result, chunk_index),
        **extra,
    }


def _report_failure(e: Exception, chunk_index: int):
    import traceback
    print(f"[PIPELINE ERROR] chunk {chunk_index}: {e}")
    traceback.print_exc()
    # Tell the app, so an upload never sits on "processing" after it has failed
    _broadcast({"type": "pipeline_error", "chunk_index": chunk_index, "message": str(e)[:300]})


@app.post("/upload-audio")
async def upload_audio(background_tasks: BackgroundTasks, file: UploadFile = File(...),
                       live: str | None = Form(None)):
    """A whole audio file → one session. With live=1 it is the next one-minute
    piece of the mic recording in progress instead."""
    global _live_session_id, _live_recording_session
    import hashlib
    content = await file.read()
    digest = hashlib.sha1(content).hexdigest()
    if digest in _active_upload_hashes:
        print(f"[upload] identical file already queued/processing — ignoring duplicate ({file.filename})")
        return {"status": "duplicate"}
    _active_upload_hashes.add(digest)
    os.makedirs("audio_input", exist_ok=True)
    ext = os.path.splitext(file.filename or "chunk.webm")[1] or ".webm"

    if live == "1":
        if _live_recording_session is None:      # piece arrived without /start-live
            await start_live()
        session = _live_recording_session
        with _live_lock:
            piece = len(session["pieces"])
            session["pieces"].append(None)
            session["pending"] += 1
        audio_path = f"audio_input/live_{session['id'][:8]}_{session.get('prior_pieces', 0) + piece}{ext}"
        with open(audio_path, "wb") as f:
            f.write(content)
        background_tasks.add_task(run_live_piece, session, piece, audio_path, digest)
        return {"status": "processing", "piece": piece}

    _live_session_id += 1
    chunk_index = len(sessions_store)
    audio_path = f"audio_input/upload_{digest[:12]}{ext}"
    with open(audio_path, "wb") as f:
        f.write(content)
    title = os.path.splitext(file.filename or "")[0] or None
    background_tasks.add_task(run_pipeline_from_audio, audio_path, chunk_index, _live_session_id, digest, title)
    return {"status": "processing", "chunk_index": chunk_index}


def run_pipeline_from_audio(audio_path: str, chunk_index: int, session_id: int = 0,
                            digest: str | None = None, title: str | None = None):
    try:
        with _pipeline_semaphore:
            _run_pipeline_from_audio(audio_path, chunk_index, session_id, title)
    finally:
        _active_upload_hashes.discard(digest)


def _run_pipeline_from_audio(audio_path: str, chunk_index: int, session_id: int = 0, title: str | None = None):
    """An uploaded file: one pass over the whole file, one session."""
    try:
        result = _run_graph(_new_state(audio_path=audio_path, chunk_index=chunk_index), chunk_index)
        session = _session_from_result(result, title, chunk_index)
        _save_chunk_result(audio_path, session)
        sessions_store.append(session)
        _save_sessions()
        _broadcast(session)
    except Exception as e:
        _report_failure(e, chunk_index)


def run_live_piece(session: dict, piece: int, audio_path: str, digest: str):
    """One minute of a mic recording, transcribed for the live preview. The final
    notes are built once over the whole recording when it stops."""
    try:
        with _pipeline_semaphore:
            result = _run_graph(_new_state(audio_path=audio_path, chunk_index=piece, live_piece=True), piece)
        session["pieces"][piece] = result
        done = [p for p in [session.get("prefix")] + session["pieces"] if p]
        session["transcript"] = "\n".join(p.get("transcript") or "" for p in done).strip()
        session["raw_transcript"] = "\n".join(p.get("raw_transcript") or p.get("transcript") or "" for p in done).strip()
        session["notes"] = "\n\n".join(p.get("notes") or "" for p in done).strip()
        session["enhanced_notes"] = session["notes"]
        session["transliterated_notes"] = "\n\n".join(p.get("transliterated_notes") or "" for p in done).strip()
        session["shlokas"] = [s for p in done for s in (p.get("shlokas") or [])]
        session["asr_provider"] = result.get("asr_provider")
        session["pieces_done"] = session.get("pieces_done", 0) + 1
        session["last_piece_at"] = datetime.utcnow().isoformat()
        _save_live_preview(session)
        _broadcast({"type": "chunk_complete", "chunk_index": piece, "title": session["title"],
                    "notes": result.get("notes"), "shlokas": result.get("shlokas") or [],
                    "transcript": result.get("transcript")})
    except Exception as e:
        _report_failure(e, piece)
    finally:
        _active_upload_hashes.discard(digest)
        with _live_lock:
            session["pending"] -= 1
            ready = session["stopped"] and session["pending"] == 0
        if ready:
            _finalize_live_session(session)


def _stored(session: dict) -> dict:
    """What gets saved: everything except the in-memory bookkeeping."""
    return {k: v for k, v in session.items() if k not in ("pieces", "pending", "stopped", "prefix", "prior_pieces")}


def _save_live_preview(session: dict):
    if not session["transcript"]:
        return
    for i, s in enumerate(sessions_store):
        if s.get("id") == session["id"]:
            sessions_store[i] = _stored(session)
            break
    else:
        sessions_store.append(_stored(session))
    _save_sessions()


def _finalize_live_session(session: dict):
    """Rebuild the recording's notes once, over its whole transcript."""
    global sessions_store
    transcript = session.get("transcript") or ""
    if not transcript.strip():
        sessions_store = [s for s in sessions_store if s.get("id") != session["id"]]
        _save_sessions()
        print("[live] recording captured no speech — nothing saved")
        _broadcast({"type": "session_complete", "session_id": session["id"], "empty": True})
        return
    pieces = [p for p in session["pieces"] if p]
    print(f"[live] finalizing recording ({len(pieces)} piece(s), {len(transcript)} chars) as one set of notes...")
    try:
        with _pipeline_semaphore:
            result = _run_text_steps(transcript, 0, f"live:{session['id']}")
        final = _session_from_result({**result, "transcript": transcript}, session["title"], 0,
                                     raw_transcript=session.get("raw_transcript"),
                                     asr_provider=session.get("asr_provider"),
                                     pieces_recorded=session.get("prior_pieces", 0) + len(pieces),
                                     stopped_at=session.get("stopped_at"), live=True)
        final["id"], final["created_at"] = session["id"], session["created_at"]
        for i, s in enumerate(sessions_store):
            if s.get("id") == session["id"]:
                sessions_store[i] = final
                break
        else:
            sessions_store.append(final)
        _save_sessions()
        _broadcast({"type": "session_complete", "session_id": session["id"]})
        print("[live] recording finalized")
    except Exception as e:
        _report_failure(e, 0)


class MergeRequest(BaseModel):
    ids: list[str]


@app.post("/merge-sessions")
async def merge_sessions(data: MergeRequest):
    """Join several recordings of one pravachanam into one set of notes, in the
    order they were recorded. The earliest keeps its id and title."""
    from fastapi import HTTPException
    found = sorted((s for s in sessions_store if s.get("id") in set(data.ids)), key=lambda s: s.get("created_at") or "")
    if len(found) < 2 or len(found) != len(set(data.ids)):
        raise HTTPException(status_code=400, detail="Need at least two existing sessions")
    threading.Thread(target=_merge_sessions, args=(found,), daemon=True).start()
    return {"status": "merging", "into": found[0]["id"]}


def _merge_sessions(found: list[dict]):
    global sessions_store
    first = found[0]
    transcript = "\n".join((s.get("transcript") or "").strip() for s in found).strip()
    raw = "\n".join((s.get("raw_transcript") or s.get("transcript") or "").strip() for s in found).strip()
    print(f"[merge] joining {len(found)} recordings ({len(transcript)} chars) into one set of notes...")
    try:
        with _pipeline_semaphore:
            result = _run_text_steps(transcript, 0, f"live:{first['id']}")
        merged = _session_from_result({**result, "transcript": transcript}, first.get("title"), 0,
                                      raw_transcript=raw, asr_provider=first.get("asr_provider"),
                                      pieces_recorded=sum(int(s.get("pieces_recorded") or 1) for s in found),
                                      stopped_at=found[-1].get("stopped_at"), live=True)
        merged["id"], merged["created_at"] = first["id"], first["created_at"]
        gone = {s["id"] for s in found[1:]}
        _forget_memory([f"live:{i}" for i in gone])
        sessions_store = [merged if s.get("id") == first["id"] else s for s in sessions_store if s.get("id") not in gone]
        _save_sessions()
        _broadcast({"type": "session_complete", "session_id": first["id"]})
        print("[merge] done")
    except Exception as e:
        _report_failure(e, 0)


def _forget_memory(sources: list[str]):
    """Drop search entries of recordings that no longer exist on their own."""
    import chromadb
    collection = chromadb.PersistentClient(path="chroma_db").get_or_create_collection(name="notes_collection")
    for source in sources:
        collection.delete(where={"source": source})


def run_pipeline(youtube_url: str):
    """A YouTube video: the whole audio (or its captions) in one pass, one session."""
    global _pipeline_thread
    _pipeline_thread = threading.current_thread()
    try:
        with _pipeline_semaphore:
            result = _run_graph(_new_state(youtube_url=youtube_url), 0)
        if stop_event.is_set():
            return
        session = _session_from_result({**result, "youtube_url": youtube_url}, None, 0)
        sessions_store.append(session)
        _save_sessions()
        _broadcast(session)
        _broadcast({"type": "session_complete", "total_chunks": 1})
    except Exception as e:
        _report_failure(e, 0)
