import os, re, time
from groq import Groq
from dotenv import load_dotenv
load_dotenv()

FAST_MODEL = "llama-3.1-8b-instant"
STRONG_MODEL = "llama-3.3-70b-versatile"

# Spare keys tried in order when primary key is rate-limited
_SPARE_KEYS = ["GROQ_API_KEY_SPARE1", "GROQ_API_KEY_SPARE2"]


def call(prompt: str, api_key_env: str, model: str = FAST_MODEL, temperature: float = 0.1) -> str:
    # Try primary key first, then spare keys
    keys_to_try = [api_key_env] + _SPARE_KEYS

    for key_env in keys_to_try:
        api_key = os.getenv(key_env, "")
        if not api_key:
            continue
        client = Groq(api_key=api_key)
        wait = 20  # start at 20s, double each retry (exponential backoff)
        for attempt in range(4):
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature,
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                msg = str(e)
                # Parse wait time from Groq error if available
                m = re.search(r'try again in ([\d.]+)s', msg)
                if m:
                    wait = float(m.group(1)) + 2
                print(f"[groq_llm] rate limit on {key_env}, waiting {wait:.0f}s (attempt {attempt + 1}): {msg[:80]}")
                time.sleep(wait)
                wait = min(wait * 2, 120)  # exponential backoff, cap at 2 min
        print(f"[groq_llm] all retries exhausted for {key_env}, trying next key...")

    print(f"[groq_llm] all keys exhausted for {api_key_env}")
    return ""
