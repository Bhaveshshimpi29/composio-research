import json
from . import config, store
from .aggregate import aggregate

def final_stage():
    for st in reversed(store.STAGES):
        if store.load(st): return st

def main():
    st = final_stage()
    if not st: print("no results yet"); return
    agg = aggregate(store.load(st)); agg["stage"] = st
    (config.DATA / "aggregate.json").write_text(json.dumps(agg, indent=1), encoding="utf-8"); print("aggregate written from", st, "n =", agg["n"])

if __name__ == "__main__": main()
