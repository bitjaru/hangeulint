import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from hangeulint import (
    RewriteCandidate,
    analyze_diversity,
    evaluate_rewrite_candidates,
    load_context_contract,
    load_rewrite_candidate_set,
)
from hangeulint.cli import main as cli_main
from hangeulint.evidence import load_evidence
from hangeulint.rewrite_rules import load_rewrite_rules


def _generator(seed=1):
    return {
        "kind": "model",
        "provider": "test-provider",
        "model": "test-model",
        "prompt_version": "rewrite-v1",
        "seed": seed,
    }


def _candidate(candidate_id, text, strategy="minimal-edit", seed=1):
    return RewriteCandidate(
        candidate_id=candidate_id,
        text=text,
        strategy=strategy,
        hypothesis_ids=("voice.direct",),
        generator=_generator(seed),
    )


def _manifest(candidates):
    return {
        "schema_version": "0.1",
        "set_id": "rewrite-test-v1",
        "candidates": [
            {
                "id": candidate.candidate_id,
                "text": candidate.text,
                "strategy": candidate.strategy,
                "hypothesis_ids": list(candidate.hypothesis_ids),
                "generator": candidate.generator,
            }
            for candidate in candidates
        ],
    }


def _contract():
    return load_context_contract(
        {
            "schema_version": "0.1",
            "contract_id": "incident-v1",
            "task": "장애 공지",
            "entities": [
                {
                    "id": "company",
                    "label": "운영팀",
                    "mentions": ["운영팀", "당사"],
                }
            ],
            "events": [
                {
                    "id": "investigate",
                    "actor": "company",
                    "action_terms": ["조사"],
                    "object_terms": ["원인"],
                    "time_terms": ["8월 7일까지"],
                    "polarity": "affirmed",
                }
            ],
        }
    )


