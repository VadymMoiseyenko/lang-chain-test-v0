PYTHON := ./.venv/bin/python
PIP := ./.venv/bin/pip
UVICORN := ./.venv/bin/uvicorn
BACKEND_SRC := backend/src
BACKEND_TESTS := backend/tests
BACKEND_REQUIREMENTS := backend/requirements.txt

.PHONY: install load-docs index-demo ask api test frontend-install frontend-dev frontend-build

install:
	$(PIP) install -r $(BACKEND_REQUIREMENTS)

load-docs:
	PYTHONPATH=$(BACKEND_SRC) $(PYTHON) -m personal_docs_qa.load_local_docs

index-demo:
	PYTHONPATH=$(BACKEND_SRC) $(PYTHON) -m personal_docs_qa.rag_indexing

ask:
ifeq ($(strip $(QUESTION)),)
	PYTHONPATH=$(BACKEND_SRC) $(PYTHON) -m personal_docs_qa.main
else
	PYTHONPATH=$(BACKEND_SRC) $(PYTHON) -m personal_docs_qa.main "$(QUESTION)"
endif

api:
	PYTHONPATH=$(BACKEND_SRC) $(UVICORN) personal_docs_qa.api:app --reload

test:
	PYTHONPATH=$(BACKEND_SRC) $(PYTHON) -m unittest discover -s $(BACKEND_TESTS)

frontend-install:
	cd frontend && npm install

frontend-dev:
	cd frontend && npm run dev

frontend-build:
	cd frontend && npm run build
