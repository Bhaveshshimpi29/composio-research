"""One-off migration: turn the earlier Firecrawl run (data/raw/<id>.json) into this repo's page cache
(data/raw/<app-slug>/<hash>.json) so the quote check can run against the exact text the extractor saw.
Page text was cut at 12,000 characters by the earlier run; that is recorded, not hidden."""
import ast, csv, hashlib, json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import config
from src.util import slug

def lenient_markdown(content: str) -> str:
    """Pull the markdown out of a (possibly truncated) Firecrawl JSON string."""
    m = re.search(r'"markdown":\s*"', content)
    if not m: return ""
    s = content[m.end():]
    out, i = [], 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            n = s[i + 1]
            if n == "u" and i + 5 < len(s) and re.fullmatch(r"[0-9a-fA-F]{4}", s[i + 2:i + 6]):
                out.append(chr(int(s[i + 2:i + 6], 16))); i += 6; continue
            out.append({"n": "\n", "t": "\t", "r": "", '"': '"', "\\": "\\", "/": "/"}.get(n, n)); i += 2; continue
        if c == '"': break
        out.append(c); i += 1
    return "".join(out)

def clean(md: str) -> str:
    md = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", md)            # images
    md = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", md)         # links -> their text
    md = re.sub(r"[*_`#>]+", "", md)                         # markdown decoration
    md = re.sub(r"\\+\s*\n", "\n", md)
    return re.sub(r"\n\s*\n+", "\n", re.sub(r"[ \t]+", " ", md)).strip()

def main(src_dir=config.RAW, out_dir=config.RAW, apps_csv=config.APPS_CSV):
    rows = list(csv.DictReader(open(apps_csv, encoding="utf-8")))
    written = 0
    for i, row in enumerate(rows, start=1):
        p = Path(src_dir) / f"{i}.json"
        if not p.exists(): continue
        d = json.loads(p.read_text(encoding="utf-8"))
        assert d["app"].lower() == row["app"].lower(), (i, d["app"], row["app"])   # ids line up with apps.csv
        ev = d.get("scraped_evidence") or []
        if isinstance(ev, str):
            try: ev = ast.literal_eval(ev)
            except Exception: ev = []
        seen = set()
        for e in ev:
            url = e["url"].split("#")[0]
            if url in seen: continue
            text = clean(lenient_markdown(e.get("content", "")))
            if len(text) < 300: continue
            seen.add(url)
            out = Path(out_dir) / slug(row["app"]) / (hashlib.sha1(url.encode()).hexdigest()[:12] + ".json")
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps({"url": url, "fetched_at": "2026-11-23", "method": "firecrawl (earlier run, cut at 12000 chars)",
                                       "text": text, "error": ""}, ensure_ascii=False), encoding="utf-8")
            written += 1
    print("pages written:", written)

if __name__ == "__main__": main()
