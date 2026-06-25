# AGENTS.md

This file gives AI coding agents the project-specific context needed to work on
this repository without rediscovering the basics each time.

## Project Summary

Personal Docs Q&A Bot is an educational full-stack LangChain RAG MVP. It answers
questions about local `.md` and `.txt` files stored in `docs/`.

The repository is now a simple monorepo:

- `backend/` contains the Python LangChain/FastAPI app.
- `frontend/` contains a small React/Vite chat UI.
- The root `Makefile` remains the main command interface.

The app demonstrates this flow:

1. Load local documents from `docs/`
2. Split documents into overlapping chunks
3. Create OpenAI embeddings
4. Store vectors in a local Chroma index at `data/index/chroma/`
5. Save an ingestion manifest at `data/index/ingestion_manifest.json`
6. Reuse the index when source documents have not changed
7. Rewrite follow-up questions into standalone retrieval questions
8. Retrieve relevant chunks
9. Ask an OpenAI chat model to answer using only retrieved context
10. Return answers and source previews through CLI, FastAPI, and React

The target user is a beginner in Python, backend development, frontend basics,
and AI backend work. Prefer clear, incremental changes and explanations.

## Tech Stack

- Python 3.9+ locally; CI uses Python 3.11; Render pins Python 3.12.12
- LangChain / LCEL
- langchain-openai
- ChromaDB
- FastAPI
- Uvicorn
- python-dotenv
- unittest
- React 18
- Vite 5
- Node.js 18+ locally; CI uses Node.js 20
- Render Blueprint deployment via `render.yaml`

Backend dependencies are in `backend/requirements.txt`.
Frontend dependencies are in `frontend/package.json` and
`frontend/package-lock.json`.

## Repository Structure

```text
.
├── backend/
│   ├── requirements.txt
│   ├── eval_cases.json
│   ├── src/
│   │   └── personal_docs_qa/
│   │       ├── api.py                 # FastAPI app, schemas, CORS, SSE endpoint
│   │       ├── config.py              # Project paths, env loading, CORS origins
│   │       ├── load_local_docs.py     # Local .md/.txt loading and metadata
│   │       ├── main.py                # CLI one-shot question and interactive chat
│   │       ├── rag_indexing.py        # Chunking, manifest, Chroma indexing/search
│   │       ├── eval_rag.py            # Manual RAG eval runner
│   │       └── services/
│   │           └── qa_service.py      # Core QA service flow
│   └── tests/                         # Network-free unittest suite
├── docs/                              # Source documents for RAG
├── data/index/                        # Generated local Chroma index and manifest
├── frontend/
│   ├── src/
│   │   ├── App.jsx                    # Chat UI, streaming fetch, chat history
│   │   ├── App.css
│   │   ├── index.css
│   │   └── main.jsx
│   ├── package.json
│   ├── package-lock.json
│   ├── vite.config.js
│   └── index.html
├── .github/workflows/ci.yml           # Backend tests, frontend build, secret scan
├── .env.example                       # Backend env template
├── Makefile                           # Root command interface
├── README.md
├── render.yaml                        # Render backend + frontend deployment
└── AGENTS.md
```

## Setup

Use a local virtual environment at the repository root:

```bash
python3 -m venv .venv
./.venv/bin/pip install -r backend/requirements.txt
cp .env.example .env
cd frontend
npm install
cp .env.example .env
cd ..
```

The real `.env` files must stay local and must not be committed.

Backend environment variables:

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4.1-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
ALLOWED_FRONTEND_ORIGINS=https://personal-docs-qa-frontend.onrender.com
```

`ALLOWED_FRONTEND_ORIGINS` is optional locally. The backend always includes:

- `http://localhost:5173`
- `http://127.0.0.1:5173`

Frontend environment variables:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

## Common Commands

Prefer the root `Makefile` commands:

```bash
make install
make test
make eval
make load-docs
make index-demo
make ask QUESTION="Яка різниця між MX-5 NA і ND?"
make api
make frontend-install
make frontend-dev
make frontend-build
```

Direct equivalents:

```bash
PYTHONPATH=backend/src ./.venv/bin/python -m personal_docs_qa.load_local_docs
PYTHONPATH=backend/src ./.venv/bin/python -m personal_docs_qa.rag_indexing
PYTHONPATH=backend/src ./.venv/bin/python -m personal_docs_qa.main "Яка різниця між MX-5 NA і ND?"
PYTHONPATH=backend/src ./.venv/bin/python -m personal_docs_qa.main
PYTHONPATH=backend/src ./.venv/bin/python -m personal_docs_qa.eval_rag
PYTHONPATH=backend/src ./.venv/bin/uvicorn personal_docs_qa.api:app --reload
PYTHONPATH=backend/src ./.venv/bin/python -m unittest discover -s backend/tests
cd frontend && npm install
cd frontend && npm run dev
cd frontend && npm run build
```

## Runtime Behavior

Backend routes:

- `GET /` returns a simple status message.
- `GET /health` returns `{"status": "ok"}` and should not touch OpenAI.
- `POST /ask` returns one complete answer plus sources.
- `POST /ask/stream` streams Server-Sent Events: `sources`, `answer_chunk`,
  optional `error`, and `done`.

Question answering lives in `backend/src/personal_docs_qa/services/qa_service.py`.
Keep the HTTP layer in `api.py` thin.

The CLI in `main.py` supports both:

