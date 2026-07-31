from __future__ import annotations

import re
from collections import Counter
from typing import Iterable

from .models import FidelityReport


_ANCHOR_PATTERNS = (
    ("url", re.compile(r"https?://[^\s)\]}>]+")),
    ("email", re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")),
    (
        "date",
        re.compile(
            r"(?<!\d)(?:\d{4}[./-]\d{1,2}[./-]\d{1,2}|"
            r"\d{1,2}월\s*\d{1,2}일)(?!\d)"
        ),
    ),
    (
        "time",
        re.compile(
            r"(?<!\d)(?:(?:오전|오후)\s*)?\d{1,2}시"
            r"(?:\s*\d{1,2}분)?|(?<!\d)\d{1,2}:\d{2}(?!\d)"
        ),
    ),
    (
        "identifier",
        re.compile(
            r"(?<![A-Za-z0-9_])[A-Z][A-Z0-9_-]{2,}"
            r"(?![A-Za-z0-9_-])"
        ),
    ),
    (
        "quantity",
        re.compile(
            r"(?<![\w])(?:₩|\$)?\d[\d,]*(?:\.\d+)?"
            r"(?:%|원|개|명|회|일|시간|분|초|GB|MB|KB|kg|g|cm|mm)"
        ),
    ),
    (
        "number",
        re.compile(r"(?<![\w])(?:₩|\$)?\d[\d,]*(?:\.\d+)?(?![\w])"),
    ),
)
_POLARITY_MARKERS = re.compile(
    r"(?:지\s*않|지\s*못|안\s+[가-힣]+|못\s+[가-힣]+|"
    r"불가(?:능)?|금지|제외|없(?:다|습니다|어요|음)|아니)"
)


def _normalize_anchor(kind: str, value: str) -> str:
    if kind == "date":
        numeric = re.fullmatch(
            r"(\d{4})[./-](\d{1,2})[./-](\d{1,2})",
            value,
        )
        if numeric:
            year, month, day = numeric.groups()
            return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
        korean = re.fullmatch(r"(\d{1,2})월\s*(\d{1,2})일", value)
        if korean:
            month, day = korean.groups()
            return f"{int(month):02d}-{int(day):02d}"
    if kind == "time":
        korean = re.fullmatch(
            r"(?:(오전|오후)\s*)?(\d{1,2})시(?:\s*(\d{1,2})분)?",
            value,
        )
        if korean:
            period, hour_text, minute_text = korean.groups()
            hour = int(hour_text)
            if period == "오후" and hour < 12:
                hour += 12
            if period == "오전" and hour == 12:
                hour = 0
            return f"{hour:02d}:{int(minute_text or 0):02d}"
        clock = re.fullmatch(r"(\d{1,2}):(\d{2})", value)
        if clock:
            hour, minute = clock.groups()
            return f"{int(hour):02d}:{int(minute):02d}"
    if kind in {"quantity", "number"}:
        return value.replace(",", "")
    return value


def _extract_by_type(
    text: str,
    protected_terms: Iterable[str] = (),
) -> dict[str, Counter[str]]:
    occupied: list[tuple[int, int]] = []
    typed: dict[str, Counter[str]] = {}
    protected = tuple(term for term in protected_terms if term)
    patterns = (
        (
            (
                "protected",
                re.compile("|".join(re.escape(term) for term in protected)),
            ),
        )
        if protected
        else ()
    )
    for kind, pattern in (*patterns, *_ANCHOR_PATTERNS):
        for match in pattern.finditer(text):
            span = match.span()
            if any(span[0] < end and start < span[1] for start, end in occupied):
                continue
            value = _normalize_anchor(kind, match.group(0).rstrip(".,"))
            typed.setdefault(kind, Counter())[value] += 1
            occupied.append(span)
    return typed


def extract_anchors(text: str) -> Counter[str]:
    anchors: Counter[str] = Counter()
    for values in _extract_by_type(text).values():
        anchors.update(values)
    return anchors


def _nested_dict(
    anchors: dict[str, Counter[str]],
) -> dict[str, dict[str, int]]:
    return {kind: dict(values) for kind, values in sorted(anchors.items()) if values}


def _subtract(
    left: dict[str, Counter[str]],
    right: dict[str, Counter[str]],
) -> dict[str, Counter[str]]:
    return {
        kind: values - right.get(kind, Counter())
        for kind, values in left.items()
        if values - right.get(kind, Counter())
    }


def compare_anchors(
    source: str,
    candidate: str,
    protected_terms: Iterable[str] = (),
) -> FidelityReport:
    source_anchors = _extract_by_type(source, protected_terms)
    candidate_anchors = _extract_by_type(candidate, protected_terms)
    missing = _subtract(source_anchors, candidate_anchors)
    added = _subtract(candidate_anchors, source_anchors)
    source_polarity = len(_POLARITY_MARKERS.findall(source))
    candidate_polarity = len(_POLARITY_MARKERS.findall(candidate))
    review_signals = ()
    if source_polarity != candidate_polarity:
        review_signals = (
            {
                "id": "fidelity.polarity-count-changed",
                "severity": "review",
                "source_count": source_polarity,
                "candidate_count": candidate_polarity,
                "message": "부정·불가 표현 수가 달라 의미 변화 여부를 확인해야 합니다.",
                "evidence_ids": ["HGL-REF-006", "HGL-REF-007"],
            },
        )
    failed = bool(missing or added)
    status = "fail" if failed else ("review" if review_signals else "pass")
    return FidelityReport(
        schema_version="1.0",
        status=status,
        passed=not failed,
        requires_review=bool(review_signals),
        source_anchors=_nested_dict(source_anchors),
        candidate_anchors=_nested_dict(candidate_anchors),
        missing=_nested_dict(missing),
        added=_nested_dict(added),
        review_signals=review_signals,
        limitations=(
            "정확히 일치하는 결정론적 앵커의 보존만 자동 판정합니다.",
            "부정 표현 변화는 검토 신호이며 문장 수준 의미 동등성을 판정하지 않습니다.",
            "인과·주체·주장의 추가/누락은 향후 semantic evaluator 범위입니다.",
        ),
    )
