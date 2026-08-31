from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks, UploadFile, File
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
            return json.load(f)
    except Exception:
        return []

def _save_sessions():
    try:
        with open(SESSIONS_FILE, "w") as f:
            json.dump(sessions_store, f, ensure_ascii=False)
    except Exception as e:
        print(f"[sessions] save failed: {e}")

import json

manager = ConnectionManager()
event_loop: asyncio.AbstractEventLoop | None = None
stop_event = threading.Event()
sessions_store: list[dict] = _load_sessions()
_pipeline_thread: threading.Thread | None = None
_live_session_id: int = 0
_pipeline_semaphore = threading.Semaphore(1)  # one pipeline at a time — Ollama is single-threaded
_live_recording_session: dict | None = None
_stopped_session_id: str | None = None  # ID of session saved at Stop time, so pipeline can merge into it


@app.on_event("startup")
async def startup():
    global event_loop
    event_loop = asyncio.get_event_loop()


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
    global _live_session_id, _live_recording_session, _stopped_session_id
    stop_event.set()
    _live_session_id += 1  # invalidate any in-flight pipeline broadcasts
    if _live_recording_session:
        if not _live_recording_session.get("id"):
            _live_recording_session["id"] = str(uuid.uuid4())
        _stopped_session_id = _live_recording_session["id"]
        existing_ids = {s.get("id") for s in sessions_store}
        if _live_recording_session["id"] not in existing_ids:
            sessions_store.append(_live_recording_session)
        _save_sessions()
        _live_recording_session = None
    return {"status": "stopped"}


@app.post("/start-live")
async def start_live():
    global _live_recording_session, _live_session_id
    _live_session_id += 1
    _live_recording_session = {
        "type": "chunk_complete",
        "title": "Live Recording",
        "transcript": "",
        "notes": "",
        "enhanced_notes": "",
        "transliterated_notes": "",
        "summary": "",
        "shlokas": [],
        "segments": [],
    }
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


def _run_reprocess(chunk_index: int, audio_path: str, transcript: str):
    from agents.shloka_detect_agent import shloka_detect_agent
    from agents.knowledge_structurer_agent import knowledge_structurer_agent
    from agents.notes_generator_agent import notes_generator_agent

    print(f"[reprocess] starting for chunk {chunk_index} ({len(transcript)} chars)...")
    state = {
        "audio_path": audio_path,
        "youtube_url": None,
        "transcript": transcript,
        "detected_language": None,
        "shlokas": None,
        "segments": None,
        "summary": None,
        "key_teachings": None,
        "notes": None,
        "enhanced_notes": None,
        "chunk_index": chunk_index,
        "current_agent": None,
        "error": None,
    }
    state = {**state, **shloka_detect_agent(state)}
    state = {**state, **knowledge_structurer_agent(state)}
    state = {**state, **notes_generator_agent(state)}

    chunk = {
        "id": str(uuid.uuid4()),
        "type": "chunk_complete",
        "chunk_index": chunk_index,
        "title": f"Live Recording – Chunk {chunk_index + 1}",
        "created_at": datetime.utcnow().isoformat(),
        "summary": state.get("summary"),
        "notes": state.get("notes"),
        "enhanced_notes": state.get("enhanced_notes"),
        "transliterated_notes": state.get("transliterated_notes"),
        "shlokas": state.get("shlokas", []),
        "segments": state.get("segments", []),
        "transcript": transcript,
        "youtube_url": None,
    }
    _save_chunk_result(audio_path, chunk)

    # Update existing session if present, otherwise append
    global sessions_store
    updated = False
    for i, s in enumerate(sessions_store):
        if s.get("chunk_index") == chunk_index:
            sessions_store[i] = {**s, **chunk, "id": s["id"]}
            updated = True
            break
    if not updated:
        sessions_store.append(chunk)
    _save_sessions()

    if event_loop:
        asyncio.run_coroutine_threadsafe(manager.broadcast(chunk), event_loop)
    print(f"[reprocess] done for chunk {chunk_index}")


