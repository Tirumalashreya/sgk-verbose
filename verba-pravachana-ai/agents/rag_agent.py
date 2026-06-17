import chromadb
def rag_agent(query: str) -> str:
    client = chromadb.PersistentClient(path="chroma_db")
    collection = client.get_or_create_collection(name="notes_collection")
    results = collection.query(
        query_texts=[query],
        n_results=3
    )
    return results["documents"][0][0] if results["documents"] else "No relevant information found."
