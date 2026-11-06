from graph.state import VerbaState
import threading
import uuid
import chromadb

_client = None
_client_lock = threading.Lock()


def _get_collection():
    """One PersistentClient for the whole process, created once and reused —
    not a fresh one per call. ChromaDB's SharedSystemClient keeps a single
    registry of open clients keyed by path; building (and then letting
    garbage-collection tear down) a new client every call raced that shared
    registry whenever two pipeline runs overlapped (this app allows up to 8
    at once), confirmed by real crashes: 'KeyError: chroma_db' and a torn-down
    Rust binding, both from two clients being created/released for the same
    path at the same moment. One long-lived client sidesteps that entirely."""
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                _client = chromadb.PersistentClient(path="chroma_db")
    return _client.get_or_create_collection(name="notes_collection")


def memory_agent(state: VerbaState) -> VerbaState:
    if state.get("live_piece"):
        # One minute of a recording still in progress: the whole recording is
        # stored once when it stops, so don't index this preview piece
        state["current_agent"] = "memory_done"
        return state
    segments = state.get("segments") or []
    collection = _get_collection()
    documents = []
    metadatas = []
    ids = []
    for segment in segments:
      if not isinstance(segment, dict) or not (segment.get("text") or "").strip():
          continue
      documents.append(segment["text"])
      metadatas.append({
          "label": str(segment.get("label") or ""),
          "summary": str(segment.get("summary") or ""),
          "chunk_index": int(state.get("chunk_index") or 0),
          "source": state.get("youtube_url") or state.get("audio_path") or "",
      })
      # ids must be unique across chunks and sessions — "segment_{i}" restarted every chunk
      ids.append(str(uuid.uuid4()))

    # Re-running a chunk (e.g. /reprocess) replaces its earlier segments instead
    # of adding a second copy that RAG would then return twice
    source = state.get("youtube_url") or state.get("audio_path") or ""
    if source:
        collection.delete(where={"$and": [{"source": source},
                                          {"chunk_index": int(state.get("chunk_index") or 0)}]})

    if documents:
        collection.add(documents=documents, metadatas=metadatas, ids=ids)
        print(f"[memory] saved {len(documents)} segments to ChromaDB")
    else:
        print("[memory] no segments to save, skipping")
    state["current_agent"] = "memory_done"
    return state