@app.post("/upload-audio")
async def upload_audio(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    global _live_session_id
    _live_session_id += 1
    my_session_id = _live_session_id
    chunk_index = len(sessions_store)
    os.makedirs("audio_input", exist_ok=True)
    ext = os.path.splitext(file.filename or "chunk.webm")[1] or ".webm"
    audio_path = f"audio_input/live_chunk_{chunk_index}{ext}"
    with open(audio_path, "wb") as f:
        content = await file.read()
        f.write(content)
    background_tasks.add_task(run_pipeline_from_audio, audio_path, chunk_index, my_session_id)
    return {"status": "processing", "chunk_index": chunk_index}


def run_pipeline_from_audio(audio_path: str, chunk_index: int, session_id: int = 0):
    with _pipeline_semaphore:
        _run_pipeline_from_audio(audio_path, chunk_index, session_id)


def _run_pipeline_from_audio(audio_path: str, chunk_index: int, session_id: int = 0):
    state = {
        "audio_path": audio_path,
        "youtube_url": None,
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
        "error": None,
    }
    _AGENT_LABELS = {
        "listener": "Downloading Audio",
        "transcription": "Transcribing Audio",
        "correction": "Correcting Transcript",
        "harmony": "Analysing Melody",
        "shloka_detector": "Detecting Shlokas",
        "knowledge_structurer": "Structuring Knowledge",
        "notes_generator": "Generating Notes",
        "memory": "Saving to Memory",
    }

    def _broadcast_progress(agent_name: str):
        label = _AGENT_LABELS.get(agent_name, agent_name)
        asyncio.run_coroutine_threadsafe(
            manager.broadcast({"type": "agent_progress", "agent": agent_name, "label": label, "chunk_index": chunk_index}),
            event_loop
        )

    def _broadcast_stage_result(payload: dict):
        asyncio.run_coroutine_threadsafe(
            manager.broadcast({"type": "stage_result", "chunk_index": chunk_index, **payload}),
            event_loop
        )

    try:
        # Use stream mode so we can broadcast progress after each agent completes
        result = {}
        for event in langgraph_app.stream(state):
            for node_name, node_output in event.items():
                result.update(node_output)
                _broadcast_progress(node_name)
                # Broadcast intermediate data so frontend can show results progressively
                if node_name == "transcription" and node_output.get("transcript"):
                    _broadcast_stage_result({"stage": "transcription", "transcript": node_output["transcript"]})
                elif node_name == "shloka_detector":
                    _broadcast_stage_result({"stage": "shlokas", "shlokas": node_output.get("shlokas") or []})
                elif node_name == "notes_generator":
                    _broadcast_stage_result({"stage": "notes", "notes": node_output.get("notes") or "", "enhanced_notes": node_output.get("enhanced_notes") or "", "transliterated_notes": node_output.get("transliterated_notes") or ""})
        chunk = {
            "id": str(uuid.uuid4()),
            "type": "chunk_complete",
            "chunk_index": chunk_index,
            "title": f"Live Recording – Chunk {chunk_index + 1}",
            "summary": result.get("summary"),
            "notes": result.get("notes"),
            "enhanced_notes": result.get("enhanced_notes"),
            "transliterated_notes": result.get("transliterated_notes"),
            "shlokas": result.get("shlokas", []),
            "segments": result.get("segments", []),
            "transcript": result.get("transcript"),
            "youtube_url": None,
            "created_at": datetime.utcnow().isoformat(),
        }
        # Persist result so server restarts can recover it
        _save_chunk_result(audio_path, chunk)
        # Merge into the live recording session (not separate entries per chunk)
        if _live_recording_session is not None:
            _live_recording_session["transcript"] = (_live_recording_session.get("transcript") or "") + "\n" + (chunk.get("transcript") or "")
            _live_recording_session["notes"] = (_live_recording_session.get("notes") or "") + "\n\n" + (chunk.get("notes") or "")
            _live_recording_session["transliterated_notes"] = (_live_recording_session.get("transliterated_notes") or "") + "\n\n" + (chunk.get("transliterated_notes") or "")
            _live_recording_session["shlokas"] = (_live_recording_session.get("shlokas") or []) + (chunk.get("shlokas") or [])
            _live_recording_session["segments"] = (_live_recording_session.get("segments") or []) + (chunk.get("segments") or [])
            if chunk.get("summary"):
                _live_recording_session["summary"] = chunk["summary"]
            # Auto-save after every chunk — don't wait for Stop button
            if not _live_recording_session.get("id"):
                _live_recording_session["id"] = str(uuid.uuid4())
            existing_ids = {s.get("id") for s in sessions_store}
            if _live_recording_session["id"] not in existing_ids:
                sessions_store.append(_live_recording_session)
            _save_sessions()
        else:
            # Stop was clicked before pipeline finished — merge into the stopped session if possible
            if _stopped_session_id:
                merged = False
                for s in sessions_store:
                    if s.get("id") == _stopped_session_id:
                        s["transcript"] = ((s.get("transcript") or "") + "\n" + (chunk.get("transcript") or "")).strip()
                        s["notes"] = ((s.get("notes") or "") + "\n\n" + (chunk.get("notes") or "")).strip()
                        s["transliterated_notes"] = ((s.get("transliterated_notes") or "") + "\n\n" + (chunk.get("transliterated_notes") or "")).strip()
                        s["shlokas"] = (s.get("shlokas") or []) + (chunk.get("shlokas") or [])
                        s["segments"] = (s.get("segments") or []) + (chunk.get("segments") or [])
                        if chunk.get("summary"):
                            s["summary"] = chunk["summary"]
                        merged = True
                        break
                if not merged:
                    sessions_store.append(chunk)
            else:
                existing_ids = {s.get("id") for s in sessions_store}
                if chunk["id"] not in existing_ids:
                    sessions_store.append(chunk)
            _save_sessions()

        # Broadcast result — always send so frontend updates; stale pipelines just get ignored by frontend
        asyncio.run_coroutine_threadsafe(manager.broadcast(chunk), event_loop)
    except Exception as e:
        import traceback
        print(f"[PIPELINE ERROR] audio chunk {chunk_index}: {e}")
        traceback.print_exc()


def run_pipeline(youtube_url: str):
    global _pipeline_thread
    _pipeline_thread = threading.current_thread()
    chunk_index = 0

    # Accumulate all chunks into one merged session
    merged = {
        "id": str(uuid.uuid4()),
        "type": "chunk_complete",
        "title": "",
        "transcript": "",
        "notes": "",
        "enhanced_notes": "",
        "transliterated_notes": "",
        "summary": "",
        "shlokas": [],
        "segments": [],
        "youtube_url": youtube_url,
        "created_at": datetime.utcnow().isoformat(),
    }

    while not stop_event.is_set():
        state = {
            "audio_path": None,
            "youtube_url": youtube_url,
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
            "error": None,
        }

        try:
            result = langgraph_app.invoke(state)

            if stop_event.is_set():
                break

            # Listener signals video is fully processed
            if result.get("error") == "video_ended":
                print(f"[pipeline] video fully processed after {chunk_index} chunks")
                sessions_store.append(merged)
                _save_sessions()
                asyncio.run_coroutine_threadsafe(
                    manager.broadcast({"type": "session_complete", "total_chunks": chunk_index}),
                    event_loop,
                )
                break

            video_title = result.get("video_title") or merged["title"] or "Pravachanam"
            merged["title"] = video_title
            merged["transcript"] = (merged["transcript"] + "\n" + (result.get("transcript") or "")).strip()
            merged["notes"] = (merged["notes"] + "\n\n" + (result.get("notes") or "")).strip()
            merged["enhanced_notes"] = (merged["enhanced_notes"] + "\n\n" + (result.get("enhanced_notes") or "")).strip()
            merged["transliterated_notes"] = (merged["transliterated_notes"] + "\n\n" + (result.get("transliterated_notes") or "")).strip()
            merged["shlokas"] += result.get("shlokas") or []
            merged["segments"] += result.get("segments") or []
            if result.get("summary"):
                merged["summary"] = result["summary"]

            # Broadcast incremental chunk so Live screen updates in real time
            chunk = {
                "type": "chunk_complete",
                "chunk_index": chunk_index,
                "title": video_title,
                "notes": result.get("notes"),
                "shlokas": result.get("shlokas", []),
                "transcript": result.get("transcript"),
            }
            asyncio.run_coroutine_threadsafe(manager.broadcast(chunk), event_loop)

        except Exception as e:
            import traceback
            print(f"[PIPELINE ERROR] chunk {chunk_index}: {e}")
            traceback.print_exc()
            break

        chunk_index += 1

        max_chunks = state.get("total_chunks")
        if max_chunks and chunk_index >= max_chunks:
            sessions_store.append(merged)
            _save_sessions()
            break
