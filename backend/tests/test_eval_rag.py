import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from personal_docs_qa.eval_rag import (
    ANSWER_NOT_FOUND,
    evaluate_case_result,
    load_eval_cases,
    normalize_source_name,
    run_eval_case,
)


class EvalHelpersTests(unittest.TestCase):
    def test_normalize_source_name_returns_file_name_only(self) -> None:
        source = "/tmp/docs/mazda-mx5-na.md"
        self.assertEqual(normalize_source_name(source), "mazda-mx5-na.md")

    def test_load_eval_cases_reads_json_list(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "eval_cases.json"
            path.write_text('[{"name": "demo", "question": "Q"}]', encoding="utf-8")

            cases = load_eval_cases(path)

        self.assertEqual(cases[0]["name"], "demo")

    def test_evaluate_case_result_checks_sources_and_phrases(self) -> None:
        case = {
            "expected_sources": ["mazda-mx5-na.md"],
            "must_include": ["pop-up headlights"],
            "expect_fallback": False,
        }

        failures = evaluate_case_result(
            case=case,
            actual_sources=["mazda-mx5-nb.txt"],
            answer="Відповідь про NB",
        )

        self.assertIn("missing expected source: mazda-mx5-na.md", failures)
        self.assertIn("answer missing phrase: pop-up headlights", failures)

    def test_evaluate_case_result_checks_fallback(self) -> None:
        case = {"expect_fallback": True}

        failures = evaluate_case_result(
            case=case,
            actual_sources=[],
            answer="Інша відповідь",
        )

        self.assertEqual(
            failures,
            [f"expected fallback answer: {ANSWER_NOT_FOUND}"],
        )

    def test_run_eval_case_uses_prepared_sources_and_generated_answer(self) -> None:
        case = {
            "name": "demo",
            "question": "Що таке PRHT?",
            "expected_sources": ["mazda-mx5-nc.md"],
            "must_include": ["PRHT"],
            "expect_fallback": False,
        }
        prepared = {
            "question": case["question"],
            "search_results": ["fake-doc"],
            "sources": [
                {
                    "source": "/workspace/docs/mazda-mx5-nc.md",
                    "chunk_index": 1,
                    "preview": "PRHT preview",
                }
            ],
            "context": "context",
        }

        with patch(
            "personal_docs_qa.eval_rag.prepare_answer_generation",
            return_value=prepared,
        ), patch(
            "personal_docs_qa.eval_rag.generate_answer_from_prepared",
            return_value="NC introduced PRHT.",
        ):
            result = run_eval_case(case)

        self.assertTrue(result["passed"])
        self.assertEqual(result["actual_sources"], ["mazda-mx5-nc.md"])


if __name__ == "__main__":
    unittest.main()
