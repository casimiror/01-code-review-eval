# diff-reviewer + eval

A small AI code reviewer (a Claude Code skill) and an eval that turns "it seems to work" into
numbers a release can be gated on. Results and analysis: **[EVAL.md](EVAL.md)**.

## Requirements

- [uv](https://docs.astral.sh/uv/), git
- [Claude Code](https://docs.claude.com/en/docs/claude-code) CLI, logged in (or `ANTHROPIC_API_KEY` set, which enables `--bare`)
- [`gh`](https://cli.github.com/) CLI, authenticated (`gh auth login`) — only for `make review-pr` (reviewing a GitHub PR)

```bash
uv sync
```

## The reviewer

Input: a unified diff. Output: a JSON file with `[{file, line, severity, category, description}]`.

```bash
make review DIFF=eval/cases/001-sql-injection/input.diff OUT=findings.json
```

On a real pull request (needs the [`gh`](https://cli.github.com/) CLI) the same reviewer runs on
the PR diff; outputs go to `reviews/` (git-ignored):

```bash
make review-pr PR=3766 REPO=encode/httpx    # gh pr diff -> reviews/pr-3766.{diff,json}
make review-branch BASE=main                # current branch vs BASE
```

Interactively in Claude Code, `/diff-reviewer <path>` reviews that diff; with no path it defaults to
`git diff main...HEAD` (the current branch). The review criteria and output contract live in [`.claude/skills/diff-reviewer/SKILL.md`](.claude/skills/diff-reviewer/SKILL.md).
Headless invocation (what `reviewer/review.py` runs, from a temp dir containing only the skill and the diff):

```bash
claude -p "/diff-reviewer Review the diff in input.diff" \
  --model sonnet --output-format json --json-schema '<schema in reviewer/contract.py>' \
  --tools Read --allowedTools Read \
  --setting-sources project --strict-mcp-config --no-session-persistence
```

## The eval

```bash
make eval RUNS=3 LABEL=baseline     # -> results/<timestamp>_baseline.json, exit 1 if gate fails
make compare A=results/a.json B=results/b.json
make test                           # grader + dataset tests, no LLM calls
```

Each case is a code change with known defects (`expected.json`), or none. Two kinds:

- **Authored** (`001`–`008`): small `before/` and `after/` trees; `make diffs` builds `input.diff`.
- **Real** (`009`+): a real GitHub PR. `input.diff` is exactly what `make review-pr` would review,
  and `source.json` pins the repo, PR, base/head SHAs, the ground-truth source (advisory or a
  hand-verified repro), and the commands to re-fetch and re-review it. For example, `009` is
  Pillow PR #9208, which shipped the root cause of GHSA-v9pv-5gc8-w2m6:

  ```bash
  make review-pr PR=9208 REPO=python-pillow/Pillow   # what a reviewer would have seen at merge time
  ```

The eval runs every case K times, matches findings to expected defects (same file, line within ±3),
and reports recall, precision, F1, false alarms on clean diffs, category/severity accuracy, per-case
detection rate, cost and latency, with run-to-run std and a bootstrap CI over cases.
