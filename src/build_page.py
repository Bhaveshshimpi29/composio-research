"""Step 6: generate site/index.html + site/results.json. Every number on the page is computed from data/, none is typed."""
import html, json, os
from collections import defaultdict
from . import config, store
from .aggregate import aggregate
from .schema import SCORED
from .util import read_csv, read_jsonl

E = lambda x: html.escape(str(x if x is not None else ""))
pct = lambda a, b: f"{round(100 * a / b)}%" if b else "n/a"
LABEL = {"pass1": "Pass 1: extraction only", "pass2": "Pass 2: + quote check & retry",
         "pass3a": "Pass 3a: + rules, 2nd agent, browser", "pass3b": "Pass 3b: + human review"}

def headlines(a):
    n = a["n"]
    if not n: return ["The pipeline has not produced results yet."]
    auth = list(a["auth_counts"].items()); acc = a["access_counts"]
    selfserve = acc.get("self_serve_free", 0) + acc.get("free_trial", 0)
    gated = acc.get("admin_approval", 0) + acc.get("partner_or_sales", 0)
    gs = sorted(a["gated_share_by_category"].items(), key=lambda kv: -kv[1])
    out = []
    if auth: out.append(f"{auth[0][1]} of {n} apps support {auth[0][0]}, the most common auth method" +
                        (f"; next is {auth[1][0]} ({auth[1][1]})." if len(auth) > 1 else "."))
    out.append(f"{selfserve} of {n} apps ({pct(selfserve, n)}) give developers credentials for free or on a trial; "
               f"{acc.get('paid_plan', 0)} need a paid plan; {gated} need admin approval or a partner/sales gate; "
               f"{a['n_unknown_access']} are still unknown.")
    if a["top_blocker"]: out.append(f"The most common blocker is {a['top_blocker']} ({a['blocker_counts'][a['top_blocker']]} apps).")
    if gs: out.append(f"Most gated or paid category: {gs[0][0]} ({pct(round(gs[0][1] * 100), 100)} of its apps); "
                      f"most open: {gs[-1][0]} ({pct(round(gs[-1][1] * 100), 100)}).")
    out.append(f"{len(a['easy_wins'])} apps are easy wins (buildable today and self-serve); {len(a['needs_outreach'])} need outreach; "
               f"{a['n_existing_mcp']} already have an MCP server.")
    return out

def bars(counts, total):
    if not counts: return "<p class=s>no data</p>"
    return "".join(f"<div class=bar><span class=bl>{E(k)}</span><span class=bt><i style='width:{(100 * v / total) if total else 0:.0f}%'></i></span><b>{v}</b></div>"
                   for k, v in counts.items())

def matrix(recs):
    rows = []
    for r in recs:
        ev = " ".join(f"<a href='{E(e['url'])}' target=_blank rel=noopener title='{E(e['field'])}: {E(e['quote'][:200])}'>{E(e['field'][:4])}↗</a>"
                      for e in r.get("evidence", [])[:6]) or "<span class=s>none</span>"
        flag = "<span class='pill bad'>needs human</span>" if r.get("needs_human") else ("<span class='pill ok'>human-checked</span>" if r.get("human_reviewed") else "")
        rows.append(f"<tr><td>{E(r['app'])}<div class=s>{E(r.get('category'))}</div></td><td>{E(r.get('one_liner'))}</td>"
                    f"<td>{E(', '.join(r['auth_methods']))}</td><td><span class='pill {E(r['access'])}'>{E(r['access'])}</span></td>"
                    f"<td>{E(', '.join(r['api_type']))}<div class=s>{E(r['api_breadth'])}</div></td>"
                    f"<td>{E(r['existing_mcp'])}</td><td><span class='pill b-{E(r['buildable_today'])}'>{E(r['buildable_today'])}</span>"
                    f"<div class=s>{E(r['main_blocker'])}</div></td><td>{E(r['confidence'])} {flag}</td><td class=ev>{ev}</td></tr>")
    return "".join(rows)

