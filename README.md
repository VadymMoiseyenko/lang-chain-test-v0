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

## GitHub Branch Protection

Branch protection варто вмикати не одразу, а після першого зеленого CI run у GitHub Actions. Причина проста: спочатку корисно переконатися, що workflow уже стабільно працює і GitHub бачить усі потрібні checks з правильними назвами.

### Коли вмикати

Увімкни branch protection після того, як:

- workflow CI хоча б один раз успішно відпрацював у GitHub
- у списку checks видно `backend-tests`, `frontend-build` і `secret-scan`

Якщо зробити це раніше, GitHub може ще не показувати required checks у списку, і правило доведеться налаштовувати повторно.

### Як увімкнути

1. Відкрий репозиторій у GitHub.
2. Перейди в `Settings` -> `Branches`.
3. Натисни `Add branch protection rule`.
4. У полі branch name pattern введи `main`.
5. Увімкни `Require a pull request before merging`.
6. Увімкни `Require status checks to pass before merging`.
7. Додай required checks:
   - `backend-tests`
   - `frontend-build`
   - `secret-scan`
8. Збережи правило.

Після цього прямий merge у `main` без PR і без зеленого CI буде заблокований.

### Що це дає команді

- `main` лишається стабільнішою, бо зміни проходять через PR
- випадковий push із поламаним backend або frontend не потрапляє в основну гілку
- secret scan теж стає обов'язковою перевіркою перед merge
- новачкам простіше працювати безпечно, бо GitHub сам підказує правильний процес

## CI vs CD

Просте правило:

- CI у PR перевіряє зміну до merge
- CD після merge в `main` публікує вже прийняту зміну

У цьому репозиторії це виглядає так:

- CI у PR запускає `backend-tests`, `frontend-build` і `secret-scan`, щоб перевірити, що pull request не ламає проєкт
- CD після merge в `main` починається вже після успішного CI, коли hosting platform може забрати новий commit і зробити deploy

Чому branch protection корисний:

- вона з'єднує review process і CI в один обов'язковий gate перед `main`
- допомагає не зламати deploy випадковим merge
- робить процес передбачуваним: спочатку PR і checks, потім merge, потім deploy

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
ALLOWED_FRONTEND_ORIGINS=https://personal-docs-qa-frontend.onrender.com
```

`ALLOWED_FRONTEND_ORIGINS` це необов'язкова змінна середовища для CORS. Backend завжди дозволяє локальні Vite origins:

- `http://localhost:5173`
- `http://127.0.0.1:5173`

Якщо додати `ALLOWED_FRONTEND_ORIGINS`, її значення не замінює local defaults, а додається до них. Для кількох frontend URL використовуй кому:

```env
ALLOWED_FRONTEND_ORIGINS=https://personal-docs-qa-frontend.onrender.com,https://staging.example.com
```

Frontend:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

## Deploy On Render

