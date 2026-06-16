# Personal Docs Q&A Bot

Локальний full-stack MVP для запитань до власних документів через LangChain, OpenAI, Chroma, FastAPI і React/Vite.

## What This Project Is

Зараз це простий monorepo без додаткового monorepo tooling. У репозиторії є окремі `backend/` і `frontend/`, але запуск лишається через один кореневий `Makefile`.

Додаток:

- читає `.md` і `.txt` файли з папки `docs/`
- будує локальний Chroma index у `data/index/chroma/`
- шукає релевантні фрагменти
- переписує follow-up питання у standalone question перед retrieval
- відповідає на питання через CLI, HTTP API або простий frontend chat
- стрімить відповідь з backend у React frontend через `POST /ask/stream`

## Project Structure

```text
.
├── backend/
│   ├── requirements.txt            # Python dependencies for backend
│   ├── src/
│   │   └── personal_docs_qa/
│   │       ├── api.py              # Thin FastAPI HTTP layer
│   │       ├── config.py           # Shared paths and env loading
│   │       ├── load_local_docs.py  # Local .md/.txt loading
│   │       ├── main.py             # CLI entrypoint
│   │       ├── rag_indexing.py     # LangChain/Chroma indexing and retrieval
│   │       └── services/
│   │           └── qa_service.py   # Service/business flow for question answering
│   └── tests/                      # Unit tests without network calls
├── data/
│   └── index/                      # Generated local vector index
├── docs/                           # Source documents for RAG
├── frontend/                       # React/Vite chat UI
├── .env.example                    # Backend env example
├── .gitignore
├── AGENTS.md
├── Makefile                        # Root commands for backend and frontend
└── README.md
```

## Requirements

- Python `3.9+`
- Node.js `18+`
- npm
- OpenAI API key
- локальне virtual environment `.venv` у корені репозиторію

## Setup

```bash
python3 -m venv .venv
./.venv/bin/pip install -r backend/requirements.txt
cp .env.example .env
cd frontend
npm install
cp .env.example .env
cd ..
```

Після цього заповни `OPENAI_API_KEY` у кореневому `.env`.

## Run Commands

Через кореневий `Makefile`:

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

Або напряму:

```bash
./.venv/bin/pip install -r backend/requirements.txt
PYTHONPATH=backend/src ./.venv/bin/python -m personal_docs_qa.load_local_docs
PYTHONPATH=backend/src ./.venv/bin/python -m personal_docs_qa.rag_indexing
PYTHONPATH=backend/src ./.venv/bin/python -m personal_docs_qa.main
PYTHONPATH=backend/src ./.venv/bin/python -m personal_docs_qa.eval_rag
PYTHONPATH=backend/src ./.venv/bin/python -m personal_docs_qa.main "Яка різниця між MX-5 NA і ND?"
PYTHONPATH=backend/src ./.venv/bin/uvicorn personal_docs_qa.api:app --reload
PYTHONPATH=backend/src ./.venv/bin/python -m unittest discover -s backend/tests
cd frontend && npm install
cd frontend && npm run dev
cd frontend && npm run build
```

Після запуску API Swagger UI доступний тут:

- [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## Environment Variables

Backend:

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4.1-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

Frontend:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

## Layer Boundaries

`backend/src/personal_docs_qa/api.py`

- FastAPI routes
- request/response schema
- CORS
- HTTP error mapping

`backend/src/personal_docs_qa/services/qa_service.py`

- основний question-answering flow
- валідація питання
- проста chat history для follow-up питань
- question rewriting перед retrieval
- побудова prompt
- orchestration між retrieval і LLM answer generation

`backend/src/personal_docs_qa/rag_indexing.py`

- LangChain chunking
- OpenAI embeddings
- Chroma index creation/opening
- similarity search access

`backend/src/personal_docs_qa/load_local_docs.py`

- читання локальних `.md` і `.txt`
- перетворення у LangChain `Document`

## Why No Turborepo Yet

На цьому етапі Turborepo, Nx або інший monorepo tooling дали б більше конфігурації, ніж користі. У нас поки:

- один Python backend
- один React frontend
- прості команди запуску
- мінімальна потреба в caching/pipelines/workspaces orchestration

Тому простий поділ на `backend/` і `frontend/` плюс кореневий `Makefile` дає зрозумілу структуру без зайвого порогу входу.

## Validation Notes

- `make test` і `make load-docs` не потребують OpenAI API
- `make test` перевіряє локальну Python-логіку без реальних OpenAI викликів
- `make eval` перевіряє реальний RAG flow end-to-end: retrieval + LLM answer
- `make index-demo`, `make ask`, `make eval` і `make api` потребують валідний `OPENAI_API_KEY`
- для побудови індексу та answer generation потрібен інтернет-доступ до OpenAI API
- `.env`, `frontend/.env`, `data/index/` і `frontend/node_modules/` не мають потрапляти в git

## Conversational RAG

Звичайний RAG часто погано працює з follow-up питаннями на кшталт `А чим вона відрізняється від ND?`, бо retriever бачить тільки поточний текст питання і не знає, що `вона` означає `MX-5 NA`.

У цьому проєкті ми використовуємо простий beginner-friendly підхід:

1. Беремо поточне питання і кілька останніх повідомлень чату
2. Просимо модель переписати follow-up у standalone question для retrieval
3. Шукаємо документи вже за переписаним питанням
4. Генеруємо відповідь тільки з retrieved context

Важлива межа: історія чату допомагає лише краще шукати документи. Вона не є джерелом фактів для фінальної відповіді.

## RAG Eval

У проєкті є простий evaluation-файл: [backend/eval_cases.json](/Users/vadym_moiseyenko/Documents/LangChain/backend/eval_cases.json).

Кожен кейс містить:

- `name`: коротка назва сценарію
- `question`: тестове питання
- `expected_sources`: які файли retrieval має дістати
- `must_include`: які фрази бажано побачити у відповіді
- `expect_fallback`: чи бот має повернути `Я не знайшов цього в документах`

Запуск:

```bash
make eval
```

Приклад кейсів:

- питання, яке прямо покривається документом про `NA`
- comparison question між `NA` і `NB`
- питання поза документами, де очікується fallback

Різниця між `unit tests` і `RAG eval`:

- `unit tests` перевіряють маленькі частини коду із моками, тому вони швидкі, стабільні й не потребують OpenAI
- `RAG eval` запускає справжній retrieval і справжню генерацію відповіді, тому він корисний для перевірки якості RAG-поведінки, але залежить від моделі, індексу та мережі

Як додати новий eval-кейс:

1. Відкрий `backend/eval_cases.json`
2. Додай новий JSON-об'єкт у список
3. Заповни `question`
4. Додай `expected_sources` через назви файлів, наприклад `mazda-mx5-nd.txt`
5. Додай `must_include` для ключових фраз у відповіді
6. Для питання без відповіді в документах постав `expect_fallback: true`

## Frontend

`frontend/` не змінює свою роль і лишається окремим Vite/React застосунком. Запуск:

```bash
make frontend-dev
```

Збірка:

```bash
make frontend-build
```
