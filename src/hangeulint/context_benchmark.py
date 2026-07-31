from __future__ import annotations

import json
import math
import random
from collections import Counter, defaultdict
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import __version__
from .context import ContextContract, load_context_contract, verify_context
from .context_rules import load_context_rules

_RELEASE_LEVELS = {
    "development_seed",
    "public_calibration",
    "private_holdout",
}
_SOURCE_KINDS = {
    "first_party_synthetic",
    "public_licensed",
    "customer_opt_in",
}
_STATUSES = {"pass", "review", "fail"}
_DATASET_KEYS = {
    "schema_version",
    "dataset_id",
    "release_level",
    "license",
    "annotation_policy",
    "contracts",
    "cases",
}
_POLICY_KEYS = {
    "required_raters",
    "adjudication_required",
    "blind_review",
    "pre_registered",
    "independent_holdout",
}
_CASE_KEYS = {
    "id",
    "domain",
    "phenomena",
    "contract_id",
    "source_context",
    "candidate",
    "source",
    "gold",
    "annotations",
}
_SOURCE_KEYS = {"kind", "license", "reference", "redistribution_allowed"}
_GOLD_KEYS = {"status", "finding_ids", "actor_resolution"}
_ANNOTATION_KEYS = {"completed_raters", "adjudicated", "agreement"}


