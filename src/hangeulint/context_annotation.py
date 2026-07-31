from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from .context_rules import load_context_rules

_STATUSES = ("pass", "review", "fail")
_ACTOR_RESOLUTIONS = {
    "explicit",
    "mentioned",
    "inherited",
    "explicit_other",
    "inherited_other",
    "unresolved",
    "missing",
}


def validate_annotation_response(
    package: Mapping[str, Any],
    response: Mapping[str, Any],
) -> dict[str, Any]:
    if package.get("schema_version") != "0.1":
        raise ValueError("지원하지 않는 annotation package schema입니다.")
    if response.get("schema_version") != "0.1":
        raise ValueError("지원하지 않는 annotation response schema입니다.")
    if response.get("package_id") != package.get("package_id"):
        raise ValueError("annotation response의 package_id가 다릅니다.")
    rater_id = response.get("rater_id")
    if not isinstance(rater_id, str) or not rater_id.strip():
        raise ValueError("annotation response.rater_id가 필요합니다.")

    package_items = package.get("items")
    if not isinstance(package_items, list) or not package_items:
        raise ValueError("annotation package.items가 비어 있습니다.")
    expected_ids = {
        item.get("annotation_id") for item in package_items if isinstance(item, Mapping)
    }
    if len(expected_ids) != len(package_items) or None in expected_ids:
        raise ValueError("annotation package item ID가 유효하지 않습니다.")

    raw_items = response.get("items")
    if not isinstance(raw_items, list):
        raise ValueError("annotation response.items는 array여야 합니다.")
    seen: set[str] = set()
    normalized: list[dict[str, Any]] = []
    known_rules = set(load_context_rules())
    for index, item in enumerate(raw_items):
        scope = f"response.items[{index}]"
        if not isinstance(item, Mapping):
            raise ValueError(f"{scope}는 object여야 합니다.")
        annotation_id = item.get("annotation_id")
        if annotation_id not in expected_ids:
            raise ValueError(f"{scope}.annotation_id가 package에 없습니다.")
        if annotation_id in seen:
            raise ValueError(f"중복 annotation_id: {annotation_id}")
        seen.add(annotation_id)
        status = item.get("status")
        if status not in _STATUSES:
            raise ValueError(f"{scope}.status가 유효하지 않습니다.")
        finding_ids = item.get("finding_ids")
        if not isinstance(finding_ids, list) or not all(
            isinstance(rule_id, str) for rule_id in finding_ids
        ):
            raise ValueError(f"{scope}.finding_ids는 문자열 배열이어야 합니다.")
        if len(set(finding_ids)) != len(finding_ids):
            raise ValueError(f"{scope}.finding_ids에는 중복이 없어야 합니다.")
        unknown = sorted(set(finding_ids) - known_rules)
        if unknown:
            raise ValueError(
                f"{scope}.finding_ids에 알 수 없는 rule이 있습니다: {unknown}"
            )
        actor_resolution = item.get("actor_resolution")
        if actor_resolution not in _ACTOR_RESOLUTIONS:
            raise ValueError(f"{scope}.actor_resolution이 유효하지 않습니다.")
        rationale = item.get("rationale")
        if not isinstance(rationale, str) or not rationale.strip():
            raise ValueError(f"{scope}.rationale이 필요합니다.")
        normalized.append(
            {
                "annotation_id": annotation_id,
                "status": status,
                "finding_ids": sorted(finding_ids),
                "actor_resolution": actor_resolution,
                "rationale": rationale.strip(),
            }
        )
    missing = sorted(expected_ids - seen)
    if missing:
        raise ValueError(f"응답하지 않은 annotation item이 있습니다: {missing}")
    return {
        "schema_version": "0.1",
        "package_id": package["package_id"],
        "rater_id": rater_id.strip(),
        "items": normalized,
    }


def _fleiss_kappa(
    item_statuses: Sequence[Sequence[str]],
) -> float | None:
    if not item_statuses:
        return None
    raters = len(item_statuses[0])
    if raters < 2 or any(len(statuses) != raters for statuses in item_statuses):
        return None
    item_agreements: list[float] = []
    category_totals: Counter[str] = Counter()
    for statuses in item_statuses:
        counts = Counter(statuses)
        category_totals.update(counts)
        item_agreements.append(
            (sum(count * count for count in counts.values()) - raters)
            / (raters * (raters - 1))
        )
    observed = sum(item_agreements) / len(item_agreements)
    total_ratings = len(item_statuses) * raters
    expected = sum(
        (category_totals[status] / total_ratings) ** 2 for status in _STATUSES
    )
    if expected == 1:
        return 1.0 if observed == 1 else None
    return round((observed - expected) / (1 - expected), 4)


def aggregate_annotation_responses(
    package: Mapping[str, Any],
    responses: Sequence[Mapping[str, Any]],
    *,
    required_raters: int,
) -> dict[str, Any]:
    if required_raters < 2:
        raise ValueError("agreement 계산에는 required_raters가 2 이상이어야 합니다.")
    validated = [
        validate_annotation_response(package, response) for response in responses
    ]
    rater_ids = [response["rater_id"] for response in validated]
    if len(set(rater_ids)) != len(rater_ids):
        raise ValueError("같은 rater_id의 응답이 중복됐습니다.")

    item_ids = [item["annotation_id"] for item in package["items"]]
    by_rater = {
        response["rater_id"]: {
            item["annotation_id"]: item for item in response["items"]
        }
        for response in validated
    }
    items: list[dict[str, Any]] = []
    status_matrix: list[list[str]] = []
    for annotation_id in item_ids:
        votes = [by_rater[rater_id][annotation_id] for rater_id in sorted(by_rater)]
        statuses = [vote["status"] for vote in votes]
        finding_sets = [tuple(vote["finding_ids"]) for vote in votes]
        actor_resolutions = [vote["actor_resolution"] for vote in votes]
        status_counts = Counter(statuses)
        majority_status, majority_count = (
            status_counts.most_common(1)[0] if status_counts else (None, 0)
        )
        status_matrix.append(statuses)
        items.append(
            {
                "annotation_id": annotation_id,
                "completed_raters": len(votes),
                "status_votes": dict(sorted(status_counts.items())),
                "majority_status": majority_status,
                "majority_fraction": round(majority_count / len(votes), 4)
                if votes
                else 0.0,
                "unanimous_status": len(set(statuses)) == 1 and bool(statuses),
                "unanimous_finding_set": len(set(finding_sets)) == 1
                and bool(finding_sets),
                "unanimous_actor_resolution": len(set(actor_resolutions)) == 1
                and bool(actor_resolutions),
                "needs_adjudication": (
                    len(votes) < required_raters
                    or len(set(statuses)) != 1
                    or len(set(finding_sets)) != 1
                    or len(set(actor_resolutions)) != 1
                ),
            }
        )
    completed = len(validated)
    return {
        "schema_version": "0.1",
        "package_id": package["package_id"],
        "raters_received": completed,
        "required_raters": required_raters,
        "ready_for_adjudication": completed >= required_raters,
        "status_fleiss_kappa": _fleiss_kappa(status_matrix),
        "unanimous_status_rate": round(
            sum(item["unanimous_status"] for item in items) / len(items),
            4,
        ),
        "unanimous_finding_set_rate": round(
            sum(item["unanimous_finding_set"] for item in items) / len(items),
            4,
        ),
        "items_needing_adjudication": sum(item["needs_adjudication"] for item in items),
        "items": items,
    }
