import csv, json, re, time
from pathlib import Path

def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")

def read_csv(path):
    path = Path(path)
    return list(csv.DictReader(open(path, newline="", encoding="utf-8"))) if path.exists() else []

def read_jsonl(path):
    path = Path(path)
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()] if path.exists() else []

def write_jsonl(path, rows):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")

def append_jsonl(path, row):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f: f.write(json.dumps(row, ensure_ascii=False) + "\n")

def today():
    return time.strftime("%Y-%m-%d")
