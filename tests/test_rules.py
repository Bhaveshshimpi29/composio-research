from src.rules import rule_flags

def rec(**kw):
    d = {"auth_methods": ["api_key"], "access": "self_serve_free", "api_type": ["rest"], "api_breadth": "large",
         "existing_mcp": "none_found", "buildable_today": "yes", "main_blocker": "none",
         "evidence": [{"field": "access", "url": "u", "quote": "q"}]}
    d.update(kw); return d

def test_clean_record_has_no_flags():
    assert rule_flags(rec(), {"u": "Get a free API key in your dashboard."}) == []

def test_self_serve_with_contact_sales_text_is_suspicious():
    f = rule_flags(rec(), {"u": "API access is available on request. Contact sales to get started."})
    assert "suspicious_access" in f

def test_inconsistent_buildable_yes_with_blocker():
    assert "inconsistent_buildable_blocker" in rule_flags(rec(main_blocker="partner_gate"), {"u": "x"})

def test_inconsistent_no_public_api_but_buildable():
    assert "inconsistent_no_api" in rule_flags(rec(api_type=["none_public"]), {"u": "x"})

def test_gated_access_with_blocker_none_is_inconsistent():
    assert "inconsistent_access_blocker" in rule_flags(rec(access="partner_or_sales", buildable_today="no"), {"u": "x"})
