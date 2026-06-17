---
name: verba-pravachana-ai-project-context
description: "Multi-agent LangGraph system that processes Telugu spiritual discourses and generates structured notes, summaries, and a searchable archive"
metadata: 
  type: project
---

Project listens to Telugu spiritual discourses (pravachanams) from YouTube or live streams containing Telugu, Sanskrit shlokas, and Tamil phrases, then automatically generates structured notes, summaries, key teachings, highlighted shlokas, and searchable knowledge archives.

**Project folder:** `verba-pravachana-ai/`

**Core design:** Event-driven, non-linear multi-agent system. All 7 agents share a single VerbaState dictionary. No agent calls another directly — they read/write state. The Orchestrator watches state and dynamically decides which agent runs next. Agents can run in parallel.

**Why:** User is building this to learn agentic AI while creating something personally meaningful (spiritual discourse archiving for Telugu devotees).

**The 7 Agents:**
1. Listener — captures live YouTube audio, buffers into 30-second chunks
2. Transcription — Whisper converts Telugu + Sanskrit + Tamil with timestamps
3. Shloka Detector — identifies Sanskrit verses by rhythm/structure, finds source scripture
4. Knowledge Structurer — labels each segment: teaching / story / shloka / philosophy / devotional
5. Notes Generator — summaries, bullet points, shloka meanings, key teachings
6. Memory Agent — stores everything as vector embeddings in ChromaDB
7. RAG Retrieval — semantic search ("What did Guru Garu say about Dharma?") with timestamps

**Parallel execution example:** After transcription, Orchestrator fires Agent 3 (Shloka Detector) AND Agent 4 (Knowledge Structurer) simultaneously. Agent 5 (Notes Generator) only runs after both complete.

**Tech Stack:**
- Agent Framework: LangGraph (multi-agent graph + orchestration)
- Speech AI: OpenAI Whisper (multilingual)
- Primary LLM: Google Gemini API
- Vector DB: ChromaDB (semantic search, RAG)
- Backend: FastAPI with WebSockets for live streaming
- Frontend: React Native (iOS + Android) styled like Sgks Live Notes
- Audio: FFmpeg + yt-dlp (YouTube extraction)
- Structured DB: PostgreSQL (user profiles, session history, bookmarks)
- Event Streaming: Redis Streams (async messages between agents)

**Completed as of 2026-05-25:**
- All 7 agents built: listener_agent.py, transcription_agent.py, shloka_detect_agent.py, knowledge_structurer_agent.py, notes_generator_agent.py, memory_agent.py, rag_agent.py
- graph/state.py, graph/orchestrator.py, main.py
- api.py — FastAPI backend
- sgks-app — React Native frontend (Expo)
- Gemini API key resolved — use gemini-2.5-flash or gemini-2.5-flash-lite, NOT gemini-2.0-flash
- START and END in LangGraph must be used without quotes (they are imported constants, not strings)

**Frontend-backend connection (done 2026-05-25):**
- `services/api.js` — added `getSessions()` for GET /sessions
- `api.py` — added `sessions_store` list, saves every chunk after processing, added GET /sessions endpoint
- `LiveScreen.js` — opens WebSocket on session start, displays real-time chunk cards
- `LibraryScreen.js` — fetches real sessions from backend instead of hardcoded data

**Backend speed improvements (done 2026-05-25):**
- Gemini client moved to module level in all 3 agents (no longer recreated per call)
- notes_generator_agent: all 3 Gemini calls run in parallel via ThreadPoolExecutor

**UI theme (done 2026-05-25):**
- Pastel Vaishnava theme: warm cream (#FFF8F0), deep warm brown (#2D1800), temple gold (#C4900F)

**Live mic recording added (2026-05-25):**
- listener_agent: pass-through if audio_path already set
- api.py: POST /upload-audio endpoint (m4a → pipeline)
- LiveScreen: YouTube mode + Live Mic mode toggle; expo-av for recording

**Gemini model situation (as of 2026-05-25):**
- gemini-2.5-flash-lite: works but 20 req/day on free tier
- gemini-2.0-flash: quota limit:0 on this key — gives 429
- FIX NEEDED: Add billing in Google AI Studio OR use gemini-2.5-flash-lite with retry/backoff

**Current status:** Full system built and connected. Pipeline runs. Blocked only by Gemini API quota. Resume by fixing Gemini model — add billing or test which model has quota.

## On new laptop setup:
1. `cd verba-pravachana-ai`
2. `python3 -m venv venv`
3. `source venv/bin/activate`
4. `pip install -r requirements.txt`
5. Copy `.env.example` to `.env` and add your GEMINI_API_KEY
6. `cd ../sgks-app && npm install`
