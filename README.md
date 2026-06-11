# Personal Docs Q&A Bot

Локальний full-stack MVP для запитань до власних документів через LangChain, OpenAI, Chroma, FastAPI і React/Vite.

## What This Project Is

Зараз це невеликий, сфокусований RAG-застосунок. Він:

- читає `.md` і `.txt` файли з папки `docs/`
- будує локальний Chroma index у `data/index/chroma/`
- шукає релевантні фрагменти
- відповідає на питання через CLI, HTTP API або простий frontend chat
- стрімить відповідь з backend у React frontend через `POST /ask/stream`

У репозиторії більше немає окремих навчальних entrypoint-файлів. README і команди нижче описують тільки актуальний MVP flow.

## Project Structure

```text
.
├── docs/                        # Джерело документів для RAG
├── data/
│   └── index/                   # Згенерований локальний vector index
├── src/
│   └── personal_docs_qa/
│       ├── api.py               # FastAPI application
│       ├── config.py            # Project paths and env settings
│       ├── load_local_docs.py   # Loading .md/.txt files into LangChain Documents
│       ├── main.py              # CLI question-answering flow
│       └── rag_indexing.py      # Chunking, embeddings, Chroma indexing
├── frontend/                    # React/Vite chat UI
│   ├── src/
│   │   ├── App.jsx
│   │   ├── App.css
│   │   ├── index.css
│   │   └── main.jsx
│   ├── .env.example
│   ├── package.json
│   └── vite.config.js
├── tests/                       # Unit tests without network calls
├── .env.example
├── .gitignore
├── Makefile
├── README.md
└── requirements.txt
```

## Requirements

- Python `3.9+`
- Node.js `18+`
- npm
- OpenAI API key
- локальне virtual environment `.venv`

## Setup

```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
cp .env.example .env
cd frontend
npm install
cp .env.example .env
cd ..
```

Після цього заповни `OPENAI_API_KEY` у кореневому `.env`.

## Clean Start Checklist

Якщо ти запускаєш проєкт з нуля на новій машині, рекомендований порядок такий:

```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
cp .env.example .env
make test
make load-docs
make index-demo
make ask QUESTION="Яка різниця між MX-5 NA і ND?"
make api
make frontend-dev
```

Що важливо знати:

- `make test` і `make load-docs` не потребують доступу до OpenAI API
- `make index-demo`, `make ask` і `make api` потребують заповненого `OPENAI_API_KEY`
- під час побудови індексу й відповіді на питання потрібен інтернет-доступ до OpenAI API
- кореневий `.env` і `frontend/.env` лишаються локальними файлами й не мають потрапляти в git
- перед публікацією перевір `docs/`, бо ця папка піде в репозиторій

## Environment Variables

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4.1-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

Frontend змінні:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

## Run Commands

Через `Makefile`:

```bash
make install
make load-docs
make index-demo
make ask QUESTION="Яка різниця між MX-5 NA і ND?"
make api
make test
make frontend-install
make frontend-dev
make frontend-build
```

Або напряму:

```bash
./.venv/bin/pip install -r requirements.txt
PYTHONPATH=src ./.venv/bin/python -m personal_docs_qa.load_local_docs
PYTHONPATH=src ./.venv/bin/python -m personal_docs_qa.rag_indexing
PYTHONPATH=src ./.venv/bin/python -m personal_docs_qa.main
PYTHONPATH=src ./.venv/bin/python -m personal_docs_qa.main "Яка різниця між MX-5 NA і ND?"
PYTHONPATH=src ./.venv/bin/uvicorn personal_docs_qa.api:app --reload
PYTHONPATH=src ./.venv/bin/python -m unittest discover -s tests
cd frontend && npm install
cd frontend && npm run dev
cd frontend && npm run build
```

Після запуску API документація доступна тут:

