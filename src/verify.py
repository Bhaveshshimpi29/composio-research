"""Step 4: the verification loops.
 pass2  = pass1 + quote check (code) + one retry for fields whose quote is not on the page
 pass3a = pass2 + rule checks + second-opinion agent (other model) + browser check on disagreements
 pass3b = pass3a + human corrections from data/corrections.csv"""
import json, sys, concurrent.futures as cf
from . import config, store, browser
from .extract import extract_app, pages_block, SYSTEM
from .fetch import load_pages
from .llm import Meter, tool_call
from .quotecheck import check_record
from .rules import rule_flags
from .schema import RISKY, SecondOpinion, UNKNOWN_VALUE
from .util import read_csv, slug, write_jsonl, today

# ---------- pass 2: quote check + retry ----------
def merge_retry(first, failed1, retry, failed2):
    merged = dict(first)
    for f in failed1:
        if f not in failed2:
            merged[f] = retry[f]
            merged["evidence"] = merged.get("evidence", []) + [e for e in retry.get("evidence", []) if e.get("field") == f]
    return merged, [f for f in failed1 if f in failed2]

def pass2_app(rec, meter):
    pages = load_pages(rec["app"])
    checked, failed = check_record(rec, pages)
    retried = False
    if failed and pages:
        retried = True
        fb = ("Your previous quotes for these fields were NOT found word for word on the cited pages: " + ", ".join(failed) +
              ". Copy the exact sentence from the page text, or answer unknown for that field.")
        try:
            r2 = extract_app(rec["app"], rec.get("hint", ""), pages, meter, fb)
            r2c, f2 = check_record(r2, pages)
            checked, failed = merge_retry(checked, failed, r2c, f2)
        except Exception as e:
            print("retry failed", rec["app"], e, file=sys.stderr)
    return {**checked, "qc_failed": failed, "retried": retried}

def run_pass2():
    with Meter("verify_quotecheck_retry", "pass2", config.MODEL_EXTRACT) as m, cf.ThreadPoolExecutor(config.WORKERS) as ex:
        out = list(ex.map(lambda r: pass2_app(r, m), store.load("pass1")))
    store.save_stage("pass2", out); print("pass2 done", len(out))

# ---------- pass 3: second opinion, rules, browser ----------
SECOND_SYSTEM = """You are an independent fact-checker. You have NOT seen anyone else's answer. From ONLY the pages given,
answer three fields about the app: auth_methods, access, main_blocker. For each give {field, url, quote} evidence with an exact
sentence copied from a given page. If the pages do not settle it, answer "unknown".
access: self_serve_free (free credentials, no approval) | free_trial | paid_plan (needs paid plan) | admin_approval (org admin or vendor review)
| partner_or_sales (partnership / contact sales / manual onboarding) | unknown.
main_blocker: the single biggest obstacle to building an agent toolkit: none | no_public_api | paid_plan | partner_gate | admin_approval |
auth_complexity | docs_missing | other | unknown."""

def _same(field, a, b):
    return sorted(a) == sorted(b) if field == "auth_methods" else a == b

def resolve(field, a, b, c, suspicious=False):
    """a = first extraction, b = second opinion, c = browser re-read (None if not run). -> (value, resolved, how)"""
    unk = UNKNOWN_VALUE.get(field, "unknown")
    c_ok = c is not None and not _same(field, c, unk)
    if _same(field, a, b):
        if not suspicious or c is None: return a, True, "two agents agree"
        if _same(field, c, a): return a, True, "two agents + browser agree"
        return a, False, "rule flagged it and the live page differs"
    if c_ok and (_same(field, c, a) or _same(field, c, b)): return c, True, "browser broke the tie (2 of 3)"
    return a, False, "agents disagree" + ("" if c is not None else " and no browser check") + ("; browser agrees with neither" if c_ok else "")

def second_opinion(rec, pages, meter, model):
    try:
        out = tool_call(model, SECOND_SYSTEM, f"App: {rec['app']}\n\n{pages_block(pages)}\n\nCall submit.", SecondOpinion, meter)
    except Exception:
        return None
    d, _ = check_record(out.model_dump(), pages)      # reuse the quote check on its evidence
    return {f: d[f] for f in RISKY}

def cache_file(app): return config.DATA / "verify_cache" / f"{slug(app)}.json"

