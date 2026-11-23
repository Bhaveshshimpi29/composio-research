"""Simple, explainable rule checks. Each flag is a named reason a person can read."""
import re
from .schema import GATED_ACCESS

GATE_WORDS = re.compile(r"contact sales|talk to sales|book a demo|partner program|become a partner|"
                        r"request access|apply for access|app review|waitlist|enterprise plan only|by invitation", re.I)

def rule_flags(rec: dict, pages: dict) -> list:
    flags = []
    cited = [pages.get(e["url"], "") for e in rec.get("evidence", []) if e.get("field") in ("access", "auth_methods")]
    if rec.get("access") in ("self_serve_free", "free_trial") and any(GATE_WORDS.search(t) for t in cited):
        flags.append("suspicious_access")        # says self-serve, but the cited page talks about sales/partner gates
    if rec.get("buildable_today") == "yes" and rec.get("main_blocker") not in ("none", "unknown", None):
        flags.append("inconsistent_buildable_blocker")
    if rec.get("buildable_today") == "yes" and "none_public" in (rec.get("api_type") or []):
        flags.append("inconsistent_no_api")
    if rec.get("access") in GATED_ACCESS and rec.get("main_blocker") == "none":
        flags.append("inconsistent_access_blocker")
    return flags
