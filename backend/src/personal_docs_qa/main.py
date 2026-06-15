import sys

from personal_docs_qa.config import DOCS_DIR, INDEX_DIR
from personal_docs_qa.services.qa_service import answer_question


def ask_question() -> str:
    """Get the user's question from CLI args or interactive input."""
    if len(sys.argv) > 1:
        return " ".join(sys.argv[1:]).strip()

    return input("Введіть ваше питання: ").strip()


def main() -> None:
    question = ask_question()
    if not question:
        print("Питання порожнє. Спробуйте ще раз.")
        return

    print(f"Documents folder: {DOCS_DIR}")
    print(f"Index folder: {INDEX_DIR}")
    print("Opening local vector store...", flush=True)

    try:
        result = answer_question(question)
    except ValueError:
        print("Питання порожнє. Спробуйте ще раз.")
        return
    except RuntimeError as error:
        print(str(error), flush=True)
        print("Check your internet connection and try again.", flush=True)
        return

    print(f"Searching relevant chunks for: {question}", flush=True)
    print()

    if not result["sources"]:
        print(result["answer"])
        return

    print("Retrieved context:", flush=True)
    print()

    for rank, source in enumerate(result["sources"], start=1):
        print(f"Result {rank}", flush=True)
        print(f"source: {source['source']}", flush=True)
        print(f"chunk_index: {source['chunk_index']}", flush=True)
        print(f"preview: {source['preview']}", flush=True)
        print(flush=True)

    print("Answer:")
    print(result["answer"])


if __name__ == "__main__":
    main()
