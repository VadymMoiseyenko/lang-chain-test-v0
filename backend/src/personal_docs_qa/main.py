import sys
from typing import Optional

from personal_docs_qa.services.qa_service import answer_question


def print_answer(result: dict[str, object]) -> None:
    """Print the answer and sources in a beginner-friendly CLI format."""
    print(f"Відповідь: {result['answer']}")

    sources = result.get("sources", [])
    if not sources:
        return

    print("\nДжерела:")
    for source in sources:
        print(f"- {source['source']} (chunk {source.get('chunk_index', '?')})")
        print(f"  {source['preview']}")


def main(argv: Optional[list[str]] = None) -> int:
    """Read a question from argv or stdin, then run the QA flow."""
    args = argv if argv is not None else sys.argv[1:]

    if args:
        question = " ".join(args).strip()
    else:
        question = input("Введіть питання про документи: ").strip()

    try:
        result = answer_question(question)
    except (RuntimeError, ValueError) as error:
        print(f"Помилка: {error}")
        return 1

    print_answer(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
