"""Quote check: plain code, no LLM. A claim only survives if its quote is in the cached page it cites."""
import re
from .schema import EVIDENCED, UNKNOWN_VALUE

MIN_QUOTE_CHARS = 15

def normalize(text: str) -> str:
    t = (text or "").replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    t = re.sub(r"[‐-―−]", "-", t).replace(" ", " ")
    return re.sub(r"\s+", " ", t).strip().lower()

def quote_in_page(quote: str, page_text: str) -> bool:
    q = normalize(quote)
    return len(q) >= MIN_QUOTE_CHARS and q in normalize(page_text)

def check_record(rec: dict, pages: dict):
    """pages: {url: full cached text}. Returns (new_record, failed_fields)."""
    rec = dict(rec); failed = []
    ev = rec.get("evidence", [])
    for field in EVIDENCED:
        value = rec.get(field)
        if field == "existing_mcp" and value == "none_found":   # absence cannot be quoted
            continue
        if value == UNKNOWN_VALUE.get(field, "unknown"):       # nothing claimed, nothing to prove
            continue
        ok = any(e.get("field") == field and e.get("url") in pages and quote_in_page(e.get("quote", ""), pages[e["url"]])
                 for e in ev)
        if not ok:
            failed.append(field)
            rec[field] = UNKNOWN_VALUE.get(field, "unknown")
    kept = [e for e in ev if e.get("url") in pages and quote_in_page(e.get("quote", ""), pages[e["url"]])]
    rec["evidence"] = kept
    return rec, failed
