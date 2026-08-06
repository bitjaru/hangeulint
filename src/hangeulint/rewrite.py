from __future__ import annotations

import hashlib
import re
import unicodedata
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

from . import __version__
from .analyzer import analyze
from .anchors import compare_anchors
from .context import ContextContract, verify_context
from .models import (
    CandidatePairMetric,
    DiversityFinding,
    DiversityReport,
    RewriteCandidateEvaluation,
    RewriteCandidateSetReport,
)
from .rewrite_rules import get_rewrite_rule
from .surface import sentences

_SET_KEYS = {"schema_version", "set_id", "candidates"}
_CANDIDATE_KEYS = {"id", "text", "strategy", "hypothesis_ids", "generator"}
_GENERATOR_KEYS = {"kind", "provider", "model", "prompt_version", "seed"}
_GENERATOR_KINDS = {"model", "human", "unknown"}
_TOKEN_RE = re.compile(r"[가-힣]+|[A-Za-z]+|\d+(?:[.,]\d+)*")
_SPACE_RE = re.compile(r"\s+")
_NON_WORD_RE = re.compile(r"[^0-9a-z가-힣]+")
_NEAR_TOKEN_THRESHOLD = 0.82
_NEAR_CHAR_THRESHOLD = 0.80
_MIN_NEAR_CHARS = 20


@dataclass(frozen=True)
class RewriteCandidate:
    candidate_id: str
    text: str
    strategy: str
    hypothesis_ids: tuple[str, ...]
    generator: dict[str, Any]


def _reject_unknown(payload: Mapping[str, Any], allowed: set[str], scope: str) -> None:
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise ValueError(f"{scope}에 알 수 없는 필드가 있습니다: {unknown}")


def _required_string(payload: Mapping[str, Any], key: str, scope: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{scope}.{key}는 비어 있지 않은 문자열이어야 합니다.")
    return value.strip()


def load_rewrite_candidate_set(
    payload: Mapping[str, Any],
) -> tuple[str, tuple[RewriteCandidate, ...]]:
    if not isinstance(payload, Mapping):
        raise ValueError("rewrite candidate set은 JSON object여야 합니다.")
    _reject_unknown(payload, _SET_KEYS, "candidate_set")
    schema_version = _required_string(payload, "schema_version", "candidate_set")
    if schema_version != "0.1":
        raise ValueError(
            f"지원하지 않는 rewrite candidate set schema_version: {schema_version}"
        )
    set_id = _required_string(payload, "set_id", "candidate_set")
    raw_candidates = payload.get("candidates")
    if not isinstance(raw_candidates, list) or not raw_candidates:
        raise ValueError("candidate_set.candidates에는 하나 이상의 후보가 필요합니다.")

    candidates: list[RewriteCandidate] = []
    candidate_ids: set[str] = set()
    for index, raw_candidate in enumerate(raw_candidates):
        scope = f"candidate_set.candidates[{index}]"
        if not isinstance(raw_candidate, Mapping):
            raise ValueError(f"{scope}는 object여야 합니다.")
        _reject_unknown(raw_candidate, _CANDIDATE_KEYS, scope)
        candidate_id = _required_string(raw_candidate, "id", scope)
        if candidate_id in candidate_ids:
            raise ValueError(f"중복 candidate id: {candidate_id}")
        candidate_ids.add(candidate_id)
        text = _required_string(raw_candidate, "text", scope)
        strategy = _required_string(raw_candidate, "strategy", scope)

        raw_hypotheses = raw_candidate.get("hypothesis_ids", [])
        if not isinstance(raw_hypotheses, list) or not all(
            isinstance(item, str) and item.strip() for item in raw_hypotheses
        ):
            raise ValueError(f"{scope}.hypothesis_ids는 문자열 배열이어야 합니다.")
        hypothesis_ids = tuple(dict.fromkeys(item.strip() for item in raw_hypotheses))

        raw_generator = raw_candidate.get("generator")
        if not isinstance(raw_generator, Mapping):
            raise ValueError(f"{scope}.generator는 object여야 합니다.")
        _reject_unknown(raw_generator, _GENERATOR_KEYS, f"{scope}.generator")
        kind = _required_string(raw_generator, "kind", f"{scope}.generator")
        if kind not in _GENERATOR_KINDS:
            raise ValueError(f"지원하지 않는 generator kind: {kind}")
        provider = _required_string(raw_generator, "provider", f"{scope}.generator")
        model = _required_string(raw_generator, "model", f"{scope}.generator")
        prompt_version = _required_string(
            raw_generator, "prompt_version", f"{scope}.generator"
        )
        seed = raw_generator.get("seed")
        if seed is not None and (not isinstance(seed, int) or isinstance(seed, bool)):
            raise ValueError(f"{scope}.generator.seed는 정수 또는 null이어야 합니다.")

        candidates.append(
            RewriteCandidate(
                candidate_id=candidate_id,
                text=text,
                strategy=strategy,
                hypothesis_ids=hypothesis_ids,
                generator={
                    "kind": kind,
                    "provider": provider,
                    "model": model,
                    "prompt_version": prompt_version,
                    "seed": seed,
                },
            )
        )
    return set_id, tuple(candidates)


def _normalized_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).lower()
    return _NON_WORD_RE.sub("", normalized)


