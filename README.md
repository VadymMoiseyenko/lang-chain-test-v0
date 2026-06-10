# Personal Docs Q&A Bot

Локальний MVP для запитань до власних документів через LangChain, OpenAI, Chroma і FastAPI.

## What This Project Is

Зараз це невеликий, сфокусований RAG-застосунок. Він:

- читає `.md` і `.txt` файли з папки `docs/`
- будує локальний Chroma index у `data/index/chroma/`
- шукає релевантні фрагменти
- відповідає на питання через CLI або HTTP API

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
├── tests/                       # Unit tests without network calls
├── .env.example
├── .gitignore
├── Makefile
├── README.md
└── requirements.txt
```

## Requirements

- Python `3.9+`
- OpenAI API key
- локальне virtual environment `.venv`

## Setup

```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
cp .env.example .env
```

Після цього заповни `OPENAI_API_KEY` у `.env`.

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
```

Що важливо знати:

- `make test` і `make load-docs` не потребують доступу до OpenAI API
- `make index-demo`, `make ask` і `make api` потребують заповненого `OPENAI_API_KEY`
- під час побудови індексу й відповіді на питання потрібен інтернет-доступ до OpenAI API
- `.env` лишається локальним файлом і не має потрапляти в git
- перед публікацією перевір `docs/`, бо ця папка піде в репозиторій

## Environment Variables

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4.1-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
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
```

Після запуску API документація доступна тут:

- [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

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
- `pydantic` request/response schemas
- запуск через `uvicorn`

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
7. Порожнє питання має повернути validation error

## Notes

- `docs/` є єдиною canonical source folder для цього MVP.
- `data/index/` є згенерованим артефактом, а не вхідними даними.
- Якщо локального індексу ще немає, застосунок створить його під час першого запиту.
- `.env` уже виключений через `.gitignore`, тому секрети треба тримати тільки там, а не в коді.
