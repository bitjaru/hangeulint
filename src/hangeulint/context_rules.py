from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from typing import Any

from .evidence import load_evidence


@dataclass(frozen=True)
class ContextRule:
    rule_id: str
    severity: str
    confidence: str
    description: str
    evidence_ids: tuple[str, ...]
    failing_example: str
    passing_example: str
    calibration: str


@lru_cache(maxsize=1)
def load_context_rules() -> dict[str, ContextRule]:
    resource = resources.files("hangeulint").joinpath("references/context-rules.json")
    payload: dict[str, Any] = json.loads(resource.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "0.1":
        raise ValueError("지원하지 않는 context rule registry schema입니다.")
    evidence = load_evidence()
    rules: dict[str, ContextRule] = {}
    for index, item in enumerate(payload.get("rules", [])):
        rule_id = item.get("id")
        if not isinstance(rule_id, str) or not rule_id:
            raise ValueError(f"context rules[{index}].id가 필요합니다.")
        if rule_id in rules:
            raise ValueError(f"중복 context rule id: {rule_id}")
        evidence_ids = tuple(item.get("evidence_ids", []))
        if not evidence_ids or not set(evidence_ids).issubset(evidence):
            raise ValueError(f"{rule_id}의 evidence ID가 유효하지 않습니다.")
        failing_example = item.get("failing_example")
        passing_example = item.get("passing_example")
        if not isinstance(failing_example, str) or not failing_example:
            raise ValueError(f"{rule_id}의 failing_example이 필요합니다.")
        if not isinstance(passing_example, str) or not passing_example:
            raise ValueError(f"{rule_id}의 passing_example이 필요합니다.")
        rules[rule_id] = ContextRule(
            rule_id=rule_id,
            severity=item["severity"],
            confidence=item["confidence"],
            description=item["description"],
            evidence_ids=evidence_ids,
            failing_example=failing_example,
            passing_example=passing_example,
            calibration=item.get("calibration", "contract_deterministic"),
        )
    if not rules:
        raise ValueError("context rule registry가 비어 있습니다.")
    return rules


def get_context_rule(rule_id: str) -> ContextRule:
    try:
        return load_context_rules()[rule_id]
    except KeyError as exc:
        raise ValueError(f"알 수 없는 context rule id: {rule_id}") from exc
