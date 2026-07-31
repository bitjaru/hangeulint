# HangeuLint

> ESLint for Korean AI output.

HangeuLint는 AI가 만든 한국어를 발행 전에 검사하는 오픈소스 품질 게이트입니다.
작성자가 사람인지 AI인지 추정하지 않습니다. 대신 문장이 쓰일 곳에 맞는지,
높임말과 격식이 유지되는지, 원문의 수치·날짜·URL·용어가 보존됐는지, 문서 앞에서
정한 주체·사건·시간 관계가 뒤에서도 유지되는지를 각각 확인합니다.

## 왜 또 다른 humanizer가 아닌가

‘AI다운 특징’과 저품질은 같은 개념이 아닙니다. 번역투 연구에서도 번역문과
비번역문을 구분하는 특징이 품질 등급은 거의 구분하지 못했고, 한국어 연구는
쉼표·띄어쓰기·품사 다양성의 차이가 장르에 따라 달라짐을 보였습니다. 그래서
HangeuLint는 다음을 하지 않습니다.

- AI 작성 확률이나 ‘사람다움’ 점수를 만들지 않습니다.
- 쉼표, 특정 단어, 짧은 문장 하나만으로 실패시키지 않습니다.
- 자연스러움과 의미 보존을 하나의 불투명한 점수로 섞지 않습니다.
- 출처가 불명확한 규칙 모음이나 연구 데이터를 복사하지 않습니다.

대신 결과를 `naturalness`, `register`, `task_fit`, `fidelity`, `risk` 축으로
분리합니다. 현재 코어는 앞의 네 축 중 결정론적으로 확인 가능한 범위만 평가하고,
평가하지 못한 축은 `not_evaluated`로 남깁니다.

## 현재 구현

`v0.3.0`은 외부 모델을 호출하지 않는 클린룸 기반 코어입니다.

- `social`, `work-message` 유형 pack
- 규칙마다 안정적인 ID, 적용 축, 신뢰도, 근거 ID, 실패 예시, 통과 반례
- 수치·금액·날짜·시간·URL·이메일·코드·보호 용어 보존 게이트
- 부정 표현 수가 바뀌면 자동 의미 판정 대신 `review` 신호
- 명시적 `KoContextContract` 기반 document-level 사건 검사
- 같은 문단 안의 제한된 한국어 생략 주체 상속
- 주체 변경, 필수 사건·시간 누락, 부정 여부 변화의 국소 finding
- 원문–후보 변경과 사람 채택 상태를 연결하는 무저장 `KoEditTrace`
- 쉼표 분포와 종결 방식 텔레메트리
- 선택형 Kiwi 형태소 텔레메트리
- JSON schema version, CI 종료 코드, 근거 목록 CLI

현재 포함하지 않는 것:

- AI 작성 여부 판정 또는 탐지 우회
- 일반 사실 확인
- 원문에서 context contract 자동 추출
- 완전한 문장 단위 의미 동등성·인과·인용 귀속 판정
- 자동 재작성
- 대표 말뭉치에서 보정된 성능 수치

## 실행

```bash
PYTHONPATH=src python3 -m hangeulint packs
PYTHONPATH=src python3 -m hangeulint evidence
PYTHONPATH=src python3 -m hangeulint check \
  examples/social_bad.txt --pack social
PYTHONPATH=src python3 -m hangeulint compare \
  examples/source.txt examples/candidate_changed.txt \
  --pack work-message --protect HangeuLint --strict-review
PYTHONPATH=src python3 -m hangeulint context-check \
  examples/context-contract.json examples/context-candidate.txt --json
PYTHONPATH=src python3 -m hangeulint trace \
  examples/source.txt examples/candidate_changed.txt \
  --decision rejected
PYTHONPATH=src python3 -m hangeulint context-benchmark \
  benchmarks/context/seed-v0.1.json
```

