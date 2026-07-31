# Contributing

HangeuLint는 규칙 수보다 오탐을 줄이는 일을 우선합니다.

## 규칙을 제안할 때

다음을 함께 제출해 주세요.

1. 문제가 드러나는 실제형 예문
2. 사람이 자연스럽게 고친 예문
3. 해당 표현이 허용되어야 하는 반례
4. 규칙이 적용될 pack
5. `naturalness`, `register`, `task_fit`, `risk` 중 적용 축
6. 논문·코퍼스·공식 문서 또는 clean-room pilot 근거
7. 적용 범위와 알려진 오탐 조건

특정 단어가 AI 글에 자주 나온다는 이유만으로 금칙어를 추가하지 않습니다. 문맥상
정상적인 사람 글까지 막는 규칙은 채택하지 않습니다.

## 로컬 검증

```bash
PYTHONPATH=src python3 scripts/run_benchmark.py
python3 -m unittest discover -s tests -v
```

새 규칙에는 최소 하나의 실패 예제와 하나의 통과 반례 테스트가 필요합니다.
pack JSON의 `evidence_ids`는 등록된
`src/hangeulint/references/evidence.json` 항목만 참조할 수 있습니다.

외부 저장소의 코드, 데이터, 규칙 카탈로그를 가져오려면 먼저 라이선스와 출처를
확인해야 합니다. 라이선스가 없거나 불명확한 자료는 복사하지 마세요.
