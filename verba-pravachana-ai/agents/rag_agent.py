import chromadb
def rag_agent(query: str) -> str:
    client = chromadb.PersistentClient(path="chroma_db")
    collection = client.get_or_create_collection(name="notes_collection")
    results = collection.query(
        query_texts=[query],
        n_results=3
    )
    # documents is [[]] (not []) when the collection is empty
    docs = (results.get("documents") or [[]])[0]
    return docs[0] if docs else "No relevant information found."
