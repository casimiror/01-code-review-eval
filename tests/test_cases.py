"""The dataset is part of the eval's code: a wrong expected line silently corrupts every metric."""

import json
import re

import pytest

from eval.make_diffs import CASES_DIR, make_diff
from reviewer.contract import CATEGORIES, SEVERITIES

CASES = sorted(p for p in CASES_DIR.iterdir() if p.is_dir())
HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def added_lines(diff: str) -> set[tuple[str, int]]:
    """(file, new-side line number) for every '+' line in a unified diff."""
    out, file, line = set(), None, 0
    for raw in diff.splitlines():
        if raw.startswith("+++ "):
            file = raw[4:].removeprefix("b/")
        elif m := HUNK.match(raw):
            line = int(m.group(1))
        elif raw.startswith("+"):
            out.add((file, line))
            line += 1
        elif raw.startswith(" "):
            line += 1
    return out


@pytest.mark.parametrize("case", CASES, ids=lambda p: p.name)
def test_diff_is_up_to_date(case):
    assert (case / "input.diff").read_text() == make_diff(case), "run: python -m eval.make_diffs"


@pytest.mark.parametrize("case", CASES, ids=lambda p: p.name)
def test_expected_points_at_an_added_line(case):
    added = added_lines((case / "input.diff").read_text())
    for e in json.loads((case / "expected.json").read_text()):
        assert e["category"] in CATEGORIES and e["severity"] in SEVERITIES
        assert (e["file"], e["line"]) in added, f"{e['file']}:{e['line']} is not a '+' line"
        assert (case / "after" / e["file"]).read_text().splitlines()[e["line"] - 1].strip()


def test_dataset_has_clean_cases():
    clean = [c for c in CASES if json.loads((c / "expected.json").read_text()) == []]
    assert clean, "without clean cases false alarms are unmeasured"
