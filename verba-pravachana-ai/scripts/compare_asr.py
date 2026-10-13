"""
Compare ASR providers on one audio clip.

    python scripts/compare_asr.py CLIP.mp3 [--notebooklm notebooklm.txt] [--out DIR]

Transcripts are saved to DIR/asr_outputs/*.txt and re-used on later runs, so adding
a NotebookLM transcript afterwards costs no API calls. Writes DIR/asr_comparison.html.
"""
import argparse, difflib, html, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)  # caches live under audio_input/
from dotenv import load_dotenv
load_dotenv(os.path.join(ROOT, ".env"))

_PUNCT = re.compile(r"[\s.,;:!?।॥\"'“”‘’()\[\]{}…—–-]+")


def words(text: str) -> list[str]:
    return [w for w in _PUNCT.split(text or "") if w]


def wer(ref: list[str], hyp: list[str]) -> float:
    """Word error rate of hyp against ref (Levenshtein over words)."""
    if not ref:
        return 0.0 if not hyp else 1.0
    prev = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, 1):
        cur = [i] + [0] * len(hyp)
        for j, h in enumerate(hyp, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (r != h))
        prev = cur
    return prev[-1] / len(ref)


def chars(text: str) -> str:
    return _PUNCT.sub("", text or "")


def cer(ref: str, hyp: str) -> float | None:
    """Character error rate — fairer than WER for Telugu, where systems join or
    split words differently. Needs rapidfuzz; returns None without it."""
    try:
        from rapidfuzz.distance import Levenshtein
    except ImportError:
        return None
    a, b = chars(ref), chars(hyp)
    return Levenshtein.distance(a, b) / max(len(a), 1)


def diff_html(ref: list[str], hyp: list[str]) -> str:
    out = []
    for op, a1, a2, b1, b2 in difflib.SequenceMatcher(a=ref, b=hyp, autojunk=False).get_opcodes():
        if op == "equal":
            out.append(html.escape(" ".join(hyp[b1:b2])))
        else:
            if a2 > a1:
                out.append(f'<del title="missing vs reference">{html.escape(" ".join(ref[a1:a2]))}</del>')
            if b2 > b1:
                out.append(f'<ins title="differs from reference">{html.escape(" ".join(hyp[b1:b2]))}</ins>')
    return " ".join(out)


def run_providers(clip: str, out_dir: str) -> dict:
    from agents.transcription_agent import _sarvam_stt, sarvam_settings
    from agents.gemini_asr import gemini_stt
    runs = {
        "Sarvam saaras:v3": lambda: _sarvam_stt(clip, sarvam_settings("saaras:v3", "transcribe", False))[0],
        "Sarvam v4 transcribe + keyterms": lambda: _sarvam_stt(clip, sarvam_settings("saaras:v4", "transcribe", True))[0],
        "Sarvam v4 verbatim + keyterms": lambda: _sarvam_stt(clip, sarvam_settings("saaras:v4", "verbatim", True))[0],
        "Sarvam v4 verbatim": lambda: _sarvam_stt(clip, sarvam_settings("saaras:v4", "verbatim", False))[0],
        "Gemini · timestamps (run 1)": lambda: gemini_stt(clip, "timestamps")[0],
        "Gemini · timestamps (run 2)": lambda: gemini_stt(clip, "timestamps", use_cache=False)[0],
        "Gemini · custom vocabulary": lambda: gemini_stt(clip, "vocabulary")[0],
        "Gemini Flash · prompt (run 1)": lambda: gemini_stt(clip, "llm")[0],
        "Gemini Flash · prompt (run 2)": lambda: gemini_stt(clip, "llm", use_cache=False)[0],
    }
    texts = {}
    os.makedirs(os.path.join(out_dir, "asr_outputs"), exist_ok=True)
    for name, fn in runs.items():
        path = os.path.join(out_dir, "asr_outputs", re.sub(r"\W+", "_", name).strip("_") + ".txt")
        if os.path.exists(path):
            texts[name] = open(path, encoding="utf-8").read()
            continue
        try:
            texts[name] = fn()
        except Exception as e:
            print(f"[compare] {name} failed: {e}")
            continue
        with open(path, "w", encoding="utf-8") as f:
            f.write(texts[name])

    # Transcripts produced elsewhere (e.g. scripts/indicconformer_transcribe.py)
    known = {re.sub(r"\W+", "_", n).strip("_") + ".txt" for n in runs}
    out_dir = os.path.join(out_dir, "asr_outputs")
    for fname in sorted(os.listdir(out_dir)):
        if fname.endswith(".txt") and fname not in known:
            texts[fname[:-4].replace("_", " ")] = open(os.path.join(out_dir, fname), encoding="utf-8").read()
    return texts


