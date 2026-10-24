# diff-reviewer + eval

A small AI code reviewer (a Claude Code skill) and an eval that turns "it seems to work" into
numbers a release can be gated on. Results and analysis: **[EVAL.md](EVAL.md)**.

## Requirements

- [uv](https://docs.astral.sh/uv/), git
- [Claude Code](https://docs.claude.com/en/docs/claude-code) CLI, logged in (or `ANTHROPIC_API_KEY` set, which enables `--bare`)

```bash
uv sync
```

## The reviewer

Input: a unified diff. Output: a JSON file with `[{file, line, severity, category, description}]`.

```bash
make review DIFF=eval/cases/001-sql-injection/input.diff OUT=findings.json
```

The review criteria and output contract live in [`.claude/skills/diff-reviewer/SKILL.md`](.claude/skills/diff-reviewer/SKILL.md).
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

Each case is a small before/after code change with known defects (`expected.json`), or none.
The eval runs every case K times, matches findings to expected defects (same file, line within ±3),
and reports recall, precision, F1, false alarms on clean diffs, category/severity accuracy, per-case
detection rate, cost and latency, with run-to-run std and a bootstrap CI over cases.
