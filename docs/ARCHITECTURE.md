# Architecture

## 제품 계약

HangeuLint는 모델 뒤에 붙는 한국어 출력 품질 계층이다. 입력이 AI 생성인지
판정하지 않고, 발행 계약을 만족하는지 검사한다.

```text
source facts/policy          candidate
        │                        │
        ├── deterministic invariants
        │      number/date/url/code/protected term
        │
        └──────────────────────> type pack
                                  │
                                  ├── naturalness
                                  ├── register
                                  ├── task_fit
                                  ├── risk (not evaluated in v0.1)
                                  └── fidelity
                                        │
                              pass / fail / review
```

`not_evaluated`는 결함을 숨기지 않기 위한 정상 상태다. 예를 들어 원문 없이
`check`를 실행하면 의미 보존을 평가할 수 없다.

## 신호 계층

### Tier 0 — 결정론적 불변식

현재 게이트의 가장 강한 층이다.

- 수치, 금액, 단위
- 날짜와 시간
- URL, 이메일
- 코드형 식별자
- 호출자가 지정한 보호 용어

원문과 후보문의 값을 유형별로 비교한다. 날짜·시간·숫자의 안전한 표기 차이는
정규화하고, 누락과 추가를 같은 오류로 뭉개지 않고 각각 반환한다.

### Tier 1 — 보수적 표면 규칙

문맥과 밀도를 갖춘 경우에만 finding을 낸다.

- 한 문단의 연속된 짧은 줄 비율
- 같은 종결어미의 반복
- 문두 연결어 밀도
- 겹친 경어와 피동
- 유형별 행동 가능성, 구체성, 독자 계약

모든 규칙은 안정적인 ID, 품질 축, 신뢰도, 적용 범위, 근거 ID, 실패 예시,
통과 반례를 가진다.

### Tier 2 — 언어학 텔레메트리

쉼표 사용량·위치, 종결 방식 분포, 선택형 Kiwi 품사 n-gram 다양성을 기록한다.
한국어 LLM 연구에서 유용한 집단 차이가 관찰됐지만 품질과 동일하지 않고 장르
의존적이므로, 자체 코퍼스로 보정하기 전까지 게이트에 연결하지 않는다.

### Tier 3a — 명시적 문맥 계약

`context-check`는 호출자가 선언한 entity와 event를 후보 문서 전체에서 검사한다.
현재 사건 노드는 다음 연결을 가진다.

```text
entity(actor) ──performs──> event(action)
                              ├── targets ──> object term
                              ├── occurs_by ──> time term
                              └── polarity ──> affirmed | negated | unspecified
```

같은 문단의 제한된 앞 문장에서 명시적 주체를 찾고, 사건 문장에 주체가 없을 때만
영형 대용 후보로 연결한다. 다른 entity가 명시적 주체이면 `actor-drift`, 선행사가
불명확하면 `actor-unresolved`를 반환한다. 이 graph는 런타임 메모리 안에서만
만들어지며 v0.2에는 외부 graph database가 필요 없다.

### Tier 3b — 모델 기반 의미 evaluator

아직 구현하지 않았다. 향후 NLI, 질문-응답 기반 일관성, 국소 명제 분해를 플러그인으로
추가한다. 모델 결과는 다음 필드를 별도로 가져야 한다.

- provider/model/version
- prompt/evaluator version
- pointwise 또는 pairwise 방식
- 위치 교환 반복 결과
- calibrated domain
- confidence와 supporting span

결정론적 결과와 모델 점수를 하나로 평균내지 않는다.

### Tier 4 — provider-neutral rewrite candidate evaluation

Core는 모델을 직접 호출하지 않는다. 생성 adapter는 전략과 재현 메타데이터가 붙은
후보 묶음을 만들고 Core는 각 후보에 기존 gate를 다시 실행한다.

