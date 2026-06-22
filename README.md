# Personal Docs Q&A Bot

Локальний full-stack MVP для запитань до власних документів через LangChain, OpenAI, Chroma, FastAPI і React/Vite.

## What This Project Is

Зараз це простий monorepo без додаткового monorepo tooling. У репозиторії є окремі `backend/` і `frontend/`, але запуск лишається через один кореневий `Makefile`.

Додаток:

- читає `.md` і `.txt` файли з папки `docs/`
- будує локальний Chroma index у `data/index/chroma/`
- зберігає простий ingestion manifest у `data/index/ingestion_manifest.json`
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

## GitHub Actions CI

Workflow лежить у [`.github/workflows/ci.yml`](/Users/vadym_moiseyenko/Documents/LangChain/.github/workflows/ci.yml) і запускається:

- на кожен `pull_request`
- на `push` у `main`

CI зараз має три окремі jobs:

- `backend-tests`: піднімає Python `3.11`, встановлює залежності з `backend/requirements.txt` і запускає `make test`
- `frontend-build`: піднімає Node `20`, виконує `npm ci` у `frontend/` і перевіряє production build через `npm run build`
- `secret-scan`: шукає в репозиторії рядки, схожі на реальні OpenAI ключі `sk-...`, але не падає через безпечні документаційні згадки на кшталт `OPENAI_API_KEY`

CI навмисно не запускає `make eval`, `make ask` або `make index-demo`, бо ці команди залежать від реального OpenAI API key і мережевих викликів.

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

Health endpoint для локальної перевірки й hosting health checks:

