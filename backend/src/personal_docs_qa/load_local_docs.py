from pathlib import Path

from langchain_core.documents import Document

from personal_docs_qa.config import DOCS_DIR


def load_text_files(folder: Path) -> list[Document]:
    """Read local .txt and .md files and convert them into LangChain Documents."""
    documents: list[Document] = []

    # glob("*") means "look at every file in this folder".
    for path in sorted(folder.glob("*")):
        # suffix is the file extension, for example ".txt" or ".md".
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


def main() -> None:
    print(f"Reading files from: {DOCS_DIR}")

    documents = load_text_files(DOCS_DIR)

    print(f"Loaded {len(documents)} document(s).")
    print()

    # enumerate(..., start=1) gives us 1, 2, 3 instead of 0, 1, 2.
    for index, document in enumerate(documents, start=1):
        source = document.metadata["source"]
        length = document.metadata["length"]
        preview = make_preview(document.page_content)

        print(f"Document {index}")
        print(f"source: {source}")
        print(f"length: {length}")
        print(f"preview: {preview}")
        print()


if __name__ == "__main__":
    main()
