from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import threading
import os
from graph.orchestrator import app as langgraph_app
from agents.rag_agent import rag_agent

app = FastAPI()

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


manager = ConnectionManager()
event_loop: asyncio.AbstractEventLoop | None = None
stop_event = threading.Event()
sessions_store: list[dict] = []


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
    stop_event.clear()
    background_tasks.add_task(run_pipeline, data.youtube_url)
    return {"status": "started", "youtube_url": data.youtube_url}


@app.post("/stop-session")
async def stop_session():
    stop_event.set()
    return {"status": "stopped"}


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


@app.post("/upload-audio")
async def upload_audio(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    chunk_index = len(sessions_store)
    os.makedirs("audio_input", exist_ok=True)
    audio_path = f"audio_input/live_chunk_{chunk_index}.m4a"
    with open(audio_path, "wb") as f:
        content = await file.read()
        f.write(content)
    background_tasks.add_task(run_pipeline_from_audio, audio_path, chunk_index)
    return {"status": "processing", "chunk_index": chunk_index}


def run_pipeline_from_audio(audio_path: str, chunk_index: int):
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
    try:
        result = langgraph_app.invoke(state)
        chunk = {
            "type": "chunk_complete",
            "chunk_index": chunk_index,
            "title": f"Live Recording – Chunk {chunk_index + 1}",
            "summary": result.get("summary"),
            "notes": result.get("notes"),
            "enhanced_notes": result.get("enhanced_notes"),
            "shlokas": result.get("shlokas", []),
            "segments": result.get("segments", []),
            "transcript": result.get("transcript"),
            "youtube_url": None,
        }
        sessions_store.append(chunk)
        asyncio.run_coroutine_threadsafe(manager.broadcast(chunk), event_loop)
    except Exception as e:
        asyncio.run_coroutine_threadsafe(
            manager.broadcast({"type": "error", "message": str(e), "chunk_index": chunk_index}),
            event_loop,
        )


def run_pipeline(youtube_url: str):
    chunk_index = 0

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

            chunk = {
                "type": "chunk_complete",
                "chunk_index": chunk_index,
                "title": f"Live Session – Chunk {chunk_index + 1}",
                "summary": result.get("summary"),
                "notes": result.get("notes"),
                "enhanced_notes": result.get("enhanced_notes"),
                "shlokas": result.get("shlokas", []),
                "segments": result.get("segments", []),
                "transcript": result.get("transcript"),
                "youtube_url": youtube_url,
            }
            sessions_store.append(chunk)

            asyncio.run_coroutine_threadsafe(
                manager.broadcast(chunk),
                event_loop,
            )

        except Exception as e:
            import traceback
            print(f"[PIPELINE ERROR] chunk {chunk_index}: {e}")
            traceback.print_exc()
            asyncio.run_coroutine_threadsafe(
                manager.broadcast({"type": "error", "message": str(e), "chunk_index": chunk_index}),
                event_loop,
            )
            break  # stop loop on error so it doesn't spin endlessly

        chunk_index += 1
