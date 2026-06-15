from pathlib import Path

from langchain_core.documents import Document

from personal_docs_qa.config import DOCS_DIR


def load_text_files(folder: Path) -> list[Document]:
    """Read local .txt and .md files and convert them into LangChain Documents."""
    documents: list[Document] = []

    for path in sorted(folder.glob("*")):
        if path.suffix.lower() not in {".txt", ".md"}:
            continue

        text = path.read_text(encoding="utf-8")

        document = Document(
            page_content=text,
            metadata={
                "source": str(path),
                "length": len(text),
            },
        )
        documents.append(document)

    return documents


def make_preview(text: str, max_chars: int = 80) -> str:
    """Create a short one-line preview from the document text."""
    clean_text = " ".join(text.split())

    if len(clean_text) <= max_chars:
        return clean_text

    return clean_text[:max_chars] + "..."
