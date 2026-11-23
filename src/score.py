"""Score agent records against the hand-made gold sample, per field."""
from .schema import SCORED

def _norm(field, v):
    if field == "auth_methods":
        items = v.split("|") if isinstance(v, str) else (v or [])
        return tuple(sorted(x.strip().lower() for x in items if x.strip()))
    return str(v or "").strip().lower()

def score_records(records, gold):
    by_app = {r["app"].lower(): r for r in records}
    fields = {f: {"correct": 0, "total": 0} for f in SCORED}
    misses = []
    for g in gold:
        rec = by_app.get(g["app"].lower())
        for f in SCORED:
            truth = _norm(f, g.get(f))
            got = _norm(f, rec.get(f)) if rec else None
            fields[f]["total"] += 1
            if got == truth: fields[f]["correct"] += 1
            else:
                disp = lambda x: "|".join(x) if isinstance(x, tuple) else (x if x is not None else "(no record)")
                misses.append({"app": g["app"], "field": f, "agent": disp(got), "truth": disp(truth)})
    correct = sum(v["correct"] for v in fields.values()); total = sum(v["total"] for v in fields.values())
    return {"n_apps": len(gold), "fields": fields, "correct": correct, "total": total,
            "overall": round(correct / total, 4) if total else None, "misses": misses}


def validate_gold(gold):
    """Return a list of human-readable problems (wrong spelling of an allowed value, empty cells)."""
    from . import schema
    allowed = {"auth_methods": schema.AUTH, "access": schema.ACCESS, "existing_mcp": schema.MCP,
               "buildable_today": schema.BUILDABLE, "main_blocker": schema.BLOCKER}
    problems = []
    for g in gold:
        for f, ok in allowed.items():
            vals = [x for x in (g.get(f) or "").split("|")] if f == "auth_methods" else [g.get(f, "")]
            for v in vals:
                if v.strip() not in ok: problems.append(f"{g['app']}.{f}: '{v}' is not one of {ok}")
    return problems

def main():
    import json
    from . import config, store
    from .util import read_csv
    gold = read_csv(config.GOLD_CSV)
    if not gold: print("no data/gold.csv yet: build the gold sample first (README step 3)"); return
    bad = validate_gold(gold)
    if bad: print("gold.csv problems:\n  " + "\n  ".join(bad)); raise SystemExit(1)
    out = {st: score_records(store.load(st), gold) for st in store.STAGES if store.load(st)}
    (config.DATA / "scores.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    for st, s in out.items(): print(f"{st}: {s['overall']:.0%} overall on {s['n_apps']} gold apps ({s['correct']}/{s['total']})")

if __name__ == "__main__": main()
