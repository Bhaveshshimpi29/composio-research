"""Seed URLs for apps that have no usable cached page. These URLs are only WHERE TO LOOK (chosen from memory by the
assistant, not evidence). The evidence is whatever the fetched page actually says, and the quote check enforces that.
A wrong URL costs a 404 and leaves the field `unknown`; it cannot create a false finding."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import config
from src.util import slug, read_csv

SEEDS = {
 "Attio": ["https://docs.attio.com/rest-api/guides/authentication", "https://attio.com/pricing", "https://docs.attio.com/rest-api/overview"],
 "Twenty": ["https://docs.twenty.com/developers/extend/api", "https://twenty.com/pricing", "https://github.com/twentyhq/twenty"],
 "Zoho CRM": ["https://www.zoho.com/crm/developer/docs/api/v8/oauth-overview.html", "https://www.zoho.com/crm/developer/docs/api/v8/", "https://www.zoho.com/crm/pricing/"],
 "Plain": ["https://www.plain.com/docs/graphql/authentication", "https://www.plain.com/docs/graphql/oauth", "https://www.plain.com/pricing"],
 "Gladly": ["https://developer.gladly.com/rest/", "https://www.gladly.com/pricing/"],
 "Telegram": ["https://core.telegram.org/bots/api", "https://core.telegram.org/api/obtaining_api_id", "https://core.telegram.org/bots"],
 "WhatsApp Business": ["https://developers.facebook.com/docs/whatsapp/cloud-api/get-started", "https://developers.facebook.com/docs/whatsapp/business-management-api/get-started", "https://developers.facebook.com/docs/whatsapp/pricing"],
 "Vonage": ["https://developer.vonage.com/en/getting-started/concepts/authentication", "https://www.vonage.com/communications-apis/pricing/"],
 "Meta Ads": ["https://developers.facebook.com/docs/marketing-api/overview", "https://developers.facebook.com/docs/marketing-api/get-started", "https://developers.facebook.com/docs/marketing-api/overview/authorization"],
 "LinkedIn Ads": ["https://learn.microsoft.com/en-us/linkedin/marketing/getting-started", "https://learn.microsoft.com/en-us/linkedin/shared/authentication/authentication", "https://learn.microsoft.com/en-us/linkedin/marketing/increasing-access"],
 "GoHighLevel": ["https://marketplace.gohighlevel.com/docs/oauth/GettingStarted", "https://highlevel.stoplight.io/docs/integrations/", "https://www.gohighlevel.com/pricing"],
 "systeme.io": ["https://developer.systeme.io/", "https://systeme.io/pricing"],
 "Ecwid": ["https://api-docs.ecwid.com/docs/get-started", "https://api-docs.ecwid.com/docs/authentication", "https://www.ecwid.com/pricing"],
 "Gumroad": ["https://gumroad.com/api"],
 "fanbasis": ["https://fanbasis.com/", "https://docs.fanbasis.com/"],
 "Ahrefs": ["https://docs.ahrefs.com/docs/api/reference/introduction", "https://ahrefs.com/api", "https://ahrefs.com/pricing"],
 "Waterfall.io": ["https://waterfall.io/", "https://docs.waterfall.io/"],
 "GitHub": ["https://docs.github.com/en/rest/authentication/authenticating-to-the-rest-api", "https://github.com/github/github-mcp-server"],
 "Netlify": ["https://docs.netlify.com/api-and-cli-guides/api-guides/get-started-with-api/", "https://www.netlify.com/pricing/"],
 "Cloudflare": ["https://developers.cloudflare.com/fundamentals/api/get-started/create-token/", "https://developers.cloudflare.com/api/", "https://github.com/cloudflare/mcp-server-cloudflare"],
 "Neo4j": ["https://neo4j.com/docs/query-api/current/", "https://neo4j.com/docs/aura/api/authentication/", "https://neo4j.com/pricing/"],
 "Notion": ["https://developers.notion.com/reference/authentication", "https://developers.notion.com/docs/authorization", "https://developers.notion.com/docs/mcp"],
 "Airtable": ["https://airtable.com/developers/web/api/authentication", "https://airtable.com/developers/web/api/introduction", "https://airtable.com/pricing"],
 "Linear": ["https://linear.app/developers/graphql", "https://linear.app/developers/oauth-2-0-authentication", "https://linear.app/docs/mcp"],
 "Jira": ["https://developer.atlassian.com/cloud/jira/platform/rest/v3/intro/", "https://developer.atlassian.com/cloud/jira/platform/basic-auth-for-rest-apis/", "https://www.atlassian.com/software/jira/pricing", "https://www.atlassian.com/platform/remote-mcp-server"],
 "Asana": ["https://developers.asana.com/docs/authentication", "https://developers.asana.com/docs/personal-access-token", "https://developers.asana.com/docs/using-asanas-mcp-server"],
 "Monday.com": ["https://developer.monday.com/api-reference/docs/authentication", "https://developer.monday.com/api-reference/docs/basics", "https://monday.com/pricing"],
 "ClickUp": ["https://developer.clickup.com/docs/authentication", "https://developer.clickup.com/docs/index", "https://clickup.com/pricing"],
 "Coda": ["https://coda.io/developers/apis/v1", "https://coda.io/pricing"],
 "Smartsheet": ["https://developers.smartsheet.com/api/smartsheet/guides/basics/authentication", "https://www.smartsheet.com/pricing"],
 "Harvest": ["https://help.getharvest.com/api-v2/authentication-api/authentication/authentication/", "https://help.getharvest.com/api-v2/", "https://www.getharvest.com/pricing"],
 "Stripe": ["https://docs.stripe.com/keys", "https://docs.stripe.com/api/authentication", "https://docs.stripe.com/mcp"],
 "Plaid": ["https://plaid.com/docs/quickstart/", "https://plaid.com/docs/api/", "https://plaid.com/pricing/", "https://plaid.com/docs/resources/mcp/"],
 "Binance": ["https://developers.binance.com/docs/binance-spot-api-docs/rest-api/general-api-information", "https://developers.binance.com/docs/binance-spot-api-docs"],
 "Paygent Connect": ["https://docs.nmi.com/", "https://www.paygent.com/"],
 "iPayX": ["https://ipayx.ai/docs", "https://ipayx.ai/"],
 "QuickBooks": ["https://developer.intuit.com/app/developer/qbo/docs/develop/authentication-and-authorization/oauth-2.0", "https://developer.intuit.com/app/developer/qbo/docs/get-started"],
 "Xero": ["https://developer.xero.com/documentation/guides/oauth2/overview/", "https://developer.xero.com/pricing", "https://developer.xero.com/documentation/getting-started-guide/"],
 "Brex": ["https://developer.brex.com/docs/authentication/", "https://developer.brex.com/"],
 "Ramp": ["https://docs.ramp.com/developer-api/v1/authorization", "https://docs.ramp.com/"],
 "PitchBook": ["https://pitchbook.com/", "https://pitchbook.com/data"],
 "NotebookLM": ["https://cloud.google.com/gemini/enterprise/notebooklm-enterprise/docs/overview", "https://cloud.google.com/gemini/enterprise/notebooklm-enterprise/docs/api-notebooks"],
 "Otter AI": ["https://help.otter.ai/", "https://otter.ai/pricing"],
 "Fathom": ["https://developers.fathom.ai/", "https://fathom.video/pricing"],
 "Consensus": ["https://consensus.app/home/api/", "https://consensus.app/pricing/"],
 "Reducto": ["https://docs.reducto.ai/", "https://reducto.ai/pricing"],
 "Devin": ["https://docs.devin.ai/api-reference/overview", "https://docs.devin.ai/"],
 "higgsfield": ["https://higgsfield.ai/cli", "https://higgsfield.ai/"],
 "Mermaid CLI": ["https://github.com/mermaid-js/mermaid-cli", "https://mermaid.js.org/"],
 "YouTube Transcript": ["https://transcriptapi.com/", "https://transcriptapi.com/docs", "https://transcriptapi.com/pricing"],
 "Grain": ["https://developers.grain.com/", "https://grain.com/pricing"],
}

def main():
    apps = [r["app"] for r in read_csv(config.APPS_CSV)]
    assert set(SEEDS) <= set(apps), set(SEEDS) - set(apps)
    config.DISCOVERED.mkdir(parents=True, exist_ok=True); n = 0
    for app, urls in SEEDS.items():
        if (config.RAW / slug(app)).exists() and any((config.RAW / slug(app)).glob("*.json")) and app not in ("Attio", "Zoho CRM", "Plain", "Gladly", "Telegram", "WhatsApp Business", "Vonage", "GitHub", "Netlify", "Cloudflare", "Neo4j", "Notion", "Gumroad"):
            continue
        (config.DISCOVERED / f"{slug(app)}.json").write_text(json.dumps(
            {"app": app, "provider": "manual-seed (not evidence)", "date": "2026-11-23",
             "urls": [{"url": u, "kind": "seed"} for u in urls]}, indent=1), encoding="utf-8"); n += 1
    print("wrote", n, "discovery files")

if __name__ == "__main__": main()
