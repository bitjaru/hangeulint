from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from hangeulint.context_annotation import aggregate_annotation_responses


def _read_json(path: str) -> dict:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON object가 필요합니다: {path}")
    return payload


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="KoContextBench annotation 응답 합의도 계산",
    )
    parser.add_argument("package", help="블라인드 annotation package JSON")
    parser.add_argument("responses", nargs="+", help="평가자별 response JSON")
    parser.add_argument("--required-raters", type=int, default=3)
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        report = aggregate_annotation_responses(
            _read_json(args.package),
            [_read_json(path) for path in args.responses],
            required_raters=args.required_raters,
        )
        if args.as_json:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            print(
                f"raters={report['raters_received']}/"
                f"{report['required_raters']} "
                f"ready={report['ready_for_adjudication']}"
            )
            print(f"status_fleiss_kappa={report['status_fleiss_kappa']}")
            print(
                "unanimous="
                f"status:{report['unanimous_status_rate']:.1%}/"
                f"findings:{report['unanimous_finding_set_rate']:.1%}"
            )
            print(f"items_needing_adjudication={report['items_needing_adjudication']}")
        return 0
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"score-context-annotations: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
