import os, re, time, requests
from dotenv import load_dotenv
load_dotenv()

_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
_URL = "https://openrouter.ai/api/v1/chat/completions"

# Best free model for multilingual Indian-language text (Telugu/Sanskrit/Tamil)
DEFAULT_MODEL = "google/gemini-2.0-flash-exp:free"


def call(prompt: str, model: str = DEFAULT_MODEL, temperature: float = 0.1) -> str:
    for attempt in range(5):
        try:
            resp = requests.post(
                _URL,
                headers={
                    "Authorization": f"Bearer {_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": temperature,
                },
                timeout=120,
            )
            if resp.status_code == 429:
                wait = 15
                m = re.search(r"(\d+)s", resp.text)
                if m:
                    wait = int(m.group(1)) + 1
                print(f"[openrouter] rate limit, waiting {wait}s (attempt {attempt + 1})")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"[openrouter] error (attempt {attempt + 1}): {e}")
            time.sleep(10)
    return ""
