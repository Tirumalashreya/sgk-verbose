"""Two phones can be logged into the exact same shared username at once (this
app hands out a short list of logins, not individual accounts) — if both
start a live recording around the same moment, their minute-pieces must land
in two separate documents, never merged into one. Routing by the recording's
own id (returned by /start-live, sent back on every piece) is what makes
that true regardless of username."""
import pytest


@pytest.fixture
def api_env(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    import api
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(api, "sessions_store", [])
    monkeypatch.setattr(api, "_active_upload_hashes", set())
    monkeypatch.setattr(api, "_live_recording_sessions", {})
    monkeypatch.setattr(api, "_last_stopped_sessions", {})
    monkeypatch.setattr(api, "_last_stopped_at", {})
    monkeypatch.setattr(api, "_live_by_id", {})
    monkeypatch.setattr(api, "_save_chunk_result", lambda *a: None)

    class SyncThread:                      # run "background" finalize immediately
        def __init__(self, target, args=(), daemon=None): self.t, self.a = target, args
        def start(self): self.t(*self.a)
    monkeypatch.setattr(api.threading, "Thread", SyncThread)

    def fake_graph(state, chunk_index):
        minute = open(state["audio_path"], "rb").read().decode()
        return {"transcript": minute, "notes": minute, "shlokas": [], "segments": []}
    monkeypatch.setattr(api, "_run_graph", fake_graph)

    def fake_text_steps(transcript, chunk_index, source):
        return {"notes": transcript, "summary": "", "shlokas": [], "segments": []}
    monkeypatch.setattr(api, "_run_text_steps", fake_text_steps)
    return api, TestClient(api.app)


def test_two_phones_same_username_recording_at_once_stay_separate(api_env, monkeypatch):
    api, client = api_env
    monkeypatch.setenv("APP_USERS", "sgkacharya:pw")
    import base64
    auth = {"Authorization": f"Basic {base64.b64encode(b'sgkacharya:pw').decode()}"}

    # Phone A starts recording
    r_a = client.post("/start-live", headers=auth)
    id_a = r_a.json()["id"]

    # Phone B, same username, starts a second recording before A has stopped
    r_b = client.post("/start-live", headers=auth)
    id_b = r_b.json()["id"]
    assert id_a != id_b

    # Each phone uploads its own minute, tagging it with its own recording id
    client.post("/upload-audio", headers=auth, data={"live": "1", "live_session_id": id_a},
                files={"file": ("a.webm", "phone A's words".encode())})
    client.post("/upload-audio", headers=auth, data={"live": "1", "live_session_id": id_b},
                files={"file": ("b.webm", "phone B's words".encode())})

    # Each stops its own recording by id, not "whatever this username has"
    client.post("/stop-session", headers=auth, json={"live_session_id": id_a})
    client.post("/stop-session", headers=auth, json={"live_session_id": id_b})

    assert len(api.sessions_store) == 2, "two phones' recordings must not merge into one session"
    by_id = {s["id"]: s for s in api.sessions_store}
    assert by_id[id_a]["transcript"] == "phone A's words"
    assert by_id[id_b]["transcript"] == "phone B's words"
    assert "phone B's words" not in by_id[id_a]["transcript"]
    assert "phone A's words" not in by_id[id_b]["transcript"]
