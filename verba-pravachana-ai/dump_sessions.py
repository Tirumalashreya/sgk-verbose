import sqlite3, json

c = sqlite3.connect("/home/shreya/sgk/sessions.db")
rows = c.execute("SELECT id, created_at, data FROM sessions").fetchall()
print(f"Total in DB: {len(rows)}")
for r in rows:
    d = json.loads(r[2])
    print(r[0][:8], r[1], "by:", d.get("created_by"), "archived:", d.get("archived"), "title:", d.get("title")[:30])
