"""Compare two results files: did the change help, hurt, or stay within noise?

uv run python -m eval.compare results/A.json results/B.json
"""

import json
import sys
from pathlib import Path

METRICS = [
    "recall",
    "precision",
    "f1",
    "category_accuracy",
    "severity_accuracy",
    "clean_false_alarm_rate",
    "contract_failure_rate",
]


def main() -> None:
    a, b = (json.loads(Path(p).read_text()) for p in sys.argv[1:3])
    print(f"A = {a['meta']['label']} (skill {a['meta']['skill_sha256']}, {a['meta']['model']})")
    print(f"B = {b['meta']['label']} (skill {b['meta']['skill_sha256']}, {b['meta']['model']})\n")
    print(f"{'metric':<24}{'A':>8}{'B':>8}{'delta':>8}   noise (max std)")
    for k in METRICS:
        ma, mb = a["summary"][k]["mean"], b["summary"][k]["mean"]
        if ma is None or mb is None:
            continue
        noise = max(a["summary"][k]["std"], b["summary"][k]["std"])
        flag = "" if abs(mb - ma) > noise else "  (within noise)"
        print(f"{k:<24}{ma:>8.2f}{mb:>8.2f}{mb - ma:>+8.2f}   {noise:.2f}{flag}")
    print("\nper case (detected runs, mean FP)")
    for name in sorted(set(a["per_case"]) | set(b["per_case"])):
        ca, cb = a["per_case"].get(name), b["per_case"].get(name)
        fa = f"{ca['detected_runs']} {ca['mean_fp']:.1f}" if ca else "-"
        fb = f"{cb['detected_runs']} {cb['mean_fp']:.1f}" if cb else "-"
        mark = "" if fa == fb else "  <-"
        print(f"  {name:<28} {fa:>10} -> {fb:<10}{mark}")
    print(f"\ncost ${a['cost']['total_usd']} -> ${b['cost']['total_usd']}")


if __name__ == "__main__":
    main()
