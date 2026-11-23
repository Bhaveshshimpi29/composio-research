# App-research agent (Composio AI Product Ops take-home)

Researches 100 apps with an agent: how to get API access, free vs gated, API surface, MCP, and whether a toolkit is buildable today.
Then it verifies itself (quote check, rules, second agent, browser, human) and builds one HTML page.

## Setup (once)
```
python -m venv .venv && source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
playwright install chromium                               # browser for JS-heavy docs + the browser check
cp .env.example .env                                      # then put your ANTHROPIC_API_KEY in .env
python -m pytest -q                                       # all tests should pass
```

## The steps (in this order)
1. **Try 3 apps first** (cheap, catches mistakes early):
   `python -m src.discover Notion Slack Stripe && python -m src.fetch Notion Slack Stripe && python -m src.extract Notion Slack Stripe`
   then open `data/results.jsonl` and `data/raw/` and check it looks sane.
2. **Build the gold sample BEFORE looking at agent output.** `python -m src.make_gold_template` writes `data/gold_template.csv` (20 apps).
   Fill every column from the real docs by hand, save as `data/gold.csv`. Allowed values are in `src/schema.py`; auth_methods uses `|` between values, e.g. `oauth2|api_key`.
   Put the docs URLs you used in `urls_used`. Do this blind: don't open `results.jsonl` first.
3. **Run everything:** `python -m src.run_all` (discover, fetch, extract, pass2, pass3a, pass3b, score, aggregate, build).
   It is cached and resumable: rerun it any time; fetched pages and LLM results are not redone. `--from pass2` starts later.
4. **Human review:** open `data/review_queue.csv` (apps the agent could not settle). Read the real docs, then add one row per fix to `data/corrections.csv`
   (`app,field,value,reason,reviewer,url,date`). Rerun `python -m src.run_all --from pass3b`.
5. **Explain the misses:** for each miss shown on the page, add a row to `data/miss_notes.csv` (`app,field,why`), then rebuild: `python -m src.build_page`.
6. **Publish:** `REPO_URL=https://github.com/you/repo python -m src.build_page`, then deploy the `site/` folder (Netlify drag-and-drop, Vercel, or GitHub Pages).
   Submit the live link (and the repo link) in the Google Form.

## What each step does
| Step | File | Output |
|---|---|---|
| Discover | `src/discover.py` | `data/discovered/*.json` (URLs) |
| Fetch + cache | `src/fetch.py` | `data/raw/<app>/*.json` (page text) |
| Extract (pass 1) | `src/extract.py` | `data/results.jsonl` |
| Quote check + retry (pass 2), rules + 2nd agent + browser (pass 3a), human fixes (pass 3b) | `src/verify.py` | `data/results.jsonl`, `data/review_queue.csv` |
| Score vs gold | `src/score.py` | `data/scores.json` |
| Aggregate | `src/aggregate_cli.py` | `data/aggregate.json` |
| Page | `src/build_page.py` | `site/index.html`, `site/results.json` |

Settings (models, limits, paths) are in `src/config.py` / `.env`. Never commit `.env`.
