from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks, UploadFile, File, Form, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel
import asyncio
import subprocess
import re
import threading
import os
import time
import uuid
from datetime import datetime, timezone, timedelta
from graph.orchestrator import app as langgraph_app

_IST = timezone(timedelta(hours=5, minutes=30))
from agents.rag_agent import rag_agent
from agents import cancellation
from auth import check_basic_header, verify_ws_token, auth_enabled, username_from_header, check_admin_header

app = FastAPI()


class BasicAuthMiddleware(BaseHTTPMiddleware):
    """Guards every REST route with the fixed username/password. A plain
    app-level `Depends(verify_credentials)` looked like it would do this,
    but FastAPI's HTTPBasic security class isn't WebSocket-safe — wired up
    that way it crashed (500) the moment the /ws route's own handshake hit
    it, since HTTPBasic expects an HTTP Request, not a WebSocket scope.
    BaseHTTPMiddleware only runs for scope["type"] == "http" and leaves
    websocket connections alone, so /ws keeps using its own token check.

    The web build's own static files (index.html, its JS bundle, fonts) are
    the one exception: they have to load before the app's JS can even show
    its Login screen or attach a stored Basic Auth header to anything. A
    browser-level auth popup in front of blank nothing would be worse than
    just letting the app shell load — the real data underneath is still
    behind this same check on every API route."""
    _PUBLIC_PATHS = {
        "/", "/index.html", "/metadata.json", "/favicon.ico",
        "/manifest.json", "/apple-touch-icon.png", "/icon-192.png", "/icon-512.png",
        "/favicon-32x32.png", "/favicon-16x16.png",
    }

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path == "/admin" or path.startswith("/admin/"):
            # Entirely separate credentials from the 10 regular app logins —
            # this never checks APP_USERS, so no app user can land here even
            # by guessing the URL.
            if not check_admin_header(request.headers.get("authorization")):
                return Response(status_code=401, headers={"WWW-Authenticate": "Basic"})
            return await call_next(request)
        is_public_static = request.method == "GET" and (
            path in self._PUBLIC_PATHS
            or path.startswith("/_expo/")
            or path.startswith("/assets/")
            or path.endswith((".png", ".ico", ".json", ".webmanifest", ".svg"))
        )
        if not is_public_static and not check_basic_header(request.headers.get("authorization")):
            return Response(status_code=401, headers={"WWW-Authenticate": "Basic"})
        request.state.username = username_from_header(request.headers.get("authorization")) or "dev"
        return await call_next(request)


app.add_middleware(BasicAuthMiddleware)


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
    expose_headers=["Content-Disposition"],
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


import json
import sqlite3

# A flat JSON file had two real problems in practice: every save rewrote the
# whole thing (no partial-write safety — a crash mid-write could corrupt
# every session, not just the one being saved), and nothing stopped two
# saves landing at the same instant from interleaving (the lock below only
# patched that second half). SQLite's own transactions solve both: a write
# either lands completely or not at all, and the database file itself
# handles concurrent access safely — no file-level lock needed anymore.
# Each session is still just "a dict", read and written whole, exactly as
# sessions_store (and every endpoint that mutates it) already expects —
# only the storage underneath changed, not the thirty-odd call sites above
# that treat sessions_store as a plain in-memory list.
SESSIONS_FILE = "sessions.json"   # the old file — read once, to migrate, then left alone
DB_FILE = "sessions.db"


def _db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, created_at TEXT, data TEXT NOT NULL)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON sessions(created_at)")
    conn.execute("CREATE TABLE IF NOT EXISTS activity (id INTEGER PRIMARY KEY AUTOINCREMENT, when_ist TEXT, username TEXT, action TEXT, ip TEXT, location TEXT, device TEXT)")
    return conn


_GEO_CACHE: dict[str, dict] = {}


def _get_client_ip(request: Request) -> str:
    if not request:
        return ""
    headers = getattr(request, "headers", None)
    if headers:
        real_ip = headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()
        forwarded = headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
    client = getattr(request, "client", None)
    if client and getattr(client, "host", None):
        return client.host or ""
    return ""


