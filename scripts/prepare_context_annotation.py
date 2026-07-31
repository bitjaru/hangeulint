from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from hangeulint.context_benchmark import (
    build_annotation_package,
    load_context_benchmark,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="KoContextBench 블라인드 annotation package 생성",
    )
    parser.add_argument("dataset", help="KoContextBench JSON")
    parser.add_argument("--output", required=True, help="gold 없는 package 출력 경로")
    parser.add_argument(
        "--key-output",
        required=True,
        help="annotation ID와 내부 case ID 매핑 출력 경로",
    )
    parser.add_argument("--seed", type=int, default=20260731)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    output = Path(args.output)
    key_output = Path(args.key_output)
    if output.resolve() == key_output.resolve():
        print("package와 key 출력 경로는 달라야 합니다.", file=sys.stderr)
        return 1
    try:
        package, key = build_annotation_package(
            load_context_benchmark(args.dataset),
            seed=args.seed,
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        key_output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(package, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        key_output.write_text(
            json.dumps(key, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"annotation_items={len(package['items'])}")
        print(f"package={output}")
        print(f"key={key_output}")
        return 0
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"prepare-context-annotation: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
