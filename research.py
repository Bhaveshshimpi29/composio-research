"""Pass 1: resumable research of apps.csv using Composio MCP + Firecrawl."""
import asyncio
import csv
import json
import os
import random
from pathlib import Path

from common import ResearchClient, extract_urls, compact_text, classify_research

RAW_DIR = Path("data/raw")
RAW_DIR.mkdir(parents=True, exist_ok=True)

def load_apps():
    with open("apps.csv", newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise RuntimeError("apps.csv is empty.")
    required = {"id", "app", "category", "hint"}
    missing = required - set(rows[0].keys())
    if missing:
        raise RuntimeError(f"apps.csv is missing columns: {sorted(missing)}")
    return rows

async def research_one(client, row):
    out_path = RAW_DIR / f"{row['id']}.json"
    if out_path.exists():
        print(f"SKIP {row['app']} (already researched)")
        return "skipped"

    app, category, domain = row["app"], row["category"], row["hint"]
    queries = [
        f"site:{domain} developers API documentation authentication",
        f"{app} official API reference developer access MCP server"
    ]

    search_data = []
    candidate_urls = []
    errors = []

    for query in queries:
        try:
            result = await client.search(query, limit=5)
            search_data.append(result)
            candidate_urls.extend(extract_urls(result))
        except Exception as exc:
            errors.append(f"Search error: {exc}")

    # Keep only URLs that appear to belong to the supplied official domain.
    domain_key = domain.lower().replace("www.", "")
    official_urls = []
    for url in candidate_urls:
        host = url.lower().split("://", 1)[-1].split("/", 1)[0].split(":", 1)[0]
        if host == domain_key or host.endswith("." + domain_key):
            if url not in official_urls:
                official_urls.append(url)

    # Search output can contain direct official links not matched due redirects/subdomains.
    if not official_urls:
        official_urls = [
            u for u in candidate_urls
            if domain_key in u.lower()
        ]

    scraped = []
    for url in official_urls[:3]:
        try:
            raw = await client.scrape(url)
            scraped.append({"url": url, "content": compact_text(raw, 12000)})
        except Exception as exc:
            errors.append(f"Scrape error for {url}: {exc}")

    record = classify_research(app, category, domain, search_data, scraped)
    record["id"] = row["id"]
    record["search_queries"] = queries
    record["search_results_count"] = len(search_data)
    record["scraped_pages"] = len(scraped)
    record["errors"] = errors
    record["raw_search"] = [compact_text(x, 7000) for x in search_data]
    record["scraped_evidence"] = scraped

    out_path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"DONE {app} | pages={len(scraped)} | {record['buildability']}")
    await asyncio.sleep(0.25 + random.random() * 0.25)
    return "done"

async def main():
    rows = load_apps()
    print(f"Apps loaded: {len(rows)}")
    async with ResearchClient() as client:
        done = skipped = failed = 0
        for index, row in enumerate(rows, start=1):
            print(f"\n[{index}/{len(rows)}] {row['app']}")
            try:
                status = await research_one(client, row)
                if status == "skipped":
                    skipped += 1
                else:
                    done += 1
            except Exception as exc:
                failed += 1
                error_record = {
                    "id": row["id"], "app": row["app"], "category": row["category"],
                    "domain": row["hint"], "status": "research_error",
                    "error": str(exc), "evidence_urls": [], "blockers": ["Research failed"]
                }
                (RAW_DIR / f"{row['id']}.json").write_text(
                    json.dumps(error_record, indent=2), encoding="utf-8"
                )
                print(f"ERROR {row['app']}: {exc}")
        print(f"\nFinished. New: {done}, skipped: {skipped}, errors: {failed}")

if __name__ == "__main__":
    asyncio.run(main())
