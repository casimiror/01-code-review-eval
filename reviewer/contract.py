"""The output contract shared by the reviewer and the eval. Changing it changes both."""

from typing import Any

SEVERITIES = ("critical", "high", "medium", "low")
CATEGORIES = ("security", "correctness", "reliability", "performance")

FINDINGS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "file": {"type": "string"},
                    "line": {"type": "integer"},
                    "severity": {"type": "string", "enum": list(SEVERITIES)},
                    "category": {"type": "string", "enum": list(CATEGORIES)},
                    "description": {"type": "string"},
                },
                "required": ["file", "line", "severity", "category", "description"],
            },
        }
    },
    "required": ["findings"],
}


class ContractError(ValueError):
    pass


def validate_findings(payload: Any) -> list[dict]:
    """Return the findings list or raise ContractError with the first violation."""
    if not isinstance(payload, dict) or not isinstance(payload.get("findings"), list):
        raise ContractError('expected {"findings": [...]}')
    for i, f in enumerate(payload["findings"]):
        for key, typ in (
            ("file", str),
            ("line", int),
            ("severity", str),
            ("category", str),
            ("description", str),
        ):
            if not isinstance(f.get(key), typ):
                raise ContractError(f"finding {i}: {key!r} missing or not {typ.__name__}")
        if f["severity"] not in SEVERITIES:
            raise ContractError(f"finding {i}: bad severity {f['severity']!r}")
        if f["category"] not in CATEGORIES:
            raise ContractError(f"finding {i}: bad category {f['category']!r}")
    return payload["findings"]
