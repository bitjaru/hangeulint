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
