# AGENTS.md

This file gives AI coding agents the project-specific context needed to work on
this repository without rediscovering the basics each time.

## Project Summary

Personal Docs Q&A Bot is a small educational LangChain MVP. It answers
questions about local `.md` and `.txt` files stored in `docs/`.

The app demonstrates a simple RAG flow:

1. Load local documents from `docs/`
2. Split documents into chunks
3. Create OpenAI embeddings
4. Store vectors in local Chroma storage
5. Retrieve relevant chunks for a question
6. Ask an OpenAI chat model to answer using only retrieved context
7. Expose the same logic through CLI and FastAPI

The target user is a beginner in Python, backend development, and AI backend
work. Prefer clear, incremental changes and explanations.

## Tech Stack

- Python 3.9+
- LangChain
- langchain-openai
- ChromaDB
- FastAPI
- Uvicorn
- python-dotenv
- unittest

Dependencies are listed in `requirements.txt`.

## Repository Structure

```text
.
├── docs/                        # Source documents for the RAG knowledge base
├── data/index/                  # Generated local Chroma index, ignored by git
├── src/personal_docs_qa/
│   ├── api.py                   # FastAPI app and HTTP schemas
│   ├── config.py                # Paths, model names, and env loading
│   ├── load_local_docs.py       # Local .md/.txt loading into LangChain Documents
│   ├── main.py                  # CLI Q&A flow
│   └── rag_indexing.py          # Chunking, embeddings, Chroma indexing/search
├── tests/                       # Network-free unit tests
├── .env.example                 # Safe env template
├── .gitignore
├── Makefile
├── README.md
└── requirements.txt
```

## Setup

Use a local virtual environment:

```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
cp .env.example .env
```

The real `.env` file must stay local and must not be committed.

Required environment variables:

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4.1-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

## Common Commands

Prefer the `Makefile` commands when possible:

```bash
make install
make load-docs
make index-demo
make ask QUESTION="Яка різниця між MX-5 NA і ND?"
make api
make test
```

Direct equivalents:

```bash
PYTHONPATH=src ./.venv/bin/python -m personal_docs_qa.load_local_docs
PYTHONPATH=src ./.venv/bin/python -m personal_docs_qa.rag_indexing
PYTHONPATH=src ./.venv/bin/python -m personal_docs_qa.main "Яка різниця між MX-5 NA і ND?"
PYTHONPATH=src ./.venv/bin/uvicorn personal_docs_qa.api:app --reload
PYTHONPATH=src ./.venv/bin/python -m unittest discover -s tests
```

## Validation Checklist

After code changes, run:

```bash
make test
```

For RAG or CLI behavior changes, also run:

```bash
make load-docs
make index-demo
make ask QUESTION="Яка різниця між MX-5 NA і ND?"
```

`make index-demo`, `make ask`, and `make api` require a valid
`OPENAI_API_KEY` and network access to the OpenAI API.

For API changes, run:

```bash
make api
```

Then test `POST /ask` in the Swagger UI at:

```text
http://127.0.0.1:8000/docs
```

## Security Rules

- Never commit `.env`.
- Never hard-code API keys, tokens, or secrets.
- Keep `.env.example` safe and placeholder-only.
- Before pushing, search for secret-looking values:

```bash
rg "OPENAI_API_KEY|sk-|api_key|token|secret|password" .
```

- Treat `docs/` as public repository content unless the user explicitly says
  otherwise.

## Generated Files

Do not commit generated local indexes or caches:

- `data/index/`
- `.venv/`
- `__pycache__/`
- `.pytest_cache/`
- `.mypy_cache/`

If the vector index behaves strangely, it is acceptable to regenerate it rather
than editing generated Chroma files manually.

## Coding Guidelines

- Keep this project simple and beginner-friendly.
- Prefer explicit, readable Python over clever abstractions.
- Keep LangChain-specific orchestration in `rag_indexing.py` and `main.py`.
- Keep HTTP concerns in `api.py`.
- Keep path and environment configuration in `config.py`.
- Avoid adding new frameworks unless they directly support the MVP goal.
- Add comments only when they clarify non-obvious LangChain or RAG behavior.
- Preserve Ukrainian examples and README language where practical.

## RAG Behavior Expectations

The assistant should:

- answer using retrieved document context
- include source file names in responses
- avoid making claims not supported by the documents
- say that the answer was not found in the documents when context is missing

When changing prompts, retrieval settings, chunk sizes, or model settings,
verify the behavior manually with at least these cases:

1. A question clearly answered by the sample docs
2. A comparison question across multiple docs
3. A question that is not answered by the docs

## Testing Guidance

Tests should avoid real network calls. Use unit tests for:

- local document loading
- request/response validation
- pure helper functions
- behavior that can be mocked without calling OpenAI

Do not require a real OpenAI API key for automated tests.

## Git And Publishing

Before a commit or push:

1. Run `git status --short`
2. Confirm `.env` is not staged
3. Run `make test`
4. Run the secret search command from the Security Rules section
5. Check that `README.md` still matches the actual commands

Good first commit message:

```text
Add personal docs LangChain RAG MVP
```

## Learning-Oriented Response Style

When assisting the user in this repository:

- explain new Python syntax briefly
- explain LangChain concepts in plain language
- give one step at a time when the user is following the tutorial
- include a clear checkpoint at the end of each learning step
- avoid assuming previous backend or Python experience

