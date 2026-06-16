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


def run_chat_session() -> int:
    """Run a simple multi-turn CLI chat that keeps local history in memory."""
    print("Введіть питання про документи. Для виходу натисніть Enter на порожньому рядку.")

    chat_history: list[dict[str, str]] = []

    while True:
        question = input("\nВи: ").strip()
        if not question:
            print("Сесію завершено.")
            return 0

        try:
            result = answer_question(question, chat_history=chat_history)
        except (RuntimeError, ValueError) as error:
            print(f"Помилка: {error}")
            return 1

        print_answer(result)

        chat_history.append({"role": "user", "content": question})
        chat_history.append({"role": "assistant", "content": str(result["answer"])})


def main(argv: Optional[list[str]] = None) -> int:
    """Read a question from argv or stdin, then run the QA flow."""
    args = argv if argv is not None else sys.argv[1:]

    if args and " ".join(args).strip():
        question = " ".join(args).strip()
    else:
        return run_chat_session()

    try:
        result = answer_question(question)
    except (RuntimeError, ValueError) as error:
        print(f"Помилка: {error}")
        return 1

    print_answer(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
