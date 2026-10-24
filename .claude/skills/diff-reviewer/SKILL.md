---
name: diff-reviewer
description: Review a unified diff for real defects (security, correctness, reliability, performance) and return structured findings as JSON. Use when asked to review a diff or patch.
---

# Diff reviewer

You review a **unified diff** as a senior engineer would review a pull request. The diff file path
is given in the request; read it. Only the diff is available: do not look for other files.

## What to report

Report a finding only when you can name a concrete input or situation that makes the changed code
misbehave. Prefer missing a nit over reporting a non-issue.

Categories (use exactly one):
- `security` — injection, hardcoded secrets, missing authz checks, unsafe deserialization, path traversal.
- `correctness` — wrong result: off-by-one, wrong condition, missing `await`, null/None not handled, wrong variable.
- `reliability` — swallowed exceptions, leaked resources (files, connections), missing timeouts, race conditions.
- `performance` — N+1 queries, quadratic loops on unbounded input, repeated expensive work in a loop.

Do **not** report: style, naming, formatting, missing docs/tests, or issues in unchanged lines
(context lines starting with a space), unless the change makes them exploitable.

Severity:
- `critical` — exploitable security hole or data loss in normal use.
- `high` — wrong behavior or crash in a common path.
- `medium` — wrong behavior in an edge case, or resource/reliability problem under load.
- `low` — minor defect with limited impact.

## Locating the line

`line` is the line number **in the new version of the file** (the `+` side). Compute it from the
hunk header `@@ -a,b +c,d @@`: the first line after the header is line `c`; count context (` `) and
added (`+`) lines, skip removed (`-`) lines. Point at the line where the defect is, not the start of the function.
`file` is the path after `+++ b/`.

## Output contract

Return a JSON object and nothing else:

```json
{"findings": [{"file": "app/db.py", "line": 12, "severity": "high",
               "category": "security", "description": "One or two sentences: what breaks and how."}]}
```

If there are no defects, return `{"findings": []}`. An empty list is a valid, often correct answer.
