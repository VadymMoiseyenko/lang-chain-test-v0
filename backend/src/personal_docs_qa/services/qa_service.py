import os
import warnings
from operator import itemgetter
from typing import Any, Iterator, Optional

# Silence a local macOS/Python SSL warning.
warnings.filterwarnings(
    "ignore",
    message="urllib3 v2 only supports OpenSSL 1.1.1+",
    category=Warning,
)

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableLambda, RunnablePassthrough
from langchain_openai import ChatOpenAI
from openai import APIConnectionError

from personal_docs_qa.config import get_chat_model_name, load_settings
from personal_docs_qa.load_local_docs import make_preview
from personal_docs_qa.rag_indexing import NETWORK_ERRORS, ensure_vector_store


ANSWER_NOT_FOUND = "Я не знайшов цього в документах"
DEFAULT_K = 4


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


def build_answer_prompt() -> ChatPromptTemplate:
    """Create the reusable prompt template for question answering."""
    return ChatPromptTemplate.from_messages(
        [
            (
                "system",
                (
                    "Ти бот для відповідей по особистих документах. "
                    "Відповідай тільки на основі наданого контексту. "
                    f"Якщо у контексті немає відповіді, скажи рівно: {ANSWER_NOT_FOUND}. "
                    "Не вигадуй фактів і не використовуй зовнішні знання. "
                    "Відповідай українською мовою."
                ),
            ),
            (
                "human",
                (
                    "Питання: {question}\n\n"
                    "Контекст:\n{context}\n\n"
                    "Дай коротку і точну відповідь тільки на основі контексту."
                ),
            ),
        ]
    )


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


def build_retriever(vector_store: Any) -> Any:
    """Create a LangChain retriever around the vector store."""
    search_k = get_search_k(vector_store, DEFAULT_K)
    return vector_store.as_retriever(search_kwargs={"k": search_k})


def add_context_to_inputs(inputs: dict[str, Any]) -> dict[str, Any]:
    """Add one formatted context string next to retrieved documents."""
    return {
        **inputs,
        "context": format_context(inputs["search_results"]),
    }


def select_prompt_inputs(inputs: dict[str, Any]) -> dict[str, str]:
    """Keep only the fields that the prompt template needs."""
    return {
        "question": inputs["question"],
        "context": inputs["context"],
    }


def build_retrieval_chain(retriever: Any) -> Runnable[Any, dict[str, Any]]:
    """Build the LCEL retrieval step: question -> retrieved docs -> formatted context."""
    return (
        RunnablePassthrough.assign(
            search_results=itemgetter("question") | retriever,
        )
        | RunnableLambda(add_context_to_inputs)
    )


def build_generation_chain(llm: Runnable[Any, Any]) -> Runnable[Any, str]:
    """Build the LCEL generation step: prompt -> chat model -> text parser."""
    return (
        RunnableLambda(select_prompt_inputs)
        | build_answer_prompt()
        | llm
        | StrOutputParser()
    )


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


def get_ready_retriever() -> Any:
    """Create the retriever after checking settings and opening the vector store."""
    load_settings()

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is missing. Add it to your .env file.")

    try:
        vector_store = ensure_vector_store()
    except NETWORK_ERRORS:
        raise RuntimeError("Could not reach the OpenAI API while creating embeddings.")

    return build_retriever(vector_store)


def prepare_answer_generation(question: str) -> dict[str, Any]:
    """Prepare retrieval results and prompt-ready inputs for answer generation."""
    clean_question = validate_question(question)
    retrieval_chain = build_retrieval_chain(get_ready_retriever())

    try:
        prepared = retrieval_chain.invoke({"question": clean_question})
    except NETWORK_ERRORS:
        raise RuntimeError("Could not reach the OpenAI API while searching.")

    search_results = prepared["search_results"]
    sources = build_sources(search_results)

    if not search_results:
        return {
            "question": clean_question,
            "search_results": [],
            "sources": [],
            "context": "",
        }

    return {
        "question": clean_question,
        "search_results": search_results,
        "sources": sources,
        "context": prepared["context"],
    }


def stream_answer_chunks(question: str) -> tuple[list[dict[str, Any]], Iterator[Any]]:
    """Return sources and a streaming iterator for the model answer."""
    prepared = prepare_answer_generation(question)

    if not prepared["search_results"]:
        return prepared["sources"], iter([ANSWER_NOT_FOUND])

    generation_chain = build_generation_chain(get_llm())

    try:
        return prepared["sources"], generation_chain.stream(prepared)
    except APIConnectionError:
        raise RuntimeError("Could not reach the OpenAI API.")


def generate_answer_from_prepared(
    prepared: dict[str, Any],
    llm: Optional[Runnable[Any, Any]] = None,
) -> str:
    """Generate one final answer from prepared retrieval results."""
    if not prepared["search_results"]:
        return ANSWER_NOT_FOUND

    generation_chain = build_generation_chain(llm or get_llm())

    try:
        response = generation_chain.invoke(prepared)
    except APIConnectionError:
        raise RuntimeError("Could not reach the OpenAI API.")

    answer = normalize_answer(response)
    if not answer:
        return ANSWER_NOT_FOUND

    return answer


def answer_question(question: str) -> dict[str, Any]:
    """Run retrieval + generation and return answer data for CLI or API usage."""
    prepared = prepare_answer_generation(question)

    return {
        "answer": generate_answer_from_prepared(prepared),
        "sources": prepared["sources"],
    }
