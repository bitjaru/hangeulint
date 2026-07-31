# Product thesis

## 한 줄 정의

HangeuLint는 한국어 humanizer가 아니라 **Korean output compiler**다. 모델이 낸
초안을 유형별 발행 계약에 맞춰 검사하고, 바뀐 사실과 격식을 추적하며, 팀이 승인한
정책 버전으로 통제한다.

## 왜 단순 재작성 SaaS로 시작하지 않는가

붙여넣기 humanizer는 결과가 좋으면 사용자가 프롬프트를 복사하고 떠날 수 있다.
차별점도 규칙 문구와 모델 선택에 묶인다. 반면 팀은 다음 운영 문제를 반복해서
가진다.

- 모델이나 prompt를 바꿨을 때 품질이 퇴행했는지 모름
- 자연스럽게 고치는 동안 수치·기한·높임말이 바뀜
- 채널마다 기준이 다른데 하나의 voice prompt로 관리
- 사람이 고친 이유가 다음 출력에 안전하게 반영되지 않음
- 누가 어떤 정책으로 발행을 막거나 허용했는지 기록이 없음

따라서 첫 유료 가치는 생성 자체보다 **policy, evaluation, audit, rollback**이다.

## 진입 순서

### 1. 오픈소스 CLI/SDK

개발자와 AI 운영자가 로컬·CI에서 결정론적 문제를 찾는다. 규칙과 한계가 공개되어
신뢰와 실제 오탐 사례를 쌓는다.

### 2. 팀 evaluation

모델/프롬프트/pack 버전별로 동일 fixture와 비공개 holdout을 실행한다. 사람의
override와 수정 시간을 기록해 실제 가치가 있는 규칙만 남긴다.

### 3. output proxy

OpenAI 호환 응답 뒤에 gate를 붙인다. fail/review 시 무조건 다시 생성하지 않고,
정책에 따라 차단·사람 승인·국소 수정으로 분기한다.

### 4. feedback control plane

승인된 사람 수정에서 정책 후보를 만들되 자동 배포하지 않는다. shadow evaluation,
owner 승인, version promotion, rollback을 제공한다.

## 성공 지표

북극성 지표는 ‘AI 티 점수’가 아니다.

- 발행 전 사람 수정 시간의 중앙값
- 결정론적 사실 변경 누락률
- pack별 false-positive/override rate
- review에서 실제 문제로 확인된 비율
- 모델/프롬프트 변경 후 회귀 발견 시간
- 정책 rollback 빈도와 원인

## 중단 기준

다음 조건이면 Cloud 개발을 늦추고 코어/평가를 다시 고친다.

- 블라인드 평가에서 수정 시간이 줄지 않음
- 오탐 때문에 팀이 gate를 반복적으로 우회함
- 규칙이 유형별로 재현되지 않음
- 의미 보존 오류가 자연스러움 개선보다 커짐
- 비공개 policy 없이도 단순 프롬프트로 동일 효과가 남

## 방어력

오픈 규칙의 개수는 방어력이 아니다. 장기 자산은 다음에 있다.

- 한국어 유형별 블라인드 평가 protocol
- 규칙의 근거·반례·보정 이력
- 조직별 승인/override 데이터와 안전한 policy lifecycle
- 모델·프롬프트·정책을 함께 재현하는 audit trail
- 실제 편집 시간과 사실 보존으로 검증된 release gate