def _tokens(text: str) -> set[str]:
    normalized = unicodedata.normalize("NFKC", text).lower()
    return set(_TOKEN_RE.findall(normalized))


def _char_ngrams(text: str, size: int = 3) -> set[str]:
    normalized = _normalized_text(text)
    if not normalized:
        return set()
    if len(normalized) < size:
        return {normalized}
    return {
        normalized[index : index + size] for index in range(len(normalized) - size + 1)
    }


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left and not right:
        return 1.0
    union = left | right
    return len(left & right) / len(union) if union else 0.0


def _pair_metric(
    left: RewriteCandidate, right: RewriteCandidate
) -> CandidatePairMetric:
    return CandidatePairMetric(
        left_candidate_id=left.candidate_id,
        right_candidate_id=right.candidate_id,
        normalized_equal=_normalized_text(left.text) == _normalized_text(right.text),
        token_jaccard=round(_jaccard(_tokens(left.text), _tokens(right.text)), 4),
        char_3gram_jaccard=round(
            _jaccard(_char_ngrams(left.text), _char_ngrams(right.text)), 4
        ),
    )


def _is_near_duplicate(pair: CandidatePairMetric, lengths: tuple[int, int]) -> bool:
    return (
        min(lengths) >= _MIN_NEAR_CHARS
        and pair.token_jaccard >= _NEAR_TOKEN_THRESHOLD
        and pair.char_3gram_jaccard >= _NEAR_CHAR_THRESHOLD
    )


def _diversity_finding(
    rule_id: str,
    candidate_ids: tuple[str, ...],
    evidence: str,
) -> DiversityFinding:
    rule = get_rewrite_rule(rule_id)
    return DiversityFinding(
        rule_id=rule_id,
        severity=rule.severity,
        confidence=rule.confidence,
        candidate_ids=candidate_ids,
        message=rule.description,
        evidence=evidence,
        evidence_ids=rule.evidence_ids,
        calibration=rule.calibration,
    )


