from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

from . import __version__
from .models import AnalysisReport, Finding
from .packs import Pack, Rule, load_pack
from .surface import ending_distribution, sentences, surface_metrics

_DIMENSIONS = ("naturalness", "register", "task_fit", "risk")


def _visible_paragraphs(text: str, pack: Pack) -> list[str]:
    paragraphs: list[str] = []
    for paragraph in re.split(r"\n\s*\n", text):
        stripped = paragraph.strip()
        if not stripped:
            continue
        if stripped.startswith(pack.ignored_section_prefixes):
            continue
        paragraphs.append(stripped)
    return paragraphs


def _metrics(
    text: str,
    pack: Pack,
    morphology: str | None,
) -> dict[str, Any]:
    paragraphs = _visible_paragraphs(text, pack)
    lines = [
        line.strip()
        for paragraph in paragraphs
        for line in paragraph.splitlines()
        if line.strip()
    ]
    compact_lengths = [len(re.sub(r"\s+", "", line)) for line in lines]
    short_lines = sum(length <= 18 for length in compact_lengths)
    metrics = surface_metrics(text, morphology)
    metrics.update(
        {
            "paragraphs": len(paragraphs),
            "visible_lines": len(lines),
            "short_line_ratio": round(short_lines / len(lines), 3) if lines else 0.0,
        }
    )
    return metrics


def _finding(
    rule: Rule,
    *,
    evidence: str,
    occurrences: int = 1,
) -> Finding:
    return Finding(
        rule_id=rule.rule_id,
        dimension=rule.dimension,
        category=rule.category,
        severity=rule.severity,
        confidence=rule.confidence,
        message=rule.message,
        evidence=evidence,
        occurrences=occurrences,
        suggestion=rule.suggestion,
        evidence_ids=rule.evidence_ids,
        calibration=rule.calibration,
    )


def _regex_finding(text: str, rule: Rule) -> Finding | None:
    if not rule.pattern:
        return None
    matches = list(re.finditer(rule.pattern, text, flags=re.MULTILINE))
    max_occurrences = int(rule.options.get("max_occurrences", 0))
    if len(matches) <= max_occurrences:
        return None
    first = matches[0].group(0)
    return _finding(
        rule,
        evidence=first[:120],
        occurrences=len(matches),
    )


def _short_line_finding(text: str, pack: Pack, rule: Rule) -> Finding | None:
    min_lines = int(rule.options.get("min_lines", 4))
    max_compact_chars = int(rule.options.get("max_compact_chars", 18))
    ratio_threshold = float(rule.options.get("ratio", 0.7))
    fragmented = 0
    example = ""
    for paragraph in _visible_paragraphs(text, pack):
        lines = [line.strip() for line in paragraph.splitlines() if line.strip()]
        if len(lines) < min_lines:
            continue
        short = [
            line for line in lines if len(re.sub(r"\s+", "", line)) <= max_compact_chars
        ]
        if len(short) / len(lines) >= ratio_threshold:
            fragmented += 1
            example = "\n".join(lines[:3])
    if not fragmented:
        return None
    return _finding(
        rule,
        evidence=example,
        occurrences=fragmented,
    )


def _repeated_ending_finding(text: str, rule: Rule) -> Finding | None:
    text_sentences = sentences(text)
    min_sentences = int(rule.options.get("min_sentences", 4))
    ratio_threshold = float(rule.options.get("ratio", 0.75))
    if len(text_sentences) < min_sentences:
        return None
    endings = []
    suffixes = tuple(
        rule.options.get(
            "suffixes",
            ["습니다", "입니다", "합니다", "됩니다", "어요", "예요", "죠", "다"],
        )
    )
    for sentence in text_sentences:
        plain = sentence.rstrip(".!? ")
        ending = next((suffix for suffix in suffixes if plain.endswith(suffix)), "")
        if ending:
            endings.append(ending)
    if len(endings) < min_sentences:
        return None
    ending, count = Counter(endings).most_common(1)[0]
    if count / len(endings) < ratio_threshold:
        return None
    return _finding(
        rule,
        evidence=f"{ending} × {count}",
        occurrences=count,
    )


