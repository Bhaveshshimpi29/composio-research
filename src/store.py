"""data/results.jsonl: one record per app per stage (pass1, pass2, pass3a, pass3b)."""
import threading
from . import config
from .util import read_jsonl, write_jsonl

STAGES = ["pass1", "pass2", "pass3a", "pass3b"]
_lock = threading.Lock()

def load(stage=None):
    rows = read_jsonl(config.RESULTS)
    return [r for r in rows if stage is None or r["stage"] == stage]

def upsert(stage, rec):
    with _lock:
        rows = [r for r in read_jsonl(config.RESULTS) if not (r["stage"] == stage and r["app"] == rec["app"])]
        write_jsonl(config.RESULTS, rows + [{**rec, "stage": stage}])

def save_stage(stage, recs):
    with _lock:
        rows = [r for r in read_jsonl(config.RESULTS) if r["stage"] != stage]
        write_jsonl(config.RESULTS, rows + [{**r, "stage": stage} for r in recs])
