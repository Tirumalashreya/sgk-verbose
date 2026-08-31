import re, time, requests

_URL = "http://localhost:11434/v1/chat/completions"
DEFAULT_MODEL = "llama3.1:8b"


def call(prompt: str, model: str = DEFAULT_MODEL, temperature: float = 0.1) -> str:
    for attempt in range(5):
        try:
            resp = requests.post(
                _URL,
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": temperature,
                },
                timeout=180,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"[ollama] error (attempt {attempt + 1}): {e}")
            time.sleep(5)
    return ""
