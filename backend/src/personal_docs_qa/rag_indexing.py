import os
import shutil
import warnings
from pathlib import Path

# Silence a local macOS/Python SSL warning.
warnings.filterwarnings(
    "ignore",
    message="urllib3 v2 only supports OpenSSL 1.1.1+",
    category=Warning,
)

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from openai import APIConnectionError
from requests.exceptions import ConnectionError as RequestsConnectionError

from personal_docs_qa.config import DOCS_DIR, INDEX_DIR, get_embedding_model_name, load_settings
from personal_docs_qa.load_local_docs import load_text_files, make_preview


CHROMA_DIR = INDEX_DIR / "chroma"
COLLECTION_NAME = "personal-docs-qa"
NETWORK_ERRORS = (APIConnectionError, RequestsConnectionError)

def load_documents() -> list[Document]:
    """Load source documents that we want to index."""
    return load_text_files(DOCS_DIR)


def split_into_chunks(
    documents: list[Document],
    chunk_size: int = 300,
    chunk_overlap: int = 60,
) -> list[Document]:
    """Split documents into smaller overlapping pieces."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    chunks = splitter.split_documents(documents)

    for index, chunk in enumerate(chunks, start=1):
        chunk.metadata["chunk_index"] = index
        chunk.metadata["chunk_chars"] = len(chunk.page_content)

    return chunks


def create_embeddings() -> OpenAIEmbeddings:
    """Create the embeddings model used for vector search."""
    return OpenAIEmbeddings(model=get_embedding_model_name())


def rebuild_vector_store(chunks: list[Document], persist_directory: Path) -> Chroma:
    """Create a fresh local Chroma index from document chunks."""
    if persist_directory.exists():
        shutil.rmtree(persist_directory)

    persist_directory.mkdir(parents=True, exist_ok=True)
    embeddings = create_embeddings()

    return Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=str(persist_directory),
        collection_name=COLLECTION_NAME,
    )


def open_vector_store(persist_directory: Path) -> Chroma:
    """Open an existing local Chroma index from disk."""
    embeddings = create_embeddings()

    return Chroma(
        persist_directory=str(persist_directory),
        embedding_function=embeddings,
        collection_name=COLLECTION_NAME,
    )


def build_vector_store_from_docs(persist_directory: Path = CHROMA_DIR) -> Chroma:
    """Load docs, split them, and build a fresh persisted vector store."""
    documents = load_documents()
    chunks = split_into_chunks(documents)
    return rebuild_vector_store(chunks, persist_directory)


def ensure_vector_store(persist_directory: Path = CHROMA_DIR) -> Chroma:
    """Open the local index, or build it first when it does not exist yet."""
    if persist_directory.exists():
        return open_vector_store(persist_directory)

    return build_vector_store_from_docs(persist_directory)


def print_chunk_examples(chunks: list[Document], max_examples: int = 3) -> None:
    """Show a few chunks so the split is easy to understand."""
    print(f"Created {len(chunks)} chunk(s).")
    print()

    for chunk in chunks[:max_examples]:
        print(f"Chunk {chunk.metadata['chunk_index']}")
        print(f"source: {chunk.metadata['source']}")
        print(f"length: {chunk.metadata['chunk_chars']}")
        print(f"preview: {make_preview(chunk.page_content, max_chars=120)}")
        print()


def print_search_results(results: list[Document]) -> None:
    """Print similarity search results in a beginner-friendly way."""
    for rank, document in enumerate(results, start=1):
        print(f"Result {rank}")
        print(f"source: {document.metadata['source']}")
        print(f"chunk_index: {document.metadata.get('chunk_index')}")
        print(f"preview: {make_preview(document.page_content, max_chars=140)}")
        print()


def main() -> None:
    print("Starting RAG indexing demo...", flush=True)
    load_settings()
    print("Loaded .env settings.", flush=True)

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is missing. Add it to your .env file.")

    query = "What is LangChain useful for?"
    print(f"Reading documents from: {DOCS_DIR}", flush=True)
    documents = load_documents()
    print(f"Loaded {len(documents)} document(s).", flush=True)

    print("Splitting documents into chunks...", flush=True)
    chunks = split_into_chunks(documents)
    print_chunk_examples(chunks)

    print(f"Building local vector store in: {CHROMA_DIR}", flush=True)

    try:
        rebuild_vector_store(chunks, CHROMA_DIR)
    except NETWORK_ERRORS:
        print("Could not reach the OpenAI API while creating embeddings.", flush=True)
        print("Check your internet connection and try again.", flush=True)
        return

    print("Vector store saved to disk.", flush=True)
    print()

    print("Re-opening the saved vector store...", flush=True)
    vector_store = open_vector_store(CHROMA_DIR)

    print(f"Running similarity search for: {query}", flush=True)

    try:
        results = vector_store.similarity_search(query, k=3)
    except NETWORK_ERRORS:
        print("Could not reach the OpenAI API while searching.", flush=True)
        print("Check your internet connection and try again.", flush=True)
        return

    print()
    print_search_results(results)


if __name__ == "__main__":
    main()