def pass3a_app(rec, meter):
    app = rec["app"]; pages = load_pages(app); flags = rule_flags(rec, pages)
    cf_ = cache_file(app); cached = json.loads(cf_.read_text(encoding="utf-8")) if cf_.exists() else {}
    if cached.get("second") is None:
        cached["second"] = second_opinion(rec, pages, meter, config.MODEL_SECOND) if pages else None
    second = cached["second"]; why, nh = [], bool(rec.get("needs_human"))
    out = dict(rec); out["rule_flags"] = flags; out["second_opinion"] = second
    if any(f.startswith("inconsistent") for f in flags):
        nh = True; why.append("rule check: " + ", ".join(f for f in flags if f.startswith("inconsistent")))
    if second is None:
        nh = True; why.append("second opinion unavailable")
    else:
        disputed = [f for f in RISKY if not _same(f, rec[f], second[f])]
        suspicious = "suspicious_access" in flags
        browser_vals = cached.get("browser")
        if (disputed or suspicious) and browser_vals is None and browser.available():
            browser_vals = browser_check(rec, disputed or ["access"], meter)
            cached["browser"] = browser_vals
        out["browser_check"] = browser_vals; out["disputed"] = disputed
        for f in (disputed or (["access"] if suspicious else [])):
            c = (browser_vals or {}).get(f)
            val, ok, how = resolve(f, rec[f], second[f], c, suspicious=(suspicious and f == "access"))
            out[f] = val
            if not ok: nh = True; why.append(f"{f}: {how}")
        for f in RISKY:                                   # undisputed fields where both agents are 'unknown'
            if f not in disputed and rec[f] == UNKNOWN_VALUE.get(f, "unknown"): nh = True; why.append(f"{f} unknown")
    if rec.get("confidence") == "low": nh = True; why.append("low confidence")
    out["needs_human"], out["why"] = nh, "; ".join(dict.fromkeys(why))
    cf_.parent.mkdir(parents=True, exist_ok=True); cf_.write_text(json.dumps(cached), encoding="utf-8")
    return out

def browser_check(rec, fields, meter):
    """Re-read the cited live pages with a real browser, ask a fresh question on the disputed fields."""
    urls = list(dict.fromkeys(e["url"] for e in rec.get("evidence", []) if e.get("field") in fields))
    urls = urls or list(load_pages(rec["app"]))[:3]
    live = {}
    for u in urls[:3]:
        try: live[u] = browser.render(u)
        except Exception: pass
    if not live: return None
    base = config.RAW_LIVE / slug(rec["app"]); base.mkdir(parents=True, exist_ok=True)
    (base / "live.json").write_text(json.dumps(live), encoding="utf-8")
    res = second_opinion(rec, live, meter, config.MODEL_SECOND)
    return {f: res[f] for f in fields} if res else None

def run_pass3a():
    with Meter("verify_second_opinion_rules_browser", "pass3a", config.MODEL_SECOND) as m, cf.ThreadPoolExecutor(config.WORKERS) as ex:
        out = list(ex.map(lambda r: pass3a_app(r, m), store.load("pass2")))
    store.save_stage("pass3a", out); print("pass3a done", len(out))

# ---------- pass 3b: human review ----------
def apply_corrections(recs, corrections):
    by_app = {}
    for c in corrections: by_app.setdefault(c["app"].lower(), []).append(c)
    out = []
    for r in recs:
        r = dict(r); cs = by_app.get(r["app"].lower(), [])
        for c in cs:
            r[c["field"]] = [x for x in c["value"].split("|") if x] if c["field"] in ("auth_methods", "api_type") else c["value"]
        if cs: r.update(needs_human=False, human_reviewed=True, corrections=cs)
        else: r.update(human_reviewed=False, corrections=[])
        out.append(r)
    return out

def write_review_queue(recs):
    import csv
    with open(config.REVIEW_QUEUE_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["app", "why", "agent_access", "agent_auth", "agent_blocker", "urls_to_check"])
        for r in recs:
            if r.get("needs_human"):
                w.writerow([r["app"], r["why"], r["access"], "|".join(r["auth_methods"]), r["main_blocker"],
                            " ".join(e["url"] for e in r.get("evidence", [])[:3])])

def run_pass3b():
    out = apply_corrections(store.load("pass3a"), read_csv(config.CORRECTIONS_CSV))
    store.save_stage("pass3b", out); write_review_queue(out)
    print("pass3b done;", sum(1 for r in out if r["needs_human"]), "still need a human (see data/review_queue.csv)")

if __name__ == "__main__":
    steps = sys.argv[1:] or ["pass2", "pass3a", "pass3b"]
    for s in steps: {"pass2": run_pass2, "pass3a": run_pass3a, "pass3b": run_pass3b}[s]()
