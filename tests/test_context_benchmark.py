import contextlib
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path

from hangeulint.cli import main as cli_main
from hangeulint.context_annotation import (
    aggregate_annotation_responses,
    validate_annotation_response,
)
from hangeulint.context_benchmark import (
    build_annotation_package,
    evaluate_context_benchmark,
    load_context_benchmark,
    validate_context_benchmark,
)
from scripts.prepare_context_annotation import main as prepare_annotation_main

_ROOT = Path(__file__).resolve().parents[1]
_SEED_PATH = _ROOT / "benchmarks" / "context" / "seed-v0.1.json"


def _response(package, rater_id, *, change_first=False):
    statuses = ("pass", "review", "fail")
    items = []
    for index, item in enumerate(package["items"]):
        status = statuses[index % len(statuses)]
        finding_ids = []
        actor_resolution = "explicit"
        if change_first and index == 0:
            status = "fail" if status != "fail" else "pass"
            finding_ids = ["context.actor-drift"]
            actor_resolution = "explicit_other"
        items.append(
            {
                "annotation_id": item["annotation_id"],
                "status": status,
                "finding_ids": finding_ids,
                "actor_resolution": actor_resolution,
                "rationale": "문맥 계약과 후보문을 대조했습니다.",
            }
        )
    return {
        "schema_version": "0.1",
        "package_id": package["package_id"],
        "rater_id": rater_id,
        "items": items,
    }


class ContextBenchmarkTests(unittest.TestCase):
    def test_seed_is_balanced_and_claim_blocked(self):
        dataset = load_context_benchmark(_SEED_PATH)
        report = evaluate_context_benchmark(dataset)
        self.assertEqual(report["summary"]["cases"], 24)
        self.assertEqual(report["engine_version"], "0.4.0")
        self.assertEqual(report["summary"]["fully_matched"], 24)
        self.assertFalse(report["claim_readiness"]["publishable"])
        self.assertEqual(
            {
                domain: metrics["cases"]
                for domain, metrics in report["slices"]["domain"].items()
            },
            {"customer-reply": 8, "incident-notice": 8, "report": 8},
        )
        blockers = " ".join(report["claim_readiness"]["blockers"])
        self.assertIn("300개 미만", blockers)
        self.assertIn("평가자", blockers)
        self.assertIn("사전 등록", blockers)
        self.assertIn("holdout", blockers)

    def test_public_dataset_rejects_nonredistributable_case(self):
        dataset = load_context_benchmark(_SEED_PATH)
        dataset["release_level"] = "public_calibration"
        dataset["cases"][0]["source"]["redistribution_allowed"] = False
        with self.assertRaisesRegex(ValueError, "재배포 불가"):
            validate_context_benchmark(dataset)

    def test_unknown_gold_rule_is_rejected(self):
        dataset = load_context_benchmark(_SEED_PATH)
        dataset["cases"][0]["gold"]["finding_ids"] = ["context.invented"]
        with self.assertRaisesRegex(ValueError, "알 수 없는 rule"):
            validate_context_benchmark(dataset)

    def test_unknown_case_field_is_rejected(self):
        dataset = load_context_benchmark(_SEED_PATH)
        dataset["cases"][0]["model_name"] = "hidden shortcut"
        with self.assertRaisesRegex(ValueError, "알 수 없는 필드"):
            validate_context_benchmark(dataset)

    def test_annotation_package_is_deterministic_and_blinded(self):
        dataset = load_context_benchmark(_SEED_PATH)
        first, first_key = build_annotation_package(dataset, seed=42)
        second, second_key = build_annotation_package(dataset, seed=42)
        self.assertEqual(first, second)
        self.assertEqual(first_key, second_key)
        self.assertFalse(first["gold_included"])
        self.assertFalse(first["case_ids_included"])
        serialized = json.dumps(first, ensure_ascii=False)
        self.assertNotIn('"gold"', serialized)
        self.assertNotIn("incident-explicit-pass", serialized)
        self.assertEqual(len(first["items"]), 24)
        self.assertEqual(len(first_key), 24)

    def test_annotation_response_requires_every_item(self):
        dataset = load_context_benchmark(_SEED_PATH)
        package, _ = build_annotation_package(dataset, seed=1)
        response = _response(package, "rater-a")
        response["items"].pop()
        with self.assertRaisesRegex(ValueError, "응답하지 않은"):
            validate_annotation_response(package, response)

    def test_perfect_annotation_agreement_scores_one(self):
        dataset = load_context_benchmark(_SEED_PATH)
        package, _ = build_annotation_package(dataset, seed=1)
        report = aggregate_annotation_responses(
            package,
            [
                _response(package, "rater-a"),
                _response(package, "rater-b"),
            ],
            required_raters=2,
        )
        self.assertTrue(report["ready_for_adjudication"])
        self.assertEqual(report["status_fleiss_kappa"], 1.0)
        self.assertEqual(report["items_needing_adjudication"], 0)

    def test_annotation_disagreement_requires_adjudication(self):
        dataset = load_context_benchmark(_SEED_PATH)
        package, _ = build_annotation_package(dataset, seed=1)
        report = aggregate_annotation_responses(
            package,
            [
                _response(package, "rater-a"),
                _response(package, "rater-b", change_first=True),
            ],
            required_raters=2,
        )
        self.assertLess(report["status_fleiss_kappa"], 1.0)
        self.assertGreaterEqual(report["items_needing_adjudication"], 1)

    def test_duplicate_rater_is_rejected(self):
        dataset = load_context_benchmark(_SEED_PATH)
        package, _ = build_annotation_package(dataset, seed=1)
        response = _response(package, "rater-a")
        with self.assertRaisesRegex(ValueError, "rater_id"):
            aggregate_annotation_responses(
                package,
                [response, copy.deepcopy(response)],
                required_raters=2,
            )

    def test_context_benchmark_cli_reports_nonpublishable_seed(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = cli_main(["context-benchmark", str(_SEED_PATH)])
        self.assertEqual(code, 0)
        self.assertIn("matched=24/24", output.getvalue())
        self.assertIn("publishable=False", output.getvalue())

    def test_prepare_annotation_script_writes_separate_package_and_key(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            package_path = Path(temp_dir) / "package.json"
            key_path = Path(temp_dir) / "key.json"
            with contextlib.redirect_stdout(io.StringIO()):
                code = prepare_annotation_main(
                    [
                        str(_SEED_PATH),
                        "--output",
                        str(package_path),
                        "--key-output",
                        str(key_path),
                        "--seed",
                        "7",
                    ]
                )
            package = json.loads(package_path.read_text(encoding="utf-8"))
            key = json.loads(key_path.read_text(encoding="utf-8"))
        self.assertEqual(code, 0)
        self.assertEqual(len(package["items"]), 24)
        self.assertEqual(len(key), 24)
        self.assertNotEqual(package, key)


if __name__ == "__main__":
    unittest.main()
