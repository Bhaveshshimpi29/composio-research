from src.verify import merge_retry, resolve, apply_corrections

def test_merge_retry_takes_retried_value_only_for_fields_that_failed_first_time():
    first = {"access": "unknown", "auth_methods": ["oauth2"], "evidence": [{"field": "auth_methods", "url": "u", "quote": "q1"}]}
    retry = {"access": "free_trial", "auth_methods": ["api_key"], "evidence": [{"field": "access", "url": "u", "quote": "q2"}]}
    merged, still = merge_retry(first, ["access"], retry, [])
    assert merged["access"] == "free_trial" and merged["auth_methods"] == ["oauth2"] and still == []
    assert {e["field"] for e in merged["evidence"]} == {"auth_methods", "access"}

def test_merge_retry_keeps_unknown_if_retry_also_fails():
    first = {"access": "unknown", "evidence": []}; retry = {"access": "unknown", "evidence": []}
    merged, still = merge_retry(first, ["access"], retry, ["access"])
    assert merged["access"] == "unknown" and still == ["access"]

def test_resolve_agreement_kept():
    assert resolve("access", "paid_plan", "paid_plan", None) == ("paid_plan", True, "two agents agree")

def test_resolve_disagreement_without_browser_needs_human():
    v, ok, why = resolve("access", "paid_plan", "free_trial", None)
    assert not ok and v == "paid_plan"

def test_resolve_browser_breaks_tie_two_of_three():
    assert resolve("access", "paid_plan", "free_trial", "free_trial")[:2] == ("free_trial", True)

def test_resolve_browser_disagrees_with_both_needs_human():
    assert resolve("access", "paid_plan", "free_trial", "partner_or_sales")[1] is False

def test_resolve_auth_methods_compared_as_sets():
    assert resolve("auth_methods", ["oauth2", "api_key"], ["api_key", "oauth2"], None)[1] is True

def test_resolve_suspicious_agreement_overturned_by_browser_needs_human():
    # both agents say self_serve_free, but a rule flagged it and the live page says otherwise
    v, ok, why = resolve("access", "self_serve_free", "self_serve_free", "partner_or_sales", suspicious=True)
    assert not ok

def test_apply_corrections_overrides_and_logs():
    recs = [{"app": "A", "access": "paid_plan", "auth_methods": ["oauth2"], "needs_human": True, "why": "disagree"}]
    corr = [{"app": "A", "field": "access", "value": "partner_or_sales", "reason": "docs say contact sales",
             "reviewer": "me", "url": "https://x", "date": "2026-11-23"},
            {"app": "A", "field": "auth_methods", "value": "oauth2|api_key", "reason": "r", "reviewer": "me", "url": "u", "date": "d"}]
    out = apply_corrections(recs, corr)
    assert out[0]["access"] == "partner_or_sales" and out[0]["auth_methods"] == ["oauth2", "api_key"]
    assert out[0]["needs_human"] is False and out[0]["human_reviewed"] is True
    assert len(out[0]["corrections"]) == 2
