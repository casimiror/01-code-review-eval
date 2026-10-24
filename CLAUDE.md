# Code Review Eval — CLAUDE.md

Take-home (Senior ML Engineer): a small AI code reviewer **and the eval that proves whether it
works**. The eval is what's graded: budget ~1/3 on the reviewer, ~2/3 on the eval and on what we
learn from running it. Deliverables: public repo, `EVAL.md` (1–2 pages), 4–6 min video.

## Layout

```
.claude/skills/diff-reviewer/SKILL.md   the reviewer (system under test): criteria + output contract
reviewer/contract.py                    output schema shared by reviewer and eval
reviewer/review.py                      headless runner: claude -p in an isolated temp workspace
eval/cases/NNN-name/                    before/ after/ (authored)  input.diff (generated)  expected.json
eval/make_diffs.py                      before/after -> input.diff
eval/grader.py                          matching rule + metrics + bootstrap CI
eval/run_eval.py                        K runs x N cases -> results/<ts>_<label>.json, release gate
eval/compare.py                         A vs B, flags deltas inside run-to-run noise
tests/                                  grader + dataset integrity tests (no LLM calls)
results/                                committed result files: the evidence for EVAL.md
```

## Commands

```bash
uv sync
make test                                   # free, run after touching grader or cases
make review DIFF=eval/cases/001-sql-injection/input.diff OUT=/tmp/f.json
make eval RUNS=3 LABEL=baseline             # costs money: ~$0.03 per review (sonnet)
make eval RUNS=1 CASES='00[1-3]*'           # cheap smoke run on a subset
make compare A=results/<a>.json B=results/<b>.json
```

## Rules

- `uv` only. Python 3.12.
- **Never change the grader and the skill in the same iteration.** Otherwise a delta can't be attributed.
  Record each iteration (hypothesis, change, result file, outcome) in `EVAL.md`.
- Result files are append-only evidence: never edit or delete one that EVAL.md cites.
- Adding a case: write `before/` and `after/`, `make diffs`, write `expected.json` with the line
  on the **new** side, `make test` (it checks the line is an added line). Keep ~25% clean cases.
- Case files are test data: excluded from ruff, never reformat them (it shifts expected lines).
- Don't leak answers: the reviewer runs in a temp dir with only the skill + `input.diff`.
  Don't add anything to that workspace that reveals `expected.json`.
- Interpret metrics with `std` and the bootstrap CI. With ~8–30 cases, a 0.05 change is usually noise.

## Gotchas found so far

- A project skill named `code-review` collides with Claude Code's built-in `/code-review`; ours is
  `diff-reviewer`. `run_eval` has a canary preflight that fails if SKILL.md isn't actually applied.
- `--bare` (skips hooks/plugins/CLAUDE.md) needs `ANTHROPIC_API_KEY`; with OAuth login we fall back
  to `--setting-sources project --strict-mcp-config`. User-level CLAUDE.md may still be loaded in
  that mode: a known confound to mention in EVAL.md.
- Line attribution is off by one sometimes (006: reports the `try` line, not the `except`): this is
  why the grader has a line tolerance. Measure how results change with `--tolerance 0/1/3`.
- Baseline (8 cases) saturates at recall 1.00: grow the dataset (harder + real bug-fix commits)
  before iterating on the skill. 005 has an unlabeled second defect (line 9) — fix the label as its
  own iteration so the precision change is attributable.
