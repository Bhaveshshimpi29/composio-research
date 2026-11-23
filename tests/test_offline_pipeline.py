"""End-to-end check of the plumbing with a fake LLM and fake pages (no network, no API key)."""
import csv, json
import pytest
from src import config, store, extract, verify, score, build_page, aggregate_cli
from src.schema import Extraction, SecondOpinion
from src.util import slug

PAGES = {
    "Alpha": "Authentication\nGet a free API key in your dashboard, no approval needed.\nWe support OAuth 2.0 for apps.",
    "Beta": "Pricing\nAPI access is included in the Pro plan and above. Create tokens under settings.",
    "Gamma": "Developers\nYou can request a trial key instantly. Our API is REST based and broad.",
    "Delta": "Partners\nAccess to the API is limited. Please contact sales or join the partner program.",
}
URL = lambda a: f"https://{a.lower()}.example/docs"

def ev(app, field, quote): return {"field": field, "url": URL(app), "quote": quote}

def ext(app, access, quote, auth=("api_key",), bad_quote=False):
    q = "THIS SENTENCE IS INVENTED BY THE MODEL" if bad_quote else quote
    evs = [ev(app, f, q) for f in ["auth_methods", "access", "api_type", "api_breadth", "buildable_today", "main_blocker"]]
    return Extraction(category="Test", one_liner="x", auth_methods=list(auth), access=access, api_type=["rest"], api_breadth="large",
                      existing_mcp="none_found", buildable_today="yes" if access in ("self_serve_free", "free_trial") else "partial",
                      main_blocker="none" if access in ("self_serve_free", "free_trial") else "paid_plan", evidence=evs, confidence="high")

CALLS = {"Beta_extract": 0}
def fake_tool_call(model, system, user, schema_cls, meter, max_tokens=4000):
    app = next(a for a in PAGES if f"App: {a}" in user)
    if schema_cls is Extraction:
        if app == "Alpha": return ext(app, "self_serve_free", "Get a free API key in your dashboard, no approval needed.")
        if app == "Beta":
            CALLS["Beta_extract"] += 1
            return ext(app, "paid_plan", "API access is included in the Pro plan and above.", bad_quote=CALLS["Beta_extract"] == 1)
        if app == "Gamma": return ext(app, "free_trial", "You can request a trial key instantly.")
        if app == "Delta": return ext(app, "self_serve_free", "Please contact sales or join the partner program.")   # contradiction on purpose
    sec = lambda access, q, blocker="none": SecondOpinion(auth_methods=["api_key"], access=access, main_blocker=blocker,
            evidence=[ev(app, f, q) for f in ["auth_methods", "access", "main_blocker"]])
    live = "LIVE" in user
    if app == "Alpha": return sec("self_serve_free", "Get a free API key in your dashboard, no approval needed.")
    if app == "Beta": return sec("paid_plan", "API access is included in the Pro plan and above.", "paid_plan")
    if app == "Gamma":   # second agent disagrees (says paid), the browser re-read sides with the first agent
        return sec("free_trial", "You can request a trial key instantly.") if live else sec("paid_plan", "You can request a trial key instantly.", "paid_plan")
    if app == "Delta":   # second agent says partner; the live browser read says a THIRD thing -> nobody agrees -> human
        return (sec("admin_approval", "Please contact sales or join the partner program.", "admin_approval") if live
                else sec("partner_or_sales", "Please contact sales or join the partner program.", "partner_gate"))

