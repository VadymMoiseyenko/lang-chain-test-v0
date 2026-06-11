import os
import sys
import warnings
from typing import Any, Optional

# Silence a local macOS/Python SSL warning that does not affect this example.
warnings.filterwarnings(
    "ignore",
    message="urllib3 v2 only supports OpenSSL 1.1.1+",
    category=Warning,
)

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from openai import APIConnectionError

from personal_docs_qa.config import DOCS_DIR, INDEX_DIR, get_chat_model_name, load_settings
from personal_docs_qa.load_local_docs import make_preview
from personal_docs_qa.rag_indexing import NETWORK_ERRORS, ensure_vector_store


ANSWER_NOT_FOUND = "Я не знайшов цього в документах"
DEFAULT_K = 4


def ask_question() -> str:
    """Get the user's question from CLI args or interactive input."""
    if len(sys.argv) > 1:
        return " ".join(sys.argv[1:]).strip()

    return input("Введіть ваше питання: ").strip()


def format_context(results: list[Any]) -> str:
    """Convert retrieved chunks into a prompt-friendly context block."""
    parts: list[str] = []

    for index, document in enumerate(results, start=1):
        source = document.metadata.get("source", "unknown")
        chunk_index = document.metadata.get("chunk_index", "?")
        parts.append(
            "\n".join(
                [
                    f"[Fragment {index}]",
                    f"source: {source}",
                    f"chunk_index: {chunk_index}",
                    document.page_content,
                ]
            )
        )

    return "\n\n".join(parts)


def get_search_k(vector_store: Any, default_k: int) -> int:
    """Limit k to the number of indexed chunks when that count is available."""
    collection = getattr(vector_store, "_collection", None)
    if collection is None:
        return default_k

    try:
        return max(1, min(default_k, collection.count()))
    except Exception:
        return default_k


def normalize_answer(answer: str) -> str:
    """Force the fallback answer to match the exact required phrase."""
    cleaned = answer.strip()
    fallback_variants = {
        ANSWER_NOT_FOUND.lower(),
        f"{ANSWER_NOT_FOUND}.".lower(),
    }

    if cleaned.lower() in fallback_variants:
        return ANSWER_NOT_FOUND

    return cleaned


def get_llm(model_name: Optional[str] = None) -> ChatOpenAI:
    """Create the chat model used for answering questions."""
    selected_model = model_name or get_chat_model_name()
    return ChatOpenAI(model=selected_model, temperature=0)


def build_messages(question: str, context: str) -> list[Any]:
    """Build the prompt messages for the question-answering call."""
    return [
        SystemMessage(
            content=(
                "Ти бот для відповідей по особистих документах. "
                "Відповідай тільки на основі наданого контексту. "
                f"Якщо у контексті немає відповіді, скажи рівно: {ANSWER_NOT_FOUND}. "
                "Не вигадуй фактів і не використовуй зовнішні знання. "
                "Відповідай українською мовою."
            )
        ),
        HumanMessage(
            content=(
                f"Питання: {question}\n\n"
                f"Контекст:\n{context}\n\n"
                "Дай коротку і точну відповідь тільки на основі контексту."
            )
        ),
    ]


def build_sources(results: list[Any]) -> list[dict[str, Any]]:
    """Convert retrieved documents into a simple API-friendly sources list."""
    sources: list[dict[str, Any]] = []

    for document in results:
        sources.append(
            {
                "source": document.metadata.get("source", "unknown"),
                "chunk_index": document.metadata.get("chunk_index"),
                "preview": make_preview(document.page_content, max_chars=140),
            }
        )

    return sources


def validate_question(question: str) -> str:
    """Normalize and validate the incoming question text."""
    clean_question = question.strip()
    if not clean_question:
        raise ValueError("Question must not be empty.")

    return clean_question


def retrieve_documents(question: str) -> list[Any]:
    """Run similarity search and return retrieved documents."""
    load_settings()

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is missing. Add it to your .env file.")

    clean_question = validate_question(question)

    try:
        vector_store = ensure_vector_store()
    except NETWORK_ERRORS:
        raise RuntimeError("Could not reach the OpenAI API while creating embeddings.")

    search_k = get_search_k(vector_store, DEFAULT_K)

    try:
        search_results = vector_store.similarity_search(
            clean_question,
            k=search_k,
        )
    except NETWORK_ERRORS:
        raise RuntimeError("Could not reach the OpenAI API while searching.")

    return search_results


def prepare_answer_generation(question: str) -> dict[str, Any]:
    """Prepare retrieval results, sources, and prompt messages for answering."""
    clean_question = validate_question(question)
    search_results = retrieve_documents(clean_question)
    sources = build_sources(search_results)

    if not search_results:
        return {
            "question": clean_question,
            "search_results": [],
            "sources": [],
            "messages": None,
        }

    context = format_context(search_results)
    messages = build_messages(clean_question, context)

    return {
        "question": clean_question,
        "search_results": search_results,
        "sources": sources,
        "messages": messages,
    }


def stream_answer_chunks(question: str) -> tuple[list[dict[str, Any]], Any]:
    """Return sources and a streaming iterator for the model answer."""
    prepared = prepare_answer_generation(question)

    if not prepared["search_results"]:
        return prepared["sources"], iter([ANSWER_NOT_FOUND])

    llm = get_llm()

    try:
        return prepared["sources"], llm.stream(prepared["messages"])
    except APIConnectionError:
        raise RuntimeError("Could not reach the OpenAI API.")


def answer_question(question: str) -> dict[str, Any]:
    """Run retrieval + generation and return answer data for CLI or API usage."""
    prepared = prepare_answer_generation(question)

    if not prepared["search_results"]:
        return {
            "answer": ANSWER_NOT_FOUND,
            "sources": prepared["sources"],
        }

    llm = get_llm()

    try:
        response = llm.invoke(prepared["messages"])
    except APIConnectionError:
        raise RuntimeError("Could not reach the OpenAI API.")

    answer = normalize_answer(str(response.content))
    if not answer:
        answer = ANSWER_NOT_FOUND

    return {
        "answer": answer,
        "sources": prepared["sources"],
    }


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
