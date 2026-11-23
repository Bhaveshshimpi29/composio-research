"""Pass 2: prepare a 20-app evidence spot-check and consolidated final dataset.

This script does not claim that an AI independently verified facts. It creates a
repeatable human-review sample and a consolidated dataset from saved research.
"""
import csv
import json
from pathlib import Path

RAW_DIR = Path("data/raw")
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

def main():
    records = []
    for path in sorted(RAW_DIR.glob("*.json")):
        try:
            records.append(json.loads(path.read_text(encoding="utf-8")))
        except Exception as exc:
            print(f"Could not read {path}: {exc}")

    if not records:
        raise SystemExit("No research records found. Run python research.py first.")

    records.sort(key=lambda x: (x.get("category", ""), x.get("app", "")))
    (DATA_DIR / "final.json").write_text(
        json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    by_category = {}
    for record in records:
        by_category.setdefault(record.get("category", "Uncategorized"), []).append(record)

    sample = []
    for category, items in by_category.items():
        # Select up to two apps from each category, spread across the sorted list.
        if len(items) <= 2:
            sample.extend(items)
        else:
            sample.extend([items[0], items[len(items) // 2]])

    fields = [
        "app", "category", "field_to_check", "current_assessment",
        "official_source_url", "review_result", "reviewer_notes"
    ]
    with open(DATA_DIR / "human_check.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for item in sample:
            urls = item.get("evidence_urls") or [""]
            for field in ["authentication", "developer_access", "api_type"]:
                writer.writerow({
                    "app": item.get("app", ""),
                    "category": item.get("category", ""),
                    "field_to_check": field,
                    "current_assessment": item.get(field, ""),
                    "official_source_url": urls[0],
                    "review_result": "",
                    "reviewer_notes": ""
                })

    print(f"Consolidated {len(records)} apps into data/final.json")
    print(f"Created {len(sample)}-app sample in data/human_check.csv")
    print("Review the CSV against official documentation before presenting findings.")

if __name__ == "__main__":
    main()
