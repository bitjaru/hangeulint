# Open-source method review

검토 시점은 2026-08-06이다. HangeuLint는 아래 프로젝트의 코드를 복사하지 않았고,
공개 문서와 구현을 읽어 재사용 가능한 방법론과 제품 경계를 확인했다. 외부 규칙의
점수나 임계값은 HangeuLint 성능 근거로 사용하지 않는다.

## Humanize KR / im-not-ai

- 저장소: [epoko77-ai/im-not-ai](https://github.com/epoko77-ai/im-not-ai)
- 검토 commit: `53e24e8f92cf344efcb812103f7c2b203e7efffc`
- 라이선스: MIT
- 확인한 강점: 진단과 윤문 분리, 탐지 span 중심 국소 수정, 변경률·문장 touch·구조
  수렴을 사후 검사, 명시적 author voice override
- 가져오지 않는 것: AI 작성자 확신 등급, 프로젝트 고유 taxonomy, 장르별로 보정되지
  않은 z-score와 30%/50% 변경률 임계값

HangeuLint는 변경률과 문장 touch rate를 우선 `telemetry_only`로 공개한다. 실제
한국어 유형별 사람 평가 없이 이를 실패 기준으로 만들지 않는다.

## KatFishNet

- 저장소: [Shinwoo-Park/katfishnet](https://github.com/Shinwoo-Park/katfishnet)
- 검토 commit: `5e3dc89cc31a029be38fb2d871476b0aff7b793c`
- 논문: [ACL 2025](https://aclanthology.org/2025.acl-long.1030/)
- 저장소 라이선스: 검토 시 명시적 `LICENSE` 없음
- 확인한 강점: 한국어 띄어쓰기, POS n-gram, 쉼표 위치를 장르별 분포로 분석하고
  unseen model OOD 평가
- 가져오지 않는 것: essay·poetry·abstract 탐지 분류기를 고객 답변이나 업무
  메시지 품질 점수로 전용하는 것, 코드·데이터 vendoring

형태·구문 신호는 batch telemetry 후보일 뿐 `AI가 썼다`거나 `품질이 낮다`는
판정이 아니다.

## HyPerAlign

- 논문: [HyPerAlign](https://arxiv.org/abs/2505.00038)
- 확인한 강점: 몇 개의 실제 글을 그대로 few-shot으로 밀어 넣기보다, 사용자의
  communication strategy와 writing style을 명시적 가설로 먼저 추출
- 가져오지 않는 것: 영어권 실험 결과를 한국어 품질 수치로 재사용하거나, 가설을
  검증 없이 조직 policy로 자동 승격하는 것

HangeuLint candidate에는 적용한 `hypothesis_ids`를 기록한다. 가설의 생성·승인
스키마는 별도 단계이며, 실제 사람 글과 반례를 거쳐야 한다.

## humanize

- 저장소: [harshaneel/humanize](https://github.com/harshaneel/humanize)
- 검토 commit: `4ec797314537ec9c2105f276d4561d240a0390ba`
- 라이선스: MIT
- 확인한 강점: detection → rewrite → audit 단계, writer-profile hypothesis,
  best-of-N과 의미 보존 재검사의 필요성
- 가져오지 않는 것: 영어 문장부호·금칙어 임계값, detector score 최적화, 근거 없는
  숫자·사례·개인 경험 삽입

구체적인 정보가 원문에 없으면 후보 생성기가 만들어내지 못하도록 fidelity와
context gate를 후보마다 다시 실행한다.

## AlignScore

- 저장소: [yuh-zha/AlignScore](https://github.com/yuh-zha/AlignScore)
- 라이선스: MIT
- 확인한 강점: source가 candidate 정보를 지지하는지를 별도의 factual consistency
  문제로 평가
- 도입 경계: 한국어 고객 문서에서 보정되기 전까지 optional semantic adapter다.
  결정론적 수치·날짜·URL gate를 대체하지 않는다.

## HangeuLint 합성

```text
real writing samples
  -> explicit style hypotheses
  -> provider-neutral generator produces N candidates
  -> surface + fidelity + KoContextContract hard gate per candidate
  -> lexical/form batch diversity + recent-output overlap telemetry
  -> semantic/syntactic diversity adapter (future, separately calibrated)
  -> human choice + KoEditTrace
  -> shadow policy -> holdout -> explicit promotion / rollback
```

현재 v0.4는 generator 앞뒤의 공개 계약과 결정론적 후보 평가까지만 구현한다. 모델
호출, 자동 style hypothesis 추출, semantic diversity, 자동 최종 후보 선택은 구현하지
않았다.