def _get_ip_location(ip: str) -> dict:
    if not ip or ip in ("127.0.0.1", "::1", "localhost", "testclient"):
        return {"city": "Local / Test", "region": "", "country": "", "isp": "", "ip": ip}
    if ip in _GEO_CACHE:
        return _GEO_CACHE[ip]
    try:
        import urllib.request
        req = urllib.request.Request(
            f"http://ip-api.com/json/{ip}?fields=status,country,regionName,city,isp,query",
            headers={"User-Agent": "SGK-Notes/1.0"}
        )
        with urllib.request.urlopen(req, timeout=2.5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("status") == "success":
                res = {
                    "city": data.get("city") or "",
                    "region": data.get("regionName") or "",
                    "country": data.get("country") or "",
                    "isp": data.get("isp") or "",
                    "ip": ip,
                }
                _GEO_CACHE[ip] = res
                return res
    except Exception:
        pass
    fallback = {"city": "", "region": "", "country": "", "isp": "", "ip": ip}
    _GEO_CACHE[ip] = fallback
    return fallback


def _fmt_location(geo: dict) -> str:
    parts = [p for p in (geo.get("city"), geo.get("region"), geo.get("country")) if p]
    loc = ", ".join(parts)
    isp = geo.get("isp")
    if loc and isp:
        return f"{loc} ({isp})"
    return loc or geo.get("ip") or "—"


def _parse_device(ua: str) -> str:
    if not ua:
        return "—"
    if "iPhone" in ua:
        return "📱 iPhone"
    elif "iPad" in ua:
        return "📱 iPad"
    elif "Android" in ua:
        return "📱 Android"
    elif "Macintosh" in ua:
        return "💻 Mac"
    elif "Windows" in ua:
        return "💻 Windows"
    elif "Linux" in ua:
        return "🐧 Linux"
    return "🌐 Web"


def _log_activity(username: str, action: str, request: Request | None = None):
    try:
        ip = _get_client_ip(request) if request else ""
        headers = getattr(request, "headers", None) if request else None
        ua = headers.get("user-agent", "") if headers else ""
        geo = _get_ip_location(ip)
        loc = _fmt_location(geo)
        dev = _parse_device(ua)
        when_str = datetime.now(_IST).strftime("%d %b %Y, %I:%M %p IST")
        with _db() as conn:
            conn.execute(
                "INSERT INTO activity (when_ist, username, action, ip, location, device) VALUES (?, ?, ?, ?, ?, ?)",
                (when_str, username or "anonymous", action, ip, loc, dev)
            )
            conn.execute("DELETE FROM activity WHERE id NOT IN (SELECT id FROM activity ORDER BY id DESC LIMIT 200)")
            conn.commit()
    except Exception as e:
        pass


def _migrate_json_to_db_if_needed():
    """One-time: if sessions.db has never been populated but the old
    sessions.json has real data in it, import every session exactly as it
    stood — nothing here is reachable again once the database has rows, so
    this never re-runs or overwrites a later edit."""
    if not os.path.exists(SESSIONS_FILE):
        return
    with _db() as conn:
        if conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] > 0:
            return
        try:
            with open(SESSIONS_FILE, encoding="utf-8") as f:
                old = json.load(f)
        except Exception as e:
            print(f"[sessions] could not read sessions.json for migration: {e}")
            return
        if not isinstance(old, list) or not old:
            return
        for s in old:
            sid = s.get("id")
            if not sid:
                continue
            conn.execute("INSERT OR REPLACE INTO sessions (id, created_at, data) VALUES (?, ?, ?)",
                         (sid, s.get("created_at") or "", json.dumps(s, ensure_ascii=False)))
        conn.commit()
        print(f"[sessions] migrated {len(old)} session(s) from sessions.json into {DB_FILE}")


def _load_sessions():
    _migrate_json_to_db_if_needed()
    with _db() as conn:
        rows = conn.execute("SELECT data FROM sessions ORDER BY created_at").fetchall()
    sessions = [json.loads(r[0]) for r in rows]
    # A session with no transcript and no notes is a leftover of a recording
    # that captured nothing (e.g. Stop pressed straight away) — never show it
    return [x for x in sessions if (x.get("transcript") or "").strip() or (x.get("notes") or "").strip()]


def _save_sessions():
    """sessions_store is the full in-memory list after whatever just changed
    — sync the table to match it in one transaction: every current session
    written, anything no longer in the list (a delete) removed. Either this
    all lands or none of it does; there's nothing in between to corrupt."""
    try:
        with _db() as conn:
            current_ids = {s["id"] for s in sessions_store if s.get("id")}
            existing_ids = {r[0] for r in conn.execute("SELECT id FROM sessions").fetchall()}
            for gone_id in existing_ids - current_ids:
                conn.execute("DELETE FROM sessions WHERE id = ?", (gone_id,))
            for s in sessions_store:
                sid = s.get("id")
                if not sid:
                    continue
                conn.execute("INSERT OR REPLACE INTO sessions (id, created_at, data) VALUES (?, ?, ?)",
                             (sid, s.get("created_at") or "", json.dumps(s, ensure_ascii=False)))
            conn.commit()
    except Exception as e:
        print(f"[sessions] save failed: {e}")


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
# This used to be Semaphore(1) — one pipeline at a time — because the
# pipeline ran against a local Ollama model, which genuinely needed
# exclusive access to one GPU. That stopped being true once everything moved
# to remote APIs (Gemini, Groq), which already handle their own concurrency
# and rate limits internally — serializing on top of that just means one
# slow or stuck recording blocks every other person using the app, with no
# benefit. A real cap still matters (ffmpeg conversion and audio I/O run on
# this one Mac's CPU, not a remote service), just a much higher one.
_pipeline_semaphore = threading.Semaphore(int(os.getenv("MAX_CONCURRENT_PIPELINES", "8")))
_live_recording_sessions: dict[str, dict] = {}   # the mic recording each user is currently capturing — one
                                                 # per logged-in username, so two people recording at the
                                                 # same moment never share (and garble) one document
