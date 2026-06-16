import hashlib
from datetime import datetime, timezone
from pathlib import Path

from langchain_core.documents import Document

from personal_docs_qa.config import DOCS_DIR, PROJECT_ROOT


def _make_relative_source(path: Path) -> str:
    """Store a readable project-relative source path in metadata."""
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def _build_file_metadata(path: Path, text: str) -> dict[str, object]:
    """Collect file metadata that will later help with indexing decisions."""
    stats = path.stat()
    modified_at = datetime.fromtimestamp(
        stats.st_mtime,
        tz=timezone.utc,
    ).isoformat()

    return {
        "source": _make_relative_source(path),
        "source_name": path.name,
        "source_type": path.suffix.lower(),
        "length": len(text),
        "source_checksum": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "modified_at": modified_at,
    }


def load_text_files(folder: Path) -> list[Document]:
    """Read local .txt and .md files and convert them into LangChain Documents."""
    documents: list[Document] = []

    for path in sorted(folder.glob("*")):
        if path.suffix.lower() not in {".txt", ".md"}:
            continue

        text = path.read_text(encoding="utf-8")

        document = Document(
            page_content=text,
            metadata=_build_file_metadata(path, text),
        )
        documents.append(document)

    return documents


def make_preview(text: str, max_chars: int = 80) -> str:
    """Create a short one-line preview from the document text."""
    clean_text = " ".join(text.split())

    if len(clean_text) <= max_chars:
        return clean_text

    return clean_text[:max_chars] + "..."


def main() -> None:
    """Print a simple summary of the local documents folder."""
    documents = load_text_files(DOCS_DIR)
    print(f"Loaded {len(documents)} documents from {DOCS_DIR}")

    for document in documents:
        checksum = str(document.metadata["source_checksum"])[:12]
        print(
            f"- {document.metadata['source']} "
            f"({document.metadata['length']} chars, sha256 {checksum})"
        )


if __name__ == "__main__":
    main()
