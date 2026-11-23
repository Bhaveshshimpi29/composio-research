"""One command reruns everything. Cached pages and cached LLM results make reruns cheap.
   python -m src.run_all                 # all steps
   python -m src.run_all --from pass2    # start from a later step"""
import sys
from . import discover, fetch, extract, verify, score, aggregate_cli, build_page

STEPS = [("discover", discover.main), ("fetch", fetch.main), ("extract", extract.main),
         ("pass2", verify.run_pass2), ("pass3a", verify.run_pass3a), ("pass3b", verify.run_pass3b),
         ("score", score.main), ("aggregate", aggregate_cli.main), ("build", build_page.build)]

if __name__ == "__main__":
    names = [n for n, _ in STEPS]
    start = names.index(sys.argv[sys.argv.index("--from") + 1]) if "--from" in sys.argv else 0
    for n, fn in STEPS[start:]:
        print(f"\n=== {n} ==="); fn()
