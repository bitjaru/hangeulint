from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .analyzer import analyze
from .anchors import compare_anchors
from .context import load_context_contract, verify_context
from .context_benchmark import (
    evaluate_context_benchmark,
    load_context_benchmark,
)
from .edit_trace import build_edit_trace
from .evidence import load_evidence
from .packs import available_packs


def _read_text(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")


def _read_json(path: str) -> dict:
    payload = json.loads(_read_text(path))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON object가 필요합니다: {path}")
    return payload


def _print_human_report(report: dict, fidelity: dict | None = None) -> None:
    if not report["passed"] or (fidelity and not fidelity["passed"]):
        state = "FAIL"
    elif fidelity and fidelity["requires_review"]:
        state = "REVIEW"
    else:
        state = "PASS"
    print(
        f"{state}  {report['pack']}  "
        f"errors={report['gate']['errors']}/{report['gate']['max_errors']}  "
        f"warnings={report['gate']['warnings']}/{report['gate']['max_warnings']}"
    )
    dimensions = ", ".join(
        f"{name}={value['status']}" for name, value in report["dimensions"].items()
    )
    print(f"dimensions: {dimensions}")
    for finding in report["findings"]:
        print(
            f"- [{finding['severity']}/{finding['confidence']}] "
            f"{finding['rule_id']}: "
            f"{finding['message']}"
        )
        if finding["evidence"]:
            print(f"  evidence: {finding['evidence']}")
        if finding["suggestion"]:
            print(f"  fix: {finding['suggestion']}")
    if fidelity:
        fidelity_state = fidelity["status"].upper()
        print(f"{fidelity_state}  fidelity")
        if fidelity["missing"]:
            print(f"- missing anchors: {fidelity['missing']}")
        if fidelity["added"]:
            print(f"- added anchors: {fidelity['added']}")
        for signal in fidelity["review_signals"]:
            print(f"- [review] {signal['id']}: {signal['message']}")


def _print_context_report(report: dict) -> None:
    print(
        f"{report['status'].upper()}  context  "
        f"contract={report['contract_id']}  "
        f"errors={report['gate']['errors']}  "
        f"reviews={report['gate']['reviews']}"
    )
    for finding in report["findings"]:
        location = (
            f" sentence={finding['sentence_index']}"
            if finding["sentence_index"] is not None
            else ""
        )
        print(
            f"- [{finding['severity']}/{finding['confidence']}] "
            f"{finding['rule_id']} event={finding['event_id']}{location}: "
            f"{finding['message']}"
        )
        if finding["evidence"]:
            print(f"  evidence: {finding['evidence']}")
        if finding["expected"]:
            print(f"  expected: {finding['expected']}")
        if finding["observed"]:
            print(f"  observed: {finding['observed']}")
    for event in report["resolved_events"]:
        if event["sentence_index"] is None:
            continue
        actor = event["resolved_actor"] or "unknown"
        print(
            f"- [resolved] {event['event_id']}: "
            f"actor={actor}/{event['actor_resolution']} "
            f"sentence={event['sentence_index']}"
        )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hangeulint",
        description="ESLint for Korean AI output",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("packs", help="사용 가능한 유형 pack 목록")
    subparsers.add_parser("evidence", help="규칙 근거 자료 목록")

    check = subparsers.add_parser("check", help="한국어 출력 품질 검사")
    check.add_argument("path", help="검사할 UTF-8 텍스트 파일 또는 stdin(-)")
    check.add_argument("--pack", default="social", choices=available_packs())
    check.add_argument(
        "--morphology",
        default="none",
        choices=("none", "kiwi"),
        help="선택 형태소 텔레메트리 backend",
    )
    check.add_argument("--json", action="store_true", dest="as_json")

    compare = subparsers.add_parser(
        "compare",
        help="후보문 품질과 원문 앵커 보존 검사",
    )
    compare.add_argument("source", help="원문 파일")
    compare.add_argument("candidate", help="후보문 파일")
    compare.add_argument("--pack", default="social", choices=available_packs())
    compare.add_argument(
        "--morphology",
        default="none",
        choices=("none", "kiwi"),
        help="선택 형태소 텔레메트리 backend",
    )
    compare.add_argument(
        "--protect",
        action="append",
        default=[],
        help="원문-후보에서 반드시 보존할 용어(반복 지정 가능)",
    )
    compare.add_argument(
        "--strict-review",
        action="store_true",
        help="부정 표현 변화 같은 review 신호도 실패 처리",
    )
    compare.add_argument("--json", action="store_true", dest="as_json")

    context_check = subparsers.add_parser(
        "context-check",
        help="명시적 문맥 계약으로 주체·사건·시간·부정 연결 검사",
    )
    context_check.add_argument("contract", help="문맥 계약 JSON 파일")
    context_check.add_argument(
        "candidate",
        help="검사할 UTF-8 후보문 또는 stdin(-)",
    )
    context_check.add_argument(
        "--strict-review",
        action="store_true",
        help="생략 주체·부정 범위 같은 review 신호도 실패 처리",
    )
    context_check.add_argument("--json", action="store_true", dest="as_json")

    trace = subparsers.add_parser(
        "trace",
        help="원문-후보 편집을 로컬 KoEditTrace JSON으로 생성",
    )
    trace.add_argument("source", help="원문 파일")
    trace.add_argument("candidate", help="후보문 파일")
    trace.add_argument(
        "--decision",
        default="unreviewed",
        choices=(
            "unreviewed",
            "accepted",
            "rejected",
            "partially_accepted",
        ),
        help="사람이 명시한 후보문 채택 상태",
    )
    trace.add_argument(
        "--context-report",
        help="finding ID를 연결할 context-check JSON 결과",
    )

    context_benchmark = subparsers.add_parser(
        "context-benchmark",
        help="KoContextBench를 실행하고 도메인·현상 slice 평가",
    )
    context_benchmark.add_argument("dataset", help="KoContextBench JSON 파일")
    context_benchmark.add_argument("--json", action="store_true", dest="as_json")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "packs":
            for pack_id in available_packs():
                print(pack_id)
            return 0

        if args.command == "evidence":
            for item in load_evidence().values():
                print(f"{item.evidence_id}\t{item.year}\t{item.title}\t{item.url}")
            return 0

        if args.command == "check":
            report = analyze(
                _read_text(args.path),
                args.pack,
                args.morphology,
            ).to_dict()
            if args.as_json:
                print(json.dumps(report, ensure_ascii=False, indent=2))
            else:
                _print_human_report(report)
            return 0 if report["passed"] else 2

        if args.command == "context-check":
            contract = load_context_contract(_read_json(args.contract))
            report = verify_context(
                _read_text(args.candidate),
                contract,
            ).to_dict()
            gate_passed = report["passed"] and not (
                args.strict_review and report["requires_review"]
            )
            if args.as_json:
                payload = dict(report)
                payload["gate_passed"] = gate_passed
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                _print_context_report(report)
            return 0 if gate_passed else 2

        if args.command == "trace":
            context_report = (
                _read_json(args.context_report) if args.context_report else None
            )
            trace = build_edit_trace(
                _read_text(args.source),
                _read_text(args.candidate),
                decision=args.decision,
                context_report=context_report,
            ).to_dict()
            print(json.dumps(trace, ensure_ascii=False, indent=2))
            return 0

        if args.command == "context-benchmark":
            benchmark = evaluate_context_benchmark(load_context_benchmark(args.dataset))
            summary = benchmark["summary"]
            if args.as_json:
                print(json.dumps(benchmark, ensure_ascii=False, indent=2))
            else:
                print(
                    f"CONTEXT BENCH  {benchmark['dataset_id']}  "
                    f"matched={summary['fully_matched']}/{summary['cases']}  "
                    f"publishable={benchmark['claim_readiness']['publishable']}"
                )
                for domain, metrics in benchmark["slices"]["domain"].items():
                    print(
                        f"- domain={domain}: "
                        f"status={metrics['status_matches']}/{metrics['cases']} "
                        f"findings={metrics['finding_exact_matches']}/"
                        f"{metrics['cases']}"
                    )
                for blocker in benchmark["claim_readiness"]["blockers"]:
                    print(f"- claim blocker: {blocker}")
            return 0 if summary["fully_matched"] == summary["cases"] else 2

        source = _read_text(args.source)
        candidate = _read_text(args.candidate)
        report = analyze(candidate, args.pack, args.morphology).to_dict()
        fidelity = compare_anchors(
            source,
            candidate,
            args.protect,
        ).to_dict()
        fidelity_passed = fidelity["passed"] and not (
            args.strict_review and fidelity["requires_review"]
        )
        payload = {
            "passed": report["passed"] and fidelity_passed,
            "analysis": report,
            "fidelity": fidelity,
        }
        if args.as_json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            _print_human_report(report, fidelity)
        return 0 if payload["passed"] else 2
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"hangeulint: {exc}", file=sys.stderr)
        return 1
