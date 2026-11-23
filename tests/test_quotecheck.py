from src.quotecheck import normalize, quote_in_page, check_record

PAGE = "Authentication\n\nThe API uses OAuth 2.0 — you can also use  personal access tokens.\nPricing: contact sales for the Enterprise plan."
URL = "https://x.dev/docs/auth"

def test_normalize_collapses_whitespace_case_and_fancy_punctuation():
    assert normalize("A  “quote” —\nhere") == 'a "quote" - here'

def test_quote_found_despite_whitespace_and_dash_style():
    assert quote_in_page("OAuth 2.0 - you can also use personal access tokens", PAGE)

def test_short_quote_rejected():
    assert not quote_in_page("OAuth", PAGE)          # too short to prove anything

def test_invented_quote_rejected():
    assert not quote_in_page("API keys are free for every developer", PAGE)

def base():
    return {
        "auth_methods": ["oauth2"], "access": "self_serve_free", "api_type": ["rest"],
        "api_breadth": "large", "existing_mcp": "none_found", "buildable_today": "yes",
        "main_blocker": "none", "confidence": "high",
        "evidence": [
            {"field": "auth_methods", "url": URL, "quote": "The API uses OAuth 2.0"},
            {"field": "access", "url": URL, "quote": "Developers get free keys instantly"},   # invented
        ],
    }

def test_check_record_unknowns_fields_with_bad_or_missing_quotes():
    rec, failed = check_record(base(), {URL: PAGE})
    assert rec["auth_methods"] == ["oauth2"]          # quote verified, kept
    assert rec["access"] == "unknown"                 # invented quote -> unknown
    assert rec["api_type"] == ["unknown"]
    assert "access" in failed and "auth_methods" not in failed
    assert "api_breadth" in failed                    # no evidence at all
    assert rec["api_breadth"] == "unknown"

def test_existing_mcp_none_found_needs_no_quote():
    rec, failed = check_record(base(), {URL: PAGE})
    assert rec["existing_mcp"] == "none_found" and "existing_mcp" not in failed

def test_quote_must_come_from_the_cited_url():
    rec = base(); rec["evidence"][0]["url"] = "https://other.dev/page"
    out, failed = check_record(rec, {URL: PAGE, "https://other.dev/page": "unrelated text here"})
    assert "auth_methods" in failed


def test_unknown_value_needs_no_evidence():
    from src.quotecheck import check_record
    from src.schema import EVIDENCED, UNKNOWN_VALUE
    rec = {f: UNKNOWN_VALUE.get(f, "unknown") for f in EVIDENCED}
    rec["evidence"] = []
    out, failed = check_record(rec, {})
    assert failed == []