def report(texts: dict, reference: str | None, clip: str) -> str:
    names = list(texts)
    w = {n: words(t) for n, t in texts.items()}
    def cell(a, b):
        if a == b:
            return "<td>—</td>"
        c = cer(texts[a], texts[b])
        cw = f"{(1 - min(c, 1)) * 100:.0f}%" if c is not None else "n/a"
        return f"<td><b>{cw}</b> <span class=n>/ {(1 - min(wer(w[a], w[b]), 1)) * 100:.0f}%</span></td>"
    rows = []
    for a in names:
        rows.append(f"<tr><th>{html.escape(a)}</th><td class=n>{len(w[a])}</td>{''.join(cell(a, b) for b in names)}</tr>")
    head = "".join(f"<th>{html.escape(n)}</th>" for n in names)
    ref = reference or names[0]
    ref_note = ("NotebookLM transcript (treated as reference)" if reference
                else f"{ref} (no human/NotebookLM reference yet — this shows disagreement, not errors)")
    cols = "".join(
        f"<section><h3>{html.escape(n)}</h3><p>{html.escape(texts[n]) if n == ref else diff_html(w[ref], w[n])}</p></section>"
        for n in names)
    return f"""<!doctype html><html><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>ASR comparison</title><style>
:root{{--bg:#faf7f0;--ink:#2b2418;--muted:#7a6e58;--line:#e4dccb;--ins:#fde2b8;--del:#f6c9c9}}
@media (prefers-color-scheme:dark){{:root{{--bg:#16130e;--ink:#eee6d6;--muted:#a89c84;--line:#3a3226;--ins:#5a4210;--del:#5a2020}}}}
body{{background:var(--bg);color:var(--ink);font:15px/1.7 system-ui,"Noto Sans Telugu",sans-serif;margin:0;padding:16px}}
h1{{font-size:20px}} table{{border-collapse:collapse;margin:12px 0;font-size:13px}} td,th{{border:1px solid var(--line);padding:6px 10px;text-align:center}}
th{{text-align:left}} td.n{{color:var(--muted)}} .note{{color:var(--muted);font-size:13px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:16px}}
section{{border:1px solid var(--line);border-radius:10px;padding:12px}} h3{{margin:0 0 8px;font-size:14px}}
ins{{background:var(--ins);text-decoration:none}} del{{background:var(--del)}}
</style></head><body>
<h1>ASR comparison — {html.escape(os.path.basename(clip))}</h1>
<p class=note>Each cell: <b>character agreement</b> / word agreement (100% − error rate, punctuation and spacing ignored). Character agreement is the fairer number for Telugu. Row = reference, column = compared.</p>
<table><tr><th></th><th>words</th>{head}</tr>{''.join(rows)}</table>
<p class=note>Highlights below are against: <b>{html.escape(ref_note)}</b>.
<del>red</del> = words in the reference that are missing, <ins>amber</ins> = words that differ.</p>
<div class=grid>{cols}</div></body></html>"""


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("clip")
    ap.add_argument("--notebooklm")
    ap.add_argument("--out", default=os.path.dirname(os.path.abspath(sys.argv[1])) if len(sys.argv) > 1 else ".")
    args = ap.parse_args()
    clip = os.path.abspath(args.clip)
    texts = run_providers(clip, args.out)
    reference = None
    if args.notebooklm:
        reference = "NotebookLM"
        texts = {reference: open(args.notebooklm, encoding="utf-8").read(), **texts}
    out = os.path.join(args.out, "asr_comparison.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(report(texts, reference, clip))
    names = list(texts)
    print("\nAgreement (100% - WER):")
    for a in names:
        print(f"  {a:30} " + "  ".join(f"{(1 - min(wer(words(texts[a]), words(texts[b])), 1)) * 100:5.0f}%" for b in names if b != a))
    print(f"\nReport: {out}")
