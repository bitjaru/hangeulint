import unittest

from hangeulint import build_edit_trace


class EditTraceTests(unittest.TestCase):
    def test_trace_is_deterministic_and_does_not_embed_full_documents(self):
        source = "운영팀이 오늘 원인을 조사합니다."
        candidate = "운영팀이 내일 원인을 조사합니다."
        first = build_edit_trace(source, candidate)
        second = build_edit_trace(source, candidate)
        self.assertEqual(first.trace_id, second.trace_id)
        self.assertEqual(first.edits, second.edits)
        self.assertFalse(first.privacy["persisted_by_core"])
        self.assertFalse(first.privacy["contains_full_documents"])
        self.assertEqual(first.edits[0].before, "오늘")
        self.assertEqual(first.edits[0].after, "내일")

    def test_trace_links_context_findings_without_raw_report(self):
        report = {
            "contract_id": "incident-v1",
            "findings": [
                {"rule_id": "context.actor-drift"},
                {"rule_id": "context.actor-drift"},
                {"rule_id": "context.time-anchor-missing"},
            ],
        }
        trace = build_edit_trace(
            "당사가 원인을 조사합니다.",
            "고객이 원인을 조사합니다.",
            decision="rejected",
            context_report=report,
        )
        self.assertEqual(trace.contract_id, "incident-v1")
        self.assertEqual(
            trace.context_finding_ids,
            ("context.actor-drift", "context.time-anchor-missing"),
        )
        self.assertEqual(trace.decision, "rejected")

    def test_identical_documents_have_no_edits(self):
        trace = build_edit_trace("같은 문장입니다.", "같은 문장입니다.")
        self.assertEqual(trace.edits, ())
        self.assertFalse(trace.privacy["contains_changed_text"])

    def test_full_replacement_sets_privacy_flag(self):
        trace = build_edit_trace("기존 문장", "새 출력")
        self.assertTrue(trace.privacy["contains_full_documents"])

    def test_invalid_decision_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "지원하지 않는 edit decision"):
            build_edit_trace("원문", "후보", decision="maybe")


if __name__ == "__main__":
    unittest.main()
