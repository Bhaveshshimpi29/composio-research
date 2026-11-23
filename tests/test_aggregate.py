from src.aggregate import aggregate

def r(app, cat, auth, access, blocker, buildable, mcp="none_found", nh=False):
    return {"app": app, "category": cat, "auth_methods": auth, "access": access, "main_blocker": blocker,
            "buildable_today": buildable, "existing_mcp": mcp, "needs_human": nh}

RECS = [
 r("A", "CRM", ["oauth2"], "self_serve_free", "none", "yes"),
 r("B", "CRM", ["oauth2", "api_key"], "free_trial", "none", "yes", mcp="official"),
 r("C", "Pay", ["api_key"], "partner_or_sales", "partner_gate", "no"),
 r("D", "Pay", ["oauth2"], "paid_plan", "paid_plan", "partial"),
 r("E", "Pay", [], "unknown", "unknown", "unknown", nh=True),
]

def test_auth_counts_and_dominant():
    a = aggregate(RECS)
    assert a["auth_counts"]["oauth2"] == 3 and a["auth_counts"]["api_key"] == 2
    assert a["dominant_auth"] == "oauth2"

def test_blocker_most_common_excludes_none_and_unknown():
    a = aggregate(RECS)
    assert a["blocker_counts"] == {"partner_gate": 1, "paid_plan": 1} and a["top_blocker"] in ("partner_gate", "paid_plan")

def test_self_serve_by_category():
    a = aggregate(RECS)
    assert a["category_access"]["CRM"]["self_serve_free"] == 1 and a["category_access"]["CRM"]["free_trial"] == 1
    assert a["gated_share_by_category"]["CRM"] == 0.0
    assert a["gated_share_by_category"]["Pay"] == round(2 / 3, 4)   # partner + paid out of 3

def test_easy_wins_and_outreach_lists():
    a = aggregate(RECS)
    assert a["easy_wins"] == ["A", "B"]
    assert a["needs_outreach"] == ["C"]       # partner/sales/admin only; paid is its own bucket
    assert a["paid_only"] == ["D"]
    assert a["n"] == 5 and a["n_needs_human"] == 1 and a["n_existing_mcp"] == 1