- one-shot mode with an argument
- interactive chat mode when no question argument is passed

Both CLI and API share the same service code.

## RAG Behavior Expectations

The assistant should:

- answer using retrieved document context
- include source file names in responses or source lists
- avoid making claims not supported by the documents
- say exactly `Я не знайшов цього в документах` when context is missing
- answer in Ukrainian

Follow-up questions are rewritten into standalone questions before retrieval.
Chat history is trimmed to the latest useful messages. Preserve that behavior
when changing retrieval, prompts, API schemas, or frontend chat flow.

When changing prompts, retrieval settings, chunk sizes, indexing, or model
settings, verify manually with at least these cases:

1. A question clearly answered by the sample docs
2. A comparison question across multiple docs
3. A follow-up question that depends on chat history
4. A question that is not answered by the docs

## Validation Checklist

After code changes, run:

```bash
make test
```

For frontend changes, also run:

```bash
make frontend-build
```

For RAG, CLI, indexing, or prompt behavior changes, also run when a valid
`OPENAI_API_KEY` and network access are available:

```bash
make load-docs
make index-demo
make ask QUESTION="Яка різниця між MX-5 NA і ND?"
make eval
```

For API changes, run:

```bash
make api
```

Then check:

- Swagger UI: `http://127.0.0.1:8000/docs`
- health check: `http://127.0.0.1:8000/health`
- `POST /ask`
- `POST /ask/stream`

For full local app testing, run backend and frontend separately:

```bash
make api
make frontend-dev
```

The frontend usually opens at `http://127.0.0.1:5173`.

## Testing Guidance

Automated tests must avoid real network calls and must not require a real
OpenAI API key. Use mocks for OpenAI, LangChain model calls, and vector-store
work where needed.

Useful test targets:

- local document loading and metadata
- chunk metadata and ingestion manifest planning
- prompt helper functions
- chat history normalization and follow-up rewriting
- API request/response validation
- CORS behavior
- streaming SSE formatting
- eval helper functions

`make eval`, `make index-demo`, and `make ask` are manual checks because they
can call OpenAI.

## Deployment And CI

GitHub Actions lives in `.github/workflows/ci.yml` and currently runs:

- `backend-tests`: install `backend/requirements.txt`, then `make test`
- `frontend-build`: `npm ci`, then `npm run build` in `frontend/`
- `secret-scan`: scan for real-looking OpenAI `sk-...` keys

Render deployment is configured in `render.yaml`:

- backend service: `personal-docs-qa-api`
- frontend static site: `personal-docs-qa-frontend`
- backend health check path: `/health`
- backend start command first runs indexing, then starts uvicorn
- frontend publishes `frontend/dist`

The Render backend rebuilds or reuses the local index on startup. On free or
ephemeral hosting, treat `data/index/` as generated runtime data, not a durable
database.

## Security Rules

- Never commit `.env` or `frontend/.env`.
- Never hard-code API keys, tokens, or secrets.
- Keep `.env.example` and `frontend/.env.example` placeholder-only.
- `VITE_API_BASE_URL` is public frontend config, not a secret.
- `OPENAI_API_KEY` is always a secret.
- Treat `docs/` as public repository content unless the user explicitly says
  otherwise.
- Before pushing, search for secret-looking values:

```bash
rg "OPENAI_API_KEY|sk-|api_key|token|secret|password" .
```

## Generated Files

Do not commit generated local indexes, caches, dependency folders, or build
outputs:

- `data/index/`
- `.venv/`
- `.env`
- `frontend/.env`
- `frontend/node_modules/`
- `frontend/dist/`
- `__pycache__/`
- `.pycache/`
- `.pytest_cache/`
- `.mypy_cache/`
- `.ruff_cache/`
- `frontend/.vite/`
- `frontend/coverage/`

If the vector index behaves strangely, regenerate it through `make index-demo`
or the indexing module rather than editing Chroma files manually.

## Coding Guidelines

- Keep the project simple and beginner-friendly.
- Prefer explicit, readable Python and React over clever abstractions.
- Keep path and environment configuration in `config.py`.
- Keep local document loading in `load_local_docs.py`.
- Keep chunking, manifests, Chroma indexing, and vector-store opening in
  `rag_indexing.py`.
- Keep question-answering business flow in `services/qa_service.py`.
- Keep HTTP schemas, CORS, and endpoints in `api.py`.
- Keep frontend API URL handling in `frontend/src/App.jsx` unless a broader
  frontend config pattern is added.
- Avoid adding new frameworks unless they directly support the MVP goal.
- Add comments only when they clarify non-obvious LangChain, RAG, streaming, or
  deployment behavior.
- Preserve Ukrainian examples and user-facing Ukrainian text where practical.
- Keep README commands and AGENTS.md commands in sync when changing workflows.

## Git And Publishing

Before a commit or push:

1. Run `git status --short`
2. Confirm `.env` and `frontend/.env` are not staged
3. Run `make test`
4. Run `make frontend-build` if frontend changed
5. Run the secret search command from the Security Rules section
6. Check that `README.md`, `AGENTS.md`, `Makefile`, and CI still agree

## Learning-Oriented Response Style

When assisting the user in this repository:

- explain new Python, React, or shell syntax briefly
- explain LangChain and RAG concepts in plain language
- give one step at a time when the user is following the tutorial
- include a clear checkpoint at the end of each learning step
- avoid assuming previous backend, frontend, or Python experience
