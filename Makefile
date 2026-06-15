PYTHON := ./.venv/bin/python
PIP := ./.venv/bin/pip
UVICORN := ./.venv/bin/uvicorn
BACKEND_SRC := backend/src
BACKEND_TESTS := backend/tests
BACKEND_REQUIREMENTS := backend/requirements.txt

.PHONY: install api test frontend-install frontend-dev frontend-build

install:
	$(PIP) install -r $(BACKEND_REQUIREMENTS)

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
