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


@dataclass(frozen=True)
class ContextFinding:
    rule_id: str
    dimension: str
    severity: str
    confidence: str
    event_id: str
    sentence_index: int | None
    message: str
    evidence: str
    expected: str
    observed: str
    evidence_ids: tuple[str, ...]
    calibration: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["evidence_ids"] = list(self.evidence_ids)
        return payload


@dataclass(frozen=True)
class ResolvedEvent:
    event_id: str
    sentence_index: int | None
    sentence: str
    actor_resolution: str
    resolved_actor: str | None
    antecedent_sentence_index: int | None
    observed_polarity: str
    matched_terms: dict[str, list[str]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ContextReport:
    schema_version: str
    engine_version: str
    contract_id: str
    task: str
    status: str
    passed: bool
    requires_review: bool
    gate: dict[str, int]
    findings: tuple[ContextFinding, ...]
    resolved_events: tuple[ResolvedEvent, ...]
    metrics: dict[str, Any]
    limitations: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "engine_version": self.engine_version,
            "contract_id": self.contract_id,
            "task": self.task,
            "status": self.status,
            "passed": self.passed,
            "requires_review": self.requires_review,
            "gate": self.gate,
            "findings": [finding.to_dict() for finding in self.findings],
            "resolved_events": [event.to_dict() for event in self.resolved_events],
            "metrics": self.metrics,
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True)
class EditOperation:
    edit_id: str
    operation: str
    before: str
    after: str
    source_span: tuple[int, int]
    candidate_span: tuple[int, int]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["source_span"] = list(self.source_span)
        payload["candidate_span"] = list(self.candidate_span)
        return payload


@dataclass(frozen=True)
class EditTrace:
    schema_version: str
    engine_version: str
    trace_id: str
    source_sha256: str
    candidate_sha256: str
    decision: str
    contract_id: str | None
    context_finding_ids: tuple[str, ...]
    edits: tuple[EditOperation, ...]
    privacy: dict[str, bool]
    limitations: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "engine_version": self.engine_version,
            "trace_id": self.trace_id,
            "source_sha256": self.source_sha256,
            "candidate_sha256": self.candidate_sha256,
            "decision": self.decision,
            "contract_id": self.contract_id,
            "context_finding_ids": list(self.context_finding_ids),
            "edits": [edit.to_dict() for edit in self.edits],
            "privacy": self.privacy,
            "limitations": list(self.limitations),
        }
