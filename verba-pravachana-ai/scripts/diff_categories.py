"""
Break down where two transcripts of the same audio differ.

    python scripts/diff_categories.py A.txt B.txt [--examples N]

Every differing stretch is classed as: word joining/splitting, spelling
variant, different words, or words missing from one side, and as inside a
Sanskrit verse or in Telugu narration. Shares are by characters.
"""
import argparse, difflib, re, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rapidfuzz.distance import Levenshtein

_PUNCT = re.compile(r"[.,;:!?।॥\"'“”‘’()\[\]{}…—–-]+")
_SANSKRIT = re.compile(r"ః|[ఖఘఛఝఠఢథధఫభశషఋ]|ృ|క్ష|జ్ఞ")
_FOLD = [("ం", "మ్"), ("ఁ", ""), ("ా", "ఆ"), ("ీ", "ఈ"), ("ూ", "ఊ"), ("ే", "ఏ"), ("ో", "ఓ"), ("ై", "ఐ"), ("ౌ", "ఔ"),
         ("ళ", "ల"), ("ణ", "న"), ("శ", "స"), ("ష", "స"), ("ఱ", "ర")]


def words(t):
    return [w for w in _PUNCT.sub(" ", t).split() if w]


def fold(s):
    for a, b in _FOLD:
        s = s.replace(a, b)
    return re.sub(r"(.)\1+", r"\1", s.replace("్", ""))


def classify(a, b):
    sa, sb = "".join(a), "".join(b)
    if not a or not b:
        return "missing words"
    if sa == sb:
        return "word joining/splitting"
    if fold(sa) == fold(sb) or Levenshtein.normalized_similarity(fold(sa), fold(sb)) >= 0.8:
        return "spelling variant"
    return "different words"


def analyse(ta, tb, examples=3, label_a="A", label_b="B"):
    wa, wb = words(ta), words(tb)
    total = sum(len(w) for w in wa)
    cats, where, samples = {}, {"verse": 0, "narration": 0}, {}
    for op, a1, a2, b1, b2 in difflib.SequenceMatcher(a=wa, b=wb, autojunk=False).get_opcodes():
        if op == "equal":
            continue
        a, b = wa[a1:a2], wb[b1:b2]
        c = classify(a, b)
        size = max(len("".join(a)), len("".join(b)))
        cats[c] = cats.get(c, 0) + size
        ctx = " ".join(wa[max(0, a1 - 4):a2 + 4])
        where["verse" if len(_SANSKRIT.findall(ctx)) >= 2 else "narration"] += size
        samples.setdefault(c, []).append((size, " ".join(a) or "∅", " ".join(b) or "∅"))
    diff = sum(cats.values())
    print(f"Differing: {diff} of {total} characters ({100 * diff / total:.1f}%)\n")
    for c, n in sorted(cats.items(), key=lambda kv: -kv[1]):
        print(f"  {c:24} {100 * n / total:5.1f}% of text   ({100 * n / diff:4.0f}% of the differences)")
    print(f"\n  inside Sanskrit verses: {100 * where['verse'] / diff:.0f}% of differences   |   in Telugu narration: {100 * where['narration'] / diff:.0f}%")
    for c in sorted(samples, key=lambda c: -cats[c]):
        print(f"\n  e.g. {c}:")
        for _, a, b in sorted(samples[c], reverse=True)[:examples]:
            print(f"     {label_a}: {a[:70]}\n     {label_b}: {b[:70]}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("a"); ap.add_argument("b"); ap.add_argument("--examples", type=int, default=3)
    x = ap.parse_args()
    analyse(open(x.a, encoding="utf-8").read(), open(x.b, encoding="utf-8").read(), x.examples,
            os.path.basename(x.a)[:12], os.path.basename(x.b)[:12])
