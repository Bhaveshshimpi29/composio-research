"""Step 1: find each app's developer docs, auth and pricing pages (and any MCP server). Saves urls only."""
import json, re, sys, concurrent.futures as cf
from . import config
from .llm import Meter, client
from .util import read_csv, slug, today

PROMPT = """Find the OFFICIAL pages for the app "{app}" (website hint: {hint}) that a developer would read:
1. API / developer documentation home or API reference
2. the authentication page (how to get API credentials: OAuth, API keys, tokens)
3. the pricing or plans page, or the page saying who can get API access (free, paid, partner, contact sales)
4. any MCP server (official or community)
Use web search. Prefer the vendor's own domains. Then reply with ONLY this JSON:
{{"docs": [urls], "auth": [urls], "pricing": [urls], "mcp": [urls]}}
Only include URLs that appeared in your search results."""

def hint_url(hint):
    tok = (hint or "").split()[0] if hint else ""
    return ("https://" + tok) if re.match(r"^[\w.-]+\.[a-z]{2,}(/\S*)?$", tok) else None

def search_anthropic(app, hint, meter):
    resp = client().messages.create(
        model=config.MODEL_DISCOVER, max_tokens=1500,
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 4}],
        messages=[{"role": "user", "content": PROMPT.format(app=app, hint=hint)}])
    meter.add(resp.usage)
    seen = []
    for b in resp.content:
        if b.type == "web_search_tool_result" and isinstance(b.content, list):
            seen += [x.url for x in b.content if hasattr(x, "url")]
    text = "".join(b.text for b in resp.content if b.type == "text")
    chosen = {}
    m = re.search(r"\{.*\}", text, re.S)
    if m:
        try: chosen = json.loads(m.group(0))
        except Exception: pass
    out = []
    for kind in ("docs", "auth", "pricing", "mcp"):
        for u in chosen.get(kind, []) or []:
            if u in seen: out.append({"url": u, "kind": kind})   # grounded: it really was in the search results
    if not out: out = [{"url": u, "kind": "search"} for u in seen[:4]]
    return out

def search_composio(app, hint, meter):
    """EXPERIMENTAL. Composio Search toolkit. The slug comes from Composio's docs, but the argument name
    ('query') and the shape of the result are NOT documented on the page I could read, so we pull every
    URL out of whatever comes back and fall back to Anthropic search on any error. See DECISIONS.md."""
    import os
    from composio import Composio
    c = Composio(api_key=os.environ["COMPOSIO_API_KEY"])
    urls = []
    for q in (f"{app} API documentation authentication", f"{app} API pricing access", f"{app} MCP server"):
        res = c.tools.execute("COMPOSIO_SEARCH_DUCK_DUCK_GO_SEARCH", user_id="default",
                              arguments={"query": q}, dangerously_skip_version_check=True)
        urls += re.findall(r"https?://[^\s\"'\\<>)]+", json.dumps(res, default=str))
    ranked = sorted(dict.fromkeys(urls), key=lambda u: 0 if re.search(r"docs|developer|api|dev\.", u) else 1)
    return [{"url": u, "kind": "search"} for u in ranked[:5]]

def discover_app(row, meter, force=False):
    path = config.DISCOVERED / f"{slug(row['app'])}.json"
    if path.exists() and not force: return
    try:
        if config.SEARCH_PROVIDER == "composio":
            try: found, provider = search_composio(row["app"], row["hint"], meter), "composio"
            except Exception as e:
                print(f"  composio search failed for {row['app']} ({e}); using Anthropic search", file=sys.stderr)
                found, provider = search_anthropic(row["app"], row["hint"], meter), "anthropic(fallback)"
        else:
            found, provider = search_anthropic(row["app"], row["hint"], meter), "anthropic"
    except Exception as e:
        found, provider = [], f"error: {e}"
    h = hint_url(row["hint"])
    if h: found.append({"url": h, "kind": "hint"})
    urls, seen = [], set()
    for f in found:
        if f["url"] not in seen: seen.add(f["url"]); urls.append(f)
    config.DISCOVERED.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"app": row["app"], "provider": provider, "date": today(),
                                "urls": urls[:config.MAX_URLS_PER_APP]}, indent=1), encoding="utf-8")
    print("discovered", row["app"], len(urls))

def main(force=False, only=None):
    hints = read_csv(config.HINTS_CSV)
    if only: hints = [h for h in hints if h["app"].lower() in {o.lower() for o in only}]
    with Meter("discover", "pass1", config.MODEL_DISCOVER) as m, cf.ThreadPoolExecutor(config.WORKERS) as ex:
        list(ex.map(lambda r: discover_app(r, m, force), hints))

if __name__ == "__main__":
    main(force="--force" in sys.argv, only=[a for a in sys.argv[1:] if not a.startswith("--")] or None)
