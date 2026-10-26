# EVAL.md

An eval for a diff-reviewer skill. Every number below cites a file in `results/`. The reviewer
(`.claude/skills/diff-reviewer/SKILL.md`) was **not changed** across any run here — its
`skill_sha256` is `ab8684b5` in all four result files — so every delta is attributable to the
dataset, not the system under test.

## What is measured

- **Unit**: one review of one diff. The reviewer sees only the diff (a temp workspace with just the
  skill + `input.diff`), so it cannot read the rest of the repo or the expected answers.
- **Dataset**: 11 cases. 8 authored small bugs (`001`–`008`), 2 real OSS pull requests
  (`009` Pillow, `010` httpx), 1 authored vulnerability demoed as a branch (`011`). 2 are clean
  (no defect) to measure false alarms. `source.json` tags each real case `github-pr` or
  `local-branch` so the real-world claim stays honest.
- **Detection rule**: a finding matches an expected defect when the file is the same and the line is
  within ±3 (one-to-one, closest first). Category/severity are **not** required to match — they are
  scored separately, so "found it but mislabeled it" is visible, not hidden.
- **Metrics**: recall, precision, F1; clean false-alarm rate; category/severity accuracy on matches;
  contract-failure rate; cost and latency. Reported as **mean ± std over K runs** (LLM output
  varies) with a **bootstrap 95% CI resampling cases** (the small-n uncertainty).
- **Release gate**: recall ≥ 0.70, precision ≥ 0.70, clean false-alarm ≤ 0.25. `run_eval` exits 1
  if it fails, so it can block CI.

## Results

| Iteration | Dataset | Recall | Precision | Clean FA | Gate | File |
|---|---|---|---|---|---|---|
| 0 baseline | 8 authored | 1.00 ± 0.00 | 0.86 ± 0.00 | 0.00 | PASS | `results/20261024-000728_baseline.json` |
| 1 real cases | 11 (8 + 2 OSS + 1 demo) | 0.89 ± 0.00 (CI 0.64–1.00) | 0.81 ± 0.08 (CI 0.64–1.00) | 0.17 | PASS | `results/20261026-155714_dataset-11.json` |

Smoke runs on the two OSS cases alone (`20261026-153854`, `20261026-154242`): recall 0.50,
precision 1.00 — i.e. 010 detected 3/3, 009 missed 0/3. All runs K=3, tolerance ±3, model sonnet.

## Iterations ("run it, change something, run it again")

### Iteration 0 — baseline
**Change**: 8 authored before/after cases, measured as-is.
**Result**: recall **1.00 ± 0.00** with zero run-to-run variance (`...baseline.json`).
**Conclusion**: the dataset is too easy to discriminate between reviewer versions — any future
change to the skill would read as "no effect". So the next move is the **dataset**, not the skill.

### Iteration 1 — add real-world cases
**Hypothesis**: authored bugs are cleaner than real ones; real diffs will lower recall and make the
eval discriminating.
**Change**: added `009` (Pillow PR #9208, the root cause of GHSA-v9pv-5gc8-w2m6), `010` (httpx PR
#3766, a `base_url` query bug verified by hand), `011` (an authored path traversal). Grader
unchanged.
**Result**: recall **1.00 → 0.89**, security recall **0.75**, driven entirely by `009`
(0/3 every run); `010` and `011` are 3/3 (`...dataset-11.json`).
**Conclusion**: the hypothesis holds — and the regression is the finding, not a failure. The eval
now separates "textbook bug in a tiny diff" from "real omission bug", which the baseline could not.

## What I found

- **Synthetic saturates, real code discriminates.** 1.00 on authored bugs, 0.89 once real code is
  in. The headline number is meaningless without saying which dataset produced it.
- **The one hard miss is structural, not noise.** `009` is missed 3/3. The diff only *adds* two
  lines that look like a fix (clear the cached buffer when the size changes). The real bug is an
  **omission**: it checks size but not mode. Seeing that requires knowing the native buffer is
  reused per-mode across frames — which lives in other files, outside the diff. A diff-only reviewer
  has nothing to latch onto. This is the hardest defect class (missing case) under the tightest
  context (diff only).
- **Precision is partly a labeling artifact.** `005` is flagged at line 9 every run (mean FP 1.0).
  That is a *real* second defect (silent fallback to a prod token) my `expected.json` omits, so the
  reported 0.81 understates true precision. Not yet fixed — see next steps.
- **One genuine false alarm on a clean case.** `007` (clean) gets a spurious finding in 1/3 runs;
  this is what the 0.17 clean false-alarm rate captures, and it is real reviewer noise, not labeling.
- **Category accuracy is perfect (1.00), severity is not (0.88).** When the reviewer finds a bug it
  names the category right; it sometimes over/under-rates severity.
- **Cost/latency**: ~$0.67 for 33 reviews; p50 7.1s, p95 14.0s.

## Where I would not trust this

- **Small n.** 11 cases, 2 clean. The bootstrap CI is wide (recall 0.64–1.00): a single case moves
  the number a lot. Treat these as directional, not precise.
- **Dataset is mostly authored.** Only 2 of 11 are bugs found in the wild; authored bugs are cleaner
  than real ones, so the true-world recall is likely **below** 0.89.
- **Matching is positional, not semantic.** file+line±3 can't tell whether the *description* names
  the same bug. A finding on the right line for the wrong reason counts as a hit.
- **Open PR can drift.** `010` is an open PR; `source.json` pins base/head, but the live PR may change.
- **Config confound.** With OAuth login (not `ANTHROPIC_API_KEY`), user-level CLAUDE.md may still
  load despite `--setting-sources project`. Running with an API key enables `--bare` and removes it.

## Next iterations (planned, one variable each)

1. **Fix the `005` label** (dataset-only): add the line-9 defect. Expect precision to rise toward
   1.00 — isolating that the 0.81 was an artifact.
2. **Give the reviewer file context** (skill/runner change): let it read the changed file, not just
   the diff, and measure whether `009` is detected **without** raising the clean false-alarm rate.
   This directly tests the "the evidence is outside the diff" explanation for the Pillow miss.
3. **Tolerance sensitivity**: re-grade the same findings at ±0/±1/±3 to quantify how much the line
   tolerance props up recall (no new LLM calls).
