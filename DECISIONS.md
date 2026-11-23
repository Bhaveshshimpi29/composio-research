# DECISIONS (read this before the interview)

**Files, not a database.** 100 rows. JSONL + CSV are diffable and need nothing installed.

**Evidence over memory.** The extraction prompt forbids using the model's own knowledge. Every field needs `{field, url, quote}`.
The quote check (`src/quotecheck.py`) is plain code: normalise whitespace/case/dashes, then require the quote (min 15 chars) to appear in the cached text
of the cited URL. Fail = the field becomes `unknown`. Why code and not an LLM: an LLM judging an LLM can be fooled the same way; a substring test cannot.

**"unknown" added to the enums.** BRIEF.md's lists have no unknown for several fields, but its rule says no evidence means unknown, so I added it.

**Two different agents.** The second opinion (`MODEL_SECOND`, default a different, larger model) gets a different prompt, never sees the first answer, and re-answers only the
risky fields (`access`, `auth_methods`, `main_blocker`). Its quotes are quote-checked too.

**Disagreement handling (`resolve()` in verify.py, tested).** Two agree = keep. Disagree = a browser re-reads the live cited pages and answers fresh; if it matches one of them
(2 of 3) that wins; if it matches neither, or no browser ran, it goes to a human. If a rule flagged an agreed answer ("self-serve" but the cited page says contact sales), the browser must confirm it.

**Rules (`src/rules.py`).** Four readable rules: suspicious self-serve, buildable=yes with a blocker, buildable=yes with no public API, gated access with blocker=none.
Inconsistency always goes to a human.

**Four stages, not three.** pass1 (extract), pass2 (+quote check), pass3a (+rules/2nd agent/browser), pass3b (+human). Splitting 3a/3b shows what automation alone achieves vs what the human added.

**Gold sample is yours, blind.** 20 apps hand-picked across all 10 categories incl. likely-gated ones (my pick is a guess, not evidence). I did not fill it, since an AI-filled gold set would not measure anything.
Small sample (about 100 field checks): differences of a few points are noise, and the page says so.

**Honest limits.** Unknown stays unknown. Gated/paid with proof is a finding. Pages that block bots or sit behind logins are listed as limits.

**Cost.** Tokens and seconds are logged per step in `data/runs.jsonl`. Dollar cost is shown only if you set prices in `.env` (I don't hard-code prices that may be stale). Search-tool fees are extra.

## Things I could NOT verify (be upfront about these)
- **Composio SDK/MCP.** The brief says to use it "where it fits" and to read the docs first. I read the direct-execution docs: `Composio(api_key=...)`, `composio.tools.execute(slug, user_id=..., arguments=..., version=... or dangerously_skip_version_check=True)`.
  The Composio Search toolkit has slugs such as `COMPOSIO_SEARCH_DUCK_DUCK_GO_SEARCH`, but the docs page I could read did not list argument names or output shape. So `SEARCH_PROVIDER=composio` is **experimental**: it assumes an argument called `query`,
  extracts URLs from whatever comes back, and falls back to Anthropic search on any error. The default is Anthropic web search. Try the Composio provider yourself on 3 apps before you claim it on the page; `composio` is not in `requirements.txt` (not pinned or audited): `pip install composio` yourself if you want it.
- **No live run.** This was built where the docs sites and your API key are not reachable, so discover/fetch/extract against the real API have NOT been run. The deterministic parts are tested (31 tests), and the full pipeline passes an offline test with a fake LLM and fake pages.
  Expect to fix small things on first live run (for example a model name or the web-search tool version string in `discover.py`). Step 1 of the README (3 apps) exists for that.
- Model IDs (`claude-sonnet-5-5`, `claude-haiku-5-5`, `claude-opus-5-5`) are defaults in `src/config.py`; change them in `.env` if your account uses different ones.
- Binance's website hint was cut off in the screenshot; `hints.csv` has a guess. Hints only seed the search.
