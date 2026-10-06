import itertools, os, re, time
from concurrent.futures import ThreadPoolExecutor
from groq import Groq
from dotenv import load_dotenv
load_dotenv()

# Groq retires models regularly (the llama-3.x models used before are gone),
# so both are overridable from .env without a code change.
FAST_MODEL = os.getenv("GROQ_FAST_MODEL", "openai/gpt-oss-20b")
STRONG_MODEL = os.getenv("GROQ_STRONG_MODEL", "openai/gpt-oss-120b")
MAX_COMPLETION_TOKENS = 8192

# Every Groq LLM key slot. Keys from different Groq accounts have separate rate
# limits, so a call may use any of them — its own step's key is tried first.
_KEY_ENVS = ["GROQ_API_KEY_SHLOKA", "GROQ_API_KEY_STRUCTURER", "GROQ_API_KEY_NOTES",
             "GROQ_API_KEY_SPARE1", "GROQ_API_KEY_SPARE2"]
_MAX_ROUNDS = 6
_cooldown_until: dict[str, float] = {}  # key -> time it may be used again (shared across calls)
_rotation = itertools.count()           # spreads concurrent calls across keys


def _distinct_keys(first_env: str | None = None) -> list[str]:
    keys = []
    for env in ([first_env] if first_env else []) + _KEY_ENVS:
        k = os.getenv(env, "")
        # The same key is often pasted into several slots — count it once
        if k and k not in keys:
            keys.append(k)
    return keys


def _keys_for(api_key_env: str) -> list[str]:
    keys = _distinct_keys(api_key_env)
    if len(keys) > 1:
        # Start each call on the next key, so parallel calls don't all pile onto one account
        start = next(_rotation) % len(keys)
        keys = keys[start:] + keys[:start]
    return keys


def parallel_map(fn, items: list) -> list:
    """fn over items, one in-flight call per distinct Groq key, results in input order."""
    workers = max(1, min(len(_distinct_keys()), int(os.getenv("GROQ_MAX_PARALLEL", "8")), len(items)))
    if workers == 1:
        return [fn(x) for x in items]
    with ThreadPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(fn, items))


def _request(api_key: str, prompt: str, model: str, temperature: float) -> str:
    extra = {}
    if "gpt-oss" in model:
        # Reasoning models spend output tokens thinking first; at the
        # default cap they often return an empty answer for long Telugu
        # prompts. Low effort + a higher cap leaves room for the answer.
        extra = {"reasoning_effort": "low"}
    response = Groq(api_key=api_key).chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_completion_tokens=MAX_COMPLETION_TOKENS,
        **extra,
    )
    choice = response.choices[0]
    content = (choice.message.content or "").strip()
    if choice.finish_reason == "length" or not content:
        print(f"[groq_llm] WARNING {model} reply {'cut off' if choice.finish_reason == 'length' else 'empty'} "
              f"({response.usage.completion_tokens} tokens) — output may be incomplete")
    return content


def call(prompt: str, api_key_env: str, model: str = FAST_MODEL, temperature: float = 0.1) -> str:
    keys = _keys_for(api_key_env)
    if not keys:
        print(f"[groq_llm] no Groq key set for {api_key_env}")
        return ""

    for round_ in range(_MAX_ROUNDS):
        for i, key in enumerate(keys):
            if _cooldown_until.get(key, 0) > time.time():
                continue
            try:
                return _request(key, prompt, model, temperature)
            except Exception as e:
                msg = str(e)
                # Rate-limited: park this key for as long as Groq asks and move
                # straight on to the next one instead of sleeping on it
                m = re.search(r'try again in (?:(\d+)m)?([\d.]+)s', msg)
                wait = (int(m.group(1) or 0) * 60 + float(m.group(2)) + 1) if m else 20 * (round_ + 1)
                _cooldown_until[key] = time.time() + wait
                print(f"[groq_llm] key #{i + 1} of {len(keys)} unavailable for {wait:.0f}s: {msg[:90]}")

        # Every key is cooling down — wait for the first one to come back
        pause = min(max(_cooldown_until.get(k, 0) - time.time(), 0) for k in keys)
        pause = min(pause, 120)
        print(f"[groq_llm] all {len(keys)} key(s) rate-limited, waiting {pause:.0f}s (round {round_ + 1}/{_MAX_ROUNDS})")
        time.sleep(pause)

    print(f"[groq_llm] giving up on this call ({api_key_env}) — all keys stayed rate-limited")
    return ""