_last_stopped_sessions: dict[str, dict] = {}    # briefly kept per user after /stop-session, so a late piece
_last_stopped_at: dict[str, float] = {}         # that was already mid-upload lands on it, not a new note
LATE_PIECE_GRACE_SECONDS = 10
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
    of by the app.

    One recording can be "still in progress" per user, not just one overall —
    two different people can each have had a live recording running when the
    server restarted, and both deserve to resume rather than only whichever
    was more recent."""
    now = datetime.utcnow()
    in_progress = [s for s in sessions_store if s.get("live_in_progress")]
    if not in_progress:
        return
    by_user: dict[str | None, list[dict]] = {}
    for s in in_progress:
        by_user.setdefault(s.get("created_by"), []).append(s)
    for user, sessions in by_user.items():
        # Only one recording can really be "the one still in progress" for a
        # given user — the most recently updated marker is it; any others are
        # leftovers from an earlier crash and get closed out properly instead
        # of left stuck.
        sessions.sort(key=lambda s: s.get("last_piece_at") or s.get("created_at") or "", reverse=True)
        newest, *rest = sessions
        age_minutes = (now - datetime.fromisoformat(newest.get("last_piece_at") or newest.get("created_at"))).total_seconds() / 60
        if age_minutes <= RESUME_WINDOW_MINUTES:
            resumed = _build_continuation(newest)
            _live_recording_sessions[user] = resumed
            _live_by_id[newest["id"]] = resumed
            print(f"[live] resumed in-progress recording {newest['id'][:8]} for {user} after restart ({age_minutes:.1f} min old)")
        else:
            rest = [newest] + rest  # too old to still count as "the same recording in progress"
        for s in rest:
            print(f"[live] finalizing orphaned in-progress recording {s['id'][:8]} for {user}")
            threading.Thread(target=_finalize_live_session, args=(_build_continuation(s),), daemon=True).start()


def _build_continuation(earlier: dict) -> dict:
    """The in-memory shape for a live session that continues an earlier
    (possibly unfinished) one: its saved text becomes a fixed prefix, and new
    minute-pieces are appended after it."""
    session = {
        **{k: earlier.get(k) for k in ("id", "type", "title", "created_at", "created_by", "notes", "enhanced_notes",
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
async def websocket_endpoint(websocket: WebSocket, token: str | None = None):
    if not verify_ws_token(token):
        await websocket.close(code=4401)   # 4401: custom close code in the app-reserved range (4000-4999), mirroring HTTP 401
        return
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


class SessionRequest(BaseModel):
    youtube_url: str


@app.post("/start-session")
async def start_session(data: SessionRequest, background_tasks: BackgroundTasks, request: Request):
    global _pipeline_thread
    # Stop any currently running pipeline
    stop_event.set()
    if _pipeline_thread and _pipeline_thread.is_alive():
        _pipeline_thread.join(timeout=3)
    stop_event.clear()
    background_tasks.add_task(run_pipeline, data.youtube_url, request.state.username)
    return {"status": "started", "youtube_url": data.youtube_url}


class StopSessionRequest(BaseModel):
    live_session_id: str | None = None   # which recording to stop — see /upload-audio's live_session_id


@app.post("/stop-session")
async def stop_session(request: Request, data: StopSessionRequest | None = None):
    """Stop a YouTube run or a mic recording. A recording's notes are rebuilt
    once over the whole transcript as soon as its last piece is processed.

    Stops the specific recording named by live_session_id when the app sent
    one (every build from here on does) — not just "whatever is in this
    username's slot", which could be a different phone's recording if the
    same shared login is being used by two people at once. Only falls back
    to the username slot for an older client that hasn't sent an id yet."""
    global _live_session_id
    username = request.state.username
    stop_event.set()
    _live_session_id += 1
    target_id = data.live_session_id if data else None
    if target_id:
        session = _live_by_id.get(target_id)
        if session is None or session.get("created_by") != username:
            session = None   # unknown id, or belongs to someone else — nothing to stop
        elif _live_recording_sessions.get(username) is session:
            # Only clear the per-username convenience slot if it still points
            # at *this* recording — a different device under the same shared
            # login may have since started a newer one there, and that one
            # must be left alone.
            del _live_recording_sessions[username]
    else:
        session = _live_recording_sessions.pop(username, None)
    if session is not None:
        with _live_lock:
            session["stopped"] = True
            session["stopped_at"] = datetime.utcnow().isoformat()
            ready = session["pending"] == 0
        _last_stopped_sessions[username], _last_stopped_at[username] = session, time.time()
        _log_activity(username, f"Stopped Live Recording ({session.get('title') or session['id'][:8]})", request)
        for stored in sessions_store:          # so the app can offer "continue" right away
            if stored.get("id") == session["id"]:
                stored["stopped_at"] = session["stopped_at"]
        if ready:
            def _delayed_finalize(sess):
                time.sleep(2.5)
                with _live_lock:
                    if sess["pending"] > 0:
                        return
                _finalize_live_session(sess)
            threading.Thread(target=_delayed_finalize, args=(session,), daemon=True).start()
    return {"status": "stopped"}


class StartLiveRequest(BaseModel):
    continue_id: str | None = None   # add to this earlier recording instead of starting new notes


