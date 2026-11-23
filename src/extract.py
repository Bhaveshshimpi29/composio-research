"""Step 3 (pass 1): an LLM reads the cached pages and fills the schema, quoting a sentence for every field."""
import sys, concurrent.futures as cf
from pydantic import ValidationError
from . import config, store
from .fetch import load_pages
from .llm import Meter, tool_call
from .schema import Extraction, UNKNOWN_VALUE, EVIDENCED
from .util import read_csv, today

SYSTEM = """You are a careful API-access researcher. You read cached web pages about one app and fill a fixed schema.

HARD RULES
- Use ONLY the pages given. Your own memory is NOT evidence.
- For every field in {evidenced} give one evidence item: {{field, url, quote}}. `url` must be one of the given page URLs and
  `quote` must be an exact sentence copied word for word from that page (no paraphrase, no ellipsis).
- If the pages do not support an answer, use "unknown" (or ["unknown"]). A confident guess is a failure.
- existing_mcp = "none_found" is allowed without a quote only if none of the pages mention an MCP server.

DEFINITIONS
access: self_serve_free = any developer can sign up and get working API credentials for free, no sales or approval.
  free_trial = credentials come only with a time-limited trial or a limited free tier needing signup.
  paid_plan = API access requires a paid plan or add-on. admin_approval = needs an org admin to enable it, or vendor review/approval
  of the app/developer. partner_or_sales = needs a partnership, "contact sales", or manual vendor onboarding.
auth_methods: what a developer uses to call the API (oauth2, api_key, basic, bearer_token, other).
api_breadth: small = few endpoints, medium = several resources, large = broad coverage of most product features.
buildable_today: yes = documented public API and a developer can get credentials alone; partial = buildable but limited
  (narrow API, paid plan, complex auth, part gated); no = no public API or access fully gated.
main_blocker: the single biggest obstacle to building a toolkit ("none" if buildable_today is yes)."""

def pages_block(pages):
    parts, used = [], 0
    for url, text in pages.items():
        chunk = text[:config.MAX_CHARS_PER_PAGE]
        if used + len(chunk) > config.MAX_CHARS_TOTAL: break
        used += len(chunk); parts.append(f"=== PAGE: {url}\n{chunk}")
    return "\n\n".join(parts)

def build_user(app, hint, pages, feedback=""):
    return (f"App: {app}\nWebsite hint: {hint}\n\n{pages_block(pages)}\n\n"
            f"{feedback}\nFill the schema now by calling submit.")

def empty_record(app, hint, why):
    rec = {"app": app, "category": "unknown", "one_liner": "unknown", "auth_methods": ["unknown"], "access": "unknown",
           "api_type": ["unknown"], "api_breadth": "unknown", "existing_mcp": "unknown", "existing_mcp_url": "",
           "buildable_today": "unknown", "main_blocker": "unknown", "evidence": [], "confidence": "low"}
    return finish(rec, app, hint, "none", needs_human=True, why=why)

def finish(rec, app, hint, model, needs_human=False, why=""):
    return {**rec, "app": app, "hint": hint, "model": model, "prompt_version": config.PROMPT_VERSION, "date": today(),
            "needs_human": needs_human, "why": why}

def extract_app(app, hint, pages, meter, feedback=""):
    """Returns an Extraction-shaped dict. Retries once if the model's output fails schema validation."""
    for attempt in range(2):
        try:
            out = tool_call(config.MODEL_EXTRACT, SYSTEM.format(evidenced=EVIDENCED), build_user(app, hint, pages, feedback),
                            Extraction, meter)
            return out.model_dump()
        except ValidationError as e:
            feedback += f"\nYour previous answer failed validation: {str(e)[:300]}"
    raise RuntimeError("schema validation failed twice")

def run_one(row, meter, force):
    app, hint = row["app"], row.get("hint", "")
    stage = "pass1"
    if not force and any(r["app"] == app for r in store.load(stage)): return
    pages = load_pages(app)
    if not pages:
        store.upsert(stage, empty_record(app, hint, "no page could be fetched (blocked, JS-only, or discovery failed)")); return
    try:
        store.upsert(stage, finish(extract_app(app, hint, pages, meter), app, hint, config.MODEL_EXTRACT))
    except Exception as e:
        store.upsert(stage, empty_record(app, hint, f"extraction error: {str(e)[:150]}"))
    print("extracted", app)

def main(force=False, only=None):
    rows = read_csv(config.HINTS_CSV)
    if only: rows = [r for r in rows if r["app"].lower() in {o.lower() for o in only}]
    with Meter("extract", "pass1", config.MODEL_EXTRACT) as m, cf.ThreadPoolExecutor(config.WORKERS) as ex:
        list(ex.map(lambda r: run_one(r, m, force), rows))

if __name__ == "__main__":
    main(force="--force" in sys.argv, only=[a for a in sys.argv[1:] if not a.startswith("--")] or None)