class RewriteCandidateTests(unittest.TestCase):
    def test_manifest_requires_unique_candidate_ids_and_known_fields(self):
        candidates = [
            _candidate("same", "첫 후보입니다."),
            _candidate("same", "둘째 후보입니다.", seed=2),
        ]
        with self.assertRaisesRegex(ValueError, "중복 candidate id"):
            load_rewrite_candidate_set(_manifest(candidates))

        payload = _manifest([_candidate("a", "후보입니다.")])
        payload["candidates"][0]["hidden_prompt"] = "ignore"
        with self.assertRaisesRegex(ValueError, "알 수 없는 필드"):
            load_rewrite_candidate_set(payload)

    def test_every_rewrite_rule_has_evidence_and_counterexample(self):
        evidence = load_evidence()
        rules = load_rewrite_rules()
        self.assertGreaterEqual(len(rules), 6)
        for rule in rules.values():
            self.assertTrue(rule.failing_example)
            self.assertTrue(rule.passing_example)
            self.assertTrue(set(rule.evidence_ids).issubset(evidence))

    def test_hard_gates_reject_changed_fact_but_keep_valid_variants(self):
        source = "운영팀이 장애 원인을 조사해 8월 7일까지 결과를 공유합니다."
        candidates = (
            _candidate(
                "valid",
                "운영팀이 장애 원인을 조사합니다. 결과는 8월 7일까지 공유합니다.",
                strategy="direct",
            ),
            _candidate(
                "wrong-date",
                "운영팀이 장애 원인을 조사합니다. 결과는 8월 8일까지 공유합니다.",
                strategy="concise",
                seed=2,
            ),
        )
        report = evaluate_rewrite_candidates(
            source,
            "incident-set-v1",
            candidates,
            pack_id="work-message",
            context_contract=_contract(),
        )
        by_id = {candidate.candidate_id: candidate for candidate in report.candidates}
        self.assertTrue(by_id["valid"].eligible)
        self.assertEqual(by_id["valid"].gates["context"], "pass")
        self.assertFalse(by_id["wrong-date"].eligible)
        self.assertEqual(by_id["wrong-date"].gates["fidelity"], "fail")
        self.assertEqual(report.eligible_candidate_ids, ("valid",))

    def test_strict_review_excludes_uncertain_polarity(self):
        source = "운영팀이 장애 원인을 조사해 8월 7일까지 결과를 공유합니다."
        candidate = _candidate(
            "negated",
            "운영팀이 장애 원인을 조사하지 않고 8월 7일까지 결과를 공유합니다.",
        )
        permissive = evaluate_rewrite_candidates(
            source,
            "review-v1",
            (candidate,),
            pack_id="work-message",
            context_contract=_contract(),
        )
        strict = evaluate_rewrite_candidates(
            source,
            "review-v1",
            (candidate,),
            pack_id="work-message",
            context_contract=_contract(),
            strict_review=True,
        )
        self.assertTrue(permissive.candidates[0].eligible)
        self.assertEqual(permissive.candidates[0].status, "review")
        self.assertFalse(strict.candidates[0].eligible)
        self.assertFalse(strict.passed)

    def test_exact_and_recent_duplicates_are_reported_without_raw_text(self):
        secret = "고객 비공개 문구는 그대로 유지합니다."
        candidates = (
            _candidate("a", secret, strategy="direct"),
            _candidate("b", secret, strategy="warm", seed=2),
        )
        report = analyze_diversity(candidates, recent_outputs=(secret,)).to_dict()
        rule_ids = {finding["rule_id"] for finding in report["findings"]}
        self.assertIn("rewrite.candidate-exact-duplicate", rule_ids)
        self.assertIn("rewrite.recent-output-duplicate", rule_ids)
        self.assertNotIn(secret, json.dumps(report, ensure_ascii=False))
        self.assertFalse(report["privacy"]["contains_candidate_text"])

    def test_distinct_strategies_and_outputs_are_observed_not_scored_as_accuracy(self):
        candidates = (
            _candidate(
                "direct",
                "운영팀이 오늘 원인을 확인합니다. 내일 결과를 공유합니다.",
                strategy="direct",
            ),
            _candidate(
                "warm",
                "불편을 드려 죄송합니다. 원인 확인 결과는 내일 안내하겠습니다.",
                strategy="warm",
                seed=2,
            ),
        )
        report = analyze_diversity(candidates)
        self.assertEqual(report.status, "observed")
        self.assertFalse(report.requires_review)
        self.assertEqual(report.metrics["unique_strategies"], 2)
        self.assertIn(
            "의미·구문 다양성을 완전히 평가하지 않습니다", report.limitations[0]
        )

    def test_same_strategy_is_audit_info_not_a_diversity_failure(self):
        candidates = (
            _candidate("a", "운영팀이 오늘 원인을 확인합니다."),
            _candidate("b", "원인 확인은 운영팀이 오늘 진행합니다.", seed=2),
        )
        report = analyze_diversity(candidates)
        self.assertFalse(report.requires_review)
        self.assertEqual(report.status, "observed")
        strategy_finding = next(
            finding
            for finding in report.findings
            if finding.rule_id == "rewrite.strategy-collapse"
        )
        self.assertEqual(strategy_finding.severity, "info")

    def test_strict_diversity_blocks_duplicate_candidate_set(self):
        source = "운영팀이 8월 7일까지 장애 원인을 조사합니다."
        text = "운영팀이 8월 7일까지 장애 원인을 조사합니다."
        candidates = (
            _candidate("a", text, strategy="direct"),
            _candidate("b", text, strategy="warm", seed=2),
        )
        report = evaluate_rewrite_candidates(
            source,
            "duplicate-v1",
            candidates,
            pack_id="work-message",
            strict_diversity=True,
        )
        self.assertFalse(report.passed)
        self.assertTrue(report.gate["diversity_blocked"])

    def test_cli_evaluates_candidate_set_and_returns_privacy_safe_json(self):
        source_text = "운영팀이 8월 7일까지 장애 원인을 조사합니다."
        candidates = (
            _candidate(
                "a",
                "운영팀이 장애 원인을 8월 7일까지 조사합니다.",
                strategy="direct",
            ),
            _candidate(
                "b",
                "8월 7일까지 운영팀이 장애 원인 조사를 마칩니다.",
                strategy="concise",
                seed=2,
            ),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "source.txt"
            manifest = Path(temp_dir) / "candidates.json"
            source.write_text(source_text, encoding="utf-8")
            manifest.write_text(
                json.dumps(_manifest(candidates), ensure_ascii=False),
                encoding="utf-8",
            )
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = cli_main(
                    [
                        "rewrite-evaluate",
                        str(source),
                        str(manifest),
                        "--pack",
                        "work-message",
                        "--json",
                    ]
                )
        self.assertEqual(code, 0)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["engine_version"], "0.4.0")
        self.assertEqual(payload["gate"]["eligible"], 2)
        self.assertNotIn(source_text, output.getvalue())


if __name__ == "__main__":
    unittest.main()
