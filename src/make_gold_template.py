"""Writes data/gold_template.csv: the 20 apps YOU fill in by hand from the real docs, BEFORE looking at agent output.
The apps were picked to cover all 10 categories and include likely-gated ones (a hand-pick, not evidence)."""
import csv
from . import config

GOLD_APPS = ["Salesforce", "DealCloud", "Zendesk", "Gladly", "Telegram", "WhatsApp Business", "Google Ads", "Mailchimp",
             "Amazon Selling Partner", "Shopify", "Ahrefs", "Firecrawl", "GitHub", "Snowflake", "Notion", "Smartsheet",
             "Plaid", "PitchBook", "Otter AI", "Mermaid CLI"]
COLS = ["app", "auth_methods", "access", "existing_mcp", "buildable_today", "main_blocker", "urls_used", "notes"]

if __name__ == "__main__":
    known = {r["app"] for r in csv.DictReader(open(config.APPS_CSV, encoding="utf-8"))}
    assert all(a in known for a in GOLD_APPS) and len(GOLD_APPS) == 20
    with open(config.DATA / "gold_template.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(COLS); [w.writerow([a] + [""] * (len(COLS) - 1)) for a in GOLD_APPS]
    print("wrote data/gold_template.csv. Fill it, then save a copy as data/gold.csv (see README for allowed values).")
