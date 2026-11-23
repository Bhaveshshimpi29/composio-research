"""Select the passages of each app's cached pages that matter for the schema, so an extractor (LLM) reads signal, not navigation.
Selection is by keyword only. The quote check later runs against the FULL cached page, not this excerpt."""
import re, sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.fetch import load_pages

KW = re.compile(r"oauth|api[ -]?key|access token|bearer|basic auth|authoriz|authenticat|personal access|token|secret|credential|"
                r"pricing|price|free|trial|plan|enterprise|paid|subscription|contact (us|sales)|sales|partner|approval|approved|review|"
                r"apply|request access|admin|permission|scope|mcp|model context|rest|graphql|soap|endpoint|sdk|rate limit|"
                r"developer (program|account|token|portal)|sandbox|waitlist|invite", re.I)

def excerpt(app, per_page=2200, total=6500):
    out, used = [], 0
    for url, text in load_pages(app).items():
        lines = [l.strip() for l in text.split("\n") if len(l.strip()) > 25]
        score = [len(KW.findall(l)) for l in lines]
        keep = set()
        for i, s in enumerate(score):
            if s: keep.update({i - 1, i, i + 1})
        chosen, n = [], 0
        for i in sorted(k for k in keep if 0 <= k < len(lines)):
            if n + len(lines[i]) > per_page: break
            chosen.append(lines[i]); n += len(lines[i]) + 1
        if chosen and used + n <= total:
            out.append(f"--- PAGE {url}\n" + "\n".join(chosen)); used += n
    return "\n".join(out)

if __name__ == "__main__":
    for app in sys.argv[1:]:
        print(f"\n######## {app}\n{excerpt(app)}")
