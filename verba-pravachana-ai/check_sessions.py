import sqlite3, json

c = sqlite3.connect("/home/shreya/sgk/sessions.db")
for r in c.execute("SELECT id, created_at, data FROM sessions ORDER BY created_at DESC LIMIT 5"):
    d = json.loads(r[2])
    print(r[0], r[1], "created_by:", repr(d.get("created_by")), "archived:", repr(d.get("archived")), "notes_len:", len(d.get("notes") or ""))