@app.post("/start-live")
async def start_live(request: Request, data: StartLiveRequest | None = None):
    global _live_session_id
    _live_session_id += 1
    continue_id = data.continue_id if data else None
    username = getattr(request.state, "username", None) if request else None
    # Only the user's own recording (live-in-memory or already saved) can be
    # continued — one username's "continue?" prompt should never be able to
    # attach new audio onto someone else's pravachanam.
    if continue_id in _live_by_id and _live_by_id[continue_id].get("created_by") == username:
        # Still in memory (maybe still finishing): reopen it; its next stop rebuilds the notes over everything
        session = _live_by_id[continue_id]
        with _live_lock:
            session["stopped"] = False
        _live_recording_sessions[username] = session
        return {"status": "ok", "continued": continue_id, "id": session["id"]}
    earlier = next((s for s in sessions_store if continue_id and s.get("id") == continue_id
                     and s.get("created_by") == username), None)
    client_ip = _get_client_ip(request) if request else ""
    headers = getattr(request, "headers", None) if request else None
    ua = headers.get("user-agent", "") if headers else ""
    geo = _get_ip_location(client_ip)
    location = _fmt_location(geo)
    device = _parse_device(ua)

    if earlier is not None:
        # Continue: same notes, same id; the new minutes are appended to its transcript
        session = _build_continuation(earlier)
        _live_recording_sessions[username] = session
        _live_by_id[earlier["id"]] = session
        _log_activity(username, f"Continued Recording ({session.get('title')})", request)
        return {"status": "ok", "continued": earlier["id"], "id": session["id"]}
    session = {
        "id": str(uuid.uuid4()),
        "type": "chunk_complete",
        "title": "Live Recording – " + datetime.now(_IST).strftime("%d %b %Y, %I:%M %p"),
        "created_at": datetime.utcnow().isoformat(),
        "created_by": username,
        "client_ip": client_ip,
        "location": location,
        "device": device,
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
    _live_recording_sessions[username] = session
    _live_by_id[session["id"]] = session
    _log_activity(username, f"Started Live Recording ({session['title']})", request)
    return {"status": "ok", "id": session["id"]}


class SearchRequest(BaseModel):
    query: str


@app.post("/search")
async def search(data: SearchRequest):
    result = rag_agent(data.query)
    return {"result": result}


@app.get("/health")
async def health():
    return {"status": "ok"}


def _recent_errors(limit: int = 30) -> list[dict]:
    """Parses pipeline_errors.log's blocks (separated by a row of '='). Older
    entries (written before per-user tracking existed) have no '— by X' and
    just show as 'unknown' — that's real, not a parsing bug."""
    if not os.path.exists(ERROR_LOG_FILE):
        return []
    with open(ERROR_LOG_FILE, encoding="utf-8") as f:
        raw = f.read()
    entries = []
    for block in raw.split("=" * 70):
        block = block.strip("\n")
        if not block:
            continue
        lines = block.split("\n")
        header = lines[0]
        m = re.match(r"^(\S+) — chunk (\S+)(?: — by (\S+))?", header)
        if not m:
            continue
        entries.append({
            "when": m.group(1), "chunk": m.group(2), "by": m.group(3) or "unknown",
            "detail": "\n".join(lines[1:]).strip()[-800:],   # last part of the traceback — the actual exception
        })
    return list(reversed(entries))[:limit]


@app.get("/admin", response_class=Response)
async def admin_page():
    import html as _html
    sessions = sorted(sessions_store, key=lambda s: s.get("created_at") or "", reverse=True)

    def _fmt_ist(iso_str: str) -> str:
        if not iso_str:
            return "—"
        try:
            dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(_IST).strftime("%d %b %Y, %I:%M %p IST")
        except Exception:
            return iso_str

    def _session_row(s):
        is_deleted = bool(s.get("deleted"))
        is_archived = bool(s.get("archived"))
        open_tag = "<tr style='opacity:0.45; text-decoration: line-through;'>" if is_deleted else ("<tr style='opacity:0.6'>" if is_archived else "<tr>")
        kind = "live" if s.get("live") else ("youtube" if s.get("youtube_url") else "upload")
        if is_deleted:
            who = _html.escape(s.get("deleted_by") or "user")
            visibility = f"<span style='color:#ff8787'>Deleted by {who}</span>"
        elif is_archived:
            visibility = "<span style='color:#868e96'>archived</span>"
        else:
            visibility = "<span style='color:#51cf66'>visible</span>"
        loc = s.get("location") or (f"IP: {s.get('client_ip')}" if s.get("client_ip") else "—")
        dev = s.get("device") or "—"
        return (
            f"{open_tag}<td>{_html.escape(_fmt_ist(s.get('created_at')))}</td>"
            f"<td>{_html.escape(s.get('title') or '')}</td>"
            f"<td>{_html.escape(s.get('created_by') or '—')}</td>"
            f"<td>📍 {_html.escape(loc)}</td>"
            f"<td>{_html.escape(dev)}</td>"
            f"<td>{kind}</td><td>{len(s.get('notes') or '')}</td>"
            f"<td>{visibility}</td></tr>"
        )
    rows = "".join(_session_row(s) for s in sessions[:200])

    activities = []
    try:
        with _db() as conn:
            activities = conn.execute(
                "SELECT when_ist, username, action, ip, location, device FROM activity ORDER BY id DESC LIMIT 50"
            ).fetchall()
    except Exception:
        pass

    activity_rows = "".join(
        f"<tr><td>{_html.escape(a[0])}</td>"
        f"<td><strong>{_html.escape(a[1])}</strong></td>"
        f"<td>📍 {_html.escape(a[4] or '—')}</td>"
        f"<td>{_html.escape(a[5] or '—')}</td>"
        f"<td><code>{_html.escape(a[3] or '—')}</code></td>"
        f"<td>{_html.escape(a[2] or '—')}</td></tr>"
        for a in activities
    ) or "<tr><td colspan='6' style='color:#aaa;'>No user activity logged yet. Activity appears here in real time as users interact with the app.</td></tr>"

    errors = _recent_errors()
    error_rows = "".join(
        f"<tr><td>{_html.escape(_fmt_ist(e['when']))}</td><td>{_html.escape(e['chunk'])}</td>"
        f"<td>{_html.escape(e['by'])}</td>"
        f"<td><pre>{_html.escape(e['detail'])}</pre></td></tr>"
        for e in errors
    ) or "<tr><td colspan='4'>No errors logged.</td></tr>"
    page = f"""<!doctype html><html><head><meta charset="utf-8">
<title>SGKS Notes — Admin</title>
<style>
body {{ font-family: -apple-system, sans-serif; background: #1a1625; color: #eee; padding: 24px; line-height: 1.5; }}
h1, h2 {{ color: #d8b26a; margin-top: 28px; margin-bottom: 12px; }}
h1 {{ margin-top: 0; }}
.badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; background: #332b4d; color: #f2c877; }}
table {{ border-collapse: collapse; width: 100%; margin-bottom: 36px; font-size: 13px; }}
td, th {{ border: 1px solid #443d5c; padding: 8px 12px; text-align: left; vertical-align: top; }}
th {{ background: #2a2340; color: #f2c877; font-weight: 600; }}
pre {{ white-space: pre-wrap; margin: 0; font-size: 11px; color: #f0a0a0; max-width: 600px; }}
tr:nth-child(even) {{ background: #221d35; }}
tr:hover {{ background: #2c2544; }}
code {{ font-family: Menlo, Monaco, monospace; font-size: 12px; color: #74c0fc; }}
</style></head><body>
<h1>SGKS Notes — Admin Dashboard</h1>
<div style="margin-bottom: 24px; color: #aaa; font-size: 13px;">
  System Time: <span class="badge">{datetime.now(_IST).strftime("%d %b %Y, %I:%M:%S %p IST")}</span>
</div>

<h2>🌍 Real-Time User Locations & Activity (Last 50 Events)</h2>
<p style="color:#aaa; font-size: 12px; margin-top: -6px; margin-bottom: 12px;">Live view of who is using the website, their city/region, internet provider, and device.</p>
<table>
  <tr><th>When (IST)</th><th>User</th><th>Location & Network</th><th>Device</th><th>IP Address</th><th>Action</th></tr>
  {activity_rows}
</table>

<h2>Sessions ({len(sessions)} total)</h2>
<table>
  <tr><th>Created (IST)</th><th>Title</th><th>By</th><th>Location & Network</th><th>Device</th><th>Type</th><th>Notes length</th><th>In app?</th></tr>
  {rows}
</table>

<h2>Recent errors (last {len(errors)})</h2>
<table>
  <tr><th>When (IST)</th><th>Chunk</th><th>By</th><th>Detail</th></tr>
  {error_rows}
</table>
</body></html>"""
    return Response(content=page, media_type="text/html")


def _session_summary(s: dict) -> dict:
    has_n = bool(s.get("notes") or s.get("transcript"))
    return {
        "id": s.get("id"),
        "title": s.get("title", "Pravachanam"),
        "created_at": s.get("created_at"),
        "duration": s.get("duration", 0),
        "created_by": s.get("created_by"),
        "edited": s.get("edited", False),
        "edited_at": s.get("edited_at"),
        "status": s.get("status"),
        "has_notes": has_n,
        "notes": "1" if has_n else "",  # backward-compatible indicator so row status sees notes exist
        "shlokas": [{"id": i} for i in range(len(s.get("shlokas") or []))],
        "shlokas_count": len(s.get("shlokas") or []),
        "asr_report": {"uncertain": s.get("asr_report", {}).get("uncertain", [])} if s.get("asr_report") else {},
    }


@app.get("/sessions")
async def get_sessions(request: Request, full: bool = False):
    # Strict per-user isolation: Each logged-in user only sees their own
    # notes and recordings on their Home and History screens.
    username = request.state.username
    _log_activity(username, "Opened App / Viewed Notes", request)
    user_sessions = [s for s in sessions_store if not s.get("archived") and not s.get("deleted") and s.get("created_by") == username]
    if full:
        return {"sessions": user_sessions}
    return {"sessions": [_session_summary(s) for s in user_sessions]}


@app.get("/sessions/{session_id}")
async def get_session(session_id: str, request: Request):
    """Retrieve full verbatim notes, verses, and transcript for one single recording on demand."""
    from fastapi import HTTPException
    username = request.state.username
    session = next((s for s in sessions_store if str(s.get("id", "")) == session_id and s.get("created_by") == username and not s.get("deleted")), None)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session": session}


@app.get("/sessions/{session_id}/timestamps")
async def get_timestamps(session_id: str, request: Request, force: bool = False):
    """Notes with [MM:SS] markers, anchored to the real audio — computed
    once per session and cached on it (notes_timestamped), since building
    it re-transcribes the recording's audio. 404 if there's no audio left
    on disk to anchor against; the app checks this before offering the
    option, so a 404 here means the option shouldn't have been shown. Also
    404 (not 403) for someone else's session — same response either way, so
    a session id doesn't reveal whether it exists."""
    from fastapi import HTTPException
    username = request.state.username
    session = next((s for s in sessions_store if s.get("id") == session_id and s.get("created_by") == username), None)
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
    try:
        out = await asyncio.get_event_loop().run_in_executor(None, _build_locked)
    except Exception as e:
        # A raw exception here crashed the connection outright instead of
        # reaching the app as a normal error response — confirmed: the app
        # saw it as "failed to fetch", not a readable error message.
        print(f"[timestamps] build failed for {session_id[:8]}: {str(e)[:200]}")
        raise HTTPException(status_code=500, detail="Could not build timestamps for this recording")
    if out is None:
        raise HTTPException(status_code=404, detail="Could not align any audio to this recording's notes")
    session["notes_timestamped"] = out
    _save_sessions()
    return {"notes_timestamped": out}


@app.get("/sessions/{session_id}/audio")
async def get_session_audio(session_id: str, request: Request):
    """Download the complete continuous audio recording for this session.
    Strictly isolated per-user: only the owner who recorded/uploaded the
    session can download its audio."""
    from fastapi import HTTPException
    from fastapi.responses import FileResponse
    username = request.state.username
    session = next((s for s in sessions_store if s.get("id") == session_id and s.get("created_by") == username), None)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    from agents import notes_timestamp as nt
    audio_path = nt._find_audio(session)
    if not audio_path or not os.path.exists(audio_path):
        raise HTTPException(status_code=404, detail="Audio file not available on server")

    # If it is a webm file (like from live recording chunks), convert or serve .m4a so it plays
    # natively on Mac (QuickTime), iPhone/iOS, Android, and Windows Media Player out-of-the-box.
    if audio_path.endswith(".webm"):
        m4a_path = os.path.splitext(audio_path)[0] + ".m4a"
        if os.path.exists(m4a_path) and os.path.getsize(m4a_path) > 0:
            audio_path = m4a_path
        else:
            try:
                subprocess.run(
                    ["ffmpeg", "-y", "-i", audio_path, "-c:a", "aac", "-b:a", "128k", m4a_path],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True,
                )
                if os.path.exists(m4a_path) and os.path.getsize(m4a_path) > 0:
                    audio_path = m4a_path
            except Exception as e:
                print(f"[get_session_audio] webm to m4a conversion failed ({e}), serving original")

    raw_title = session.get("title") or "pravachanam"
    clean_title = re.sub(r'[^\w\s-]', '', raw_title).strip() or "recording"
    clean_title = re.sub(r'[-\s]+', '_', clean_title)
    ext = os.path.splitext(audio_path)[1] or ".m4a"
    media_type = (
        "audio/mp4" if ext in (".m4a", ".mp4") else
        "audio/mpeg" if ext == ".mp3" else
        "audio/webm" if ext == ".webm" else
        "audio/wav" if ext == ".wav" else
        "application/octet-stream"
    )

    _log_activity(username, f"Downloaded Audio ({clean_title})", request)

    return FileResponse(
        path=audio_path,
        media_type=media_type,
        filename=f"{clean_title}{ext}",
    )


class UpdateNotesRequest(BaseModel):
    notes: str | None = None
    title: str | None = None


@app.put("/sessions/{session_id}/notes")
async def update_notes(session_id: str, data: UpdateNotesRequest, request: Request):
    """A manual correction from the Reading screen's edit mode. Replaces the
    notes text and/or title outright — no re-validation, this is a human overriding
    the pipeline's output on purpose. Clears any cached timestamped version if notes
    were changed, since it was built from the text before this edit and would no longer
    line up; the next request for it rebuilds fresh."""
    from fastapi import HTTPException
    username = request.state.username
    session = next((s for s in sessions_store if s.get("id") == session_id and s.get("created_by") == username), None)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if data.notes is not None:
        session["notes"] = data.notes
        session["enhanced_notes"] = data.notes
        session.pop("notes_timestamped", None)
        session.pop("notes_headings", None)   # paragraph indices no longer line up with the edited text
    if data.title is not None and data.title.strip():
        session["title"] = data.title.strip()
    session["edited"] = True
    session["edited_by"] = username
    _save_sessions()
    _broadcast({"type": "chunk_complete", "chunk_index": session.get("chunk_index", 0),
                "title": session.get("title"), "notes": session.get("notes"), "created_by": username})
    res = {"status": "saved"}
    if session.get("title"):
        res["title"] = session.get("title")
    return res


class UpdateTitleRequest(BaseModel):
    title: str


@app.put("/sessions/{session_id}/title")
async def update_title(session_id: str, data: UpdateTitleRequest, request: Request):
    """Update only the title/name of a session."""
    from fastapi import HTTPException
    username = request.state.username
    session = next((s for s in sessions_store if s.get("id") == session_id and s.get("created_by") == username), None)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    new_title = data.title.strip()
    if not new_title:
        raise HTTPException(status_code=400, detail="Title cannot be empty")
    session["title"] = new_title
    session["edited"] = True
    session["edited_by"] = username
    _save_sessions()
    _broadcast({"type": "session_complete", "session_id": session["id"], "session": session, "created_by": username})
    return {"status": "saved", "title": new_title}


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str, request: Request):
    global sessions_store
    username = request.state.username
    target = next((s for s in sessions_store if str(s.get("id", "")) == session_id and s.get("created_by") == username), None)
    if target is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Session not found")
    target["deleted"] = True
    target["deleted_by"] = username
    target["deleted_at"] = datetime.utcnow().isoformat()
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
            "enhanced_notes": None, "chunk_index": 0, "current_agent": None, "error": None, "digest": None}
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
        # Checked between nodes, not just inside transcription's own piece
        # loop — a cancel landing during shloka detection, structuring or
        # summary (the three parallel LLM steps) still takes effect here,
        # right after whichever one was in flight finishes.
        if cancellation.is_cancelled(state.get("digest")):
            raise cancellation.UploadCancelled("upload discarded by user")
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
        "notes_headings": result.get("notes_headings") or {},
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


