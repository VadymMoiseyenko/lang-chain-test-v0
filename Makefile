PYTHON := ./.venv/bin/python
PIP := ./.venv/bin/pip
UVICORN := ./.venv/bin/uvicorn

.PHONY: install load-docs index-demo ask api test

install:
	$(PIP) install -r requirements.txt

load-docs:
	PYTHONPATH=src $(PYTHON) -m personal_docs_qa.load_local_docs

index-demo:
	PYTHONPATH=src $(PYTHON) -m personal_docs_qa.rag_indexing

ask:
ifeq ($(strip $(QUESTION)),)
	PYTHONPATH=src $(PYTHON) -m personal_docs_qa.main
else
	PYTHONPATH=src $(PYTHON) -m personal_docs_qa.main "$(QUESTION)"
endif

api:
	PYTHONPATH=src $(UVICORN) personal_docs_qa.api:app --reload

test:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests
