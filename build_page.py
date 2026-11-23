
"""Build an evidence-first interactive HTML case study from data/final.json."""

import json
import html
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data" / "final.json"
OUTPUT_PATH = ROOT / "site" / "index.html"


def esc(value):
    return html.escape(str(value if value is not None else ""))


def main():
    if not DATA_PATH.exists():
        raise SystemExit("data/final.json not found. Run the research pipeline first.")

    records = json.loads(DATA_PATH.read_text(encoding="utf-8"))

    if not isinstance(records, list):
        raise SystemExit("Expected data/final.json to contain a list of records.")

    total = len(records)
    categories = Counter(r.get("category", "Uncategorized") for r in records)
    buildability = Counter(r.get("buildability", "Unknown") for r in records)

    auth_known = sum(
        r.get("authentication") not in (
            None, "", "Not established from collected evidence"
        )
        for r in records
    )

    evidence_count = sum(bool(r.get("evidence_urls")) for r in records)

    human_review = sum(
        r.get("status") == "needs_human_review" for r in records
    )

    other_status = Counter(r.get("status", "Unknown") for r in records)

    rows = []

    for r in records:
        urls = r.get("evidence_urls") or []

        links = " ".join(
            f'<a href="{esc(u)}" target="_blank" rel="noopener noreferrer">'
            f'Source {i + 1}</a>'
            for i, u in enumerate(urls)
            if isinstance(u, str) and u.startswith(("https://", "http://"))
        ) or "No official source captured"

        blockers = "; ".join(r.get("blockers") or [])

        search_text = " ".join([
            str(r.get("app", "")),
            str(r.get("category", "")),
            str(r.get("description", ""))
        ]).lower()

        rows.append(f"""
        <tr data-category="{esc(r.get('category', ''))}"
            data-search="{esc(search_text)}">
          <td><strong>{esc(r.get('app'))}</strong>
              <small>{esc(r.get('category'))}</small></td>
          <td>{esc(r.get('authentication', 'Unknown'))}</td>
          <td>{esc(r.get('developer_access', 'Unknown'))}</td>
          <td>{esc(r.get('api_type', 'Unknown'))}</td>
          <td>{esc(r.get('api_breadth', 'Unknown'))}</td>
          <td>{esc(r.get('existing_mcp', 'Unknown'))}</td>
          <td><strong>{esc(r.get('buildability', 'Unknown'))}</strong>
              <small>{esc(blockers)}</small></td>
          <td>{links}</td>
        </tr>
        """)

    category_options = "\n".join(
        f'<option value="{esc(cat)}">{esc(cat)}</option>'
        for cat in sorted(categories)
    )

    table_rows = "\n".join(rows)

    category_list = "\n".join(
        f"<li><span>{esc(cat)}</span><b>{count}</b></li>"
        for cat, count in sorted(categories.items())
    )

    buildability_list = "\n".join(
        f"<li><span>{esc(k)}</span><b>{v}</b></li>"
        for k, v in sorted(buildability.items())
    )

    status_list = "\n".join(
        f"<li><span>{esc(k)}</span><b>{v}</b></li>"
        for k, v in sorted(other_status.items())
    )

    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">

<title>SaaS Agent Integration Readiness — Research Case Study</title>

<style>
:root {{
  --bg:#f5f7fb;
  --ink:#172033;
  --muted:#64748b;
  --line:#e2e8f0;
  --panel:#fff;
  --accent:#3157d5;
}}
* {{box-sizing:border-box}}
body {{
  margin:0;background:var(--bg);color:var(--ink);
  font:15px/1.55 Inter,Segoe UI,Arial,sans-serif
}}
header {{
  padding:48px max(22px,calc((100vw - 1200px)/2));
  background:#111b34;color:white
}}
header p {{color:#cbd5e1;max-width:780px}}
h1 {{font-size:clamp(30px,5vw,48px);line-height:1.08;margin:8px 0 14px}}
main {{max-width:1200px;margin:28px auto;padding:0 20px}}
.grid {{
  display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));
  gap:14px
}}
.card,section {{
  background:var(--panel);border:1px solid var(--line);
  border-radius:14px;padding:20px;margin-bottom:18px
}}
.metric {{font-size:30px;font-weight:750}}
.muted,small {{color:var(--muted)}}
small {{display:block;font-size:12px;margin-top:4px}}
h2 {{margin:0 0 14px;font-size:21px}}
.filters {{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px}}
input,select {{
  padding:11px 12px;border:1px solid var(--line);
  border-radius:9px;background:white;min-width:210px
}}
.table-wrap {{overflow:auto}}
table {{border-collapse:collapse;width:100%;min-width:1100px;font-size:13px}}
th,td {{padding:12px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}}
th {{background:#f8fafc;position:sticky;top:0}}
a {{color:var(--accent);margin-right:8px}}
ul.categories {{
  list-style:none;padding:0;margin:0;
  display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:8px
}}
.categories li {{
  display:flex;justify-content:space-between;
  padding:9px 11px;background:#f8fafc;border-radius:8px
}}
.note {{
  border-left:3px solid var(--accent);padding:12px 14px;
  background:#f7f9ff;color:#334155
}}
.warning {{
  border-left:3px solid #d97706;padding:12px 14px;
  background:#fff8eb;color:#713f12
}}
footer {{color:var(--muted);font-size:12px;padding:20px 0 40px}}
@media(max-width:600px) {{
  header {{padding:34px 20px}}
}}
</style>
</head>

<body>

<header>
  <div style="color:#a5b4fc;font-weight:700;letter-spacing:.12em">
    RESEARCH CASE STUDY
  </div>

  <h1>SaaS Agent Integration Readiness</h1>

  <p>
    A structured assessment of API access, authentication,
    developer onboarding, MCP availability and implementation
    readiness across 100 researched applications.
  </p>

  <p>
    <strong>Evidence-first assessment.</strong>
    Unknown fields remain explicitly unknown and should not be
    interpreted as proof that an API or MCP server does not exist.
  </p>
</header>

<main>

<div class="grid">
  <div class="card">
    <div class="muted">Apps researched</div>
    <div class="metric">{total}</div>
  </div>

  <div class="card">
    <div class="muted">Categories</div>
    <div class="metric">{len(categories)}</div>
  </div>

  <div class="card">
    <div class="muted">Authentication identified</div>
    <div class="metric">{auth_known}/{total}</div>
  </div>

  <div class="card">
    <div class="muted">Apps with source URLs</div>
    <div class="metric">{evidence_count}/{total}</div>
  </div>

  <div class="card">
    <div class="muted">Awaiting human review</div>
    <div class="metric">{human_review}</div>
  </div>
</div>

<section>
  <h2>Category coverage</h2>
  <ul class="categories">{category_list}</ul>
</section>

<section>
  <h2>Buildability snapshot</h2>
  <ul class="categories">{buildability_list}</ul>
</section>

<section>
  <h2>Research review status</h2>
  <ul class="categories">{status_list}</ul>
</section>

<section>
  <h2>Research findings</h2>

  <p class="note">
    The assessment uses collected public search results, official
    documentation and rule-based extraction. Unsupported conclusions
    are kept unconfirmed. Records marked for human review have not
    been presented as fully verified.
  </p>

  <div class="filters">
    <input id="q" placeholder="Search apps or descriptions...">
    <select id="cat">
      <option value="">All categories</option>
      {category_options}
    </select>
  </div>

  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>App</th>
          <th>Authentication</th>
          <th>Developer access</th>
          <th>API type</th>
          <th>API breadth</th>
          <th>Existing MCP</th>
          <th>Buildability / blockers</th>
          <th>Evidence</th>
        </tr>
      </thead>
      <tbody id="rows">{table_rows}</tbody>
    </table>
  </div>
</section>

<section>
  <h2>Methodology</h2>
  <ol>
    <li>Discover application-related search and documentation sources.</li>
    <li>Search for developer documentation, API references and MCP information.</li>
    <li>Prioritize official-domain URLs and collect available page content.</li>
    <li>Extract authentication, developer access, API type, API breadth,
        MCP availability and implementation blockers.</li>
    <li>Apply quote-based checks: unsupported claims are not retained
        as established facts.</li>
    <li>Use a 20-app evaluation sample prepared through Claude-assisted
        documentation review. This was not an independent human audit.</li>
  </ol>
</section>

<section>
  <h2>Verification limitations</h2>

  <p class="warning">
    Independent second-opinion model verification and automated browser
    checks could not be completed because the required Anthropic API
    credentials were unavailable. These stages must not be interpreted
    as successfully completed.
  </p>

  <p>
    The review queue contains records requiring further attention.
    Some fields remain unknown because the collected pages did not
    establish the relevant fact. This does not prove that the product
    lacks that capability.
  </p>

  <p>
    Search coverage is not exhaustive. API scopes, rate limits, pricing,
    terms, approval requirements and production readiness may require
    additional direct confirmation with each provider.
  </p>
</section>

<footer>
  Generated locally from data/final.json.
  Rebuild using <code>python build_page.py</code>.
</footer>

</main>

<script>
const q = document.getElementById('q');
const cat = document.getElementById('cat');

function filterRows() {{
  const term = q.value.toLowerCase();
  const category = cat.value;

  document.querySelectorAll('#rows tr').forEach(row => {{
    row.style.display =
      row.dataset.search.includes(term) &&
      (!category || row.dataset.category === category)
        ? ''
        : 'none';
  }});
}}

q.addEventListener('input', filterRows);
cat.addEventListener('change', filterRows);
</script>

</body>
</html>
"""

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(page, encoding="utf-8")

    print(f"Created: {OUTPUT_PATH.resolve()}")
    print(f"Applications: {total}")
    print(f"Categories: {len(categories)}")
    print(f"Awaiting human review: {human_review}")
    print(f"Apps with source URLs: {evidence_count}")


if __name__ == "__main__":
    main()
