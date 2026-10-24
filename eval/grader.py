"""Match reviewer findings to expected defects and compute metrics.

Matching rule (deliberately explicit, it is the main judgment call of this eval):
a finding matches an expected defect when the file is the same and the line is within
LINE_TOLERANCE of the expected line. Category and severity are NOT required to match; they
are reported separately so "found it but mislabeled it" is visible instead of hidden.
Matching is one-to-one, closest line first, so duplicate findings count as false positives.
"""

import random
import statistics
from dataclasses import dataclass, field

LINE_TOLERANCE = 3


@dataclass
class CaseGrade:
    case: str
    tp: int
    fp: int
    fn: int
    category_hits: int  # matched findings with the right category
    severity_hits: int
    matched: list[tuple[dict, dict]] = field(default_factory=list)  # (expected, finding)
    missed: list[dict] = field(default_factory=list)
    spurious: list[dict] = field(default_factory=list)
    contract_ok: bool = True


def _norm(path: str) -> str:
    return path.strip().removeprefix("./").removeprefix("b/")


def grade_case(
    case: str,
    expected: list[dict],
    findings: list[dict],
    tolerance: int = LINE_TOLERANCE,
    contract_ok: bool = True,
) -> CaseGrade:
    candidates = []
    for ei, e in enumerate(expected):
        for fi, f in enumerate(findings):
            distance = abs(f["line"] - e["line"])
            if _norm(f["file"]) == _norm(e["file"]) and distance <= tolerance:
                candidates.append((distance, ei, fi))

    used_e, used_f, matched = set(), set(), []
    for _, ei, fi in sorted(candidates):
        if ei not in used_e and fi not in used_f:
            used_e.add(ei)
            used_f.add(fi)
            matched.append((expected[ei], findings[fi]))

    return CaseGrade(
        case=case,
        tp=len(matched),
        fp=len(findings) - len(matched),
        fn=len(expected) - len(matched),
        category_hits=sum(e["category"] == f["category"] for e, f in matched),
        severity_hits=sum(e["severity"] == f["severity"] for e, f in matched),
        matched=matched,
        missed=[e for i, e in enumerate(expected) if i not in used_e],
        spurious=[f for i, f in enumerate(findings) if i not in used_f],
        contract_ok=contract_ok,
    )


def _ratio(num: float, den: float) -> float | None:
    return num / den if den else None


def run_metrics(grades: list[CaseGrade], clean_cases: set[str]) -> dict:
    """Metrics for one full pass over the dataset (one run)."""
    tp, fp, fn = (sum(getattr(g, k) for g in grades) for k in ("tp", "fp", "fn"))
    precision, recall = _ratio(tp, tp + fp), _ratio(tp, tp + fn)
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision is not None and recall and precision + recall
        else None
    )
    clean = [g for g in grades if g.case in clean_cases]
    by_category: dict[str, dict[str, int]] = {}
    for g in grades:
        for e, _ in g.matched:
            by_category.setdefault(e["category"], {"tp": 0, "fn": 0})["tp"] += 1
        for e in g.missed:
            by_category.setdefault(e["category"], {"tp": 0, "fn": 0})["fn"] += 1

    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "category_accuracy": _ratio(sum(g.category_hits for g in grades), tp),
        "severity_accuracy": _ratio(sum(g.severity_hits for g in grades), tp),
        # Share of no-defect diffs where the reviewer still reported something (noise).
        "clean_false_alarm_rate": _ratio(sum(g.fp > 0 for g in clean), len(clean)),
        "contract_failure_rate": _ratio(sum(not g.contract_ok for g in grades), len(grades)),
        "recall_by_category": {
            c: _ratio(v["tp"], v["tp"] + v["fn"]) for c, v in by_category.items()
        },
    }


def summarize(values: list[float | None]) -> dict:
    vals = [v for v in values if v is not None]
    if not vals:
        return {"mean": None, "std": None, "min": None, "max": None, "n": 0}
    return {
        "mean": statistics.fmean(vals),
        "std": statistics.stdev(vals) if len(vals) > 1 else 0.0,
        "min": min(vals),
        "max": max(vals),
        "n": len(vals),
    }


def bootstrap_ci(
    grades_by_case: dict[str, list[CaseGrade]],
    metric: str,
    iterations: int = 2000,
    seed: int = 0,
) -> tuple[float, float] | None:
    """95% CI of pooled precision or recall, resampling *cases* (the small-n uncertainty)."""
    rng = random.Random(seed)
    cases = list(grades_by_case)
    samples = []
    for _ in range(iterations):
        picked = [g for c in rng.choices(cases, k=len(cases)) for g in grades_by_case[c]]
        tp = sum(g.tp for g in picked)
        den = tp + sum(g.fp if metric == "precision" else g.fn for g in picked)
        if den:
            samples.append(tp / den)
    if not samples:
        return None
    samples.sort()
    return samples[int(0.025 * len(samples))], samples[int(0.975 * len(samples)) - 1]
