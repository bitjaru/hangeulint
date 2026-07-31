# KoContextBench annotation protocol

## 범위

`seed-v0.1.json`은 평가 도구와 현상 분류를 검증하는 첫 제작 seed다. 전부 이
프로젝트에서 직접 작성했으며 실제 고객 문서나 외부 연구 데이터가 아니다.

- 24 cases
- `incident-notice`, `customer-reply`, `report` 각 8개
- explicit actor, zero anaphora, actor drift, wrong antecedent
- event omission, temporal omission, negation scope, paragraph boundary

24/24 회귀 일치는 이 seed를 현재 알고리즘에 맞춰 작성했다는 뜻이다. 실제 한국어
문맥 정확도나 사람 평가 결과가 아니다.

## case 수집 계약

새 case는 다음을 모두 기록한다.

1. `domain`, `phenomena`
2. 평가자가 판단에 사용할 `source_context`
3. 검사할 `candidate`
4. 명시적 `KoContextContract`
5. source kind, reference, license, redistribution permission
6. gold status, finding ID, actor resolution
7. 완료 평가자 수, adjudication 여부, agreement

실제 고객 문서는 별도 opt-in, 비식별화, 보존 기간이 없으면 공개 dataset에 넣지
않는다. `customer_opt_in` source도 자동으로 공개 승격하지 않는다.

## 평가자 운영

- 한국어 원어민 평가자 최소 3명
- 평가자끼리 상의하지 않고 1차 독립 평가
- 이름이나 이메일 대신 pseudonymous `rater_id`
- 생성 모델, prompt, HangeuLint 결과, gold label을 가림
- 각 판단에 rationale 필수
- status뿐 아니라 finding set과 actor resolution도 기록
- 불일치 case만 별도 adjudicator가 원문 근거로 판정

평가 전에는 rule 정의와 경계 예시를 교육하되 실제 평가 case를 예시로 쓰지 않는다.

## 블라인드 package 생성

출력 경로는 `.gitignore`에 포함된 `annotation-runs/`를 권장한다.

```bash
PYTHONPATH=src python3 scripts/prepare_context_annotation.py \
  benchmarks/context/seed-v0.1.json \
  --output benchmarks/context/annotation-runs/batch-001/package.json \
  --key-output benchmarks/context/annotation-runs/batch-001/private-key.json \
  --seed 20260731
```

`package.json`에는 gold와 내부 case ID가 없다. `private-key.json`은 annotation ID와
case ID를 연결하므로 평가자에게 주지 않고 dataset owner가 따로 보관한다.

## response 형식

각 평가자는 `schemas/context-annotation-response.schema.json`에 맞는 JSON 한 개를
제출한다.

```json
{
  "schema_version": "0.1",
  "package_id": "kocontextbench-development-seed-v0.1-blind-seed-20260731",
  "rater_id": "reviewer-7f31",
  "items": [
    {
      "annotation_id": "item-0001",
      "status": "review",
      "finding_ids": ["context.actor-unresolved"],
      "actor_resolution": "inherited_other",
      "rationale": "생략된 주체의 가장 가까운 선행사가 고객입니다."
    }
  ]
}
```

실제 response는 package의 모든 item을 정확히 한 번씩 포함해야 한다.

## 합의도와 adjudication

```bash
PYTHONPATH=src python3 scripts/score_context_annotations.py \
  benchmarks/context/annotation-runs/batch-001/package.json \
  benchmarks/context/annotation-runs/batch-001/reviewer-a.json \
  benchmarks/context/annotation-runs/batch-001/reviewer-b.json \
  benchmarks/context/annotation-runs/batch-001/reviewer-c.json \
  --required-raters 3 --json
```

도구는 다음을 계산한다.

- status Fleiss’ kappa
- unanimous status rate
- unanimous finding-set rate
- adjudication이 필요한 item 수

다수결 결과를 자동 gold로 쓰지 않는다. 평가자 rationale과 source context를 확인한
adjudicator가 최종 label을 별도 승인해야 한다.

## 성능 주장 gate

`claim_readiness.publishable`은 다음을 모두 충족해야만 `true`가 된다.

- `public_calibration` release
- 300 cases 이상
- blind review
- 사전 등록된 protocol
- 독립 holdout 확인
- case마다 원어민 평가자 3명 이상
- adjudication 완료
- agreement 기록
- 모든 공개 case의 재배포 권리 확인

이 gate는 높은 fixture 점수만으로 품질 주장을 만드는 것을 막는다.
