from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

from . import __version__
from .models import EditOperation, EditTrace

_TOKEN = re.compile(r"\S+")
_DECISIONS = {"unreviewed", "accepted", "rejected", "partially_accepted"}


@dataclass(frozen=True)
class _TokenSpan:
    value: str
    start: int
    end: int


def _tokens(text: str) -> tuple[_TokenSpan, ...]:
    return tuple(
        _TokenSpan(match.group(0), match.start(), match.end())
        for match in _TOKEN.finditer(text)
    )


def _span(
    text: str,
    tokens: tuple[_TokenSpan, ...],
    start: int,
    end: int,
) -> tuple[int, int, str]:
    if start == end:
        position = tokens[start].start if start < len(tokens) else len(text)
        return position, position, ""
    char_start = tokens[start].start
    char_end = tokens[end - 1].end
    return char_start, char_end, text[char_start:char_end]


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_edit_trace(
    source: str,
    candidate: str,
    *,
    decision: str = "unreviewed",
    context_report: dict[str, Any] | None = None,
) -> EditTrace:
    if decision not in _DECISIONS:
        raise ValueError(f"지원하지 않는 edit decision: {decision}")
    source_tokens = _tokens(source)
    candidate_tokens = _tokens(candidate)
    matcher = SequenceMatcher(
        a=[token.value for token in source_tokens],
        b=[token.value for token in candidate_tokens],
        autojunk=False,
    )
    operations: list[EditOperation] = []
    for (
        tag,
        source_start,
        source_end,
        candidate_start,
        candidate_end,
    ) in matcher.get_opcodes():
        if tag == "equal":
            continue
        src_start, src_end, before = _span(
            source,
            source_tokens,
            source_start,
            source_end,
        )
        cand_start, cand_end, after = _span(
            candidate,
            candidate_tokens,
            candidate_start,
            candidate_end,
        )
        operations.append(
            EditOperation(
                edit_id=f"edit-{len(operations) + 1:03d}",
                operation=tag,
                before=before,
                after=after,
                source_span=(src_start, src_end),
                candidate_span=(cand_start, cand_end),
            )
        )

    finding_ids: tuple[str, ...] = ()
    contract_id: str | None = None
    if context_report is not None:
        raw_findings = context_report.get("findings", [])
        if not isinstance(raw_findings, list):
            raise ValueError("context report findings는 array여야 합니다.")
        ids: list[str] = []
        for index, finding in enumerate(raw_findings):
            if not isinstance(finding, dict) or not isinstance(
                finding.get("rule_id"),
                str,
            ):
                raise ValueError(
                    f"context report findings[{index}].rule_id가 필요합니다."
                )
            ids.append(finding["rule_id"])
        finding_ids = tuple(dict.fromkeys(ids))
        raw_contract_id = context_report.get("contract_id")
        if raw_contract_id is not None and not isinstance(raw_contract_id, str):
            raise ValueError("context report contract_id는 문자열이어야 합니다.")
        contract_id = raw_contract_id

    source_hash = _sha256(source)
    candidate_hash = _sha256(candidate)
    trace_hash = hashlib.sha256(f"{source_hash}:{candidate_hash}".encode()).hexdigest()
    contains_full_documents = any(
        (edit.before == source and bool(source))
        or (edit.after == candidate and bool(candidate))
        for edit in operations
    )
    return EditTrace(
        schema_version="0.1",
        engine_version=__version__,
        trace_id=f"ket-{trace_hash[:20]}",
        source_sha256=source_hash,
        candidate_sha256=candidate_hash,
        decision=decision,
        contract_id=contract_id,
        context_finding_ids=finding_ids,
        edits=tuple(operations),
        privacy={
            "persisted_by_core": False,
            "contains_full_documents": contains_full_documents,
            "contains_changed_text": bool(operations),
        },
        limitations=(
            "v0 diff는 공백 단위 토큰 변경이며 편집 이유를 자동 추론하지 않습니다.",
            "전체 교체 diff에서는 변경 구간이 전체 문서와 같을 수 있습니다.",
            "accepted 결정은 호출자가 제공하며 HangeuLint가 사람 승인을 추정하지 않습니다.",
        ),
    )