Для першої production-версії в цьому репозиторії використовуємо [Render Blueprint](https://render.com/docs/blueprint-spec): Render читає `render.yaml` з кореня репозиторію і створює одразу два сервіси.

- backend web service: `personal-docs-qa-api`
- frontend static site: `personal-docs-qa-frontend`

У `render.yaml` зараз зафіксовано:

- backend build command: `pip install -r backend/requirements.txt`
- backend start command: `PYTHONPATH=backend/src python -m personal_docs_qa.rag_indexing && PYTHONPATH=backend/src uvicorn personal_docs_qa.api:app --host 0.0.0.0 --port $PORT`
- frontend build command: `cd frontend && npm ci && npm run build`
- frontend publish path: `frontend/dist`
- frontend public API URL: `VITE_API_BASE_URL=https://personal-docs-qa-api.onrender.com`
- backend CORS allowlist для Render frontend: `ALLOWED_FRONTEND_ORIGINS=https://personal-docs-qa-frontend.onrender.com`

`VITE_API_BASE_URL` тут навмисно зберігається прямо в `render.yaml`, бо це не secret. `OPENAI_API_KEY`, навпаки, лишається secret і в Blueprint має `sync: false`.

### Blueprint Setup

1. Запуш репозиторій у GitHub, GitLab або Bitbucket.
2. У Render Dashboard натисни `New +` -> `Blueprint`.
3. Підключи репозиторій і вибери цей проєкт.
4. Render покаже сервіси з `render.yaml`. Переконайся, що в preview видно:
   - `personal-docs-qa-api`
   - `personal-docs-qa-frontend`
5. Під час створення Blueprint введи лише один secret:

```env
OPENAI_API_KEY=your_real_key
```

6. Залиш решту значень із `render.yaml` без змін. Це стосується:
   - `OPENAI_MODEL`
   - `OPENAI_EMBEDDING_MODEL`
   - `ALLOWED_FRONTEND_ORIGINS`
   - `VITE_API_BASE_URL`
7. Створи Blueprint і дочекайся першого deploy.

Після першого deploy очікувані URL такі:

```text
https://personal-docs-qa-api.onrender.com
https://personal-docs-qa-frontend.onrender.com
```

У першій версії ми не додаємо Render PR previews. Це означає, що в `render.yaml` немає окремого `previews` конфігу і деплой лишається простішим для старту.

### Why Static Site Looks Like This

Для Static Site у Blueprint використовується `type: web` разом із `runtime: static`, а publish path у Render YAML задається полем `staticPublishPath`. Це відповідає офіційній документації Render для Blueprint static sites.

### Manual Smoke Test Checklist

Після deploy пройди короткий smoke test уже на production frontend і production backend.

1. Відкрий backend health check:

```text
https://personal-docs-qa-api.onrender.com/health
```

Очікування:

- HTTP `200 OK`
- JSON `{"status":"ok"}`

2. Відкрий backend Swagger UI:

```text
https://personal-docs-qa-api.onrender.com/docs
```

Очікування:

- Swagger UI відкривається без `502` або `504`
- видно `GET /health`, `POST /ask` і `POST /ask/stream`

3. Відкрий frontend public URL:

```text
https://personal-docs-qa-frontend.onrender.com
```

Очікування:

- сторінка відкривається без помилок build/deploy
- chat UI рендериться
- frontend не падає з `Failed to fetch` одразу після завантаження

4. Постав питання у frontend UI, наприклад:

```text
Яка різниця між MX-5 NA і ND?
```

Очікування:

- frontend надсилає запит на `https://personal-docs-qa-api.onrender.com/ask/stream`
- відповідь з'являється поступово, а не лише в кінці
- після завершення відповіді видно список `Sources`
- у `Sources` є назви файлів із `docs/`

5. Якщо щось не працює, перевір logs:

- `Render Dashboard -> personal-docs-qa-api -> Logs`
- `Render Dashboard -> personal-docs-qa-frontend -> Events`

6. Пам'ятай про cold start і rebuild index:

- на Render free plan backend може прокидатися із затримкою
- під час старту backend заново перевіряє або перебудовує локальний Chroma index
- для цього потрібен валідний `OPENAI_API_KEY`

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

### Local Frontend Against Render Backend

Щоб перевірити локальний frontend проти Render backend:

1. Створи або онови `frontend/.env`:

```env
VITE_API_BASE_URL=https://personal-docs-qa-api.onrender.com
```

2. Запусти frontend:

```bash
make frontend-dev
```

3. Відкрий локальний Vite URL, який покаже термінал, зазвичай:

```text
http://127.0.0.1:5173
```

4. Постав питання через UI, наприклад:

```text
Яка різниця між MX-5 NA і ND?
```

Очікування:

- UI відкривається локально
- frontend відправляє запит на `https://personal-docs-qa-api.onrender.com`
- у чаті з'являється відповідь backend
- перший запит може бути повільнішим, якщо backend прокидається після cold start
- якщо бачиш `Failed to fetch` або CORS-помилку, перевір `frontend/.env`, backend `ALLOWED_FRONTEND_ORIGINS`, Render URL і backend logs

### Smoke Test Script

Після deploy можна пройти smoke test у такому порядку:

```text
1. Відкрити https://personal-docs-qa-api.onrender.com/health
2. Відкрити https://personal-docs-qa-api.onrender.com/docs
3. Виконати POST /ask через Swagger UI або curl
4. Перевірити Render logs
5. Виставити frontend/.env -> VITE_API_BASE_URL=https://personal-docs-qa-api.onrender.com
6. Запустити make frontend-dev
7. Поставити те саме питання через UI
```

Expected results:

- `/health` повертає `200` і `{"status":"ok"}`
- `/docs` відкривається і показує Swagger endpoints
- `POST /ask` повертає `200` з `answer` і `sources`
- у Render logs немає startup, auth або runtime помилок
- перший запит після idle може бути повільним через Render free cold start
- перший startup після deploy або restart може бути повільнішим через rebuild Chroma index
- локальний frontend показує відповідь від Render backend

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
- CORS через `ALLOWED_FRONTEND_ORIGINS` + local defaults
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