```text
RewriteCandidateSet
  ├── candidate id / strategy / hypothesis ids
  ├── provider / model / prompt version / seed
  └── raw candidate text (local input only)
        │
        ├── surface pack
        ├── source fidelity
        ├── optional context contract
        └── eligible / review / rejected
              │
              └── DiversityReport
                    ├── candidate pair overlap
                    ├── recent-output overlap
                    └── strategy audit
```

report에는 원문·후보·최근 출력 전체를 넣지 않는다. exact·normalized duplicate는
결정적 신호이고 near-duplicate는 보정 전 telemetry다. 의미·구문 다양성과 자동
최종 후보 선택은 아직 평가하지 않는다.

## 코드 구조

```text
src/hangeulint/
├── analyzer.py      # pack 실행, 축별 상태, 게이트
├── anchors.py       # 유형별 불변식과 부정 표현 review 신호
├── cli.py           # 로컬·CI 인터페이스
├── context.py       # 명시적 문맥 계약과 document-level event 연결
├── context_rules.py # 문맥 rule registry 검증
├── edit_trace.py    # 로컬·결정적 KoEditTrace 생성
├── rewrite.py       # 후보별 hard gate와 묶음 반복 telemetry
├── rewrite_rules.py # rewrite/diversity rule registry 검증
├── evidence.py      # 근거 레지스트리 로더와 검증
├── models.py        # schema-versioned 결과 계약
├── packs.py         # 규칙 schema와 pack 합성
├── surface.py       # 보정 전 텔레메트리, 선택형 형태소 분석
├── packs/
│   ├── common.json
│   ├── social.json
│   └── work-message.json
└── references/
    ├── context-rules.json
    └── evidence.json
```

## 결과 계약

최상위 report에는 전체 품질 점수가 없다.

- `schema_version`, `engine_version`, `pack_version`
- `passed`
- `gate`: error/warning 허용 예산과 현재 개수
- `dimensions`: 축별 `pass`, `warn`, `fail`, `not_evaluated`
- `findings`: 위치 근거, 규칙 근거, 신뢰도, 수정 방향
- `metrics`: 판정과 분리된 텔레메트리
- `limitations`

`compare`는 별도 fidelity report를 반환한다.

- `pass`: 결정론적 앵커가 보존되고 검토 신호 없음
- `review`: 앵커는 보존됐지만 부정 표현 수가 달라 사람/semantic evaluator 확인 필요
- `fail`: 필수 앵커 누락 또는 후보에 새 앵커 추가

`context-check`도 결과를 평균 점수로 압축하지 않는다.

- `pass`: 계약 사건과 명시/상속 주체, 시간 앵커가 보존됨
- `review`: 생략 주체 또는 부정 범위를 결정적으로 확정할 수 없음
- `fail`: 필수 사건·시간이 누락되거나 명시 주체가 다른 entity로 바뀜

`trace`는 원문과 후보의 hash, 변경 구간, 사람의 명시적 채택 상태, 연결된 context
finding ID를 반환한다. Core는 trace나 전체 문서를 저장하지 않는다.

## Pack과 정책

공개 pack은 채널에서 반복되는 일반 규칙만 포함한다. 회사명, 고객명, 금지 주제,
대표 말투, 승인 용어 같은 정책은 공개 pack에 넣지 않는다. 향후 조직 정책은
pack 위에 합성하되 다음 우선순위를 따른다.

```text
hard invariant > legal/risk policy > organization policy > public pack > advice
```

조직 override는 공개 rule을 조용히 삭제하지 않고, rule ID와 사유를 audit log에
남긴다.

## 개인정보 경계

Core는 원문과 후보문을 외부로 보내거나 저장하지 않는다. 향후 Cloud에서도 원문
저장은 opt-in이며, 학습/규칙 후보 생성 동의와 운영 로그 동의를 분리한다.
고객 문서에서 나온 비공개 표현은 공개 evidence나 fixture로 승격하지 않는다.
