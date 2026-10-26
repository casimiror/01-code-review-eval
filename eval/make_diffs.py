"""Regenerate every case's input.diff from its before/ and after/ trees.

    uv run python -m eval.make_diffs

Cases are authored as real file trees so line numbers in expected.json can be checked against
after/ (see tests/test_cases.py) instead of being counted by hand inside a diff.

Real-world cases have no before/after: their input.diff is the PR diff as fetched by the command in
source.json, so this script leaves them alone.
"""

import subprocess
from pathlib import Path

CASES_DIR = Path(__file__).resolve().parent / "cases"


def make_diff(case: Path) -> str:
    before = case / "before"
    before.mkdir(exist_ok=True)  # a case may only add files
    proc = subprocess.run(
        ["git", "diff", "--no-index", "--no-prefix", "--relative", "before", "after"],
        cwd=case,
        capture_output=True,
        text=True,
    )
    if proc.returncode not in (0, 1):  # 1 = differences found
        raise RuntimeError(proc.stderr)
    lines = []
    for line in proc.stdout.splitlines():
        if line.startswith("diff --git ") or line.startswith("index "):
            continue
        if line.startswith("--- "):
            path = line[4:]
            line = (
                "--- /dev/null" if path == "/dev/null" else f"--- a/{path.removeprefix('before/')}"
            )
        elif line.startswith("+++ "):
            line = f"+++ b/{line[4:].removeprefix('after/')}"
        lines.append(line)
    return "\n".join(lines) + "\n"


def authored_cases() -> list[Path]:
    return sorted(p for p in CASES_DIR.iterdir() if (p / "after").is_dir())


def main() -> None:
    for case in authored_cases():
        (case / "input.diff").write_text(make_diff(case))
        print(f"{case.name}: input.diff")


if __name__ == "__main__":
    main()
