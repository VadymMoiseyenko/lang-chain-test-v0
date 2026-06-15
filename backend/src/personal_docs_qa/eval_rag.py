import json
from pathlib import Path
from typing import Any

from personal_docs_qa.config import PROJECT_ROOT
from personal_docs_qa.services.qa_service import (
    ANSWER_NOT_FOUND,
    generate_answer_from_prepared,
    prepare_answer_generation,
)


EVAL_CASES_PATH = PROJECT_ROOT / "backend" / "eval_cases.json"


def load_eval_cases(path: Path = EVAL_CASES_PATH) -> list[dict[str, Any]]:
    """Load evaluation cases from a small JSON file."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Evaluation file must contain a JSON list.")

    return data


def normalize_source_name(source: str) -> str:
    """Compare sources by file name so absolute paths stay easy to assert."""
    return Path(source).name


def evaluate_case_result(
    case: dict[str, Any],
    actual_sources: list[str],
    answer: str,
) -> list[str]:
    """Return human-readable failure messages for one eval case."""
    failures: list[str] = []

    expected_sources = case.get("expected_sources", [])
    for expected_source in expected_sources:
        if expected_source not in actual_sources:
            failures.append(f"missing expected source: {expected_source}")

    must_include = case.get("must_include", [])
    answer_lower = answer.lower()
    for phrase in must_include:
        if phrase.lower() not in answer_lower:
            failures.append(f"answer missing phrase: {phrase}")

    if case.get("expect_fallback") and answer != ANSWER_NOT_FOUND:
        failures.append(f"expected fallback answer: {ANSWER_NOT_FOUND}")

    if not case.get("expect_fallback") and answer == ANSWER_NOT_FOUND:
        failures.append("answer unexpectedly fell back")

    return failures


def run_eval_case(case: dict[str, Any]) -> dict[str, Any]:
    """Run retrieval and answer generation for one evaluation case."""
    prepared = prepare_answer_generation(case["question"])
    answer = generate_answer_from_prepared(prepared)
    actual_sources = [
        normalize_source_name(source["source"]) for source in prepared["sources"]
    ]
    failures = evaluate_case_result(case, actual_sources, answer)

    return {
        "name": case["name"],
        "question": case["question"],
        "answer": answer,
        "actual_sources": actual_sources,
        "failures": failures,
        "passed": not failures,
    }


def print_eval_report(results: list[dict[str, Any]]) -> None:
    """Print a short beginner-friendly summary for the eval run."""
    passed_count = sum(1 for result in results if result["passed"])
    total_count = len(results)

    print(f"RAG eval: {passed_count}/{total_count} passed")

    for result in results:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"\n[{status}] {result['name']}")
        print(f"Question: {result['question']}")
        print(f"Sources: {', '.join(result['actual_sources']) or '-'}")
        print(f"Answer: {result['answer']}")

        for failure in result["failures"]:
            print(f"- {failure}")


def main() -> int:
    """Run all evaluation cases and return a shell-friendly exit code."""
    results = [run_eval_case(case) for case in load_eval_cases()]
    print_eval_report(results)

    if all(result["passed"] for result in results):
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
