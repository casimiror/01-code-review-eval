"""Run the diff-reviewer skill headlessly on a diff and write findings JSON.

    uv run python -m reviewer.review --diff path/to/change.diff --out findings.json

The skill runs in a throwaway workspace that contains only the skill and the diff, so the
reviewer cannot see anything else (in particular the eval's expected answers) and user-level
Claude Code settings don't leak into results.
"""

import argparse
import json
import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from reviewer.contract import FINDINGS_SCHEMA, ContractError, validate_findings

ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / ".claude" / "skills" / "diff-reviewer"
DEFAULT_MODEL = "sonnet"


@dataclass
class ReviewResult:
    findings: list[dict]
    ok: bool
    error: str | None
    cost_usd: float | None
    duration_s: float


def build_command(model: str) -> list[str]:
    cmd = [
        "claude",
        "-p",
        "/diff-reviewer Review the diff in input.diff",
        "--model",
        model,
        "--output-format",
        "json",
        "--json-schema",
        json.dumps(FINDINGS_SCHEMA),
        "--tools",
        "Read",
        "--allowedTools",
        "Read",
        "--setting-sources",
        "project",
        "--strict-mcp-config",
        "--no-session-persistence",
    ]
    # --bare also skips hooks, plugins and CLAUDE.md discovery, but needs ANTHROPIC_API_KEY.
    if os.environ.get("ANTHROPIC_API_KEY"):
        cmd.append("--bare")
    return cmd


def _extract_payload(stdout: str) -> tuple[dict, dict]:
    envelope = json.loads(stdout)
    if envelope.get("is_error"):
        raise ContractError(f"claude error: {envelope.get('result')}")
    if isinstance(envelope.get("structured_output"), dict):
        return envelope["structured_output"], envelope
    text = (envelope.get("result") or "").strip().removeprefix("```json").removesuffix("```")
    return json.loads(text), envelope


def review(
    diff_text: str, model: str = DEFAULT_MODEL, timeout_s: int = 300, skill_dir: Path = SKILL_DIR
) -> ReviewResult:
    start = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="review-") as tmp:
        workspace = Path(tmp)
        shutil.copytree(skill_dir, workspace / ".claude" / "skills" / "diff-reviewer")
        (workspace / "input.diff").write_text(diff_text)
        try:
            proc = subprocess.run(
                build_command(model),
                cwd=workspace,
                capture_output=True,
                text=True,
                timeout=timeout_s,
            )
            payload, envelope = _extract_payload(proc.stdout)
            findings = validate_findings(payload)
            return ReviewResult(
                findings, True, None, envelope.get("total_cost_usd"), time.monotonic() - start
            )
        except (subprocess.TimeoutExpired, json.JSONDecodeError, ContractError, OSError) as e:
            # A contract failure is a result, not a crash: the eval counts it.
            return ReviewResult(
                [], False, f"{type(e).__name__}: {e}", None, time.monotonic() - start
            )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--diff", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    args = parser.parse_args()

    result = review(args.diff.read_text(), args.model)
    args.out.write_text(json.dumps(result.findings, indent=2))
    print(json.dumps({k: v for k, v in asdict(result).items() if k != "findings"}))
    raise SystemExit(0 if result.ok else 1)


if __name__ == "__main__":
    main()
