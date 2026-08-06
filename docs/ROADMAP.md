# Roadmap

## 0.1 — Output lint foundation

- [x] JSON 기반 공통·유형별 pack
- [x] `social`, `work-message`
- [x] 근거 레지스트리와 규칙별 evidence trace
- [x] 점수 없는 품질 벡터와 `not_evaluated`
- [x] 수치·날짜·시간·URL·이메일·코드·보호 용어 fidelity gate
- [x] 부정 표현 변화 review 신호
- [x] CLI, JSON 출력, CI 종료 코드

## 0.2 — Context integrity foundation

- [x] `KoContextContract` JSON schema
- [x] entity–event–time–polarity 연결
- [x] 같은 문단의 제한된 한국어 생략 주체 상속
- [x] actor drift, event omission, time omission, polarity review
- [x] 근거·실패 예제·통과 반례를 가진 context rule registry
- [x] `KoContextBench v0` 클린룸 최소쌍
- [x] `KoEditTrace` schema와 무저장 로컬 생성기
- [x] context CLI와 CI gate

## 0.3 — KoContextBench calibration

- [x] provenance·license·annotation 상태를 강제하는 dataset schema
- [x] 도메인·현상별 slice와 finding precision/recall 측정기
- [x] 3개 도메인 × 8개 현상의 자체 제작 development seed 24쌍
- [x] gold를 제거한 블라인드 package와 private key 분리
- [x] 평가 응답 schema, Fleiss kappa, adjudication queue 산출
- [x] 표본·평가자·사전등록·holdout·재배포 조건의 claim gate
- [ ] `customer-reply`, `incident-notice`, `report` 현상별 300쌍
- [ ] 생략 주체, 높임 관계, 시간, 부정 범위, 인과, 인용 귀속 slice
- [ ] 한국어 원어민 3인 독립 annotation과 adjudication
- [ ] 평가자 합의도, rule precision, review 적중률, 오탐률
- [ ] 공개 calibration set과 독립된 private holdout
- [ ] 경쟁 baseline을 가린 블라인드 비교

## 0.4 — Candidate evaluation and semantic adapter foundation

- [x] provider/model/prompt/seed를 기록하는 `RewriteCandidateSet`
- [x] 후보별 surface·fidelity·context hard gate 합성
- [x] exact·normalized·near duplicate와 최근 출력 반복 report
- [x] 원문·후보문을 report에 싣지 않는 privacy contract
- [x] 변경률·문장 touch rate를 실패와 분리한 telemetry
- [ ] 한국어 유형별 near-duplicate 임계 보정
- [ ] Kiwi POS n-gram 기반 batch syntactic diversity adapter
- [ ] 한국어 embedding 기반 semantic diversity adapter

- [ ] source/context에서 contract 후보를 만드는 provider-neutral adapter
- [ ] 자동 추출 결과와 사람이 승인한 contract의 diff
- [ ] predicate–argument/NLI/QA verifier 플러그인
- [ ] provider/model/prompt/evaluator version audit
- [ ] LLM judge 반복·위치 교환·사람 정답 보정
- [ ] 결정론적 결과와 model-based 결과의 분리 유지

## 0.5 — Rewrite adapter

- [ ] 실제 글에서 검토 가능한 style hypothesis 후보 추출
- [ ] 전략별 다중 후보 생성과 generator provider adapter
- [ ] finding span만 수정하는 국소 재작성
- [ ] 재작성 후 pack·fidelity·context gate 재실행
- [ ] fail-closed 결과와 사람 검토 분기
- [ ] 모델 호출 없이 검사만 하는 기존 경로 유지
- [ ] 합성 출력 재학습 금지와 사람 승인 trace만 쓰는 승격 gate

## Cloud private beta

- [ ] OpenAI 호환 output proxy
- [ ] 팀별 context/voice policy와 승인 용어
- [ ] tenant별 KoEditTrace, reviewer decision, retention control
- [ ] 규칙·verifier 후보의 shadow evaluation
- [ ] 승인·버전·롤백과 private holdout release gate
- [ ] 모델·프롬프트별 품질 추적과 회귀 알림

Cloud 학습 루프는 사람 수정을 곧바로 규칙이나 모델로 승격하지 않는다. tenant
데이터는 기본적으로 tenant 안에 머물고, 전역 개선은 별도 opt-in과 클린룸 재현을
거친다.