ERROR_LOG_FILE = "pipeline_errors.log"


def _report_failure(e: Exception, chunk_index: int, created_by: str | None = None):
    """This only fires once every retry and fallback this pipeline has has
    already been exhausted (both Gemini providers down, or a genuine code
    bug) — everything recoverable (a rate limit, one provider's billing
    issue, a Groq key cooling down) is already handled further down and
    never reaches here. So when it does fire, it's worth a real record: a
    permanent log entry with the full traceback (for you to review later,
    even if you're not watching this screen) and a native notification on
    this Mac (since this is exactly where the backend runs) — while the
    person actually using the app only ever sees a short, calm message, not
    a stack trace."""
    import traceback
    tb = traceback.format_exc()
    who = created_by or "unknown"
    print(f"[PIPELINE ERROR] chunk {chunk_index} (by {who}): {e}")
    print(tb)
    try:
        with open(ERROR_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"\n{'=' * 70}\n{datetime.utcnow().isoformat()} — chunk {chunk_index} — by {who}\n{tb}\n")
    except Exception as log_err:
        print(f"[PIPELINE ERROR] could not write to {ERROR_LOG_FILE}: {log_err}")
    try:
        import subprocess
        subprocess.run(["osascript", "-e",
                        f'display notification "{str(e)[:150]}" with title "SGKS Notes — a recording failed"'],
                       timeout=5, capture_output=True)
    except Exception:
        pass   # not on a Mac, or osascript unavailable — the log file above still has it
    # The app only ever sees this calm, fixed message — never the raw exception,
    # which could be a 300-character stack-trace fragment that reads as broken
    # even when it's really "both providers happened to be down for a minute"
    _broadcast({"type": "pipeline_error", "chunk_index": chunk_index,
                "message": "This recording couldn't be processed. It's been logged — try again in a few minutes."})


