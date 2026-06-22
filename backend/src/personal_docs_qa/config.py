import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DOCS_DIR = PROJECT_ROOT / "docs"
INDEX_DIR = PROJECT_ROOT / "data" / "index"
DEFAULT_ALLOWED_FRONTEND_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


def load_settings() -> None:
    """Load local environment variables from .env."""
    load_dotenv(PROJECT_ROOT / ".env")


def get_chat_model_name() -> str:
    """Return the chat model name used for answers."""
    return os.getenv("OPENAI_MODEL", "gpt-4.1-mini")


def get_embedding_model_name() -> str:
    """Return the embeddings model name used for indexing."""
    return os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")


def get_allowed_frontend_origins() -> list[str]:
    """Return default local frontend origins plus any extra origins from env."""
    configured_origins = os.getenv("ALLOWED_FRONTEND_ORIGINS", "")
    allowed_origins = list(DEFAULT_ALLOWED_FRONTEND_ORIGINS)

    for origin in configured_origins.split(","):
        cleaned_origin = origin.strip()
        if cleaned_origin and cleaned_origin not in allowed_origins:
            allowed_origins.append(cleaned_origin)

    return allowed_origins
