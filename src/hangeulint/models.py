from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class Finding:
    rule_id: str
    dimension: str
    category: str
    severity: str
    confidence: str
    message: str
    evidence: str
    occurrences: int = 1
    suggestion: str = ""
    evidence_ids: tuple[str, ...] = ()
    calibration: str = "heuristic"

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["evidence_ids"] = list(self.evidence_ids)
        return payload


@dataclass(frozen=True)
class AnalysisReport:
    schema_version: str
    engine_version: str
    pack: str
    pack_version: str
    passed: bool
    gate: dict[str, int | bool]
    dimensions: dict[str, dict[str, int | str]]
    findings: tuple[Finding, ...]
    metrics: dict[str, Any]
    limitations: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "engine_version": self.engine_version,
            "pack": self.pack,
            "pack_version": self.pack_version,
            "passed": self.passed,
            "gate": self.gate,
            "dimensions": self.dimensions,
            "findings": [finding.to_dict() for finding in self.findings],
            "metrics": self.metrics,
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True)
class FidelityReport:
    schema_version: str
    status: str
    passed: bool
    requires_review: bool
    source_anchors: dict[str, dict[str, int]]
    candidate_anchors: dict[str, dict[str, int]]
    missing: dict[str, dict[str, int]]
    added: dict[str, dict[str, int]]
    review_signals: tuple[dict[str, Any], ...]
    limitations: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["review_signals"] = list(self.review_signals)
        payload["limitations"] = list(self.limitations)
        return payload
