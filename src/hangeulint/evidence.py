from __future__ import annotations

import json
from dataclasses import dataclass
from importlib.resources import files
from typing import Any


@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    title: str
    year: int
    url: str
    basis: str
    supports: tuple[str, ...]
    limitations: tuple[str, ...]
    artifact_license: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.evidence_id,
            "title": self.title,
            "year": self.year,
            "url": self.url,
            "basis": self.basis,
            "supports": list(self.supports),
            "limitations": list(self.limitations),
            "artifact_license": self.artifact_license,
        }


def load_evidence() -> dict[str, Evidence]:
    path = files("hangeulint").joinpath("references", "evidence.json")
    raw = json.loads(path.read_text(encoding="utf-8"))
    entries = {}
    for item in raw["evidence"]:
        evidence = Evidence(
            evidence_id=str(item["id"]),
            title=str(item["title"]),
            year=int(item["year"]),
            url=str(item["url"]),
            basis=str(item["basis"]),
            supports=tuple(str(value) for value in item["supports"]),
            limitations=tuple(str(value) for value in item["limitations"]),
            artifact_license=str(item["artifact_license"]),
        )
        if evidence.evidence_id in entries:
            raise ValueError(f"중복 evidence ID: {evidence.evidence_id}")
        entries[evidence.evidence_id] = evidence
    return entries


def validate_evidence_ids(evidence_ids: tuple[str, ...]) -> None:
    known = load_evidence()
    missing = sorted(set(evidence_ids) - set(known))
    if missing:
        raise ValueError(f"등록되지 않은 evidence ID: {', '.join(missing)}")
