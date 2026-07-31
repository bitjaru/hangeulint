import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from hangeulint.cli import main


class CliTests(unittest.TestCase):
    def test_check_returns_two_when_gate_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "draft.txt"
            path.write_text("첫 줄\n둘째 줄\n셋째 줄\n넷째 줄", encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(["check", str(path), "--pack", "social"])
        self.assertEqual(code, 2)
        self.assertIn("FAIL", output.getvalue())

    def test_packs_lists_starter_packs(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main(["packs"])
        self.assertEqual(code, 0)
        self.assertIn("social", output.getvalue())
        self.assertIn("work-message", output.getvalue())

    def test_evidence_lists_primary_sources(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main(["evidence"])
        self.assertEqual(code, 0)
        self.assertIn("HGL-REF-001", output.getvalue())
        self.assertIn("aclanthology.org", output.getvalue())

    def test_compare_strict_review_fails_on_polarity_change(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "source.txt"
            candidate = Path(temp_dir) / "candidate.txt"
            source.write_text("주문을 취소합니다.", encoding="utf-8")
            candidate.write_text("주문을 취소하지 않습니다.", encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(
                    [
                        "compare",
                        str(source),
                        str(candidate),
                        "--pack",
                        "work-message",
                        "--strict-review",
                    ]
                )
        self.assertEqual(code, 2)
        self.assertIn("REVIEW  fidelity", output.getvalue())

    def test_context_check_reports_inherited_zero_subject(self):
        contract_payload = {
            "schema_version": "0.1",
            "contract_id": "incident-v1",
            "task": "장애 공지",
            "entities": [
                {
                    "id": "company",
                    "label": "당사",
                    "mentions": ["당사", "운영팀"],
                }
            ],
            "events": [
                {
                    "id": "investigate",
                    "actor": "company",
                    "action_terms": ["조사"],
                    "object_terms": ["원인"],
                    "time_terms": ["내일까지"],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            contract = Path(temp_dir) / "contract.json"
            candidate = Path(temp_dir) / "candidate.txt"
            contract.write_text(
                json.dumps(contract_payload, ensure_ascii=False),
                encoding="utf-8",
            )
            candidate.write_text(
                "운영팀이 오류를 확인했습니다. 원인을 조사해 내일까지 알리겠습니다.",
                encoding="utf-8",
            )
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(["context-check", str(contract), str(candidate), "--json"])
        self.assertEqual(code, 0)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["status"], "pass")
        self.assertEqual(
            payload["resolved_events"][0]["actor_resolution"],
            "inherited",
        )

    def test_context_check_strict_review_returns_two(self):
        contract_payload = {
            "schema_version": "0.1",
            "contract_id": "incident-v1",
            "task": "장애 공지",
            "entities": [
                {
                    "id": "company",
                    "label": "당사",
                    "mentions": ["당사", "운영팀"],
                }
            ],
            "events": [
                {
                    "id": "investigate",
                    "actor": "company",
                    "action_terms": ["조사"],
                    "object_terms": ["원인"],
                    "polarity": "affirmed",
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            contract = Path(temp_dir) / "contract.json"
            candidate = Path(temp_dir) / "candidate.txt"
            contract.write_text(
                json.dumps(contract_payload, ensure_ascii=False),
                encoding="utf-8",
            )
            candidate.write_text(
                "운영팀이 원인을 조사하지 않습니다.",
                encoding="utf-8",
            )
            with contextlib.redirect_stdout(io.StringIO()):
                code = main(
                    [
                        "context-check",
                        str(contract),
                        str(candidate),
                        "--strict-review",
                    ]
                )
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