@app.post("/upload-audio")
async def upload_audio(request: Request, background_tasks: BackgroundTasks, file: UploadFile = File(...),
                       live: str | None = Form(None), live_session_id: str | None = Form(None)):
    """A whole audio file → one session. With live=1 it is the next one-minute
    piece of the mic recording in progress instead.

    Which recording a piece belongs to is decided by live_session_id (the id
    /start-live returned, which the app now sends back on every piece) when
    given — not by username. Username alone isn't unique: the same shared
    login can be used by two different phones at once (this app hands out a
    short, memorable list of logins, not individual accounts), and routing
    by username would merge their audio into one document the moment the
    second phone's /start-live overwrote the first phone's slot. Routing by
    this recording's own id can't collide that way — two phones under the
    same username get two different ids and stay fully separate. The
    per-username lookup only remains as a fallback for a piece that somehow
    arrives with no id attached."""
    global _live_session_id
    username = getattr(request.state, "username", None)
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
        session = _live_by_id.get(live_session_id) if live_session_id else None
        if session is None:
            if username not in _live_recording_sessions:      # piece arrived without /start-live
                last_stopped = _last_stopped_sessions.get(username)
                if last_stopped is not None and time.time() - _last_stopped_at.get(username, 0) < LATE_PIECE_GRACE_SECONDS:
                    # Not actually a new recording — recorder.stop() resolves once
                    # the last piece's upload *starts*, not once the server has
                    # finished processing it, so that piece can legitimately still
                    # be in flight when /stop-session clears the pointer. Route it
                    # back into the recording it belongs to instead of silently
                    # starting a fresh, never-closed note with it (confirmed this
                    # happened for real — a recording's own closing line ended up
                    # orphaned in exactly this way).
                    _live_recording_sessions[username] = last_stopped
                else:
                    await start_live(request)
            session = _live_recording_sessions[username]
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
    _log_activity(username, f"Uploaded Audio File ({file.filename})", request)
    chunk_index = len(sessions_store)
    audio_path = f"audio_input/upload_{digest[:12]}{ext}"
    with open(audio_path, "wb") as f:
        f.write(content)
    title = os.path.splitext(file.filename or "")[0] or None
    background_tasks.add_task(run_pipeline_from_audio, audio_path, chunk_index, _live_session_id, digest, title, username)
    return {"status": "processing", "chunk_index": chunk_index, "digest": digest}