def _required_string(payload: Mapping[str, Any], key: str, scope: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{scope}.{key}는 비어 있지 않은 문자열이어야 합니다.")
    return value.strip()


def _required_string_list(
    payload: Mapping[str, Any],
    key: str,
    scope: str,
) -> tuple[str, ...]:
    value = payload.get(key)
    if (
        not isinstance(value, list)
        or not value
        or not all(isinstance(item, str) and item.strip() for item in value)
    ):
        raise ValueError(f"{scope}.{key}는 비어 있지 않은 문자열 배열이어야 합니다.")
    normalized = tuple(dict.fromkeys(item.strip() for item in value))
    if len(normalized) != len(value):
        raise ValueError(f"{scope}.{key}에는 중복 값이 없어야 합니다.")
    return normalized


def _reject_unknown(
    payload: Mapping[str, Any],
    allowed: set[str],
    scope: str,
) -> None:
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise ValueError(f"{scope}에 알 수 없는 필드가 있습니다: {unknown}")


def load_context_benchmark(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return validate_context_benchmark(payload)


def validate_context_benchmark(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise ValueError("context benchmark는 JSON object여야 합니다.")
    _reject_unknown(payload, _DATASET_KEYS, "dataset")
    if payload.get("schema_version") != "0.1":
        raise ValueError("지원하지 않는 context benchmark schema_version입니다.")
    dataset_id = _required_string(payload, "dataset_id", "dataset")
    release_level = payload.get("release_level")
    if release_level not in _RELEASE_LEVELS:
        raise ValueError(
            f"dataset.release_level은 {sorted(_RELEASE_LEVELS)} 중 하나여야 합니다."
        )
    license_name = _required_string(payload, "license", "dataset")

    policy = payload.get("annotation_policy")
    if not isinstance(policy, Mapping):
        raise ValueError("dataset.annotation_policy는 object여야 합니다.")
    _reject_unknown(policy, _POLICY_KEYS, "dataset.annotation_policy")
    required_raters = policy.get("required_raters")
    if (
        not isinstance(required_raters, int)
        or isinstance(required_raters, bool)
        or required_raters < 1
    ):
        raise ValueError("annotation_policy.required_raters는 1 이상의 정수입니다.")
    adjudication_required = policy.get("adjudication_required")
    if not isinstance(adjudication_required, bool):
        raise ValueError("annotation_policy.adjudication_required는 boolean입니다.")
    blind_review = policy.get("blind_review")
    if not isinstance(blind_review, bool):
        raise ValueError("annotation_policy.blind_review는 boolean입니다.")
    pre_registered = policy.get("pre_registered")
    if not isinstance(pre_registered, bool):
        raise ValueError("annotation_policy.pre_registered는 boolean입니다.")
    independent_holdout = policy.get("independent_holdout")
    if not isinstance(independent_holdout, bool):
        raise ValueError("annotation_policy.independent_holdout은 boolean입니다.")

    raw_contracts = payload.get("contracts")
    if not isinstance(raw_contracts, list) or not raw_contracts:
        raise ValueError("dataset.contracts에는 하나 이상의 계약이 필요합니다.")
    contracts: dict[str, ContextContract] = {}
    normalized_contracts: list[dict[str, Any]] = []
    for index, raw_contract in enumerate(raw_contracts):
        if not isinstance(raw_contract, Mapping):
            raise ValueError(f"dataset.contracts[{index}]는 object여야 합니다.")
        contract = load_context_contract(raw_contract)
        if contract.contract_id in contracts:
            raise ValueError(f"중복 contract_id: {contract.contract_id}")
        contracts[contract.contract_id] = contract
        normalized_contracts.append(dict(raw_contract))

    known_rules = load_context_rules()
    raw_cases = payload.get("cases")
    if not isinstance(raw_cases, list) or not raw_cases:
        raise ValueError("dataset.cases에는 하나 이상의 case가 필요합니다.")
    case_ids: set[str] = set()
    normalized_cases: list[dict[str, Any]] = []
    for index, raw_case in enumerate(raw_cases):
        scope = f"dataset.cases[{index}]"
        if not isinstance(raw_case, Mapping):
            raise ValueError(f"{scope}는 object여야 합니다.")
        _reject_unknown(raw_case, _CASE_KEYS, scope)
        case_id = _required_string(raw_case, "id", scope)
        if case_id in case_ids:
            raise ValueError(f"중복 case id: {case_id}")
        case_ids.add(case_id)
        domain = _required_string(raw_case, "domain", scope)
        phenomena = _required_string_list(raw_case, "phenomena", scope)
        contract_id = _required_string(raw_case, "contract_id", scope)
        if contract_id not in contracts:
            raise ValueError(f"{scope}.contract_id가 알 수 없는 계약입니다.")
        source_context = _required_string(raw_case, "source_context", scope)
        candidate = _required_string(raw_case, "candidate", scope)

        source = raw_case.get("source")
        if not isinstance(source, Mapping):
            raise ValueError(f"{scope}.source는 object여야 합니다.")
        _reject_unknown(source, _SOURCE_KEYS, f"{scope}.source")
        source_kind = source.get("kind")
        if source_kind not in _SOURCE_KINDS:
            raise ValueError(
                f"{scope}.source.kind는 {sorted(_SOURCE_KINDS)} 중 하나여야 합니다."
            )
        source_license = _required_string(source, "license", f"{scope}.source")
        source_reference = _required_string(
            source,
            "reference",
            f"{scope}.source",
        )
        redistribution_allowed = source.get("redistribution_allowed")
        if not isinstance(redistribution_allowed, bool):
            raise ValueError(
                f"{scope}.source.redistribution_allowed는 boolean이어야 합니다."
            )
        if release_level == "public_calibration" and not redistribution_allowed:
            raise ValueError(
                f"public_calibration에는 재배포 불가 case를 넣을 수 없습니다: {case_id}"
            )

        gold = raw_case.get("gold")
        if not isinstance(gold, Mapping):
            raise ValueError(f"{scope}.gold는 object여야 합니다.")
        _reject_unknown(gold, _GOLD_KEYS, f"{scope}.gold")
        status = gold.get("status")
        if status not in _STATUSES:
            raise ValueError(f"{scope}.gold.status가 유효하지 않습니다.")
        finding_ids = gold.get("finding_ids")
        if not isinstance(finding_ids, list) or not all(
            isinstance(item, str) for item in finding_ids
        ):
            raise ValueError(f"{scope}.gold.finding_ids는 문자열 배열이어야 합니다.")
        if len(set(finding_ids)) != len(finding_ids):
            raise ValueError(f"{scope}.gold.finding_ids에는 중복이 없어야 합니다.")
        unknown_rules = sorted(set(finding_ids) - set(known_rules))
        if unknown_rules:
            raise ValueError(
                f"{scope}.gold에 알 수 없는 rule이 있습니다: {unknown_rules}"
            )
        actor_resolution = gold.get("actor_resolution")
        if actor_resolution is not None and not isinstance(actor_resolution, str):
            raise ValueError(f"{scope}.gold.actor_resolution은 문자열이어야 합니다.")

        annotations = raw_case.get("annotations")
        if not isinstance(annotations, Mapping):
            raise ValueError(f"{scope}.annotations는 object여야 합니다.")
        _reject_unknown(
            annotations,
            _ANNOTATION_KEYS,
            f"{scope}.annotations",
        )
        completed_raters = annotations.get("completed_raters")
        if (
            not isinstance(completed_raters, int)
            or isinstance(completed_raters, bool)
            or completed_raters < 0
        ):
            raise ValueError(
                f"{scope}.annotations.completed_raters는 0 이상의 정수입니다."
            )
        adjudicated = annotations.get("adjudicated")
        if not isinstance(adjudicated, bool):
            raise ValueError(f"{scope}.annotations.adjudicated는 boolean입니다.")
        agreement = annotations.get("agreement")
        if agreement is not None and (
            not isinstance(agreement, (int, float))
            or isinstance(agreement, bool)
            or not math.isfinite(agreement)
            or not 0 <= agreement <= 1
        ):
            raise ValueError(f"{scope}.annotations.agreement는 0~1 또는 null입니다.")

        normalized_cases.append(
            {
                "id": case_id,
                "domain": domain,
                "phenomena": list(phenomena),
                "contract_id": contract_id,
                "source_context": source_context,
                "candidate": candidate,
                "source": {
                    "kind": source_kind,
                    "license": source_license,
                    "reference": source_reference,
                    "redistribution_allowed": redistribution_allowed,
                },
                "gold": {
                    "status": status,
                    "finding_ids": list(finding_ids),
                    "actor_resolution": actor_resolution,
                },
                "annotations": {
                    "completed_raters": completed_raters,
                    "adjudicated": adjudicated,
                    "agreement": agreement,
                },
            }
        )

    return {
        "schema_version": "0.1",
        "dataset_id": dataset_id,
        "release_level": release_level,
        "license": license_name,
        "annotation_policy": {
            "required_raters": required_raters,
            "adjudication_required": adjudication_required,
            "blind_review": blind_review,
            "pre_registered": pre_registered,
            "independent_holdout": independent_holdout,
        },
        "contracts": normalized_contracts,
        "cases": normalized_cases,
    }


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def _slice_metrics(items: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "cases": len(items),
        "status_matches": sum(item["status_match"] for item in items),
        "status_match_rate": _rate(
            sum(item["status_match"] for item in items),
            len(items),
        ),
        "finding_exact_matches": sum(item["finding_exact"] for item in items),
        "finding_exact_match_rate": _rate(
            sum(item["finding_exact"] for item in items),
            len(items),
        ),
    }


def _claim_readiness(dataset: Mapping[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    cases = dataset["cases"]
    policy = dataset["annotation_policy"]
    if dataset["release_level"] != "public_calibration":
        blockers.append("release_level이 public_calibration이 아닙니다.")
    if not policy["blind_review"]:
        blockers.append("평가가 blind review로 설계되지 않았습니다.")
    if not policy["pre_registered"]:
        blockers.append("평가 protocol이 사전 등록되지 않았습니다.")
    if not policy["independent_holdout"]:
        blockers.append("독립 holdout 평가가 확인되지 않았습니다.")
    if len(cases) < 300:
        blockers.append(f"case가 300개 미만입니다: {len(cases)}")
    incomplete = sum(
        case["annotations"]["completed_raters"] < policy["required_raters"]
        for case in cases
    )
    if incomplete:
        blockers.append(f"필수 평가자 수를 못 채운 case가 있습니다: {incomplete}")
    if policy["adjudication_required"]:
        unadjudicated = sum(not case["annotations"]["adjudicated"] for case in cases)
        if unadjudicated:
            blockers.append(
                f"adjudication이 끝나지 않은 case가 있습니다: {unadjudicated}"
            )
    missing_agreement = sum(case["annotations"]["agreement"] is None for case in cases)
    if missing_agreement:
        blockers.append(f"평가자 합의도가 없는 case가 있습니다: {missing_agreement}")
    nonredistributable = sum(
        not case["source"]["redistribution_allowed"] for case in cases
    )
    if nonredistributable:
        blockers.append(f"재배포 불가 case가 있습니다: {nonredistributable}")
    return {
        "publishable": not blockers,
        "blockers": blockers,
        "required_case_count": 300,
        "required_raters": policy["required_raters"],
    }


def evaluate_context_benchmark(dataset: Mapping[str, Any]) -> dict[str, Any]:
    validated = validate_context_benchmark(dataset)
    contracts = {
        contract["contract_id"]: load_context_contract(contract)
        for contract in validated["contracts"]
    }
    results: list[dict[str, Any]] = []
    confusion: dict[str, Counter[str]] = defaultdict(Counter)
    finding_tp = 0
    finding_fp = 0
    finding_fn = 0
    for case in validated["cases"]:
        report = verify_context(
            case["candidate"],
            contracts[case["contract_id"]],
        )
        actual_findings = {finding.rule_id for finding in report.findings}
        expected_findings = set(case["gold"]["finding_ids"])
        actual_resolution = (
            report.resolved_events[0].actor_resolution
            if report.resolved_events
            else None
        )
        expected_resolution = case["gold"]["actor_resolution"]
        resolution_match = (
            expected_resolution is None or expected_resolution == actual_resolution
        )
        finding_tp += len(actual_findings & expected_findings)
        finding_fp += len(actual_findings - expected_findings)
        finding_fn += len(expected_findings - actual_findings)
        confusion[case["gold"]["status"]][report.status] += 1
        results.append(
            {
                "case_id": case["id"],
                "domain": case["domain"],
                "phenomena": case["phenomena"],
                "expected_status": case["gold"]["status"],
                "actual_status": report.status,
                "status_match": report.status == case["gold"]["status"],
                "expected_findings": sorted(expected_findings),
                "actual_findings": sorted(actual_findings),
                "finding_exact": actual_findings == expected_findings,
                "expected_actor_resolution": expected_resolution,
                "actual_actor_resolution": actual_resolution,
                "actor_resolution_match": resolution_match,
                "matched": (
                    report.status == case["gold"]["status"]
                    and actual_findings == expected_findings
                    and resolution_match
                ),
            }
        )

    by_domain: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_phenomenon: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in results:
        by_domain[result["domain"]].append(result)
        for phenomenon in result["phenomena"]:
            by_phenomenon[phenomenon].append(result)

    return {
        "schema_version": "0.1",
        "engine_version": __version__,
        "dataset_id": validated["dataset_id"],
        "release_level": validated["release_level"],
        "summary": {
            **_slice_metrics(results),
            "fully_matched": sum(item["matched"] for item in results),
            "full_match_rate": _rate(
                sum(item["matched"] for item in results),
                len(results),
            ),
            "finding_micro_precision": _rate(
                finding_tp,
                finding_tp + finding_fp,
            ),
            "finding_micro_recall": _rate(
                finding_tp,
                finding_tp + finding_fn,
            ),
        },
        "status_confusion": {
            expected: dict(sorted(actual.items()))
            for expected, actual in sorted(confusion.items())
        },
        "slices": {
            "domain": {
                name: _slice_metrics(items) for name, items in sorted(by_domain.items())
            },
            "phenomenon": {
                name: _slice_metrics(items)
                for name, items in sorted(by_phenomenon.items())
            },
        },
        "claim_readiness": _claim_readiness(validated),
        "cases": results,
        "claim_scope": (
            "development and calibration evidence only; not AI authorship detection"
        ),
    }


def build_annotation_package(
    dataset: Mapping[str, Any],
    *,
    seed: int,
) -> tuple[dict[str, Any], dict[str, str]]:
    validated = validate_context_benchmark(dataset)
    order = list(range(len(validated["cases"])))
    random.Random(seed).shuffle(order)
    items: list[dict[str, Any]] = []
    key: dict[str, str] = {}
    for display_index, case_index in enumerate(order, start=1):
        case = validated["cases"][case_index]
        annotation_id = f"item-{display_index:04d}"
        key[annotation_id] = case["id"]
        items.append(
            {
                "annotation_id": annotation_id,
                "domain": case["domain"],
                "task": next(
                    contract["task"]
                    for contract in validated["contracts"]
                    if contract["contract_id"] == case["contract_id"]
                ),
                "source_context": case["source_context"],
                "candidate": case["candidate"],
                "questions": {
                    "status": ["pass", "review", "fail"],
                    "finding_ids": sorted(load_context_rules()),
                    "actor_resolution": [
                        "explicit",
                        "mentioned",
                        "inherited",
                        "explicit_other",
                        "inherited_other",
                        "unresolved",
                        "missing",
                    ],
                    "rationale_required": True,
                },
            }
        )
    package = {
        "schema_version": "0.1",
        "engine_version": __version__,
        "package_id": f"{validated['dataset_id']}-blind-seed-{seed}",
        "dataset_id": validated["dataset_id"],
        "gold_included": False,
        "case_ids_included": False,
        "items": items,
    }
    return package, key
