from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from . import __version__
from .context_rules import get_context_rule
from .models import ContextFinding, ContextReport, ResolvedEvent

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
_SUBJECT_MARKERS = r"(?:은|는|이|가|께서|에서)"
_NEGATION = re.compile(
    r"(?:지\s*않|지\s*못|안\s+[가-힣]+|못\s+[가-힣]+|"
    r"불가(?:능)?|금지|제외|없(?:다|습니다|어요|음)|아니)"
)
_POLARITIES = {"affirmed", "negated", "unspecified"}
_CONTRACT_KEYS = {"schema_version", "contract_id", "task", "entities", "events"}
_ENTITY_KEYS = {"id", "label", "mentions"}
_EVENT_KEYS = {
    "id",
    "actor",
    "action_terms",
    "object_terms",
    "polarity",
    "time_terms",
    "required",
    "context_window",
}


@dataclass(frozen=True)
class ContextEntity:
    entity_id: str
    label: str
    mentions: tuple[str, ...]


@dataclass(frozen=True)
class ContextEvent:
    event_id: str
    actor: str
    action_terms: tuple[str, ...]
    object_terms: tuple[str, ...]
    polarity: str
    time_terms: tuple[str, ...]
    required: bool
    context_window: int


@dataclass(frozen=True)
class ContextContract:
    schema_version: str
    contract_id: str
    task: str
    entities: tuple[ContextEntity, ...]
    events: tuple[ContextEvent, ...]


@dataclass(frozen=True)
class _Sentence:
    index: int
    paragraph: int
    text: str


def _reject_unknown(
    payload: Mapping[str, Any],
    allowed: set[str],
    scope: str,
) -> None:
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise ValueError(f"{scope}에 알 수 없는 필드가 있습니다: {unknown}")


