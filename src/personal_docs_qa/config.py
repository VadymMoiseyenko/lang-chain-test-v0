import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = PROJECT_ROOT / "docs"
INDEX_DIR = PROJECT_ROOT / "data" / "index"


def load_settings() -> None:
    """Load local environment variables from .env."""
    load_dotenv(PROJECT_ROOT / ".env")


def get_chat_model_name() -> str:
    """Return the chat model name used for answers."""
    return os.getenv("OPENAI_MODEL", "gpt-4.1-mini")


def get_embedding_model_name() -> str:
    """Return the embeddings model name used for indexing."""
    return os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
