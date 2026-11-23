"""Headless browser rendering for JavaScript-heavy docs (used by fetch.py and by the verify browser check)."""
import threading
from . import config
_lock = threading.Lock()   # one browser at a time: simple and safe

def available():
    try:
        import playwright  # noqa: F401
        return True
    except ImportError:
        return False

def render(url, timeout_ms=30000):
    from playwright.sync_api import sync_playwright
    with _lock, sync_playwright() as p:
        b = p.chromium.launch()
        try:
            page = b.new_page(user_agent=config.USER_AGENT)
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            try: page.wait_for_load_state("networkidle", timeout=10000)
            except Exception: pass
            return page.inner_text("body")
        finally:
            b.close()
