import json
import shutil
import warnings
from collections import Counter
from pathlib import Path
from typing import Optional, Tuple

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

from personal_docs_qa.config import (
    DOCS_DIR,
    INDEX_DIR,
    get_embedding_model_name,
    load_settings,
)
from personal_docs_qa.load_local_docs import load_text_files


CHROMA_DIR = INDEX_DIR / "chroma"
MANIFEST_PATH = INDEX_DIR / "ingestion_manifest.json"
COLLECTION_NAME = "personal-docs-qa"
MANIFEST_VERSION = 1
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

    chunk_counters: Counter[str] = Counter()

    for chunk in chunks:
        source = str(chunk.metadata.get("source", "unknown"))
        chunk_counters[source] += 1
        chunk_index = chunk_counters[source]
        chunk.metadata["chunk_index"] = chunk_index
        chunk.metadata["chunk_chars"] = len(chunk.page_content)
        chunk.metadata["chunk_id"] = build_chunk_id(source, chunk_index)

    return chunks


def build_chunk_id(source: str, chunk_index: int) -> str:
    """Create a deterministic chunk id from the source file and chunk position."""
    return f"{source}::chunk::{chunk_index}"


def load_ingestion_manifest(path: Path = MANIFEST_PATH) -> Optional[dict[str, object]]:
    """Read the saved ingestion manifest when it exists."""
    if not path.exists():
        return None

    return json.loads(path.read_text(encoding="utf-8"))


def summarize_documents(documents: list[Document]) -> list[dict[str, object]]:
    """Keep only the document metadata that matters for ingestion decisions."""
    summaries: list[dict[str, object]] = []

    for document in documents:
        summaries.append(
            {
                "source": document.metadata["source"],
                "source_name": document.metadata.get("source_name"),
                "source_type": document.metadata.get("source_type"),
                "length": document.metadata.get("length", len(document.page_content)),
                "source_checksum": document.metadata.get("source_checksum"),
                "modified_at": document.metadata.get("modified_at"),
            }
        )

    return sorted(summaries, key=lambda item: str(item["source"]))


def build_ingestion_plan(
    documents: list[Document],
    previous_manifest: Optional[dict[str, object]],
) -> dict[str, object]:
    """Compare current docs with the saved manifest and decide what changed."""
    current_documents = summarize_documents(documents)
    previous_documents = previous_manifest.get("documents", []) if previous_manifest else []

    current_by_source = {
        str(document["source"]): document for document in current_documents
    }
    previous_by_source = {
        str(document["source"]): document for document in previous_documents
    }

    added = sorted(
        source for source in current_by_source if source not in previous_by_source
    )
    deleted = sorted(
        source for source in previous_by_source if source not in current_by_source
    )

    changed: list[str] = []
    unchanged: list[str] = []

    for source in sorted(
        source for source in current_by_source if source in previous_by_source
    ):
        current_document = current_by_source[source]
        previous_document = previous_by_source[source]

        if current_document.get("source_checksum") != previous_document.get("source_checksum"):
            changed.append(source)
        else:
            unchanged.append(source)

    needs_rebuild = previous_manifest is None or bool(added or changed or deleted)

    return {
        "added": added,
        "changed": changed,
        "deleted": deleted,
        "unchanged": unchanged,
        "needs_rebuild": needs_rebuild,
        "current_documents": current_documents,
    }


def build_manifest(
    documents: list[Document],
    chunks: list[Document],
) -> dict[str, object]:
    """Create the manifest that describes the current indexed document set."""
    document_summaries = summarize_documents(documents)
    chunk_counts_by_source = Counter(
        str(chunk.metadata.get("source", "unknown")) for chunk in chunks
    )

    manifest_documents: list[dict[str, object]] = []
    for summary in document_summaries:
        manifest_documents.append(
            {
                **summary,
                "chunk_count": chunk_counts_by_source.get(str(summary["source"]), 0),
            }
        )

    return {
        "version": MANIFEST_VERSION,
        "collection_name": COLLECTION_NAME,
        "document_count": len(documents),
        "chunk_count": len(chunks),
        "documents": manifest_documents,
    }


def save_ingestion_manifest(
    manifest: dict[str, object],
    path: Path = MANIFEST_PATH,
) -> None:
    """Persist the ingestion manifest next to the local Chroma index."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def describe_ingestion_plan(plan: dict[str, object]) -> str:
    """Format a compact human-readable summary of ingestion changes."""
    added = len(plan["added"])
    changed = len(plan["changed"])
    deleted = len(plan["deleted"])
    unchanged = len(plan["unchanged"])
    return (
        "Ingestion plan: "
        f"{added} added, {changed} changed, {deleted} deleted, {unchanged} unchanged."
    )


def create_embeddings() -> OpenAIEmbeddings:
    """Create the embeddings model used for vector search."""
    load_settings()
    return OpenAIEmbeddings(model=get_embedding_model_name())


def rebuild_vector_store(chunks: list[Document], persist_directory: Path) -> Chroma:
    """Create a fresh local Chroma index from document chunks."""
    if persist_directory.exists():
        shutil.rmtree(persist_directory)

    persist_directory.mkdir(parents=True, exist_ok=True)
    embeddings = create_embeddings()
    chunk_ids = [str(chunk.metadata["chunk_id"]) for chunk in chunks]

    return Chroma.from_documents(
        documents=chunks,
        ids=chunk_ids,
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
    """Sync the local vector store with docs, rebuilding only when inputs changed."""
    vector_store, _, _ = sync_vector_store_with_docs(persist_directory)
    return vector_store


def sync_vector_store_with_docs(
    persist_directory: Path = CHROMA_DIR,
    manifest_path: Path = MANIFEST_PATH,
) -> Tuple[Chroma, dict[str, object], str]:
    """Plan ingestion changes, then reuse or rebuild the Chroma index."""
    documents = load_documents()
    previous_manifest = load_ingestion_manifest(manifest_path)
    plan = build_ingestion_plan(documents, previous_manifest)

    if persist_directory.exists() and manifest_path.exists() and not plan["needs_rebuild"]:
        return open_vector_store(persist_directory), plan, "reused"

    chunks = split_into_chunks(documents)
    vector_store = rebuild_vector_store(chunks, persist_directory)
    manifest = build_manifest(documents, chunks)
    save_ingestion_manifest(manifest, manifest_path)
    return vector_store, plan, "rebuilt"


def ensure_vector_store(persist_directory: Path = CHROMA_DIR) -> Chroma:
    """Reuse the local index when possible, or sync it with docs when needed."""
    vector_store, _, _ = sync_vector_store_with_docs(persist_directory)
    return vector_store


def main() -> None:
    """Build the local vector store and print a small status message."""
    vector_store, plan, action = sync_vector_store_with_docs()
    collection = getattr(vector_store, "_collection", None)
    chunk_count = collection.count() if collection is not None else "unknown"
    print(describe_ingestion_plan(plan))
    print(
        f"Index {action} in {CHROMA_DIR} with {chunk_count} chunks."
    )


if __name__ == "__main__":
    main()
