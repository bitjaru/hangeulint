from __future__ import annotations

import json
import sys
from pathlib import Path

from hangeulint import verify_context


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    fixture_path = root / "benchmarks" / "context" / "fixtures" / "v0.jsonl"
    total = 0
    matched = 0
    failures: list[str] = []
    with fixture_path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            fixture = json.loads(line)
            report = verify_context(
                fixture["candidate"],
                fixture["contract"],
            )
            actual_findings = {finding.rule_id for finding in report.findings}
            expected_findings = set(fixture.get("expected_findings", []))
            expected_resolution = fixture.get("expected_actor_resolution")
            actual_resolution = (
                report.resolved_events[0].actor_resolution
                if report.resolved_events
                else None
            )
            total += 1
            passed = (
                report.status == fixture["expected_status"]
                and expected_findings.issubset(actual_findings)
                and (
                    expected_resolution is None
                    or expected_resolution == actual_resolution
                )
            )
            if passed:
                matched += 1
            else:
                failures.append(
                    f"{fixture['id']}: expected={fixture['expected_status']}/"
                    f"{sorted(expected_findings)}/{expected_resolution} "
                    f"actual={report.status}/{sorted(actual_findings)}/"
                    f"{actual_resolution}"
                )
    ratio = matched / total if total else 0.0
    print(f"context_fixtures={total} matched={matched} match_rate={ratio:.1%}")
    print("claim_scope=clean-room regression only; not population accuracy")
    for failure in failures:
        print(f"- {failure}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