- [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

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

## Deploy Backend On Render

У цьому milestone деплоїмо тільки backend. Основний шлях: [Render Blueprint](https://render.com/docs/blueprint-spec), тобто Render читає `render.yaml` з репозиторію і сам створює service з потрібними командами та environment variables.

У репозиторії є `render.yaml`, який описує backend service:

```yaml
buildCommand: pip install -r backend/requirements.txt
startCommand: PYTHONPATH=backend/src python -m personal_docs_qa.rag_indexing && PYTHONPATH=backend/src uvicorn personal_docs_qa.api:app --host 0.0.0.0 --port $PORT
healthCheckPath: /health
autoDeployTrigger: checksPass
envVars:
  - key: PYTHON_VERSION
    value: 3.12.12
```

Що важливо:

- service name: `personal-docs-qa-api`
- Python зафіксований на `3.12.12`, щоб Render не перемикав service на нову default major/minor версію автоматично.
- `OPENAI_API_KEY` не зберігається в git. У `render.yaml` він позначений як `sync: false`, тому Render попросить ввести значення в dashboard.
- `OPENAI_MODEL` і `OPENAI_EMBEDDING_MODEL` можна лишити як public default values.
- `data/index/` не комітиться. На hosting index буде створюватися заново під час startup command.
- deploy hooks тут не використовуються. Rebuild index виконується прямо в `startCommand`.
- Якщо OpenAI тимчасово недоступний, startup indexing повторює з'єднання до трьох разів з короткими паузами.

### Blueprint Setup

1. Запуш репозиторій у GitHub/GitLab/Bitbucket.
2. У Render Dashboard натисни `New +` -> `Blueprint`.
3. Підключи свій repo і вибери цей репозиторій.
4. Render покаже preview сервісу з `render.yaml`. Переконайся, що бачиш `personal-docs-qa-api`.
5. Під час створення Blueprint додай secret:

```env
OPENAI_API_KEY=your_real_key
```

6. `OPENAI_MODEL` і `OPENAI_EMBEDDING_MODEL` можна лишити без змін, бо Blueprint уже задає default values.
7. Створи Blueprint і дочекайся першого deploy.

Після deploy відкрий:

```text
https://your-service-name.onrender.com/health
https://your-service-name.onrender.com/docs
```

### Manual Web Service Fallback

Якщо Blueprint з якоїсь причини не підходить, можна створити звичайний Web Service вручну. Вистав:

```text
Language: Python
Build Command: pip install -r backend/requirements.txt
Start Command: PYTHONPATH=backend/src python -m personal_docs_qa.rag_indexing && PYTHONPATH=backend/src uvicorn personal_docs_qa.api:app --host 0.0.0.0 --port $PORT
Health Check Path: /health
Auto-Deploy: After CI checks pass
PYTHON_VERSION: 3.12.12
```

Потім у `Environment` додай:

```env
OPENAI_API_KEY=your_real_key
OPENAI_MODEL=gpt-4.1-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

Після deploy перевір API:

```bash
curl -X POST "https://your-service-name.onrender.com/ask" \
  -H "Content-Type: application/json" \
  -d '{"question":"Яка різниця між MX-5 NA і ND?"}'
```

### Chroma Index On Hosting

Локально Chroma index лежить у `data/index/chroma/`, а ingestion manifest у `data/index/ingestion_manifest.json`. Ця папка згенерована і не має потрапляти в git.

На багатьох hosting-платформах filesystem є ephemeral: файли, створені під час роботи сервісу, можуть зникати після redeploy або restart. Це означає, що локальний `data/index/` не можна сприймати як production database.

Для demo ми обрали простий підхід: rebuild index під час startup. Render start command спочатку запускає:

```bash
PYTHONPATH=backend/src python -m personal_docs_qa.rag_indexing
```

а потім стартує `uvicorn`. Це добре для маленької demo-бази документів, але має компроміс: deploy/startup потребує `OPENAI_API_KEY`, network access до OpenAI embeddings API і кілька додаткових секунд.

Якщо платформа підтримує persistent volume/disk, можна зберігати `data/index/` на ньому. Для Render persistent disk потрібно монтувати шлях, який покриває generated index, наприклад:

```text
/opt/render/project/src/data
```

Тоді Chroma index і manifest збережуться між restart/deploy, а startup зможе перевикористати index, якщо документи не змінилися.

### Auto Deploy Check

У `render.yaml` виставлено `autoDeployTrigger: checksPass`. Це означає: Render має чекати, поки CI checks для commit пройдуть успішно, і лише після цього запускати deploy.

Щоб перевірити auto deploy:

1. Зроби маленьку зміну в README або коді.
2. Запусти локально `make test`.
3. Закоміть і запуш у branch, яку підключив Render.
4. У Render відкрий service -> `Events` або `Deploys` і переконайся, що з'явився новий deploy для останнього commit після успішних checks.
5. Після завершення deploy перевір:

```bash
curl "https://your-service-name.onrender.com/health"
curl -X POST "https://your-service-name.onrender.com/ask" \
  -H "Content-Type: application/json" \
  -d '{"question":"Яка різниця між MX-5 NA і ND?"}'
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
- change-aware ingestion planning
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

## Why Ingestion Matters In RAG

Ingestion це етап, на якому ми перетворюємо сирі файли у щось, з чим може працювати retrieval:

- читаємо документи
- додаємо metadata
- ріжемо текст на chunks
- рахуємо embeddings
- записуємо все у vector store

Якщо ingestion ненадійний, у RAG з'являються дуже практичні проблеми:

- новий файл є у `docs/`, але його ще немає в index
- змінений файл повертає стару інформацію
- видалений файл усе ще підмішується у retrieval
- важко зрозуміти, з якого саме файлу прийшов fragment

Тому в цьому проєкті ingestion став трохи ближчим до production:

- кожен source document має checksum і базову file metadata
- кожен chunk має `chunk_index` і стабільний `chunk_id`
- перед індексацією ми порівнюємо поточні файли з попереднім manifest
- якщо змін немає, існуючий Chroma index перевикористовується
- якщо є `added`, `changed` або `deleted`, index перебудовується і manifest оновлюється

Це ще не повний incremental upsert/delete у Chroma, але це правильний перший крок: система вже розуміє, що саме змінилося.

## Current Ingestion Design

Зараз flow такий:

1. `load_local_docs.py` читає `.md` і `.txt`, додає `source`, `source_name`, `source_checksum`, `modified_at`
2. `rag_indexing.py` будує ingestion plan: `added`, `changed`, `deleted`, `unchanged`
3. якщо змін нема, відкриваємо існуючий index
4. якщо зміни є, заново будуємо chunks і Chroma index
5. після rebuild зберігаємо `data/index/ingestion_manifest.json`

Наступний production-like крок, якщо захочеш піти далі:

1. видаляти з Chroma тільки чанки файлів із `deleted` та `changed`
2. доіндексовувати тільки чанки файлів із `added` та `changed`
3. уникати повного rebuild навіть коли змінився один документ

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