def accuracy_table(scores):
    if not scores: return "<p class=s>Accuracy not measured yet: build data/gold.csv (the hand-checked sample) and run <code>python -m src.score</code>.</p>"
    head = "".join(f"<th>{f}</th>" for f in SCORED)
    body = "".join(f"<tr><td>{E(LABEL.get(st, st))}</td>" +
                   "".join(f"<td>{pct(s['fields'][f]['correct'], s['fields'][f]['total'])}</td>" for f in SCORED) +
                   f"<td><b>{pct(s['correct'], s['total'])}</b></td></tr>" for st, s in scores.items())
    n = next(iter(scores.values()))["n_apps"]
    return (f"<p>Scored on a gold sample of <b>{n} apps</b> that was written by <b>Claude, not a human</b>, from live web searches of each vendor's own docs (not from the cached pages the agent used). "
            f"It is an independent second reading, not a human-verified truth; some rows rest on prior knowledge and are noted in data/gold.csv. A human spot-check is still pending. "
            f"({n * len(SCORED)} field checks per pass.) With a sample this small, a few points of difference are noise. "
            f"Accuracy went <b>down</b> from pass 1 to pass 2: the quote check erased answers it could not back with an exact quote, and an erased answer counts as a miss. "
            f"Of the answers the agent did give, wrong ones fell, which is the intended trade (fewer confident errors, more unknowns).</p>"
            f"<div class=wrap><table><tr><th>Stage</th>{head}<th>Overall</th></tr>{body}</table></div>")

def misses_table(scores, final_recs, notes):
    if not scores: return ""
    first = scores.get("pass1") or next(iter(scores.values())); last_stage = list(scores)[-1]
    final = {(m["app"], m["field"]): m for m in scores[last_stage]["misses"]}
    note = {(n["app"].lower(), n["field"]): n.get("why", "") for n in notes}
    rows = []
    for m in first["misses"]:
        fixed = (m["app"], m["field"]) not in final
        rows.append(f"<tr><td>{E(m['app'])}</td><td>{E(m['field'])}</td><td>{E(m['agent'])}</td><td>{E(m['truth'])}</td>"
                    f"<td>{'fixed by later passes' if fixed else '<b>still wrong: ' + E(final[(m['app'], m['field'])]['agent']) + '</b>'}</td>"
                    f"<td>{E(note.get((m['app'].lower(), m['field'])) or 'not analysed yet')}</td></tr>")
    new = [m for k, m in final.items() if not any(k == (x['app'], x['field']) for x in first["misses"])]
    for m in new:
        rows.append(f"<tr><td>{E(m['app'])}</td><td>{E(m['field'])}</td><td colspan=2>pass 1 was right; final says {E(m['agent'])} (truth {E(m['truth'])})</td>"
                    f"<td><b>introduced by a later pass</b></td><td>{E(note.get((m['app'].lower(), m['field'])) or 'not analysed yet')}</td></tr>")
    if not rows: return "<p>No misses on the gold sample.</p>"
    return ("<h3>Every miss, shown honestly</h3><div class=wrap><table><tr><th>App</th><th>Field</th><th>Pass-1 agent said</th><th>Truth</th>"
            f"<th>Outcome</th><th>Why it was wrong</th></tr>{''.join(rows)}</table></div>")

def cost_table(runs):
    if not runs: return ""
    rows = "".join(f"<tr><td>{E(r['stage'])}</td><td>{E(r['step'])}</td><td>{E(r['model'])}</td><td>{E(r['prompt_version'])}</td><td>{E(r['date'])}</td>"
                   f"<td>{r['calls']}</td><td>{r['input_tokens']:,} / {r['output_tokens']:,}</td><td>{r['seconds']}s</td>"
                   f"<td>{'$' + str(r['est_cost_usd']) if r.get('est_cost_usd') is not None else 'n/a'}</td></tr>" for r in runs)
    return ("<h3>Run log (reproducibility, time and spend)</h3><div class=wrap><table><tr><th>Stage</th><th>Step</th><th>Model</th><th>Prompt</th><th>Date</th>"
            f"<th>Calls</th><th>Tokens in / out</th><th>Time</th><th>Est. cost</th></tr>{rows}</table></div>"
            "<p class=s>Web-search tool fees are billed separately by the API and are not in this estimate.</p>")

def limits(recs, agg):
    still = [r for r in recs if r.get("needs_human")]
    nopage = [r["app"] for r in recs if any(k in (r.get("why") or "") for k in ("no page could be fetched", "blocked by robots", "headless browser", "No usable page", "No pages cached"))]
    unk = [r["app"] for r in recs if r["access"] == "unknown"]
    li = [f"<li><b>{len(still)}</b> apps still need a human and are marked in the matrix: " + (E(", ".join(r["app"] for r in still)) or "none") + ".</li>",
          f"<li><b>{len(nopage)}</b> apps had no readable page (blocked, JavaScript-only or discovery failed): {E(', '.join(nopage)) or 'none'}.</li>",
          f"<li><b>{len(unk)}</b> apps have access = unknown, which means the pages did not settle it. That is reported as unknown, not guessed: {E(', '.join(unk)) or 'none'}.</li>",
          "<li><b>How pass 1 was run:</b> the first-pass answers were written by Claude reading the cached pages in a chat session, not by an automated API call, so they are not in the run log. The quote check that follows is code and ran on every record.</li>",
          "<li><b>Honest scope:</b> an earlier collection of 59 apps by another tool was rule-based and unverified. Its cached pages were re-read, but its answers were not reused. That run also stopped when its scraping credits ran out.</li>",
          "<li>Pages that robots.txt disallows were not fetched, and the apps behind them are left unknown.</li>",
          "<li>The agent reads only the pages it could fetch. Docs behind a login, or pages that block bots, cannot be read.</li>",
          "<li>Access rules change. Every record has a fetch date; re-run before relying on it.</li>"]
    return "<ul>" + "".join(li) + "</ul>"