def _required_string(payload: Mapping[str, Any], key: str, scope: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{scope}.{key}는 비어 있지 않은 문자열이어야 합니다.")
    return value.strip()


def _string_tuple(
    payload: Mapping[str, Any],
    key: str,
    scope: str,
    *,
    required: bool,
) -> tuple[str, ...]:
    value = payload.get(key, [])
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        raise ValueError(f"{scope}.{key}는 문자열 배열이어야 합니다.")
    normalized = tuple(dict.fromkeys(item.strip() for item in value))
    if required and not normalized:
        raise ValueError(f"{scope}.{key}에는 하나 이상의 값이 필요합니다.")
    return normalized


def load_context_contract(payload: Mapping[str, Any]) -> ContextContract:
    if not isinstance(payload, Mapping):
        raise ValueError("문맥 계약은 JSON object여야 합니다.")
    _reject_unknown(payload, _CONTRACT_KEYS, "contract")
    schema_version = _required_string(payload, "schema_version", "contract")
    if schema_version != "0.1":
        raise ValueError(f"지원하지 않는 문맥 계약 schema_version: {schema_version}")
    contract_id = _required_string(payload, "contract_id", "contract")
    task = _required_string(payload, "task", "contract")

    raw_entities = payload.get("entities")
    if not isinstance(raw_entities, list) or not raw_entities:
        raise ValueError("contract.entities에는 하나 이상의 entity가 필요합니다.")
    entities: list[ContextEntity] = []
    entity_ids: set[str] = set()
    for index, raw_entity in enumerate(raw_entities):
        scope = f"contract.entities[{index}]"
        if not isinstance(raw_entity, Mapping):
            raise ValueError(f"{scope}는 object여야 합니다.")
        _reject_unknown(raw_entity, _ENTITY_KEYS, scope)
        entity_id = _required_string(raw_entity, "id", scope)
        if entity_id in entity_ids:
            raise ValueError(f"중복 entity id: {entity_id}")
        entity_ids.add(entity_id)
        label = _required_string(raw_entity, "label", scope)
        mentions = _string_tuple(
            raw_entity,
            "mentions",
            scope,
            required=True,
        )
        entities.append(ContextEntity(entity_id, label, mentions))

    raw_events = payload.get("events")
    if not isinstance(raw_events, list) or not raw_events:
        raise ValueError("contract.events에는 하나 이상의 event가 필요합니다.")
    events: list[ContextEvent] = []
    event_ids: set[str] = set()
    for index, raw_event in enumerate(raw_events):
        scope = f"contract.events[{index}]"
        if not isinstance(raw_event, Mapping):
            raise ValueError(f"{scope}는 object여야 합니다.")
        _reject_unknown(raw_event, _EVENT_KEYS, scope)
        event_id = _required_string(raw_event, "id", scope)
        if event_id in event_ids:
            raise ValueError(f"중복 event id: {event_id}")
        event_ids.add(event_id)
        actor = _required_string(raw_event, "actor", scope)
        if actor not in entity_ids:
            raise ValueError(f"{scope}.actor가 알 수 없는 entity를 참조합니다: {actor}")
        action_terms = _string_tuple(
            raw_event,
            "action_terms",
            scope,
            required=True,
        )
        object_terms = _string_tuple(
            raw_event,
            "object_terms",
            scope,
            required=False,
        )
        time_terms = _string_tuple(
            raw_event,
            "time_terms",
            scope,
            required=False,
        )
        polarity = raw_event.get("polarity", "unspecified")
        if not isinstance(polarity, str) or polarity not in _POLARITIES:
            raise ValueError(
                f"{scope}.polarity는 {sorted(_POLARITIES)} 중 하나여야 합니다."
            )
        required = raw_event.get("required", True)
        if not isinstance(required, bool):
            raise ValueError(f"{scope}.required는 boolean이어야 합니다.")
        context_window = raw_event.get("context_window", 2)
        if (
            not isinstance(context_window, int)
            or isinstance(context_window, bool)
            or not 0 <= context_window <= 5
        ):
            raise ValueError(f"{scope}.context_window는 0~5 정수여야 합니다.")
        events.append(
            ContextEvent(
                event_id=event_id,
                actor=actor,
                action_terms=action_terms,
                object_terms=object_terms,
                polarity=polarity,
                time_terms=time_terms,
                required=required,
                context_window=context_window,
            )
        )
    return ContextContract(
        schema_version=schema_version,
        contract_id=contract_id,
        task=task,
        entities=tuple(entities),
        events=tuple(events),
    )


def _sentences(text: str) -> tuple[_Sentence, ...]:
    result: list[_Sentence] = []
    for paragraph_index, paragraph in enumerate(re.split(r"\n\s*\n", text)):
        for part in _SENTENCE_SPLIT.split(paragraph):
            stripped = part.strip()
            if stripped:
                result.append(
                    _Sentence(
                        index=len(result),
                        paragraph=paragraph_index,
                        text=stripped,
                    )
                )
    return tuple(result)


def _contains_any(text: str, terms: Sequence[str]) -> bool:
    return not terms or any(term in text for term in terms)


def _subject_entities(
    sentence: str,
    entities: Sequence[ContextEntity],
) -> tuple[str, ...]:
    found: list[tuple[int, str]] = []
    for entity in entities:
        for mention in entity.mentions:
            pattern = re.compile(
                rf"(?<![가-힣A-Za-z0-9]){re.escape(mention)}"
                rf"\s*{_SUBJECT_MARKERS}"
            )
            match = pattern.search(sentence)
            if match:
                found.append((match.start(), entity.entity_id))
                break
    return tuple(entity_id for _, entity_id in sorted(found))


def _mentioned_entity(
    sentence: str,
    entity: ContextEntity,
) -> bool:
    return any(mention in sentence for mention in entity.mentions)


def _nearest_subject(
    sentences: Sequence[_Sentence],
    sentence: _Sentence,
    entities: Sequence[ContextEntity],
    context_window: int,
) -> tuple[str | None, int | None]:
    start = max(0, sentence.index - context_window)
    for previous_index in range(sentence.index - 1, start - 1, -1):
        previous = sentences[previous_index]
        if previous.paragraph != sentence.paragraph:
            break
        subjects = _subject_entities(previous.text, entities)
        if len(subjects) == 1:
            return subjects[0], previous.index
        if len(subjects) > 1:
            return None, previous.index
    return None, None


def _event_sentence(
    sentences: Sequence[_Sentence],
    event: ContextEvent,
) -> _Sentence | None:
    candidates = [
        sentence
        for sentence in sentences
        if _contains_any(sentence.text, event.action_terms)
        and _contains_any(sentence.text, event.object_terms)
    ]
    if not candidates:
        return None
    return candidates[0]


def _finding(
    rule_id: str,
    severity: str,
    confidence: str,
    event: ContextEvent,
    message: str,
    *,
    evidence: str = "",
    sentence_index: int | None = None,
    expected: str = "",
    observed: str = "",
) -> ContextFinding:
    rule = get_context_rule(rule_id)
    if severity != rule.severity or confidence != rule.confidence:
        raise RuntimeError(f"{rule_id} metadata가 context rule registry와 다릅니다.")
    return ContextFinding(
        rule_id=rule_id,
        dimension="context_integrity",
        severity=severity,
        confidence=confidence,
        event_id=event.event_id,
        sentence_index=sentence_index,
        message=message,
        evidence=evidence,
        expected=expected,
        observed=observed,
        evidence_ids=rule.evidence_ids,
        calibration=rule.calibration,
    )


def verify_context(
    candidate: str,
    contract: ContextContract | Mapping[str, Any],
) -> ContextReport:
    loaded = (
        contract
        if isinstance(contract, ContextContract)
        else load_context_contract(contract)
    )
    text_sentences = _sentences(candidate)
    entities = {entity.entity_id: entity for entity in loaded.entities}
    findings: list[ContextFinding] = []
    resolved_events: list[ResolvedEvent] = []

    for event in loaded.events:
        sentence = _event_sentence(text_sentences, event)
        if sentence is None:
            if event.required:
                findings.append(
                    _finding(
                        "context.event-missing",
                        "error",
                        "high",
                        event,
                        "필수 사건을 후보문에서 찾지 못했습니다.",
                        expected=(
                            f"action={list(event.action_terms)}, "
                            f"object={list(event.object_terms)}"
                        ),
                    )
                )
            resolved_events.append(
                ResolvedEvent(
                    event_id=event.event_id,
                    sentence_index=None,
                    sentence="",
                    actor_resolution="missing",
                    resolved_actor=None,
                    antecedent_sentence_index=None,
                    observed_polarity="unknown",
                    matched_terms={},
                )
            )
            continue

        actor_entity = entities[event.actor]
        subjects = _subject_entities(sentence.text, loaded.entities)
        resolved_actor: str | None = None
        antecedent_index: int | None = None
        actor_resolution = "unresolved"
        if event.actor in subjects:
            resolved_actor = event.actor
            actor_resolution = "explicit"
        elif subjects:
            resolved_actor = subjects[0] if len(subjects) == 1 else None
            actor_resolution = "explicit_other"
            findings.append(
                _finding(
                    "context.actor-drift",
                    "error",
                    "high",
                    event,
                    "사건의 명시적 수행 주체가 문맥 계약과 다릅니다.",
                    evidence=sentence.text,
                    sentence_index=sentence.index,
                    expected=actor_entity.label,
                    observed=entities[resolved_actor].label
                    if resolved_actor in entities
                    else "복수 또는 불명확",
                )
            )
        elif _mentioned_entity(sentence.text, actor_entity):
            resolved_actor = event.actor
            actor_resolution = "mentioned"
        else:
            inherited_actor, antecedent_index = _nearest_subject(
                text_sentences,
                sentence,
                loaded.entities,
                event.context_window,
            )
            if inherited_actor == event.actor:
                resolved_actor = event.actor
                actor_resolution = "inherited"
            elif inherited_actor is not None:
                resolved_actor = inherited_actor
                actor_resolution = "inherited_other"
                findings.append(
                    _finding(
                        "context.actor-unresolved",
                        "review",
                        "medium",
                        event,
                        "생략된 주체의 가장 가까운 선행사가 기대 주체와 다릅니다.",
                        evidence=sentence.text,
                        sentence_index=sentence.index,
                        expected=actor_entity.label,
                        observed=entities[inherited_actor].label,
                    )
                )
            else:
                findings.append(
                    _finding(
                        "context.actor-unresolved",
                        "review",
                        "medium",
                        event,
                        "생략된 사건 주체를 결정적으로 복원할 수 없습니다.",
                        evidence=sentence.text,
                        sentence_index=sentence.index,
                        expected=actor_entity.label,
                        observed="선행사 없음",
                    )
                )

        observed_polarity = "negated" if _NEGATION.search(sentence.text) else "affirmed"
        if event.polarity != "unspecified" and observed_polarity != event.polarity:
            findings.append(
                _finding(
                    "context.polarity-mismatch",
                    "review",
                    "medium",
                    event,
                    "사건의 부정 여부가 문맥 계약과 다릅니다.",
                    evidence=sentence.text,
                    sentence_index=sentence.index,
                    expected=event.polarity,
                    observed=observed_polarity,
                )
            )

        nearby_start = max(0, sentence.index - event.context_window)
        nearby_end = min(len(text_sentences), sentence.index + event.context_window + 1)
        nearby = " ".join(item.text for item in text_sentences[nearby_start:nearby_end])
        missing_times = [term for term in event.time_terms if term not in nearby]
        if missing_times:
            findings.append(
                _finding(
                    "context.time-anchor-missing",
                    "error",
                    "high",
                    event,
                    "사건에 필요한 시간 앵커가 누락됐습니다.",
                    evidence=sentence.text,
                    sentence_index=sentence.index,
                    expected=", ".join(missing_times),
                )
            )

        resolved_events.append(
            ResolvedEvent(
                event_id=event.event_id,
                sentence_index=sentence.index,
                sentence=sentence.text,
                actor_resolution=actor_resolution,
                resolved_actor=resolved_actor,
                antecedent_sentence_index=antecedent_index,
                observed_polarity=observed_polarity,
                matched_terms={
                    "action": [
                        term for term in event.action_terms if term in sentence.text
                    ],
                    "object": [
                        term for term in event.object_terms if term in sentence.text
                    ],
                    "time": [term for term in event.time_terms if term in nearby],
                },
            )
        )

    errors = sum(finding.severity == "error" for finding in findings)
    reviews = sum(finding.severity == "review" for finding in findings)
    status = "fail" if errors else ("review" if reviews else "pass")
    resolution_counts: dict[str, int] = {}
    for event in resolved_events:
        resolution_counts[event.actor_resolution] = (
            resolution_counts.get(event.actor_resolution, 0) + 1
        )
    return ContextReport(
        schema_version="0.1",
        engine_version=__version__,
        contract_id=loaded.contract_id,
        task=loaded.task,
        status=status,
        passed=errors == 0,
        requires_review=reviews > 0,
        gate={
            "errors": errors,
            "reviews": reviews,
            "events": len(loaded.events),
        },
        findings=tuple(findings),
        resolved_events=tuple(resolved_events),
        metrics={
            "sentences": len(text_sentences),
            "actor_resolution": resolution_counts,
        },
        limitations=(
            "v0는 명시적 문맥 계약을 검증하며 원문에서 계약을 자동 추출하지 않습니다.",
            "생략 주체는 같은 문단의 제한된 선행 문장만 보수적으로 연결합니다.",
            "부정 범위는 결정하지 않으며 불일치는 review로 반환합니다.",
            "동의어와 함의는 계약에 용어 변형으로 명시해야 합니다.",
        ),
    )
