from src.score import score_records

GOLD = [{"app": "A", "auth_methods": "oauth2|api_key", "access": "self_serve_free", "existing_mcp": "none_found",
         "buildable_today": "yes", "main_blocker": "none"},
        {"app": "B", "auth_methods": "api_key", "access": "partner_or_sales", "existing_mcp": "official",
         "buildable_today": "no", "main_blocker": "partner_gate"}]

def rec(app, **kw):
    d = {"app": app, "auth_methods": ["api_key", "oauth2"], "access": "self_serve_free", "existing_mcp": "none_found",
         "buildable_today": "yes", "main_blocker": "none"}
    d.update(kw); return d

def test_auth_compared_as_set_order_ignored():
    s = score_records([rec("A"), rec("B", auth_methods=["api_key"])], GOLD)
    assert s["fields"]["auth_methods"] == {"correct": 2, "total": 2}

def test_only_gold_apps_are_scored_and_misses_listed():
    s = score_records([rec("A"), rec("B"), rec("ZZZ")], GOLD)
    assert s["n_apps"] == 2
    assert s["fields"]["access"] == {"correct": 1, "total": 2}
    miss = [m for m in s["misses"] if m["app"] == "B" and m["field"] == "access"][0]
    assert miss["agent"] == "self_serve_free" and miss["truth"] == "partner_or_sales"

def test_overall_is_correct_cells_over_total_cells():
    s = score_records([rec("A"), rec("B")], GOLD)
    assert s["overall"] == round(s["correct"] / s["total"], 4) and s["total"] == 10

def test_missing_agent_record_counts_as_wrong():
    s = score_records([rec("A")], GOLD)
    assert s["n_apps"] == 2 and s["fields"]["access"]["total"] == 2
