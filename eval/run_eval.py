"""Run the reviewer over every case K times, grade, and write a results file.

    uv run python -m eval.run_eval --runs 3 --label baseline

Exit code 1 when the release gate fails, so this can block a CI job.
"""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

from eval.grader import LINE_TOLERANCE, CaseGrade, bootstrap_ci, grade_case, run_metrics, summarize
from reviewer.review import DEFAULT_MODEL, ROOT, SKILL_DIR, review

CASES_DIR = ROOT / "eval" / "cases"
RESULTS_DIR = ROOT / "results"
CANARY = "CANARY"


def load_cases(pattern: str) -> list[dict]:
    cases = []
    for d in sorted(CASES_DIR.glob(pattern)):
        if d.is_dir() and (d / "input.diff").exists():
            cases.append(
                {
                    "name": d.name,
                    "diff": (d / "input.diff").read_text(),
                    "expected": json.loads((d / "expected.json").read_text()),
                }
            )
    return cases


def preflight_skill_loaded(model: str, diff: str) -> None:
    """Fail fast if the skill isn't actually loaded (e.g. a name clash with a built-in skill):
    a copy of the skill with a canary instruction must change the output."""
    with tempfile.TemporaryDirectory() as tmp:
        skill = Path(tmp) / "skill"
        shutil.copytree(SKILL_DIR, skill)
        with (skill / "SKILL.md").open("a") as f:
            f.write(f"\n\nIMPORTANT: start every description with the word {CANARY}.\n")
        result = review(diff, model, skill_dir=skill)
    if not result.ok or not any(f["description"].startswith(CANARY) for f in result.findings):
        sys.exit(
            f"preflight failed: skill instructions not applied ({result.error or 'no canary'})"
        )


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def metadata(args: argparse.Namespace) -> dict:
    claude_version = subprocess.run(["claude", "--version"], capture_output=True, text=True)
    return {
        "label": args.label,
        "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
        "model": args.model,
        "runs": args.runs,
        "line_tolerance": args.tolerance,
        "skill_sha256": hashlib.sha256((SKILL_DIR / "SKILL.md").read_bytes()).hexdigest()[:12],
        "git_commit": _git("rev-parse", "--short", "HEAD") or None,
        "git_dirty": bool(_git("status", "--porcelain")),
        "claude_version": claude_version.stdout.strip(),
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--runs", type=int, default=3, help="repeats per case (LLM output varies)")
    p.add_argument("--label", default="run")
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--cases", default="*", help="glob over eval/cases, e.g. '00[1-3]*'")
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--tolerance", type=int, default=LINE_TOLERANCE)
    p.add_argument("--skip-preflight", action="store_true")
    # Release gate, on the mean over runs.
    p.add_argument("--min-recall", type=float, default=0.7)
    p.add_argument("--min-precision", type=float, default=0.7)
    p.add_argument("--max-clean-false-alarm", type=float, default=0.25)
    args = p.parse_args()

    cases = load_cases(args.cases)
    if not cases:
        sys.exit(f"no cases match {args.cases!r}")
    clean_cases = {c["name"] for c in cases if not c["expected"]}
    if not args.skip_preflight:
        preflight_skill_loaded(args.model, cases[0]["diff"])

    jobs = [(run, c) for run in range(args.runs) for c in cases]
    print(f"{len(cases)} cases x {args.runs} runs = {len(jobs)} reviews ({args.model})")
    with ThreadPoolExecutor(args.workers) as pool:
        outputs = list(pool.map(lambda job: review(job[1]["diff"], args.model), jobs))

    per_run: dict[int, list[CaseGrade]] = {r: [] for r in range(args.runs)}
    by_case: dict[str, list[CaseGrade]] = {c["name"]: [] for c in cases}
    raw = []
    for (run, case), out in zip(jobs, outputs, strict=True):
        g = grade_case(case["name"], case["expected"], out.findings, args.tolerance, out.ok)
        per_run[run].append(g)
        by_case[case["name"]].append(g)
        raw.append(
            {
                "run": run,
                "case": case["name"],
                "ok": out.ok,
                "error": out.error,
                "cost_usd": out.cost_usd,
                "duration_s": round(out.duration_s, 2),
                "findings": out.findings,
                "missed": g.missed,
                "spurious": g.spurious,
            }
        )

    runs = [run_metrics(per_run[r], clean_cases) for r in range(args.runs)]
    keys = [
        "precision",
        "recall",
        "f1",
        "category_accuracy",
        "severity_accuracy",
        "clean_false_alarm_rate",
        "contract_failure_rate",
    ]
    summary = {k: summarize([m[k] for m in runs]) for k in keys}
    summary["precision"]["ci95_cases"] = bootstrap_ci(by_case, "precision")
    summary["recall"]["ci95_cases"] = bootstrap_ci(by_case, "recall")
    categories = sorted({c for m in runs for c in m["recall_by_category"]})
    summary["recall_by_category"] = {
        c: summarize([m["recall_by_category"].get(c) for m in runs]) for c in categories
    }
    per_case = {
        name: {
            "expected": len(cases_g[0].missed) + cases_g[0].tp,
            "detected_runs": f"{sum(g.fn == 0 for g in cases_g)}/{len(cases_g)}",
            "mean_fp": sum(g.fp for g in cases_g) / len(cases_g),
        }
        for name, cases_g in by_case.items()
    }
    costs = [o.cost_usd for o in outputs if o.cost_usd is not None]
    durations = sorted(o.duration_s for o in outputs)

    gate = {
        "recall": (summary["recall"]["mean"] or 0) >= args.min_recall,
        "precision": (summary["precision"]["mean"] or 0) >= args.min_precision,
        "clean_false_alarm_rate": (summary["clean_false_alarm_rate"]["mean"] or 0)
        <= args.max_clean_false_alarm,
    }
    result = {
        "meta": metadata(args),
        "gate": {
            "passed": all(gate.values()),
            "checks": gate,
            "thresholds": {
                "min_recall": args.min_recall,
                "min_precision": args.min_precision,
                "max_clean_false_alarm": args.max_clean_false_alarm,
            },
        },
        "summary": summary,
        "per_case": per_case,
        "per_run": runs,
        "cost": {
            "total_usd": round(sum(costs), 4),
            "p50_s": durations[len(durations) // 2],
            "p95_s": durations[int(0.95 * (len(durations) - 1))],
        },
        "raw": raw,
    }

    RESULTS_DIR.mkdir(exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    out_path = RESULTS_DIR / f"{stamp}_{args.label}.json"
    out_path.write_text(json.dumps(result, indent=2))
    print_report(result, out_path)
    sys.exit(0 if result["gate"]["passed"] else 1)


def _fmt(s: dict) -> str:
    if s["mean"] is None:
        return "n/a"
    text = f"{s['mean']:.2f} ± {s['std']:.2f}"
    if s.get("ci95_cases"):
        lo, hi = s["ci95_cases"]
        text += f"  (95% CI over cases {lo:.2f}–{hi:.2f})"
    return text


def print_report(result: dict, path: Path) -> None:
    s = result["summary"]
    print(f"\n{'metric':<24} mean ± std over runs")
    for k in (
        "recall",
        "precision",
        "f1",
        "category_accuracy",
        "severity_accuracy",
        "clean_false_alarm_rate",
        "contract_failure_rate",
    ):
        print(f"{k:<24} {_fmt(s[k])}")
    print("\nrecall by category")
    for c, v in s["recall_by_category"].items():
        print(f"  {c:<22} {_fmt(v)}")
    print("\nper case                       detected   mean FP")
    for name, v in result["per_case"].items():
        print(
            f"  {name:<28} {v['detected_runs'] if v['expected'] else '  -':>8}   {v['mean_fp']:.1f}"
        )
    c = result["cost"]
    print(f"\ncost ${c['total_usd']}  latency p50 {c['p50_s']:.1f}s p95 {c['p95_s']:.1f}s")
    print(f"GATE {'PASS' if result['gate']['passed'] else 'FAIL'} {result['gate']['checks']}")
    print(f"-> {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
