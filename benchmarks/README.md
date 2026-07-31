# Benchmarks

현재 `fixtures/*.jsonl`은 규칙 구현이 바뀌지 않았는지 확인하는 클린룸 회귀
fixture다. 실제 사용자 문서, 논문 데이터, 경쟁 프로젝트의 예문을 복사하지 않았다.

각 행은 다음 필드를 가질 수 있다.

- `id`
- `pack`
- `text`
- `expected_pass`
- `expected_rules`
- `forbidden_rules`

실행:

```bash
PYTHONPATH=src python3 scripts/run_benchmark.py
```

출력의 `match_rate`는 fixture와 현재 구현의 일치율이다. 대표 말뭉치의 accuracy,
AI 탐지율, 실제 오탐률이 아니다. 공개 성능은 `docs/EVALUATION.md`의 별도
KoOutputBench에서만 산출한다.

## KoContextBench v0

`context/fixtures/v0.jsonl`은 명시적 문맥 계약에 대한 클린룸 최소쌍이다.

- 명시 주체
- 같은 문단 안에서 생략된 주체
- 잘못 연결된 주체
- 필수 사건 누락
- 시간 앵커 누락
- 부정 여부 변화
- 문단 경계를 넘는 잘못된 주체 상속

실행:

```bash
PYTHONPATH=src python3 scripts/run_context_benchmark.py
```

이 fixture는 문맥 엔진의 계약과 회귀를 고정한다. 8개 예문 일치율을 한국어 전체
문맥 이해 정확도나 경쟁 제품 대비 성능으로 홍보하면 안 된다. 대표성을 갖춘
`KoContextBench`는 실제 문서 출처, 현상별 slice, 원어민 복수 평가와 비공개
holdout을 별도로 가져야 한다.