@pytest.fixture
def env(tmp_path, monkeypatch):
    d = tmp_path / "data"; d.mkdir()
    for k, v in dict(DATA=d, RAW=d / "raw", RAW_LIVE=d / "raw_live", DISCOVERED=d / "disc", RESULTS=d / "results.jsonl", RUNS=d / "runs.jsonl",
                     HINTS_CSV=d / "hints.csv", APPS_CSV=d / "apps.csv", GOLD_CSV=d / "gold.csv", CORRECTIONS_CSV=d / "corrections.csv",
                     MISS_NOTES_CSV=d / "miss_notes.csv", REVIEW_QUEUE_CSV=d / "review_queue.csv", SITE=tmp_path / "site").items():
        monkeypatch.setattr(config, k, v)
    with open(d / "hints.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["app", "list_category", "hint"]); [w.writerow([a, "Cat", "x.com"]) for a in PAGES]
    for a, text in PAGES.items():
        p = d / "raw" / slug(a); p.mkdir(parents=True)
        (p / "p.json").write_text(json.dumps({"url": URL(a), "text": text, "error": ""}))
    monkeypatch.setattr(extract, "tool_call", fake_tool_call); monkeypatch.setattr(verify, "tool_call", fake_tool_call)
    monkeypatch.setattr(verify.browser, "available", lambda: True)
    monkeypatch.setattr(verify.browser, "render", lambda url: PAGES[next(a for a in PAGES if a.lower() in url)] + " LIVE")
    CALLS["Beta_extract"] = 0
    return d

def by_app(stage): return {r["app"]: r for r in store.load(stage)}

def test_full_pipeline(env):
    extract.main()
    p1 = by_app("pass1")
    assert len(p1) == 4 and p1["Beta"]["access"] == "paid_plan"       # pass 1 trusts the model, even its invented quote

    verify.run_pass2()
    p2 = by_app("pass2")
    assert p2["Beta"]["retried"] and p2["Beta"]["access"] == "paid_plan" and p2["Beta"]["qc_failed"] == []   # retry fixed the quote
    assert p2["Alpha"]["retried"] is False

    verify.run_pass3a()
    p3 = by_app("pass3a")
    assert p3["Alpha"]["needs_human"] is False
    assert p3["Gamma"]["access"] == "free_trial" and not p3["Gamma"]["needs_human"]           # browser broke the tie
    assert p3["Delta"]["needs_human"] and "agents disagree" in p3["Delta"]["why"]
    assert "suspicious_access" in p3["Delta"]["rule_flags"]                                    # the rule check fired too

    with open(config.CORRECTIONS_CSV, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["app", "field", "value", "reason", "reviewer", "url", "date"])
        w.writerow(["Delta", "access", "partner_or_sales", "docs say contact sales", "me", URL("Delta"), "2026-11-23"])
        w.writerow(["Delta", "main_blocker", "partner_gate", "same", "me", URL("Delta"), "2026-11-23"])
        w.writerow(["Delta", "buildable_today", "no", "same", "me", URL("Delta"), "2026-11-23"])
    verify.run_pass3b()
    fin = by_app("pass3b")
    assert fin["Delta"]["human_reviewed"] and fin["Delta"]["access"] == "partner_or_sales" and not fin["Delta"]["needs_human"]

    with open(config.GOLD_CSV, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["app", "auth_methods", "access", "existing_mcp", "buildable_today", "main_blocker", "urls_used", "notes"])
        w.writerow(["Delta", "api_key", "partner_or_sales", "none_found", "no", "partner_gate", "u", ""])
        w.writerow(["Alpha", "api_key", "self_serve_free", "none_found", "yes", "none", "u", ""])
    score.main()
    sc = json.loads((config.DATA / "scores.json").read_text())
    assert sc["pass1"]["overall"] < sc["pass3b"]["overall"] == 1.0            # accuracy rises, and the miss list explains why

    aggregate_cli.main(); build_page.build()
    page = (config.SITE / "index.html").read_text()
    assert "Headline patterns" in page and "Delta" in page and "still wrong" not in page and "Every miss" in page
    res = json.loads((config.SITE / "results.json").read_text())
    assert res["aggregate"]["n"] == 4 and len(res["records"]) == 4

def test_page_builds_with_no_results_at_all(env):
    build_page.build()
    assert "has not produced results yet" in (config.SITE / "index.html").read_text()
