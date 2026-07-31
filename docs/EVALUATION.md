# Evaluation protocol

## 검증할 가설

HangeuLint의 1차 제품 가설은 ‘AI 티를 더 잘 찾는다’가 아니다.

> 유형별 품질 게이트를 통과한 후보는 일반적인 재작성 프롬프트보다 한국어 원어민
> 편집자의 수정 시간을 줄이면서, 원문의 사실과 격식을 덜 훼손한다.

## 평가 단위

원문, 초안, 후보, 사람 최종본을 한 묶음으로 본다. 유형별 최소 표본을 따로
확보하며, social 결과를 work-message 성능으로 합산하지 않는다.

1. `social`
2. `work-message`
3. 이후 `customer-reply`, `report`

각 예문에는 민감정보를 제거하고 다음 메타데이터만 둔다.

- task/pack
- 원문의 필수 사실과 보호 용어
- 목표 독자 관계와 격식
- 허용되는 형식
- 생성 모델군과 prompt version
- 편집 소요 시간

문맥 평가 예문에는 다음 정답도 추가한다.

- entity와 허용 mention
- 필수 event의 actor/action/object/polarity/time
- 생략 주체의 올바른 선행사
- 오류 현상 slice: actor drift, event omission, temporal drift, negation scope
- `pass`, `review`, `fail` 정답과 판단 근거 span

## 비교군

- 원 AI 초안
- ‘자연스럽게 써줘’ 일반 프롬프트
- 공개 humanizer의 기본 설정
- HangeuLint finding 기반 국소 수정
- 원어민 편집본

도구명과 생성 방식을 가리고 무작위 순서로 제시한다.

## 사람 평가 축

각 축을 따로 기록한다.

1. 의미/사실 보존
2. 높임말·격식 보존
3. 자연스러움
4. 유형/행동 적합성
5. 발행 가능 여부
6. 추가 수정 시간

자연스러움이 높더라도 사실이나 격식을 바꾸면 성공으로 세지 않는다.

## annotation 운영

- 한국어 원어민 평가자 최소 3명
- 각 예문을 독립 평가한 뒤 불일치만 adjudication
- 평가 전 pack별 예시와 경계 사례 교육
- Cohen/Fleiss kappa 또는 Krippendorff alpha 보고
- 중앙값 수정 시간과 bootstrap 95% 신뢰구간 보고
- 규칙별 precision, pack별 false-positive rate 보고
- 모델군/문서 길이/유형별 slice 공개

## LLM evaluator 검증

LLM judge는 사람 평가를 대체하지 않는다.

- pointwise를 기본으로 하고 pairwise는 보조 분석
- pairwise 사용 시 A/B 위치를 바꿔 반복
- 동일 후보 반복으로 안정성 측정
- 장문 선호, 단정적 표현 선호, 불확실성 표현 불이익 확인
- judge model과 prompt version 고정
- 사람 평가와 예제 수준 confusion matrix 공개

기준을 못 맞춘 judge 결과는 연구 로그에만 남기고 제품 게이트에 연결하지 않는다.

## 공개 가능한 주장 기준

다음을 모두 만족할 때만 ‘편집 시간 감소’ 또는 ‘오탐률’을 말한다.

- 사전 등록된 평가 protocol
- 유형별 충분한 표본
- 블라인드 원어민 평가
- 신뢰구간과 평가자 합의도
- 실패 사례와 제외 기준 공개
- 독립된 holdout 결과

`scripts/run_benchmark.py`의 fixture 일치율은 구현 회귀 전용이며 위 주장에 사용할 수
없다. `scripts/run_context_benchmark.py`도 동일하다.

## KoContextBench 단계

1. `v0 clean-room`: 알고리즘 계약을 고정하는 최소쌍. 현재 구현.
2. `public calibration`: 재배포 가능한 한국어 자료와 직접 작성한 반례를 현상별로
   수집한다.
3. `human adjudication`: 원어민 3명이 actor/event/time/polarity 정답을 독립 표기한다.
4. `private holdout`: 규칙·추출기·verifier 개발에 노출하지 않은 예문으로 릴리스를
   막거나 허용한다.
5. `production drift`: 고객 opt-in trace에서는 원문 정확도를 공개 benchmark와 섞지
   않고 tenant별 override와 review 적중률만 집계한다.
