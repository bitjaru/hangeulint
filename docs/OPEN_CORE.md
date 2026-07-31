# Open-core boundary

## 공개하는 것

- 결정론적 한국어 분석기
- 공개 유형 pack과 pack 스키마
- 원문-후보 fidelity gate
- 명시적 KoContextContract와 결정론적 document-level verifier
- KoEditTrace 스키마와 로컬 diff 생성기
- KoContextBench schema, slice evaluator, annotation 도구
- CLI, SDK, CI 통합
- 공개 fixture와 벤치마크 실행기
- 자체 호스팅 가능한 기본 API 계약

## HangeuLint Cloud가 맡을 것

- 조직별 비공개 voice policy
- 원문, AI 초안, 사람 최종본의 안전한 피드백 저장
- tenant별 KoEditTrace 보존, 익명화, 접근 통제
- 문맥 verifier 보정 데이터와 비공개 holdout
- 규칙 후보 생성과 승인 워크플로
- API 키, 사용량 제한, 감사 로그
- 모델·프롬프트별 품질 추적과 회귀 알림
- SaaS 연동과 전용 배포

Cloud의 기본 요청 모드는 무저장 처리다. 원문/후보 저장, 사람 수정본 저장,
정책 후보 학습은 각각 별도 동의와 보존 기간을 가져야 한다.

## 정책 학습 루프

사람이 고친 문장을 바로 자동 규칙으로 배포하지 않는다.

```text
source + AI draft + human final + context findings
  -> local/private KoEditTrace
  -> repeated pattern candidate
  -> false-positive counterexample search
  -> owner review
  -> versioned shadow policy
  -> holdout evaluation
  -> explicit promotion / rollback
```

조직 데이터에서 얻은 policy는 공개 pack으로 자동 이동하지 않는다. 공개 규칙
후보는 식별 정보를 제거한 클린룸 예시와 재현 가능한 근거를 새로 만들어야 한다.

## 왜 이 경계인가

검사 코어를 공개하면 사용자가 결과를 재현하고 규칙의 근거를 검토할 수 있습니다.
유료 가치는 숨겨진 프롬프트가 아니라 팀 데이터, 운영 편의, 지속적인 평가와
통합에서 만들어야 합니다.

공개 프로젝트를 SaaS의 데모판으로 약화시키지 않습니다. 로컬과 CI에서 쓸 수 있는
코어는 독립적으로 유용해야 합니다.

공개되는 것은 trace의 **형식과 생성기**다. 고객 문서에서 실제로 생성된 trace,
조직별 승인/거절 분포, verifier 보정값, 비공개 holdout은 고객 소유 데이터 또는
Cloud 운영 자산으로 남는다.