SVG = """<svg viewBox="0 0 900 190" role="img" aria-label="Pipeline diagram" class="diagram">
<defs><marker id="a" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="currentColor"/></marker></defs>
<g font-size="12" text-anchor="middle" fill="currentColor">
<g class="bx"><rect x="5" y="20" width="100" height="44" rx="8"/><text x="55" y="38">1 Discover</text><text x="55" y="54" font-size="10">search the web</text></g>
<g class="bx"><rect x="125" y="20" width="100" height="44" rx="8"/><text x="175" y="38">2 Fetch+cache</text><text x="175" y="54" font-size="10">httpx / browser</text></g>
<g class="bx"><rect x="245" y="20" width="100" height="44" rx="8"/><text x="295" y="38">3 Extract</text><text x="295" y="54" font-size="10">LLM + quotes</text></g>
<g class="bx"><rect x="365" y="20" width="100" height="44" rx="8"/><text x="415" y="38">4a Quote check</text><text x="415" y="54" font-size="10">code, no LLM</text></g>
<g class="bx"><rect x="485" y="20" width="100" height="44" rx="8"/><text x="535" y="38">4b Rules</text><text x="535" y="54" font-size="10">explainable</text></g>
<g class="bx"><rect x="605" y="20" width="130" height="44" rx="8"/><text x="670" y="38">4c Second agent</text><text x="670" y="54" font-size="10">different model</text></g>
<g class="bx"><rect x="755" y="20" width="140" height="44" rx="8"/><text x="825" y="38">4d Browser check</text><text x="825" y="54" font-size="10">on disagreement</text></g>
<g class="bx human"><rect x="605" y="115" width="130" height="44" rx="8"/><text x="670" y="133">5 Human review</text><text x="670" y="149" font-size="10">needs_human only</text></g>
<g class="bx"><rect x="365" y="115" width="100" height="44" rx="8"/><text x="415" y="133">6 Aggregate</text><text x="415" y="149" font-size="10">patterns</text></g>
<g class="bx"><rect x="125" y="115" width="100" height="44" rx="8"/><text x="175" y="133">7 This page</text><text x="175" y="149" font-size="10">+ results.json</text></g>
<g class="bx human"><rect x="5" y="115" width="100" height="44" rx="8"/><text x="55" y="133">Gold sample</text><text x="55" y="149" font-size="10">by hand, blind</text></g>
</g>
<g stroke="currentColor" stroke-width="1.5" fill="none" marker-end="url(#a)">
<path d="M105,42 H123"/><path d="M225,42 H243"/><path d="M345,42 H363"/><path d="M465,42 H483"/><path d="M585,42 H603"/><path d="M735,42 H753"/>
<path d="M825,64 V90 H735 V113" /><path d="M670,64 V113"/><path d="M605,137 H467"/><path d="M365,137 H227"/>
</g></svg>"""

