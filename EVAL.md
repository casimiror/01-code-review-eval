# EVAL.md

> Draft. Filled in as iterations run. Every number below cites a file in `results/`.

## What is measured

- **Unit**: one review of one diff. **Dataset**: N cases (M with defects, K clean). Each case runs R times.
- **Detection**: a finding matches an expected defect if same file and line within ±3 (one-to-one).
- **Metrics**: recall, precision, F1; clean false-alarm rate; category and severity accuracy on matches;
  contract failure rate; cost and latency. Mean ± std over runs, bootstrap 95% CI over cases.
- **Release gate** (proposed): recall ≥ 0.70, precision ≥ 0.70, clean false-alarm ≤ 0.25.

## Results

| Iteration | Change | Recall | Precision | Clean FA | Cost | File |
|---|---|---|---|---|---|---|
| 0 baseline | — | 1.00 ± 0.00 | 0.86 ± 0.00 | 0.00 | $0.46 (24 reviews) | `results/20261024-000728_baseline.json` |

## What I found

- **Baseline saturates**: 8 cases × 3 runs, recall 1.00 with zero run-to-run variance. The dataset is too
  easy to discriminate between reviewer versions; any change would look like "no effect". Next: harder and
  real-world cases before tuning the skill.
- **The only false positive is a labeling error**: in `005-hardcoded-secret` the reviewer also flags line 9
  (silent fallback to the prod token when the env var is unset) in 3/3 runs. That is a real second defect
  my `expected.json` omits. Precision 0.86 is therefore a dataset artifact, not reviewer noise.
- **Line attribution is imprecise**: `006` is reported at line 12 (`try` body) instead of 13 (`except`).
  With `--tolerance 0` this would be a miss + a false positive; the matching rule matters.
- **Skill name collision**: a skill called `code-review` silently loses to Claude Code's built-in one.
  Caught with a canary preflight that now runs before every eval.

## Iterations

### 0 — baseline
Hypothesis / change / result / conclusion.

## Where I would not trust this

- Small, synthetic dataset: authored bugs are cleaner than real ones (TODO: add real bug-fix commits).
- Matching by file+line ignores whether the description is the same bug (TODO: LLM-judge, validated by hand).
- One model, one CLI version; user-level config may leak in OAuth mode.
