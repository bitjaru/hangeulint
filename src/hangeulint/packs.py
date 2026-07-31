from __future__ import annotations

import json
from dataclasses import dataclass
from importlib.resources import files
from typing import Any

from .evidence import validate_evidence_ids


@dataclass(frozen=True)
class Rule:
    rule_id: str
    kind: str
    dimension: str
    category: str
    severity: str
    confidence: str
    message: str
    suggestion: str
    pattern: str | None
    options: dict[str, Any]
    evidence_ids: tuple[str, ...]
    calibration: str
    failing_example: str
    passing_example: str


@dataclass(frozen=True)
class Pack:
    pack_id: str
    display_name: str
    version: str
    max_errors: int
    max_warnings: int
    ignored_section_prefixes: tuple[str, ...]
    rules: tuple[Rule, ...]


_PACK_IDS = ("social", "work-message")


def available_packs() -> tuple[str, ...]:
    return _PACK_IDS


def _read_pack(pack_id: str) -> dict[str, Any]:
    path = files("hangeulint").joinpath("packs", f"{pack_id}.json")
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_rule(raw: dict[str, Any]) -> Rule:
    examples = raw.get("examples", {})
    rule = Rule(
        rule_id=str(raw["id"]),
        kind=str(raw["kind"]),
        dimension=str(raw["dimension"]),
        category=str(raw["category"]),
        severity=str(raw.get("severity", "warning")),
        confidence=str(raw.get("confidence", "medium")),
        message=str(raw["message"]),
        suggestion=str(raw.get("suggestion", "")),
        pattern=raw.get("pattern"),
        options=dict(raw.get("options", {})),
        evidence_ids=tuple(str(value) for value in raw.get("evidence_ids", [])),
        calibration=str(raw.get("calibration", "heuristic")),
        failing_example=str(examples.get("fail", "")),
        passing_example=str(examples.get("pass", "")),
    )
    if not rule.rule_id or not rule.failing_example or not rule.passing_example:
        raise ValueError(
            f"rule은 안정적 ID와 fail/pass 예시가 필요합니다: {rule.rule_id}"
        )
    if rule.dimension not in {"naturalness", "register", "task_fit", "risk"}:
        raise ValueError(f"지원하지 않는 dimension: {rule.dimension}")
    if rule.severity not in {"error", "warning", "info"}:
        raise ValueError(f"지원하지 않는 severity: {rule.severity}")
    validate_evidence_ids(rule.evidence_ids)
    return rule


def load_pack(pack_id: str) -> Pack:
    if pack_id not in _PACK_IDS:
        choices = ", ".join(_PACK_IDS)
        raise ValueError(f"알 수 없는 pack: {pack_id}. 사용 가능: {choices}")

    common = _read_pack("common")
    selected = _read_pack(pack_id)
    raw_rules = [*common["rules"], *selected["rules"]]
    gate = selected.get("gate", {})
    return Pack(
        pack_id=pack_id,
        display_name=str(selected["display_name"]),
        version=str(selected["version"]),
        max_errors=int(gate.get("max_errors", 0)),
        max_warnings=int(gate.get("max_warnings", 2)),
        ignored_section_prefixes=tuple(selected.get("ignored_section_prefixes", [])),
        rules=tuple(_parse_rule(rule) for rule in raw_rules),
    )
