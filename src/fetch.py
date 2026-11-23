"""Step 2: download each discovered page ONCE into data/raw/<app>/ so reruns are free and repeatable."""
import hashlib, json, re, sys, threading, time, urllib.robotparser, concurrent.futures as cf
from urllib.parse import urlparse
import httpx
from bs4 import BeautifulSoup
from . import config, browser
from .util import read_csv, slug, today

_last, _lock, _robots = {}, threading.Lock(), {}

def cache_path(app, url):
    return config.RAW / slug(app) / (hashlib.sha1(url.encode()).hexdigest()[:12] + ".json")

def html_to_text(html):
    soup = BeautifulSoup(html, "html.parser")
    for t in soup(["script", "style", "noscript", "svg"]): t.decompose()
    text = soup.get_text("\n")
    return re.sub(r"\n\s*\n+", "\n", text).strip()

def allowed(url):
    host = urlparse(url).netloc
    if host not in _robots:
        rp = urllib.robotparser.RobotFileParser(f"{urlparse(url).scheme}://{host}/robots.txt")
        try: rp.read()
        except Exception: rp = None
        _robots[host] = rp
    rp = _robots[host]
    return True if rp is None else rp.can_fetch(config.USER_AGENT, url)

def polite_wait(url):
    host = urlparse(url).netloc
    with _lock:
        wait = _last.get(host, 0) + config.FETCH_DELAY_SECONDS - time.time()
        _last[host] = time.time() + max(wait, 0)
    if wait > 0: time.sleep(wait)

def fetch_url(url):
    rec = {"url": url, "fetched_at": today(), "method": "httpx", "text": "", "error": ""}
    if not allowed(url):
        rec["error"] = "blocked by robots.txt"; return rec
    for attempt in range(config.FETCH_RETRIES):
        try:
            polite_wait(url)
            r = httpx.get(url, headers={"User-Agent": config.USER_AGENT}, follow_redirects=True, timeout=30)
            rec["status"], rec["final_url"] = r.status_code, str(r.url)
            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep(2 ** attempt * 2); continue
            ct = r.headers.get("content-type", "")
            if r.status_code >= 400: rec["error"] = f"http {r.status_code}"
            elif not re.search(r"html|text|json|xml", ct): rec["error"] = f"unsupported content-type {ct}"
            else: rec["text"] = html_to_text(r.text) if "html" in ct else r.text
            break
        except Exception as e:
            rec["error"] = str(e); time.sleep(2 ** attempt)
    if len(rec["text"]) < 600 and not rec["error"].startswith("blocked") and browser.available():
        try:                                                       # page probably needs JavaScript
            t = browser.render(url)
            if len(t) > len(rec["text"]): rec.update(text=t, method="playwright", error="")
        except Exception as e:
            rec["error"] = rec["error"] or f"browser: {e}"
    return rec

def fetch_app(app):
    d = config.DISCOVERED / f"{slug(app)}.json"
    if not d.exists(): return
    for u in json.loads(d.read_text(encoding="utf-8"))["urls"]:
        p = cache_path(app, u["url"])
        if p.exists() and p.stat().st_size > 0: continue     # an empty file is left over from a crashed run
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(fetch_url(u["url"]), ensure_ascii=False), encoding="utf-8")
    print("fetched", app)

def load_pages(app, live=False):
    """{url: full text} for every cached page with text (from data/raw, or data/raw_live for browser re-reads)."""
    base = (config.RAW_LIVE if live else config.RAW) / slug(app)
    out = {}
    for p in sorted(base.glob("*.json")) if base.exists() else []:
        try: d = json.loads(p.read_text(encoding="utf-8"))
        except ValueError: continue                            # corrupt or empty cache file: treat as not fetched
        if d.get("text"): out[d["url"]] = d["text"]
    return out

def main(only=None):
    apps = [r["app"] for r in read_csv(config.APPS_CSV)]
    if only: apps = [a for a in apps if a.lower() in {o.lower() for o in only}]
    with cf.ThreadPoolExecutor(config.WORKERS) as ex: list(ex.map(fetch_app, apps))

if __name__ == "__main__":
    main(only=sys.argv[1:] or None)
