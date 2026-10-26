RUNS ?= 3
LABEL ?= run
MODEL ?= sonnet
CASES ?= *
BASE ?= main
REVIEWS ?= reviews

.PHONY: review review-pr review-branch eval compare diffs test lint

## Review one diff: make review DIFF=path/to.diff OUT=findings.json
review:
	uv run python -m reviewer.review --diff $(DIFF) --out $(OUT) --model $(MODEL)

## Review a GitHub PR by number or URL: make review-pr PR=123 [REPO=owner/repo]
review-pr:
	@mkdir -p $(REVIEWS)
	gh pr diff $(PR) $(if $(REPO),--repo $(REPO)) > $(REVIEWS)/pr-$(notdir $(PR)).diff
	$(MAKE) --no-print-directory review DIFF=$(REVIEWS)/pr-$(notdir $(PR)).diff OUT=$(REVIEWS)/pr-$(notdir $(PR)).json
	@cat $(REVIEWS)/pr-$(notdir $(PR)).json

## Review the current branch against BASE (default main): make review-branch [BASE=develop]
review-branch:
	@mkdir -p $(REVIEWS)
	git diff $(BASE)...HEAD > $(REVIEWS)/branch.diff
	$(MAKE) --no-print-directory review DIFF=$(REVIEWS)/branch.diff OUT=$(REVIEWS)/branch.json
	@cat $(REVIEWS)/branch.json

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