- [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## Backend For React Frontend

Для локального React frontend на Vite backend уже дозволяє CORS-запити з:

- `http://localhost:5173`
- `http://127.0.0.1:5173`

Запуск backend:

```bash
make api
```

або:

```bash
PYTHONPATH=src ./.venv/bin/uvicorn personal_docs_qa.api:app --reload
```

Після запуску React frontend може викликати:

- `POST http://127.0.0.1:8000/ask`
- `POST http://127.0.0.1:8000/ask/stream`

Що таке CORS:

- CORS (`Cross-Origin Resource Sharing`) це браузерне правило безпеки для запитів між різними origin.
- `http://localhost:5173` і `http://127.0.0.1:8000` для браузера є різними origin, бо відрізняються порт і host.
- Без дозволеного CORS browser заблокує frontend-запит ще на рівні політики безпеки, навіть якщо сам FastAPI сервер працює нормально.

Для `POST /ask` і `POST /ask/stream` це особливо важливо, бо React frontend зазвичай надсилає JSON, а перед таким запитом браузер часто робить preflight `OPTIONS` перевірку.

## Frontend

У проєкті є окрема папка:

```text
frontend/
├── package.json
├── index.html
├── .env.example
├── vite.config.js
└── src/
    ├── main.jsx
    ├── App.jsx
    ├── App.css
    └── index.css
```

### Run Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Vite за замовчуванням підіймає frontend тут:

- [http://localhost:5173](http://localhost:5173)

Перед цим окремо запусти backend:

```bash
make api
```

### React Structure For Beginner

`package.json`

- це головний файл frontend-проєкту
- тут зберігаються назва проєкту, залежності (`react`, `vite`) і команди на кшталт `npm run dev`

`src/`

- це основна папка з React-кодом
- зазвичай саме тут лежать компоненти, стилі й frontend-логіка

`src/main.jsx`

- це точка входу frontend-застосунку
- файл підключає React до HTML-сторінки і рендерить компонент `App`

`src/App.jsx`

- це головний React-компонент
- у цьому проєкті саме тут живе весь простий чат: список повідомлень, поле вводу, кнопка `Send`, `fetch` на `POST /ask/stream`

`src/App.css`

- стилі саме для компонента `App`
- тут описаний вигляд чату, повідомлень, кнопки та поля вводу

`src/index.css`

- це глобальні стилі для всього frontend
- тут зручно задати базовий шрифт, кольори сторінки й `box-sizing`

`index.html`

- це єдина HTML-сторінка, в яку Vite підставляє React-додаток
- у ній є `<div id="root"></div>`, і саме в цей елемент React монтує інтерфейс

`vite.config.js`

- це конфігурація Vite
- зараз вона мінімальна: просто підключає React plugin

`frontend/.env.example`

- тут показаний приклад frontend-змінної середовища
- `VITE_API_BASE_URL` дозволяє змінити адресу backend без редагування коду

## Full-Stack Flow Check

Повна ручна перевірка MVP:

```bash
make load-docs
make index-demo
make api
```

В іншому terminal:

```bash
make frontend-dev
```

Потім відкрий:

- [http://localhost:5173](http://localhost:5173)

У чаті задай питання:

```text
Яка різниця між MX-5 NA і ND?
```

Очікуваний результат:

- frontend надсилає `POST /ask/stream` на backend
- backend дістає релевантні chunks з Chroma index
- відповідь з'являється поступово, streaming chunks
- під відповіддю показуються source file names

## Dependencies

- `langchain` - базовий orchestration шар для RAG flow
- `langchain-community` - community integrations, включно з Chroma adapter
- `langchain-openai` - інтеграція LangChain з OpenAI chat models та embeddings
- `chromadb` - локальний vector store
- `fastapi` - HTTP backend
- `uvicorn` - ASGI server для FastAPI
- `openai` - прямий Python client, який код імпортує явно
- `requests` - прямий dependency для network error handling
- `python-dotenv` - завантаження `.env`
- `tiktoken` - tokenizer dependency для OpenAI stack

## How The App Works

1. Документи лежать у `docs/`
2. `rag_indexing.py` читає їх і ділить на чанки
3. OpenAI embeddings перетворюють чанки на vectors
4. Chroma зберігає index локально
5. `main.py` або `api.py` отримують питання
6. similarity search дістає релевантні фрагменти
7. LLM відповідає тільки на основі знайденого контексту

## LangChain vs Python vs Backend

### LangChain

Це частини, які реалізують саме LLM/RAG orchestration:

- `Document` у `load_local_docs.py`
- `RecursiveCharacterTextSplitter` у `rag_indexing.py`
- `OpenAIEmbeddings` у `rag_indexing.py`
- `Chroma` integration у `rag_indexing.py`
- `ChatOpenAI`, `SystemMessage`, `HumanMessage` у `main.py`

### Python

Це звичайна прикладна логіка:

- читання файлів через `pathlib`
- робота з `os.getenv`
- metadata і preview
- CLI через `sys.argv` та `input()`
- обробка помилок
- unit-тести

### Backend

Це HTTP-шар навколо тієї ж Q&A логіки:

- [api.py](/Users/vadym_moiseyenko/Documents/LangChain/src/personal_docs_qa/api.py:1)
- `FastAPI` app
- `GET /`
- `POST /ask`
- `POST /ask/stream`
- `pydantic` request/response schemas
- запуск через `uvicorn`

## Frontend Streaming

Тепер frontend працює так:

1. користувач натискає `Send`
2. у список одразу додається `user` message
3. відразу після нього створюється порожній `assistant` message
4. frontend викликає `POST /ask/stream`
5. браузер читає `response.body` як потік і отримує маленькі частини тексту
6. кожен `answer_chunk` дописується в `assistant` message
7. коли приходить `done`, frontend показує `sources`

### Як браузер читає chunks простими словами

- `fetch(...)` повертає `response`
- у streaming-відповіді `response.body` це не готовий рядок, а `ReadableStream`
- `response.body.getReader()` дає reader, який вміє читати потік по шматочках
- `await reader.read()` повертає черговий chunk байтів
- `TextDecoder` перетворює ці байти у звичайний текст
- frontend накопичує текст, розділяє SSE-події по `\n\n` і обробляє їх по черзі
- якщо прийшов `answer_chunk`, ми просто дописуємо його в поточне assistant-повідомлення
- якщо прийшов `sources`, тимчасово зберігаємо їх
- якщо прийшов `done`, показуємо `sources` під готовою відповіддю

Ідея тут така сама, як читати повідомлення не цілим абзацом, а речення за реченням: сервер надсилає частини, а браузер одразу їх підхоплює і малює на екрані.

## Testing

Automated tests:

```bash
make test
```

або

```bash
PYTHONPATH=src ./.venv/bin/python -m unittest discover -s tests
```

Manual test checklist:

1. `cp .env.example .env` і заповнити `OPENAI_API_KEY`
2. `make load-docs` має показати demo documents з папки `docs/`
3. `make index-demo` має створити або оновити `data/index/chroma/`
4. `make ask QUESTION="Яка різниця між MX-5 NA і ND?"` має повернути відповідь українською
5. `make api` має підняти сервер на `127.0.0.1:8000`
6. `POST /ask` через Swagger або `curl` має повернути `answer` і `sources`
7. frontend на `http://localhost:5173` має поступово показувати відповідь через `POST /ask/stream`
8. Порожнє питання має повернути validation error

## Notes

- `docs/` є єдиною canonical source folder для цього MVP.
- `data/index/` є згенерованим артефактом, а не вхідними даними.
- Якщо локального індексу ще немає, застосунок створить його під час першого запиту.
- `.env` уже виключений через `.gitignore`, тому секрети треба тримати тільки там, а не в коді.
