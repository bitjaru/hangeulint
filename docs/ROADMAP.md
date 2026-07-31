# Roadmap

## 0.1 — Open-source core

- [x] JSON 기반 공통·유형별 pack
- [x] `social`, `work-message`
- [x] 근거 레지스트리와 규칙별 evidence trace
- [x] 점수 없는 품질 벡터와 `not_evaluated`
- [x] 수치·날짜·시간·URL·이메일·코드·보호 용어 fidelity gate
- [x] 부정 표현 변화 review 신호
- [x] 판정과 분리된 쉼표·종결·선택형 품사 텔레메트리
- [x] CLI, JSON 출력, CI 종료 코드
- [x] 회귀 fixture와 단위 테스트

## 0.2 — KoOutputBench

- [ ] 실제 AI 초안과 한국인 최종 편집본 300쌍
- [ ] 사람 평가 기준: 자연스러움, 격식, 의미 보존, 유형 적합성, 추가 수정시간
- [ ] 일반 프롬프트, 공개 humanizer, HangeuLint 블라인드 비교
- [ ] 오탐 예문과 허용 반례 공개
- [ ] 평가자 간 합의도와 bootstrap 신뢰구간
- [ ] 공개 가능한 성능 주장과 회귀 전용 수치 분리

## 0.3 — Rewrite adapter

- [ ] OpenAI 호환 provider 인터페이스
- [ ] finding span만 수정하는 국소 재작성
- [ ] 재작성 후 pack·fidelity gate 재실행
- [ ] 실패 시 원문 반환이 아닌 명시적 fail-closed 결과
- [ ] 모델 호출 없이 검사만 하는 기존 경로 유지
- [ ] judge 위치 교환·반복 안정성·provider version 기록

## 0.4 — More packs

- [ ] `customer-reply`
- [ ] `report`
- [ ] pack 상속, allowlist, 조직별 override
- [ ] pack별 사람 평가 fixture

## Cloud private beta

- [ ] OpenAI 호환 output proxy
- [ ] 팀별 voice policy와 승인 용어
- [ ] 사람 최종 수정에서 규칙 후보 생성
- [ ] 승인·버전·롤백
- [ ] 모델·프롬프트 변경 회귀 대시보드
- [ ] Slack, Notion, CMS 연동

Cloud 개발은 0.2의 블라인드 평가에서 사람 수정시간 감소가 확인된 뒤 시작합니다.
