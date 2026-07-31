import unittest

from hangeulint import analyze, compare_anchors, extract_anchors
from hangeulint.evidence import load_evidence
from hangeulint.packs import available_packs, load_pack


class AnalyzerTests(unittest.TestCase):
    def test_social_pack_flags_fragmented_lines(self):
        text = "\n".join(["첫 줄", "둘째 줄", "셋째 줄", "넷째 줄", "다섯째 줄"])
        report = analyze(text, "social")
        self.assertFalse(report.passed)
        self.assertIn(
            "social.fragmented-lines",
            {finding.rule_id for finding in report.findings},
        )

    def test_social_pack_accepts_natural_paragraphs(self):
        text = (
            "이번 업데이트에서는 반복 작업을 줄였습니다. "
            "문서를 열 때마다 같은 설정을 다시 고르지 않아도 됩니다.\n\n"
            "팀에서 먼저 일주일 동안 써보고 불편한 부분을 고치겠습니다."
        )
        self.assertTrue(analyze(text, "social").passed)

    def test_attachment_section_is_not_treated_as_fragmentation(self):
        text = (
            "이번 컬러는 볼수록 맑아 보여요.\n\n"
            "[📎 첨부 제안]\n"
            "유형: 이미지\n"
            "추천 컷: 착용 컷\n"
            "이유: 실제 크기를 보여주기 좋음"
        )
        self.assertTrue(analyze(text, "social").passed)

    def test_work_message_flags_stacked_honorific(self):
        report = analyze(
            "자료 확인 가능하실 수 있을까요? 오늘 중 의견을 주세요.",
            "work-message",
        )
        self.assertFalse(report.passed)
        self.assertIn(
            "work-message.stacked-honorific",
            {finding.rule_id for finding in report.findings},
        )

    def test_extracts_numbers_urls_and_identifiers(self):
        anchors = extract_anchors(
            "고객 12명에게 https://example.com/alpha 안내. 코드는 CX-204."
        )
        self.assertEqual(anchors["12명"], 1)
        self.assertEqual(anchors["https://example.com/alpha"], 1)
        self.assertEqual(anchors["CX-204"], 1)
        self.assertNotIn("204", anchors)

    def test_abstract_density_does_not_flag_one_normal_term(self):
        report = analyze(
            "제품 경험을 바꾸기보다 결제 단계를 한 번 줄였습니다.",
            "social",
        )
        self.assertNotIn(
            "social.abstract-brand-density",
            {finding.rule_id for finding in report.findings},
        )

    def test_fidelity_passes_when_anchors_are_preserved(self):
        source = "7월 31일까지 12명에게 https://example.com 안내. 코드 CX-204."
        candidate = "코드 CX-204 관련 안내를 7월 31일까지 12명에게 보냅니다. https://example.com"
        report = compare_anchors(source, candidate)
        self.assertTrue(report.passed)
        self.assertEqual(report.status, "pass")
        self.assertEqual(report.missing, {})

    def test_fidelity_fails_on_missing_and_added_numbers(self):
        source = "고객 12명에게 보냅니다."
        candidate = "고객 10명에게 2회 보냅니다."
        report = compare_anchors(source, candidate)
        self.assertFalse(report.passed)
        self.assertEqual(report.missing["quantity"]["12명"], 1)
        self.assertEqual(report.added["quantity"]["10명"], 1)
        self.assertEqual(report.added["quantity"]["2회"], 1)

    def test_fidelity_types_dates_times_and_protected_terms(self):
        source = "HangeuLint 배포는 2026-07-31 오후 3시입니다."
        candidate = "배포 시각은 2026-07-31 오후 4시입니다."
        report = compare_anchors(source, candidate, ["HangeuLint"])
        self.assertFalse(report.passed)
        self.assertEqual(report.missing["protected"]["HangeuLint"], 1)
        self.assertEqual(report.missing["time"]["15:00"], 1)
        self.assertEqual(report.added["time"]["16:00"], 1)
        self.assertNotIn("2026", report.missing.get("number", {}))

    def test_fidelity_normalizes_safe_date_and_time_formatting(self):
        report = compare_anchors(
            "배포는 2026.07.31 오후 3시, 대상은 1,000명입니다.",
            "1,000명을 대상으로 2026-07-31 15:00에 배포합니다.",
        )
        self.assertTrue(report.passed)
        self.assertEqual(report.status, "pass")

    def test_polarity_change_requires_review_without_claiming_semantics(self):
        report = compare_anchors(
            "이 기능은 주문을 자동 취소합니다.",
            "이 기능은 주문을 자동 취소하지 않습니다.",
        )
        self.assertTrue(report.passed)
        self.assertEqual(report.status, "review")
        self.assertTrue(report.requires_review)

    def test_register_mix_is_separate_dimension(self):
        report = analyze(
            "자료를 확인했습니다. 문제는 없어요. 내일 배포합니다. 궁금하면 말해요.",
            "work-message",
        )
        finding_ids = {finding.rule_id for finding in report.findings}
        self.assertIn("common.register-mix", finding_ids)
        self.assertEqual(report.dimensions["register"]["status"], "warn")

    def test_comma_signal_is_telemetry_not_a_failure(self):
        text = "오늘은, 자료를 열고, 내용을 확인한 뒤, 바로 답했습니다."
        report = analyze(text, "work-message")
        self.assertTrue(report.passed)
        self.assertEqual(report.metrics["comma"]["status"], "telemetry_only")

    def test_every_rule_has_evidence_and_counterexample(self):
        evidence = load_evidence()
        for pack_id in available_packs():
            for rule in load_pack(pack_id).rules:
                self.assertTrue(rule.evidence_ids)
                self.assertTrue(rule.failing_example)
                self.assertTrue(rule.passing_example)
                self.assertTrue(set(rule.evidence_ids).issubset(evidence))

    def test_report_has_no_ai_authorship_score(self):
        payload = analyze("자료를 확인했습니다.", "work-message").to_dict()
        self.assertNotIn("ai_score", payload)
        self.assertNotIn("human_score", payload)
        self.assertNotIn("score", payload)
        self.assertIn("dimensions", payload)


if __name__ == "__main__":
    unittest.main()
