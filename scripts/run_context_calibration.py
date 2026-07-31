from __future__ import annotations

import json
import sys
from pathlib import Path

from hangeulint.context_benchmark import (
    evaluate_context_benchmark,
    load_context_benchmark,
)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    dataset_path = root / "benchmarks" / "context" / "seed-v0.1.json"
    report = evaluate_context_benchmark(load_context_benchmark(dataset_path))
    summary = report["summary"]
    print(
        f"context_seed={summary['cases']} "
        f"fully_matched={summary['fully_matched']} "
        f"full_match_rate={summary['full_match_rate']:.1%}"
    )
    print(
        "finding_micro="
        f"precision:{summary['finding_micro_precision']:.1%}/"
        f"recall:{summary['finding_micro_recall']:.1%}"
    )
    print(
        "claim_readiness=" + json.dumps(report["claim_readiness"], ensure_ascii=False)
    )
    for case in report["cases"]:
        if not case["matched"]:
            print(
                f"- {case['case_id']}: "
                f"expected={case['expected_status']}/{case['expected_findings']}/"
                f"{case['expected_actor_resolution']} "
                f"actual={case['actual_status']}/{case['actual_findings']}/"
                f"{case['actual_actor_resolution']}"
            )
    print(
        "claim_scope=development seed regression; "
        "not calibrated Korean context accuracy"
    )
    return 0 if summary["fully_matched"] == summary["cases"] else 1


if __name__ == "__main__":
    sys.exit(main())
