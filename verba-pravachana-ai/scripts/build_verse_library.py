"""
Build the local verse library used to verify Tamil pasurams.

    python scripts/build_verse_library.py

Downloads the Nalayira Divya Prabandham (Unicode Tamil) from Project Madurai
(https://www.projectmadurai.org, free for non-commercial use with credit) and
writes data/verse_library/divya_prabandham.json. The text is not committed to
this repository; run this script to fetch it.
"""
import html, json, os, re, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "data", "verse_library")
PARTS = [f"https://www.projectmadurai.org/pm_etexts/utf8/pmuni{n}_tam.html" for n in ("0621", "0622", "0623", "0624")]
SOURCE = "Project Madurai — nAlAyira tiviya pirapantam, pAcurams in Tamil (pmuni0621–0624)"

_WORK = re.compile(r"^\s*\d+\.\s*(.+?)\s*\(\s*(\d+)\s*-\s*(\d+)\s*\)\s*$")   # "2. ஆண்டாள் - திருப்பாவை (474 -503)"
_SECTION = re.compile(r"<strong>\s*(.*?)\s*</strong>", re.S)
_START = re.compile(r"^\s*(\d{1,4})\.?[ \t]+(\S.*)$")                          # "1068  ...", "474\t...", "1.  ..."
_END = re.compile(r"\(\s*(\d{1,3})\s*\)\s*$")                                  # "... (1)"


def _lines(page: str):
    for raw in re.split(r"<br\s*/?>", page):
        section = _SECTION.search(raw)
        text = html.unescape(re.sub(r"<[^>]+>", "", raw)).replace("\xa0", " ").strip()
        yield text, (html.unescape(re.sub(r"<[^>]+>", "", section.group(1))).strip() if section else None)


def parse(page: str) -> list[dict]:
    verses, work, section, cur = [], "", "", None

    def close(position=None):
        nonlocal cur
        if cur is not None:
            cur["lines"] = [re.sub(r"\s+", " ", l).strip(" -") for l in cur["lines"] if l.strip(" -")]
            cur["position"] = position
            if cur["lines"]:
                verses.append(cur)
        cur = None

    for text, sect in _lines(page):
        if sect:
            section = re.sub(r"^\d+\.\s*", "", sect).strip()
        if _WORK.match(text):          # work heading, e.g. "2. ஆண்டாள் - திருப்பாவை (474 -503)"
            close()
            work = _WORK.match(text).group(1).strip()
            continue
        m = _START.match(text)
        if m and not text.startswith("-"):
            close()                    # a new number always ends the previous pasuram
            cur = {"number": int(m.group(1)), "work": work, "section": section, "lines": [m.group(2).strip()]}
        elif cur is not None and text:
            cur["lines"].append(text)
        if cur is not None and _END.search(text):
            cur["lines"][-1] = _END.sub("", cur["lines"][-1]).strip()
            close(int(_END.search(text).group(1)))
    close()
    return verses


def main():
    verses = []
    for url in PARTS:
        print(f"[library] downloading {url}")
        with urllib.request.urlopen(url, timeout=60) as r:
            verses.extend(parse(r.read().decode("utf-8", errors="replace")))
    seen, unique = set(), []
    for v in verses:
        if v["number"] not in seen:
            seen.add(v["number"])
            unique.append(v)
    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, "divya_prabandham.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"source": SOURCE, "license": "Project Madurai e-text: free for non-commercial use; credit required",
                   "verses": unique}, f, ensure_ascii=False)
    nums = sorted(v["number"] for v in unique)
    print(f"[library] {len(unique)} pasurams (numbers {nums[0]}–{nums[-1]}) → {out}")
    missing = sorted(set(range(1, 4001)) - set(nums))
    if missing:
        print(f"[library] {len(missing)} numbers not parsed, e.g. {missing[:15]}")


if __name__ == "__main__":
    sys.exit(main())
