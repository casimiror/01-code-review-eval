from eval.grader import bootstrap_ci, grade_case, run_metrics

EXPECTED = [{"file": "app/db.py", "line": 10, "category": "security", "severity": "high"}]


def finding(line: int, category: str = "security", file: str = "app/db.py") -> dict:
    return {
        "file": file,
        "line": line,
        "category": category,
        "severity": "high",
        "description": "x",
    }


def test_exact_match_is_true_positive():
    g = grade_case("c", EXPECTED, [finding(10)])
    assert (g.tp, g.fp, g.fn) == (1, 0, 0)


def test_line_within_tolerance_matches_outside_does_not():
    assert grade_case("c", EXPECTED, [finding(13)], tolerance=3).tp == 1
    g = grade_case("c", EXPECTED, [finding(14)], tolerance=3)
    assert (g.tp, g.fp, g.fn) == (0, 1, 1)


def test_wrong_file_never_matches():
    assert grade_case("c", EXPECTED, [finding(10, file="app/other.py")]).tp == 0


def test_duplicate_findings_count_as_false_positives():
    g = grade_case("c", EXPECTED, [finding(10), finding(11)])
    assert (g.tp, g.fp) == (1, 1)


def test_category_mismatch_still_detected_but_not_category_hit():
    g = grade_case("c", EXPECTED, [finding(10, category="correctness")])
    assert g.tp == 1 and g.category_hits == 0


def test_closest_finding_wins_one_to_one():
    expected = EXPECTED + [
        {"file": "app/db.py", "line": 12, "category": "security", "severity": "high"}
    ]
    g = grade_case("c", expected, [finding(11), finding(12)])
    assert (g.tp, g.fp, g.fn) == (2, 0, 0)


def test_b_prefix_normalized():
    assert grade_case("c", EXPECTED, [finding(10, file="b/app/db.py")]).tp == 1


def test_run_metrics_and_clean_false_alarm():
    grades = [grade_case("bug", EXPECTED, [finding(10)]), grade_case("clean", [], [finding(3)])]
    m = run_metrics(grades, clean_cases={"clean"})
    assert m["recall"] == 1.0 and m["precision"] == 0.5
    assert m["clean_false_alarm_rate"] == 1.0
    assert m["recall_by_category"] == {"security": 1.0}


def test_empty_findings_on_clean_case_has_undefined_precision_not_zero():
    m = run_metrics([grade_case("clean", [], [])], clean_cases={"clean"})
    assert m["precision"] is None and m["clean_false_alarm_rate"] == 0.0


def test_bootstrap_ci_brackets_point_estimate():
    by_case = {
        "a": [grade_case("a", EXPECTED, [finding(10)])],
        "b": [grade_case("b", EXPECTED, [])],
    }
    lo, hi = bootstrap_ci(by_case, "recall")
    assert lo <= 0.5 <= hi
