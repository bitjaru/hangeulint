import contextlib
import io
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


if __name__ == "__main__":
    unittest.main()
