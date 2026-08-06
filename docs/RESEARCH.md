# Research basis

이 문서는 HangeuLint의 설계에 영향을 준 1차 자료와 적용 한계를 기록한다.
논문의 코드나 데이터는 복사하지 않았고, 라이선스가 불명확한 저장소는 방법론만
참조했다. 실행 시 사용되는 구조화 레지스트리는
`src/hangeulint/references/evidence.json`이다.

## 핵심 결론

### 1. ‘AI다운 특징’은 품질 점수가 아니다

KatFishNet은 한국어에서 띄어쓰기, 품사 n-gram 다양성, 쉼표 사용이 사람/LLM
텍스트 사이에서 달라질 수 있음을 보였지만 연구 목적은 작성 주체 탐지이며 차이는
장르 의존적이다.

- Park et al. (2025), [KatFishNet](https://aclanthology.org/2025.acl-long.1030/)

더 직접적인 경고도 있다. 영어-러시아어 번역 연구에서는 번역문/비번역문 특징이
두 집단은 거의 완벽하게 구분했지만 품질 등급 분류는 우연 수준을 조금 넘는 데
그쳤다. 한국어 번역투 연구 역시 번역투로 불리는 표현이 비번역 한국어에도 나타날
수 있다고 보고한다.

- Kunilovskaya & Lapshinova-Koltunski (2019),
  [Translationese Features as Indicators of Quality](https://aclanthology.org/W19-8706/)
- Choi (2016),
  [Revisiting the Concept of Translationese](https://doi.org/10.15749/jts.2016.17.1.007)

따라서 쉼표, 간격, 품사 다양성은 `telemetry_only`다. 규칙도 단어 금지보다
문맥·반복·밀도를 검사한다.

짧은 뉴스 댓글을 다룬 XDAC과 여러 도메인·모델군을 다룬 한국어 비지도 탐지
연구도 같은 경계를 강화한다. 두 연구 모두 탐지 과제이므로 해당 성능을 품질
성능으로 가져오지 않고, 유형별 보정과 국소 설명이라는 방법론만 반영한다.

- Go et al. (2025), [XDAC](https://aclanthology.org/2025.acl-long.1108/)
- Jeon et al. (2026),
  [Unsupervised Detection Using Syntactic and Semantic Cues](https://aclanthology.org/2026.findings-eacl.77/)

### 2. 한국어 격식과 의미는 분리해서 보존해야 한다

StyleKQC는 한국어 질문과 명령의 바꿔쓰기를 핵심 내용/의도와 격식 변환 문제로
구성했다. Kosmic은 의미 중심 유사도만으로는 한국어 높임말 차이를 놓친다는 점을
보이고 의미와 톤을 함께 평가하는 별도 모델을 제시했다.

- Cho et al. (2022), [StyleKQC](https://aclanthology.org/2022.lrec-1.771/)
- Hwang et al. (2024), [Kosmic](https://aclanthology.org/2024.lrec-main.870/)

그래서 HangeuLint는 `naturalness`, `register`, `task_fit`, `fidelity`를 합산하지
않는다. 같은 뜻이라도 업무 메시지의 높임말이 바뀌면 별도 문제다.

### 3. 의미 보존은 국소적이고 예제 수준이어야 한다

TRUE는 데이터셋 전체 상관계수만으로는 개별 예문의 일관성 성능을 알기 어렵다고
지적했고, 여러 과제에서 NLI와 QA 기반 방식이 상호 보완적임을 보였다.
QASemConsistency는 오류를 최소 술어-논항 명제로 나눠 어느 부분이 근거 없이
바뀌었는지 찾는 방향을 제시한다.

- Honovich et al. (2022), [TRUE](https://aclanthology.org/2022.naacl-main.287/)
- Cattan et al. (2026),
  [Localizing Factual Inconsistencies](https://aclanthology.org/2026.tacl-1.6/)

v0.1은 이 방향의 하한선으로 수치·날짜·URL·식별자를 유형별로 국소화한다. 부정
표현 수가 바뀌면 유사도 점수를 꾸며내지 않고 `review`를 반환한다.

한국어 담화 번역 testset은 어휘 중의성, 영형 대용, 속어, 관용어, 비유, 함축처럼
문장만 봐서는 보존 여부를 판단하기 어려운 현상을 따로 구성했다. 번역 방향은
한국어→영어지만, HangeuLint semantic evaluator가 문장 유사도 하나에 기대면 안
된다는 범위 근거로 사용한다.

- Lee et al. (2025),
  [Context-Aware Korean-to-English Testset](https://aclanthology.org/2025.coling-main.110/)

### 4. 다양성은 단문 lint가 아니라 batch 품질이다

언어 다양성은 어휘·구문·의미 차원으로 나뉘며 생성 시스템 전체의 분포로 보는
편이 맞다.

- Guo et al. (2025),
  [Benchmarking Linguistic Diversity of LLMs](https://aclanthology.org/2025.tacl-1.69/)

향후 반복 hook, 종결어미, 문장 구조의 다양성은 여러 출력 묶음에서 측정한다.
짧은 문서 하나를 ‘다양성 부족’으로 낙제시키지 않는다.

### 5. LLM judge는 독립된 실험 계층이다

대규모 비교 연구에서 LLM judge의 위치 편향은 우연이 아니며 judge와 과제에 따라
달라졌다.

- Shi et al. (2025),
  [Judging the Judges](https://aclanthology.org/2025.ijcnlp-long.18/)

따라서 향후 judge는 결정론적 코어와 분리하고, 후보 위치 교환, 반복 안정성,
원어민 평가와의 보정을 통과한 경우에만 보조 신호로 쓴다.

### 6. 평균 말투 대신 검토 가능한 style hypothesis를 쓴다

HyPerAlign은 소수의 사용자 글에서 communication strategy와 writing style 가설을
먼저 추출한 뒤 개인화에 사용하는 방식을 제안한다. HangeuLint는 이 아이디어를
한국어 품질 수치로 직접 전용하지 않고, 생성 후보가 어떤 가설을 사용했는지
`hypothesis_ids`로 감사 가능하게 만드는 데 적용한다.

- Garbacea & Tan (2025), [HyPerAlign](https://arxiv.org/abs/2505.00038)

한국어·범용 humanizer와 factual consistency 오픈소스의 구현·라이선스·도입 경계는
[OPEN_SOURCE_METHODS.md](OPEN_SOURCE_METHODS.md)에 별도로 기록한다.

## 도구와 라이선스 결정

- HangeuLint Core와 자체 fixture: Apache-2.0.
- 논문: 인용과 방법론만 사용.
- KatFishNet, StyleKQC 등 연결 저장소: 검토 당시 명시적 라이선스가 확인되지 않아
  코드·데이터를 포함하지 않음.
- `kiwipiepy`: 선택 설치되는 LGPL 라이브러리. 기본 의존성이 아니며 배포물에
  모델이나 코드를 번들하지 않음.
- KLUE: 향후 semantic evaluator 연구 후보. CC BY-SA 4.0 조건과 파생물 경계를
  별도로 검토한 뒤 도입.

## 아직 근거가 없는 것

- HangeuLint가 사람의 편집 시간을 줄인다는 주장
- starter pack이 한국어 전체에 일반화된다는 주장
- 특정 모델 또는 humanizer보다 낫다는 주장
- finding이 AI 생성의 증거라는 주장

이 네 주장은 [EVALUATION.md](EVALUATION.md)의 실험을 통과하기 전까지 제품 문구에
사용하지 않는다.