def analyze_diversity(
    candidates: Sequence[RewriteCandidate],
    recent_outputs: Sequence[str] = (),
) -> DiversityReport:
    candidate_ids = tuple(candidate.candidate_id for candidate in candidates)
    pairs: list[CandidatePairMetric] = []
    findings: list[DiversityFinding] = []
    exact_pairs = 0
    normalized_pairs = 0
    near_pairs = 0

    for left_index, left in enumerate(candidates):
        for right in candidates[left_index + 1 :]:
            pair = _pair_metric(left, right)
            pairs.append(pair)
            exact = left.text == right.text
            normalized = pair.normalized_equal
            near = _is_near_duplicate(
                pair,
                (len(_normalized_text(left.text)), len(_normalized_text(right.text))),
            )
            exact_pairs += int(exact)
            normalized_pairs += int(normalized)
            near_pairs += int(near and not normalized)
            if exact:
                findings.append(
                    _diversity_finding(
                        "rewrite.candidate-exact-duplicate",
                        (left.candidate_id, right.candidate_id),
                        "exact_match=true",
                    )
                )
            elif normalized:
                findings.append(
                    _diversity_finding(
                        "rewrite.candidate-normalized-duplicate",
                        (left.candidate_id, right.candidate_id),
                        "normalized_match=true",
                    )
                )
            elif near:
                findings.append(
                    _diversity_finding(
                        "rewrite.candidate-near-duplicate",
                        (left.candidate_id, right.candidate_id),
                        (
                            f"token_jaccard={pair.token_jaccard},"
                            f"char_3gram_jaccard={pair.char_3gram_jaccard}"
                        ),
                    )
                )

    recent_exact = 0
    recent_near = 0
    max_recent_token = 0.0
    max_recent_char = 0.0
    for candidate in candidates:
        for recent_index, recent in enumerate(recent_outputs):
            recent_candidate = RewriteCandidate(
                candidate_id=f"recent-{recent_index + 1:03d}",
                text=recent,
                strategy="history",
                hypothesis_ids=(),
                generator={},
            )
            pair = _pair_metric(candidate, recent_candidate)
            max_recent_token = max(max_recent_token, pair.token_jaccard)
            max_recent_char = max(max_recent_char, pair.char_3gram_jaccard)
            normalized = pair.normalized_equal
            near = _is_near_duplicate(
                pair,
                (len(_normalized_text(candidate.text)), len(_normalized_text(recent))),
            )
            if normalized:
                recent_exact += 1
                findings.append(
                    _diversity_finding(
                        "rewrite.recent-output-duplicate",
                        (candidate.candidate_id,),
                        f"recent_output_index={recent_index}",
                    )
                )
            elif near:
                recent_near += 1
                findings.append(
                    _diversity_finding(
                        "rewrite.recent-output-near-duplicate",
                        (candidate.candidate_id,),
                        (
                            f"recent_output_index={recent_index},"
                            f"token_jaccard={pair.token_jaccard},"
                            f"char_3gram_jaccard={pair.char_3gram_jaccard}"
                        ),
                    )
                )

    strategies = Counter(candidate.strategy for candidate in candidates)
    if len(candidates) > 1 and len(strategies) == 1:
        findings.append(
            _diversity_finding(
                "rewrite.strategy-collapse",
                candidate_ids,
                f"strategy_count=1,candidate_count={len(candidates)}",
            )
        )

    requires_review = any(finding.severity == "review" for finding in findings)
    if len(candidates) < 2 and not recent_outputs:
        status = "not_evaluated"
    elif requires_review:
        status = "review"
    else:
        status = "observed"
    max_pair_token = max((pair.token_jaccard for pair in pairs), default=0.0)
    max_pair_char = max((pair.char_3gram_jaccard for pair in pairs), default=0.0)
    return DiversityReport(
        schema_version="0.1",
        engine_version=__version__,
        status=status,
        requires_review=requires_review,
        candidate_ids=candidate_ids,
        findings=tuple(findings),
        pairwise=tuple(pairs),
        metrics={
            "candidate_count": len(candidates),
            "recent_output_count": len(recent_outputs),
            "pair_count": len(pairs),
            "unique_normalized_candidates": len(
                {_normalized_text(candidate.text) for candidate in candidates}
            ),
            "unique_strategies": len(strategies),
            "exact_duplicate_pairs": exact_pairs,
            "normalized_equal_pairs": normalized_pairs,
            "near_duplicate_pairs": near_pairs,
            "recent_exact_matches": recent_exact,
            "recent_near_matches": recent_near,
            "max_pair_token_jaccard": round(max_pair_token, 4),
            "max_pair_char_3gram_jaccard": round(max_pair_char, 4),
            "max_recent_token_jaccard": round(max_recent_token, 4),
            "max_recent_char_3gram_jaccard": round(max_recent_char, 4),
        },
        privacy={
            "persisted_by_core": False,
            "contains_candidate_text": False,
            "contains_recent_output_text": False,
        },
        limitations=(
            "문자·어휘 유사도는 의미·구문 다양성을 완전히 평가하지 않습니다.",
            "near-duplicate 임계값은 한국어 유형별 사람 평가로 보정되지 않았습니다.",
            "단일 문장보다 후보 묶음과 최근 출력 묶음에서 해석해야 합니다.",
        ),
    )


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _change_rate(source: str, candidate: str) -> float:
    left = _SPACE_RE.sub(" ", unicodedata.normalize("NFKC", source)).strip()
    right = _SPACE_RE.sub(" ", unicodedata.normalize("NFKC", candidate)).strip()
    return round(1.0 - SequenceMatcher(a=left, b=right, autojunk=False).ratio(), 4)


def _sentence_touch_rate(source: str, candidate: str) -> float:
    source_sentences = [
        _SPACE_RE.sub(" ", sentence).strip()
        for sentence in sentences(source)
        if sentence
    ]
    if not source_sentences:
        return 0.0
    candidate_sentences = {
        _SPACE_RE.sub(" ", sentence).strip()
        for sentence in sentences(candidate)
        if sentence
    }
    touched = sum(sentence not in candidate_sentences for sentence in source_sentences)
    return round(touched / len(source_sentences), 4)


