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

from personal_docs_qa.config import DOCS_DIR, INDEX_DIR, get_embedding_model_name
from personal_docs_qa.load_local_docs import load_text_files


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


def main() -> None:
    """Build the local vector store and print a small status message."""
    vector_store = build_vector_store_from_docs()
    collection = getattr(vector_store, "_collection", None)
    chunk_count = collection.count() if collection is not None else "unknown"
    print(f"Built Chroma index in {CHROMA_DIR} with {chunk_count} chunks.")


if __name__ == "__main__":
    main()
