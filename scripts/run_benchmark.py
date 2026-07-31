from __future__ import annotations

import json
import sys
from pathlib import Path

from hangeulint import analyze


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    fixture_paths = sorted((root / "benchmarks" / "fixtures").glob("*.jsonl"))
    total = 0
    correct = 0
    failures: list[str] = []
    for fixture_path in fixture_paths:
        with fixture_path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                fixture = json.loads(line)
                report = analyze(fixture["text"], fixture["pack"])
                expected = bool(fixture["expected_pass"])
                actual_rules = {finding.rule_id for finding in report.findings}
                expected_rules = set(fixture.get("expected_rules", []))
                forbidden_rules = set(fixture.get("forbidden_rules", []))
                total += 1
                passed = (
                    report.passed == expected
                    and expected_rules.issubset(actual_rules)
                    and not forbidden_rules.intersection(actual_rules)
                )
                if passed:
                    correct += 1
                else:
                    failures.append(
                        f"{fixture['id']}: expected_pass={expected} "
                        f"actual_pass={report.passed} rules={sorted(actual_rules)}"
                    )
    ratio = correct / total if total else 0.0
    print(f"regression_fixtures={total} matched={correct} match_rate={ratio:.1%}")
    print("claim_scope=regression-only; not authorship or population accuracy")
    for failure in failures:
        print(f"- {failure}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
