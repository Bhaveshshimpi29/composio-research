"""Load Claude-in-session extractions as pass1, then run the code-only quote check as pass2 (no LLM, no retry).
Run: python tools/load_pass1.py"""
import sys; sys.path.insert(0, ".")
from src import store, config
from src.extract import finish
from src.fetch import load_pages
from src.quotecheck import check_record
from tools.normalize_extractions import load
hints, cats = {}, {}
import csv
for row in csv.DictReader(open(config.DATA / "hints.csv", encoding="utf-8")):
    hints[row["app"]] = row.get("hint", ""); cats[row["app"]] = row.get("list_category", "")
p1, p2 = [], []
for r in load():
    r["category"] = cats.get(r["app"]) or r["category"]       # the assignment's own 10 categories
    note = r.pop("note", ""); r.pop("_norm", None)
    rec = finish(r, r["app"], hints.get(r["app"], ""), "claude-in-session", why=note)
    store.upsert("pass1", rec)
    checked, failed = check_record(rec, load_pages(r["app"]))
    store.upsert("pass2", {**checked, "qc_failed": failed, "retried": False})
print("loaded", len(load()), "records into pass1 and pass2")
