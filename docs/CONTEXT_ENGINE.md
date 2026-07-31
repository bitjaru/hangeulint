# Korean context integrity engine

## 목표

문장 하나를 자연스럽게 고치는 것이 아니라 문서 앞부분에서 정한 주체·사건·시간·
부정 관계가 뒤 문장에서도 유지되는지 검사한다. v0.2의 핵심은 더 큰 모델이 아니라
재현 가능한 중간 표현이다.

```text
source / policy / task
        │
        ▼
KoContextContract
  entities + events
        │
        ├── deterministic document resolver
        │       explicit actor
        │       same-paragraph zero subject
        │       event/action/object
        │       time/polarity
        │
        ▼
ContextReport ──> KoEditTrace ──> human decision
```

## 왜 계약을 먼저 만드는가

LLM에게 원문과 후보를 주고 “같은 뜻인가”라고 묻는 방식만으로는 판정 재현, 실패
위치, 고객별 정책, 회귀 테스트를 고정하기 어렵다. 반면 계약은 자동 추출기가
바뀌어도 verifier 입력과 기대 결과를 유지할 수 있다.

현재는 사람이 또는 상위 시스템이 계약을 명시한다. 향후 추출기는 계약 **후보**를
만들고, 자동 추출 정확도를 별도로 측정한다. 추출과 검증을 한 모델 호출로 합치지
않는다.

## KoContextContract

```json
{
  "schema_version": "0.1",
  "contract_id": "incident-v1",
  "task": "고객 장애 공지",
  "entities": [
    {
      "id": "company",
      "label": "당사",
      "mentions": ["당사", "저희", "운영팀"]
    }
  ],
  "events": [
    {
      "id": "investigate",
      "actor": "company",
      "action_terms": ["조사"],
      "object_terms": ["원인"],
      "polarity": "affirmed",
      "time_terms": ["7월 31일까지"],
      "context_window": 2
    }
  ]
}
```

`action_terms`와 `object_terms`는 동의어 사전이 아니다. 계약 작성자가 동일한
사건으로 허용하는 표면형을 명시한다. time term은 현재 모두 필요한 앵커다.

## 생략 주체 처리

한국어에서는 연속 문장에서 이미 알려진 주체를 자주 생략한다. v0 resolver는
사건 문장에 명시 주체가 없을 때만 같은 문단의 앞 `context_window`개 문장을
역순으로 확인한다.

- 기대 entity가 명시됨: `explicit`
- 기대 entity가 같은 문단 앞 문장의 유일한 명시 주체: `inherited`
- 다른 entity가 사건 문장의 명시 주체: `context.actor-drift` 오류
- 다른 entity만 가까운 선행사로 발견: `context.actor-unresolved` 검토
- 문단 경계 또는 복수 선행사로 확정 불가: `context.actor-unresolved` 검토

문단 경계를 넘겨 자동 상속하지 않는다. 틀린 확신보다 `review`를 우선한다.

## KoEditTrace

Core의 `trace` 명령은 원문/후보 hash와 변경 구간을 결정적으로 만든다. 별도의 전체
문서 필드는 만들지 않고 외부로 전송하지 않으며, Core가 파일이나 데이터베이스에
저장하지도 않는다. 다만 전체 교체라면 변경 구간이 전체 문서와 같아질 수 있으며
이 경우 `privacy.contains_full_documents=true`로 표시한다.

사람의 `accepted`, `rejected`, `partially_accepted`는 호출자가 명시한다. 엔진은
사용자의 침묵을 승인으로 추정하지 않는다. context report를 연결하면 해당 trace가
어떤 문맥 finding과 함께 검토됐는지 rule ID가 남는다.

## 자산 경계

공개 자산:

- contract/report/edit-trace schema
- 결정론적 resolver와 rule registry
- provenance·license·annotation 상태가 있는 KoContextBench schema
- domain/phenomenon slice 측정기와 clean-room development seed
- 블라인드 annotation package, 평가 응답, 합의도 계산 도구

고객 또는 Cloud 자산:

- 실제 고객 KoEditTrace
- 조직별 entity/policy/exception history
- reviewer 승인·거절과 override 이유
- verifier 보정값과 private holdout 결과

전역 학습에는 원문을 자동 합류시키지 않는다. opt-in trace에서도 반복되는 구조적
후보를 만든 뒤 반례 탐색, owner review, shadow policy, holdout, 명시적 승격을
거친다.

## 현재 한계

- 원문에서 entity/event를 자동 추출하지 않는다.
- 조사 기반 주체 탐지는 인용, 긴 관형절, 복합문을 완전히 분석하지 못한다.
- 부정 표현의 scope를 결정하지 않고 review로 보낸다.
- 인과관계와 주장/인용 귀속은 아직 contract schema에 없다.
- clean-room fixture 일치율은 실제 한국어 문서 정확도가 아니다.
- development seed 24쌍은 사람 평가를 받지 않아 성능 주장에 쓸 수 없다.
