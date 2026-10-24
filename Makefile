RUNS ?= 3
LABEL ?= run
MODEL ?= sonnet
CASES ?= *

.PHONY: review eval compare diffs test lint

## Review one diff: make review DIFF=path/to.diff OUT=findings.json
review:
	uv run python -m reviewer.review --diff $(DIFF) --out $(OUT) --model $(MODEL)

## Full eval -> results/<timestamp>_<label>.json (exit 1 if the release gate fails)
eval:
	uv run python -m eval.run_eval --runs $(RUNS) --label $(LABEL) --model $(MODEL) --cases '$(CASES)'

## Compare two result files: make compare A=results/x.json B=results/y.json
compare:
	uv run python -m eval.compare $(A) $(B)

## Regenerate input.diff for every case from before/ and after/
diffs:
	uv run python -m eval.make_diffs

## Unit tests for the grader and the dataset (no LLM calls)
test:
	uv run pytest -q

lint:
	uv run ruff check . && uv run ruff format --check .
