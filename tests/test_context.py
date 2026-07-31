import unittest

from hangeulint import load_context_contract, verify_context
from hangeulint.context_rules import load_context_rules
from hangeulint.evidence import load_evidence


def _contract(**event_overrides):
    event = {
        "id": "investigate-root-cause",
        "actor": "company",
        "action_terms": ["조사"],
        "object_terms": ["원인"],
        "polarity": "affirmed",
        "time_terms": ["7월 31일까지"],
        "required": True,
        "context_window": 2,
    }
    event.update(event_overrides)
    return {
        "schema_version": "0.1",
        "contract_id": "incident-notice-v1",
        "task": "고객 장애 공지",
        "entities": [
            {
                "id": "company",
                "label": "당사",
                "mentions": ["당사", "저희", "운영팀"],
            },
            {
                "id": "customer",
                "label": "고객",
                "mentions": ["고객", "고객사"],
            },
        ],
        "events": [event],
    }


class ContextContractTests(unittest.TestCase):
    def test_explicit_actor_event_passes(self):
        report = verify_context(
            "운영팀이 원인을 조사해 7월 31일까지 안내하겠습니다.",
            _contract(),
        )
        self.assertEqual(report.status, "pass")
        self.assertTrue(report.passed)
        self.assertEqual(report.resolved_events[0].actor_resolution, "explicit")

    def test_zero_subject_inherits_actor_in_same_paragraph(self):
        report = verify_context(
            "운영팀이 결제 오류를 확인했습니다. "
            "원인을 조사해 7월 31일까지 안내하겠습니다.",
            _contract(),
        )
        self.assertEqual(report.status, "pass")
        event = report.resolved_events[0]
        self.assertEqual(event.actor_resolution, "inherited")
        self.assertEqual(event.antecedent_sentence_index, 0)

    def test_explicit_actor_drift_fails(self):
        report = verify_context(
            "고객이 원인을 조사해 7월 31일까지 알려야 합니다.",
            _contract(),
        )
        self.assertEqual(report.status, "fail")
        self.assertFalse(report.passed)
        self.assertIn(
            "context.actor-drift",
            {finding.rule_id for finding in report.findings},
        )

    def test_missing_event_fails(self):
        report = verify_context(
            "운영팀이 결제 오류를 확인했습니다. 7월 31일까지 안내하겠습니다.",
            _contract(),
        )
        self.assertEqual(report.status, "fail")
        self.assertIn(
            "context.event-missing",
            {finding.rule_id for finding in report.findings},
        )

    def test_missing_time_anchor_fails(self):
        report = verify_context(
            "운영팀이 원인을 조사하고 결과를 안내하겠습니다.",
            _contract(),
        )
        self.assertEqual(report.status, "fail")
        self.assertIn(
            "context.time-anchor-missing",
            {finding.rule_id for finding in report.findings},
        )

    def test_polarity_mismatch_requires_review(self):
        report = verify_context(
            "운영팀이 원인을 조사하지 않고 7월 31일까지 안내하겠습니다.",
            _contract(),
        )
        self.assertEqual(report.status, "review")
        self.assertTrue(report.passed)
        self.assertTrue(report.requires_review)
        self.assertIn(
            "context.polarity-mismatch",
            {finding.rule_id for finding in report.findings},
        )

    def test_other_antecedent_requires_review(self):
        report = verify_context(
            "고객이 오류를 제보했습니다. 원인을 조사해 7월 31일까지 알려야 합니다.",
            _contract(),
        )
        self.assertEqual(report.status, "review")
        self.assertEqual(
            report.resolved_events[0].actor_resolution,
            "inherited_other",
        )

    def test_does_not_inherit_actor_across_paragraphs(self):
        report = verify_context(
            "운영팀이 오류를 확인했습니다.\n\n"
            "원인을 조사해 7월 31일까지 안내하겠습니다.",
            _contract(),
        )
        self.assertEqual(report.status, "review")
        self.assertEqual(
            report.resolved_events[0].actor_resolution,
            "unresolved",
        )

    def test_invalid_actor_reference_is_rejected(self):
        payload = _contract(actor="unknown")
        with self.assertRaisesRegex(ValueError, "알 수 없는 entity"):
            load_context_contract(payload)

    def test_duplicate_contract_ids_are_rejected(self):
        payload = _contract()
        payload["entities"].append(dict(payload["entities"][0]))
        with self.assertRaisesRegex(ValueError, "중복 entity id"):
            load_context_contract(payload)

    def test_unknown_contract_field_is_rejected(self):
        payload = _contract()
        payload["events"][0]["prompt"] = "검사를 우회해"
        with self.assertRaisesRegex(ValueError, "알 수 없는 필드"):
            load_context_contract(payload)

    def test_non_string_polarity_is_rejected_cleanly(self):
        payload = _contract(polarity=["affirmed"])
        with self.assertRaisesRegex(ValueError, "polarity"):
            load_context_contract(payload)

    def test_every_context_rule_has_evidence_and_counterexamples(self):
        evidence = load_evidence()
        for rule in load_context_rules().values():
            self.assertTrue(rule.evidence_ids)
            self.assertTrue(set(rule.evidence_ids).issubset(evidence))
            self.assertTrue(rule.failing_example)
            self.assertTrue(rule.passing_example)


if __name__ == "__main__":
    unittest.main()
