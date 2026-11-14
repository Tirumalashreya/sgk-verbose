import os
import chromadb

try:
    from indic_transliteration import sanscript
    from indic_transliteration.sanscript import transliterate
except ImportError:
    sanscript = None
    transliterate = None

_CASUAL_WORDS = {
    'sri': 'శ్రీ', 'shri': 'శ్రీ', 'shree': 'శ్రీ',
    'saranagati': 'శరణాగతి', 'sharanagati': 'శరణాగతి',
    'gadyam': 'గద్యం', 'swami': 'స్వామి', 'ramanuja': 'రామానుజ',
    'bhagavath': 'భగవద్', 'bhagavad': 'భగవద్', 'bhagavan': 'భగవాన్',
    'namaskaram': 'నమస్కారం', 'namaste': 'నమస్తే',
    'ante': 'అంటే', 'enti': 'ఏంటి', 'emiti': 'ఏమిటి',
}

def _to_telugu(text: str) -> str:
    if not text or not sanscript:
        return ""
    words = text.split()
    converted = []
    for w in words:
        wl = w.lower().strip(",.?!;:\"'")
        if wl in _CASUAL_WORDS:
            converted.append(_CASUAL_WORDS[wl])
        else:
            try:
                itrans = wl.replace("ee", "I").replace("oo", "U").replace("aa", "A")
                t = transliterate(itrans, sanscript.ITRANS, sanscript.TELUGU)
                converted.append(t)
            except Exception:
                converted.append(w)
    return " ".join(converted)


def rag_agent(query: str) -> str:
    db_path = os.getenv("CHROMA_PATH", "chroma_db")
    client = chromadb.PersistentClient(path=db_path)
    collection = client.get_or_create_collection(name="notes_collection")

    query_variants = [query]
    if any('a' <= ch.lower() <= 'z' for ch in query):
        te = _to_telugu(query)
        if te and te != query:
            query_variants.append(te)

    results = collection.query(
        query_texts=query_variants,
        n_results=3
    )
    # documents is a list of lists corresponding to query_texts
    docs_lists = results.get("documents") or []
    for d_list in docs_lists:
        if d_list and any(d_list):
            for doc in d_list:
                if doc and doc.strip():
                    return doc
    return "No relevant information found."