def _term_density_finding(text: str, rule: Rule) -> Finding | None:
    terms = tuple(str(term) for term in rule.options.get("terms", []))
    window = max(1, int(rule.options.get("characters", 500)))
    threshold = int(rule.options.get("count", 5))
    hits = [term for term in terms for _ in re.finditer(re.escape(term), text)]
    normalized_threshold = math.ceil(threshold * max(len(text), window) / window)
    if len(hits) < normalized_threshold:
        return None
    return _finding(
        rule,
        evidence=", ".join(hits[:6]),
        occurrences=len(hits),
    )


def _register_mix_finding(text: str, rule: Rule) -> Finding | None:
    distribution = ending_distribution(text)
    min_recognized = int(rule.options.get("min_recognized", 4))
    min_minor = int(rule.options.get("min_minor", 2))
    recognized = sum(distribution.values())
    if recognized < min_recognized or len(distribution) < 2:
        return None
    _, dominant_count = distribution.most_common(1)[0]
    minor_count = recognized - dominant_count
    if minor_count < min_minor:
        return None
    evidence = ", ".join(
        f"{label}={count}" for label, count in distribution.most_common()
    )
    return _finding(rule, evidence=evidence, occurrences=minor_count)


def _run_rule(text: str, pack: Pack, rule: Rule) -> Finding | None:
    if rule.kind == "regex":
        return _regex_finding(text, rule)
    if rule.kind == "short_line_ratio":
        return _short_line_finding(text, pack, rule)
    if rule.kind == "repeated_ending":
        return _repeated_ending_finding(text, rule)
    if rule.kind == "term_density":
        return _term_density_finding(text, rule)
    if rule.kind == "register_mix":
        return _register_mix_finding(text, rule)
    raise ValueError(f"지원하지 않는 rule kind: {rule.kind}")


def _dimension_summary(
    findings: tuple[Finding, ...],
    pack: Pack,
) -> dict[str, dict[str, int | str]]:
    result: dict[str, dict[str, int | str]] = {}
    evaluated = {rule.dimension for rule in pack.rules}
    for dimension in _DIMENSIONS:
        selected = [finding for finding in findings if finding.dimension == dimension]
        errors = sum(item.severity == "error" for item in selected)
        warnings = sum(item.severity == "warning" for item in selected)
        infos = sum(item.severity == "info" for item in selected)
        if dimension not in evaluated:
            status = "not_evaluated"
        elif errors:
            status = "fail"
        elif warnings:
            status = "warn"
        elif selected:
            status = "pass_with_info"
        else:
            status = "pass"
        result[dimension] = {
            "status": status,
            "errors": errors,
            "warnings": warnings,
            "infos": infos,
        }
    result["fidelity"] = {
        "status": "not_evaluated",
        "errors": 0,
        "warnings": 0,
        "infos": 0,
    }
    return result


def analyze(
    text: str,
    pack_id: str = "social",
    morphology: str | None = None,
) -> AnalysisReport:
    pack = load_pack(pack_id)
    findings = tuple(
        finding
        for rule in pack.rules
        if (finding := _run_rule(text, pack, rule)) is not None
    )
    error_count = sum(finding.severity == "error" for finding in findings)
    warning_count = sum(finding.severity == "warning" for finding in findings)
    passed = error_count <= pack.max_errors and warning_count <= pack.max_warnings
    return AnalysisReport(
        schema_version="1.0",
        engine_version=__version__,
        pack=pack.pack_id,
        pack_version=pack.version,
        passed=passed,
        gate={
            "passed": passed,
            "errors": error_count,
            "warnings": warning_count,
            "max_errors": pack.max_errors,
            "max_warnings": pack.max_warnings,
        },
        dimensions=_dimension_summary(findings, pack),
        findings=findings,
        metrics=_metrics(text, pack, morphology),
        limitations=(
            "작성 주체나 AI 생성 여부를 판정하지 않습니다.",
            "코퍼스 보정 전 surface metric은 통과/실패에 사용하지 않습니다.",
            "check 명령만으로 의미 보존은 평가하지 않습니다. compare를 사용하세요.",
        ),
    )