def evaluate_rewrite_candidates(
    source: str,
    set_id: str,
    candidates: Sequence[RewriteCandidate],
    *,
    pack_id: str = "social",
    morphology: str | None = None,
    protected_terms: Iterable[str] = (),
    context_contract: ContextContract | None = None,
    recent_outputs: Sequence[str] = (),
    strict_review: bool = False,
    strict_diversity: bool = False,
) -> RewriteCandidateSetReport:
    if not source.strip():
        raise ValueError("rewrite source는 비어 있을 수 없습니다.")
    if not set_id.strip():
        raise ValueError("rewrite set_id는 비어 있을 수 없습니다.")
    if not candidates:
        raise ValueError("하나 이상의 rewrite candidate가 필요합니다.")
    candidate_ids = [candidate.candidate_id for candidate in candidates]
    if len(candidate_ids) != len(set(candidate_ids)):
        raise ValueError("rewrite candidate id는 중복될 수 없습니다.")

    evaluations: list[RewriteCandidateEvaluation] = []
    eligible_candidates: list[RewriteCandidate] = []
    for candidate in candidates:
        analysis = analyze(candidate.text, pack_id, morphology)
        fidelity = compare_anchors(source, candidate.text, protected_terms)
        context = (
            verify_context(candidate.text, context_contract)
            if context_contract is not None
            else None
        )
        hard_failed = (
            not analysis.passed
            or not fidelity.passed
            or (context is not None and not context.passed)
        )
        requires_review = fidelity.requires_review or bool(
            context is not None and context.requires_review
        )
        eligible = not hard_failed and not (strict_review and requires_review)
        if hard_failed:
            status = "rejected"
        elif requires_review:
            status = "review"
        else:
            status = "eligible"
        if eligible:
            eligible_candidates.append(candidate)
        evaluations.append(
            RewriteCandidateEvaluation(
                candidate_id=candidate.candidate_id,
                strategy=candidate.strategy,
                hypothesis_ids=candidate.hypothesis_ids,
                generator=candidate.generator,
                candidate_sha256=_sha256(candidate.text),
                status=status,
                eligible=eligible,
                requires_review=requires_review,
                gates={
                    "surface": "pass" if analysis.passed else "fail",
                    "fidelity": fidelity.status,
                    "context": context.status
                    if context is not None
                    else "not_evaluated",
                },
                finding_ids={
                    "surface": tuple(finding.rule_id for finding in analysis.findings),
                    "fidelity": tuple(
                        signal["id"] for signal in fidelity.review_signals
                    ),
                    "context": tuple(finding.rule_id for finding in context.findings)
                    if context is not None
                    else (),
                },
                metrics={
                    "character_change_rate": _change_rate(source, candidate.text),
                    "source_sentence_touch_rate": _sentence_touch_rate(
                        source, candidate.text
                    ),
                },
            )
        )

    diversity = analyze_diversity(eligible_candidates, recent_outputs)
    diversity_blocked = strict_diversity and diversity.requires_review
    passed = bool(eligible_candidates) and not diversity_blocked
    contract_id = context_contract.contract_id if context_contract is not None else None
    return RewriteCandidateSetReport(
        schema_version="0.1",
        engine_version=__version__,
        set_id=set_id,
        source_sha256=_sha256(source),
        pack=pack_id,
        contract_id=contract_id,
        passed=passed,
        gate={
            "candidates": len(candidates),
            "eligible": len(eligible_candidates),
            "rejected": sum(item.status == "rejected" for item in evaluations),
            "review": sum(item.status == "review" for item in evaluations),
            "strict_review": strict_review,
            "strict_diversity": strict_diversity,
            "diversity_blocked": diversity_blocked,
        },
        eligible_candidate_ids=tuple(
            candidate.candidate_id for candidate in eligible_candidates
        ),
        candidates=tuple(evaluations),
        diversity=diversity,
        privacy={
            "persisted_by_core": False,
            "contains_source_text": False,
            "contains_candidate_text": False,
            "contains_recent_output_text": False,
        },
        limitations=(
            "후보 생성은 provider adapter의 책임이며 Core는 문장을 생성하지 않습니다.",
            "자동 최우수 후보를 고르지 않고 hard gate 통과 후보를 반환합니다.",
            "변경률과 문장 touch rate는 보정 전 telemetry이며 실패 조건이 아닙니다.",
            "의미·구문 다양성은 향후 보정된 evaluator plugin 범위입니다.",
        ),
    )