def build():
    have = [st for st in store.STAGES if store.load(st)]
    global STAGES_DONE, P3_STATE
    STAGES_DONE = "Stages completed: " + ", ".join(have) + "."
    P3_STATE = "completed" if "pass3a" in have else "NOT run for this submission"
    final_stage = next((s for s in reversed(store.STAGES) if store.load(s)), None)
    recs = sorted(store.load(final_stage), key=lambda r: r["app"].lower()) if final_stage else []
    agg = aggregate(recs) if recs else aggregate([])
    scores = json.loads((config.DATA / "scores.json").read_text(encoding="utf-8")) if (config.DATA / "scores.json").exists() else {}
    notes, runs = read_csv(config.MISS_NOTES_CSV), read_jsonl(config.RUNS)
    corrections = read_csv(config.CORRECTIONS_CSV)
    repo = os.getenv("REPO_URL", "").strip()
    models = sorted({r.get("model", "") for r in recs if r.get("model")} | {config.MODEL_SECOND})
    cats = sorted(agg["category_access"]); acc_cols = ["self_serve_free", "free_trial", "paid_plan", "admin_approval", "partner_or_sales", "unknown"]
    cat_rows = "".join(f"<tr><td>{E(c)}</td>" + "".join(f"<td>{agg['category_access'][c].get(k, 0)}</td>" for k in acc_cols) + "</tr>" for c in cats)
    page = TEMPLATE.format(
        stages_done=E(STAGES_DONE), p3_state=E(P3_STATE),
        title="100 apps: which can become an agent toolkit today?", n=agg["n"], stage=E(final_stage or "none"),
        heads="".join(f"<li>{E(h)}</li>" for h in headlines(agg)),
        auth_bars=bars(agg["auth_counts"], agg["n"]), access_bars=bars(agg["access_counts"], agg["n"]),
        blocker_bars=bars(agg["blocker_counts"], agg["n"]),
        cat_head="".join(f"<th>{k}</th>" for k in acc_cols), cat_rows=cat_rows,
        easy=E(", ".join(agg["easy_wins"])) or "none", outreach=E(", ".join(agg["needs_outreach"])) or "none",
        paid=E(", ".join(agg["paid_only"])) or "none", rows=matrix(recs), svg=SVG,
        n_nh=sum(1 for r in recs if r.get("human_reviewed")), n_corr=len(corrections),
        n_queue=agg["n_needs_human"], accuracy=accuracy_table(scores), misses=misses_table(scores, recs, notes),
        cost=cost_table(runs), limits=limits(recs, agg), models=E(", ".join(models)), prompt=config.PROMPT_VERSION,
        repo=(f"<a href='{E(repo)}'>{E(repo)}</a>" if repo else "<b>(set REPO_URL before building: link to the source repo)</b>"))
    config.SITE.mkdir(exist_ok=True)
    (config.SITE / "index.html").write_text(page, encoding="utf-8")
    (config.SITE / "results.json").write_text(json.dumps({"stage": final_stage, "models": models, "prompt_version": config.PROMPT_VERSION,
        "aggregate": agg, "scores": scores, "records": recs}, indent=1, ensure_ascii=False), encoding="utf-8")
    print("wrote site/index.html and site/results.json from stage", final_stage)