개발 설치:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
hangeulint check examples/social_bad.txt --pack social --json
```

Kiwi 기반 품사 텔레메트리는 선택 기능입니다. 이 값은 자체 한국어 코퍼스로
보정되기 전까지 통과/실패에 쓰지 않습니다.

```bash
pip install -e '.[morphology]'
hangeulint check draft.txt --pack social --morphology kiwi --json
```

검사 통과는 종료 코드 `0`, 게이트 실패는 `2`, 실행 오류는 `1`입니다.
`compare --strict-review`를 쓰면 결정론적 앵커는 보존됐더라도 부정 표현 변화 같은
검토 신호가 있을 때 실패 처리합니다.

`context-check`는 entity와 event를 선언한 JSON 계약을 받습니다. 사건 문장에 주체가
생략되면 같은 문단의 제한된 앞 문장에서 명시 주체를 찾습니다. 확정할 수 없는
경우 추측해서 통과시키지 않고 `review`를 반환합니다. `--strict-review`를 붙이면
CI에서 review도 종료 코드 `2`로 처리합니다.

```text
PASS  context  contract=customer-incident-notice-v1  errors=0  reviews=0
- [resolved] investigate-root-cause: actor=company/inherited sentence=1
```

`trace`는 별도의 전체 문서 필드 없이 hash와 변경 구간을 JSON으로 출력합니다. 명령
자체도 파일이나 서버에 결과를 보존하지 않습니다. 전체 교체라면 변경 구간이 전체
문서와 같아질 수 있고 privacy flag로 표시됩니다. Cloud 저장은 별도 동의와 보존
정책이 필요합니다.

`context-benchmark`는 전체 결과를 하나의 점수로만 보여주지 않습니다. 도메인과
문맥 현상별 상태 일치, finding precision/recall, claim blocker를 분리합니다. 현재
development seed는 24개 자체 제작 예문이며 사람 평가가 없어 성능 주장에는 사용할
수 없습니다.

## 결과 예시

```text
FAIL  social  errors=1/0  warnings=1/2
dimensions: naturalness=pass_with_info, register=pass,
task_fit=fail, risk=not_evaluated, fidelity=not_evaluated
- [error/high] social.fragmented-lines: 짧은 줄이 연속되어 본문이 카드뉴스처럼 끊깁니다.
```

점수 대신 게이트 예산과 축별 상태를 보여줍니다. `check`는 후보문만 보므로
`fidelity=not_evaluated`가 정상이며, 원문이 있으면 `compare`를 사용해야 합니다.

## 근거와 한계

연구에서 가져온 것은 ‘사람처럼 보이게 만드는 요령’이 아니라 평가 구조입니다.

- 한국어 형식 변환은 핵심 의도와 격식을 함께 다뤄야 합니다.
- 의미 유사도와 높임말/톤 보존은 별도 축이어야 합니다.
- 번역투나 LLM 분포 신호는 곧바로 저품질 판정이 될 수 없습니다.
- 의미 보존은 전체 점수보다 누락된 수치·주장 위치를 보여주는 편이 유용합니다.
- LLM judge는 위치 편향 등이 있어 결정론적 결과와 분리하고 보정해야 합니다.

전체 문헌, 적용 범위, 라이선스 검토는
[docs/RESEARCH.md](docs/RESEARCH.md), 평가 계획은
[docs/EVALUATION.md](docs/EVALUATION.md), 문맥 엔진 계약은
[docs/CONTEXT_ENGINE.md](docs/CONTEXT_ENGINE.md)에 기록했습니다. 런타임에서는
`hangeulint evidence`로 동일한 근거 레지스트리를 조회할 수 있습니다.

## 검증

```bash
PYTHONPATH=src python3 scripts/run_benchmark.py
PYTHONPATH=src python3 scripts/run_context_benchmark.py
PYTHONPATH=src python3 scripts/run_context_calibration.py
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

두 fixture 일치율은 구현 회귀 검사일 뿐 일반화된 정확도나 AI 탐지 성능이 아닙니다.
공개 성능 주장은 한국어 원어민 블라인드 평가, 평가자 간 합의도, 신뢰구간,
유형별 오탐률을 갖춘 뒤에만 게시합니다.

## 오픈소스와 SaaS

Core는 Apache-2.0으로 공개합니다. 계약·검사·trace 형식도 공개합니다. 유료 제품은
고객 문서에서 실제로 쌓이는 비공개 KoEditTrace, 팀별 정책 버전 관리, 사람 수정
피드백, verifier 보정, 비공개 holdout, 승인·감사·롤백, 모델/프롬프트 회귀 추적,
배포 연동에서 가치를 만듭니다. 경계는 [docs/OPEN_CORE.md](docs/OPEN_CORE.md)에
정리했고, 제품 가설과 중단 기준은 [docs/PRODUCT.md](docs/PRODUCT.md)에 명시했습니다.

## 라이선스

Apache License 2.0. 연구 저장소의 코드나 데이터는 포함하지 않습니다. 선택형
`kiwipiepy`는 별도 설치되는 LGPL 라이브러리이며 HangeuLint 배포물에 번들하지
않습니다.
