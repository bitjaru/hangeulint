# AGENTS.md — HangeuLint

## Product contract

- HangeuLint는 AI 작성자 탐지기나 탐지 우회 도구가 아니다.
- 목표는 발행 가능한 한국어 품질, 원문 의미 보존, 유형 적합성이다.
- 공개 공통 규칙과 조직·브랜드별 비공개 policy를 분리한다.
- 단어 하나를 금지하기보다 문맥과 반복 밀도를 검사한다.
- 사람 글의 정상적인 다양성을 오탐하지 않는 것을 규칙 수보다 우선한다.

## Engineering rules

- 결정론적 검사와 LLM 기반 평가를 같은 점수로 섞지 않는다.
- 모든 규칙은 안정적인 ID, 실패 예제, 통과 반례를 가져야 한다.
- fixture 성능을 일반화된 AI 탐지 정확도로 홍보하지 않는다.
- 원문과 후보문을 저장하는 기능은 기본값으로 꺼져 있어야 한다.
- 시크릿, 고객 문서, 비공개 voice policy를 Git에 저장하지 않는다.

## Verification

```bash
PYTHONPATH=src python3 scripts/run_benchmark.py
PYTHONPATH=src python3 scripts/run_context_benchmark.py
PYTHONPATH=src python3 scripts/run_context_calibration.py
python3 -m unittest discover -s tests -v
```
