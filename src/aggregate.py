"""Turn the final records into the patterns the reviewer wants."""
from collections import Counter, defaultdict
from .schema import GATED_ACCESS

SELF_SERVE = {"self_serve_free", "free_trial"}

def aggregate(recs):
    n = len(recs)
    auth = Counter(a for r in recs for a in r.get("auth_methods", []) if a not in ("unknown", "none_found"))
    blockers = Counter(r["main_blocker"] for r in recs if r.get("main_blocker") not in ("none", "unknown", None))
    access = Counter(r.get("access") for r in recs)
    cat_access = defaultdict(Counter)
    for r in recs: cat_access[r.get("category", "?")][r.get("access")] += 1
    gated_share = {}
    for c, cnt in cat_access.items():
        tot = sum(cnt.values())
        gated_share[c] = round((sum(cnt[a] for a in GATED_ACCESS) + cnt["paid_plan"]) / tot, 4) if tot else 0
    easy = [r["app"] for r in recs if r.get("buildable_today") == "yes" and r.get("access") in SELF_SERVE]
    outreach = [r["app"] for r in recs if r.get("access") in GATED_ACCESS]
    paid = [r["app"] for r in recs if r.get("access") == "paid_plan"]
    return {
        "n": n, "auth_counts": dict(auth.most_common()),
        "dominant_auth": auth.most_common(1)[0][0] if auth else None,
        "access_counts": dict(access.most_common()),
        "blocker_counts": dict(blockers.most_common()),
        "top_blocker": blockers.most_common(1)[0][0] if blockers else None,
        "category_access": {c: dict(v) for c, v in cat_access.items()},
        "gated_share_by_category": gated_share,
        "easy_wins": easy, "needs_outreach": outreach, "paid_only": paid,
        "buildable_counts": dict(Counter(r.get("buildable_today") for r in recs)),
        "n_needs_human": sum(1 for r in recs if r.get("needs_human")),
        "n_existing_mcp": sum(1 for r in recs if r.get("existing_mcp") in ("official", "community")),
        "n_unknown_access": access.get("unknown", 0),
    }
