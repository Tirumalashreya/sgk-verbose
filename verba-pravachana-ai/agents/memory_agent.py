from graph.state import VerbaState
import uuid
import chromadb
def memory_agent(state: VerbaState) -> VerbaState:
    segments = state.get("segments") or []
    client = chromadb.PersistentClient(path="chroma_db")
    collection = client.get_or_create_collection(name="notes_collection")
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