@app.delete("/upload-audio/{digest}")
async def cancel_upload(digest: str):
    """Discard an upload still processing. Already in-flight API calls finish
    (can't be force-killed mid-request), but no further work starts, and the
    result is never saved as a session once it unwinds."""
    cancellation.cancel(digest)
    return {"status": "cancelling"}


def run_pipeline_from_audio(audio_path: str, chunk_index: int, session_id: int = 0,
                            digest: str | None = None, title: str | None = None,
                            created_by: str | None = None):
    try:
        with _pipeline_semaphore:
            _run_pipeline_from_audio(audio_path, chunk_index, session_id, title, digest, created_by)
    finally:
        _active_upload_hashes.discard(digest)
        cancellation.clear(digest)


def _run_pipeline_from_audio(audio_path: str, chunk_index: int, session_id: int = 0,
                             title: str | None = None, digest: str | None = None,
                             created_by: str | None = None):
    """An uploaded file: one pass over the whole file, one session."""
    try:
        result = _run_graph(_new_state(audio_path=audio_path, chunk_index=chunk_index, digest=digest), chunk_index)
        session = _session_from_result(result, title, chunk_index, created_by=created_by)
        _save_chunk_result(audio_path, session)
        sessions_store.append(session)
        _save_sessions()
        _broadcast(session)
    except cancellation.UploadCancelled:
        print(f"[upload] chunk {chunk_index} discarded by user — not saved")
        _broadcast({"type": "upload_cancelled", "chunk_index": chunk_index})
    except Exception as e:
        _report_failure(e, chunk_index, created_by=created_by)


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
        _report_failure(e, piece, created_by=session.get("created_by"))
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
                                     stopped_at=session.get("stopped_at"), live=True,
                                     created_by=session.get("created_by"))
        final["id"], final["created_at"] = session["id"], session["created_at"]
        final["created_by"] = session.get("created_by")
        final["client_ip"] = session.get("client_ip")
        final["location"] = session.get("location")
        final["device"] = session.get("device")

        # Pre-stitch live audio pieces in background so master audio file is ready immediately
        from agents import notes_timestamp as nt
        threading.Thread(target=nt._concat_live_pieces, args=(session["id"],), daemon=True).start()
        for i, s in enumerate(sessions_store):
            if s.get("id") == session["id"]:
                sessions_store[i] = final
                break
        else:
            sessions_store.append(final)
        _save_sessions()
        _broadcast({"type": "session_complete", "session_id": session["id"], "session": final})
        print("[live] recording finalized")
    except Exception as e:
        _report_failure(e, 0, created_by=session.get("created_by"))


