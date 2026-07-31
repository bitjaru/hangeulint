from __future__ import annotations

import re
from collections import Counter
from typing import Any


_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
_ENDING_PATTERNS = (
    ("formal", re.compile(r"(?:습니다|ㅂ니다|입니다|합니다|됩니다)$")),
    ("polite", re.compile(r"(?:요|예요|이에요|해요|돼요)$")),
    ("plain", re.compile(r"(?:한다|된다|이다|했다|됐다|다)$")),
)


def sentences(text: str) -> list[str]:
    return [part.strip() for part in _SENTENCE_SPLIT.split(text) if part.strip()]


def ending_distribution(text: str) -> Counter[str]:
    distribution: Counter[str] = Counter()
    for sentence in sentences(text):
        plain = sentence.rstrip(".!?… ")
        for label, pattern in _ENDING_PATTERNS:
            if pattern.search(plain):
                distribution[label] += 1
                break
    return distribution


def comma_metrics(text: str) -> dict[str, int | float | str]:
    visible = re.sub(r"\s+", "", text)
    commas = [match.start() for match in re.finditer(r"[,，]", text)]
    if not text:
        return {
            "status": "insufficient_context",
            "count": 0,
            "per_100_chars": 0.0,
            "mean_relative_position": 0.0,
        }
    sentence_lengths = [len(re.sub(r"\s+", "", item)) for item in sentences(text)]
    return {
        "status": "telemetry_only",
        "count": len(commas),
        "per_100_chars": round(len(commas) * 100 / max(1, len(visible)), 3),
        "mean_relative_position": round(
            sum(position / len(text) for position in commas) / len(commas), 3
        )
        if commas
        else 0.0,
        "mean_sentence_compact_chars": round(
            sum(sentence_lengths) / len(sentence_lengths), 3
        )
        if sentence_lengths
        else 0.0,
    }


def morphology_metrics(text: str, backend: str | None = None) -> dict[str, Any]:
    if backend in (None, "none"):
        return {
            "status": "not_requested",
            "backend": None,
            "note": "형태소 기반 신호는 선택 기능이며 기본 게이트에 포함되지 않습니다.",
        }
    if backend != "kiwi":
        raise ValueError(f"지원하지 않는 형태소 분석 backend: {backend}")
    try:
        from kiwipiepy import Kiwi
    except ImportError as exc:
        raise ValueError(
            "kiwi backend는 선택 의존성입니다. "
            "`pip install 'hangeulint[morphology]'`로 설치하세요."
        ) from exc

    tokens = Kiwi().tokenize(text)
    tags = [token.tag for token in tokens if not token.tag.startswith(("S", "W"))]
    bigrams = list(zip(tags, tags[1:]))
    return {
        "status": "telemetry_only",
        "backend": "kiwi",
        "tokens": len(tags),
        "pos_bigram_types": len(set(bigrams)),
        "pos_bigram_type_token_ratio": round(len(set(bigrams)) / len(bigrams), 3)
        if bigrams
        else 0.0,
        "note": "코퍼스 보정 전이므로 품사 다양성은 통과/실패에 사용하지 않습니다.",
    }


def surface_metrics(text: str, morphology: str | None = None) -> dict[str, Any]:
    distribution = ending_distribution(text)
    return {
        "characters": len(text),
        "sentences": len(sentences(text)),
        "ending_distribution": dict(distribution),
        "comma": comma_metrics(text),
        "morphology": morphology_metrics(text, morphology),
    }