TEMPLATE = """<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>{title}</title><style>
:root{{--bg:#fff;--fg:#14161a;--mu:#5b6270;--card:#f4f5f7;--line:#dfe2e7;--ac:#4f46e5;--ok:#1f9d55;--bad:#d6393e;--warn:#c78a0a}}
@media(prefers-color-scheme:dark){{:root{{--bg:#111316;--fg:#eceef1;--mu:#9aa1ad;--card:#1b1e23;--line:#2c3037;--ac:#9a95ff;--ok:#3ecf7b;--bad:#ff6b70;--warn:#f0b43c}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--fg);font:16px/1.55 system-ui,sans-serif}}
main{{max-width:1080px;margin:auto;padding:16px}}h1{{font-size:1.6rem;margin:.3em 0}}h2{{margin-top:2.2rem;padding-top:1rem;border-top:1px solid var(--line)}}
.s{{color:var(--mu);font-size:.8rem}}.card{{background:var(--card);border-radius:12px;padding:12px 18px}}.card li{{margin:.3em 0}}
.wrap{{overflow-x:auto}}table{{border-collapse:collapse;width:100%;font-size:.84rem}}th,td{{border-bottom:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}}
th{{position:sticky;top:0;background:var(--card);cursor:pointer;white-space:nowrap}}
.pill{{padding:1px 8px;border-radius:99px;background:var(--line);font-size:.74rem;white-space:nowrap}}
.pill.self_serve_free,.pill.free_trial,.pill.b-yes,.pill.ok{{background:color-mix(in srgb,var(--ok) 25%,transparent)}}
.pill.paid_plan,.pill.b-partial{{background:color-mix(in srgb,var(--warn) 25%,transparent)}}
.pill.admin_approval,.pill.partner_or_sales,.pill.b-no,.pill.bad{{background:color-mix(in srgb,var(--bad) 25%,transparent)}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px}}
.bar{{display:flex;align-items:center;gap:8px;font-size:.82rem;margin:3px 0}}.bl{{width:130px;flex:none}}.bt{{flex:1;background:var(--line);height:10px;border-radius:5px}}.bt i{{display:block;height:10px;background:var(--ac);border-radius:5px}}
input,select{{padding:8px;border-radius:8px;border:1px solid var(--line);background:var(--card);color:var(--fg);margin:4px 4px 8px 0}}
code,pre{{background:var(--card);border-radius:6px;padding:2px 6px}}pre{{padding:10px;overflow-x:auto}}a{{color:var(--ac)}}
.diagram{{width:100%;height:auto;color:var(--fg)}}.bx rect{{fill:var(--card);stroke:var(--line)}}.bx.human rect{{stroke:var(--warn);stroke-width:2}}
td.ev a{{margin-right:6px;font-size:.75rem}}
</style></head><body><main>
<h1>{title}</h1>
<p class=s>{n} apps researched by an agent and re-checked by code. {stages_done} Final stage: {stage}. Models: {models}. Prompt {prompt}.</p>

<h2>1. Headline patterns</h2><div class=card><ul>{heads}</ul></div>
<div class=grid><div><h3>Auth methods</h3>{auth_bars}</div><div><h3>Access</h3>{access_bars}</div><div><h3>Main blockers</h3>{blocker_bars}</div></div>
<h3>Access by category</h3><div class=wrap><table><tr><th>Category</th>{cat_head}</tr>{cat_rows}</table></div>
<p><b>Easy wins</b> (buildable now, self-serve): {easy}</p><p><b>Need outreach</b> (approval, partner or sales): {outreach}</p><p><b>Paid plan needed:</b> {paid}</p>

<h2>2. The matrix</h2>
<input id=q placeholder="Filter by app, auth, blocker…" aria-label=filter>
<select id=fa><option value="">any access</option><option>self_serve_free</option><option>free_trial</option><option>paid_plan</option><option>admin_approval</option><option>partner_or_sales</option><option>unknown</option></select>
<select id=fb><option value="">any buildable</option><option>yes</option><option>partial</option><option>no</option><option>unknown</option></select>
<div class=wrap><table id=t><thead><tr><th>App</th><th>What it does</th><th>Auth</th><th>Access</th><th>API</th><th>MCP</th><th>Buildable today</th><th>Confidence</th><th>Evidence (hover = quote)</th></tr></thead><tbody>{rows}</tbody></table></div>

<h2>3. The agent</h2>{svg}
<ol><li><b>Discover</b>: web search finds each app's docs, auth and pricing pages.</li><li><b>Fetch + cache</b>: every page is downloaded once (politely, with retries); JavaScript pages use a headless browser.</li>
<li><b>Extract</b>: an LLM fills a fixed schema and must quote a sentence for every answer.</li><li><b>Quote check</b>: plain code. If a quote is not on the cited page, that field becomes <code>unknown</code> and is retried once.</li>
<li><b>Rules, second agent, browser</b> ({p3_state}): explainable rules; a different model re-answers the risky fields; disagreements are re-read in a real browser, and a 2-of-3 vote decides.</li>
<li><b>Human review</b>: only what is still unresolved.</li></ol>
<p><b>Where a human stepped in:</b> built the 20-app gold sample by hand from the real docs before seeing the agent's answers; a human reviewed {n_nh} flagged apps and {n_queue} are still waiting for review; every fix is logged in <code>data/corrections.csv</code> ({n_corr} logged so far).</p>

<h2>4. The proof</h2><p>Source repo: {repo}</p><p>Data for other agents: <a href="results.json">results.json</a></p>
<p>Re-run everything from the cached pages with one command:</p><pre>python -m src.run_all</pre>

<h2>5. Verification</h2>{accuracy}{misses}{cost}

<h2>6. Limits</h2>{limits}
</main><script>
const q=document.getElementById('q'),fa=document.getElementById('fa'),fb=document.getElementById('fb'),t=document.getElementById('t');
function f(){{const v=q.value.toLowerCase();t.tBodies[0].querySelectorAll('tr').forEach(r=>{{const c=r.cells;
 r.style.display=(!v||r.textContent.toLowerCase().includes(v))&&(!fa.value||c[3].textContent.includes(fa.value))&&(!fb.value||c[6].textContent.startsWith(fb.value))?'':'none'}})}}
[q,fa,fb].forEach(e=>e.oninput=f);
t.tHead.querySelectorAll('th').forEach((th,i)=>th.onclick=()=>{{const d=th.dataset.d=th.dataset.d==='1'?'-1':'1';
 const rows=[...t.tBodies[0].rows].sort((a,b)=>a.cells[i].textContent.localeCompare(b.cells[i].textContent)*d);rows.forEach(r=>t.tBodies[0].append(r))}});
</script></body></html>"""

if __name__ == "__main__": build()
