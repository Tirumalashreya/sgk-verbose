from graph.state import VerbaState
import chromadb
def memory_agent(state: VerbaState) -> VerbaState:
    segments = state.get("segments", [])
    client = chromadb.PersistentClient(path="chroma_db")
    collection = client.get_or_create_collection(name="notes_collection")
    documents = []
    metadatas = []
    ids = []
    for i, segment in enumerate(segments):
      documents.append(segment["text"])
      metadatas.append({"label": segment["label"], "summary": segment["summary"]})
      ids.append(f"segment_{i}")

    if documents:
        collection.add(documents=documents, metadatas=metadatas, ids=ids)
        print(f"[memory] saved {len(documents)} segments to ChromaDB")
    else:
        print("[memory] no segments to save, skipping")
    state["current_agent"] = "memory_done"
    return state