class MergeRequest(BaseModel):
    ids: list[str]


@app.post("/merge-sessions")
async def merge_sessions(data: MergeRequest, request: Request):
    """Join several recordings of one pravachanam into one set of notes, in the
    exact sequence selected by the user. The first chosen keeps its id and title."""
    from fastapi import HTTPException
    username = request.state.username
    id_order = {sid: idx for idx, sid in enumerate(data.ids)}
    found = [s for s in sessions_store if s.get("id") in id_order and s.get("created_by") == username]
    found.sort(key=lambda s: id_order.get(s.get("id"), 0))
    if len(found) < 2 or len(found) != len(set(data.ids)):
        raise HTTPException(status_code=400, detail="Need at least two existing sessions belonging to this user")
    threading.Thread(target=_merge_sessions, args=(found,), daemon=True).start()
    return {"status": "merging", "into": found[0]["id"]}


def _merge_sessions(found: list[dict]):
    global sessions_store
    first = found[0]
    transcript = "\n".join((s.get("transcript") or "").strip() for s in found).strip()
    raw = "\n".join((s.get("raw_transcript") or s.get("transcript") or "").strip() for s in found).strip()
    print(f"[merge] joining {len(found)} recordings ({len(transcript)} chars) into one set of notes in user-selected order...")
    try:
        with _pipeline_semaphore:
            result = _run_text_steps(transcript, 0, f"live:{first['id']}")

        # Concatenate audio files if present
        merged_audio_path = None
        try:
            from agents import notes_timestamp as nt
            audio_files = []
            for s in found:
                ap = nt._find_audio(s)
                if ap and os.path.exists(ap):
                    audio_files.append(ap)
            if len(audio_files) == len(found):
                merged_audio_path = f"audio_input/merged_{first['id'][:8]}.m4a"
                concat_list_path = f"audio_input/concat_{first['id'][:8]}.txt"
                with open(concat_list_path, "w", encoding="utf-8") as f_list:
                    for af in audio_files:
                        f_list.write(f"file '{os.path.abspath(af)}'\n")
                subprocess.run(
                    ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list_path, "-c:a", "aac", "-b:a", "128k", merged_audio_path],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True
                )
                try: os.remove(concat_list_path)
                except Exception: pass
        except Exception as e_audio:
            print(f"[merge] audio concat optional step skipped: {e_audio}")

        merged = _session_from_result({**result, "transcript": transcript}, first.get("title"), 0,
                                      raw_transcript=raw, asr_provider=first.get("asr_provider"),
                                      pieces_recorded=sum(int(s.get("pieces_recorded") or 1) for s in found),
                                      stopped_at=found[-1].get("stopped_at"), live=True,
                                      created_by=first.get("created_by"))
        merged["id"], merged["created_at"] = first["id"], first["created_at"]
        merged["created_by"] = first.get("created_by")
        if merged_audio_path and os.path.exists(merged_audio_path):
            merged["source_audio_path"] = merged_audio_path
        gone = {s["id"] for s in found[1:]}
        _forget_memory([f"live:{i}" for i in gone])
        sessions_store = [merged if s.get("id") == first["id"] else s for s in sessions_store if s.get("id") not in gone]
        _save_sessions()
        _broadcast({"type": "session_complete", "session_id": first["id"], "session": merged})
        print("[merge] done")
    except Exception as e:
        _report_failure(e, 0, created_by=first.get("created_by"))


def _forget_memory(sources: list[str]):
    """Drop search entries of recordings that no longer exist on their own."""
    import chromadb
    collection = chromadb.PersistentClient(path="chroma_db").get_or_create_collection(name="notes_collection")
    for source in sources:
        collection.delete(where={"source": source})


def run_pipeline(youtube_url: str, created_by: str | None = None):
    """A YouTube video: the whole audio (or its captions) in one pass, one session."""
    global _pipeline_thread
    _pipeline_thread = threading.current_thread()
    try:
        with _pipeline_semaphore:
            result = _run_graph(_new_state(youtube_url=youtube_url), 0)
        if stop_event.is_set():
            return
        session = _session_from_result({**result, "youtube_url": youtube_url}, None, 0, created_by=created_by)
        sessions_store.append(session)
        _save_sessions()
        _broadcast(session)
        _broadcast({"type": "session_complete", "total_chunks": 1})
    except Exception as e:
        _report_failure(e, 0, created_by=created_by)


# The web build (react-native/dist, synced here as ./web) — mounted last, so
# every @app route above still wins; this only catches what nothing else
# matched. html=True serves index.html for "/" and for any path with no file
# extension, which is what a browser refresh needs even though this app has
# no server-side routes of its own (it's one page with in-memory view state).
if os.path.isdir("web"):
    app.mount("/", StaticFiles(directory="web", html=True), name="web")
