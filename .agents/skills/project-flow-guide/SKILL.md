---
name: project-flow-guide
description: Maintain this repository's project-flow-guide.html as an up-to-date beginner-friendly visual architecture guide. Use when the user asks to create, update, refresh, improve, or regenerate the Project Flow Guide, project architecture HTML guide, RAG/LangChain flow guide, onboarding infographic, or documentation page after changes to the Personal Docs Q&A Bot repository.
---

# Project Flow Guide

## Purpose

Update `project-flow-guide.html` so a beginner can understand the current Personal Docs Q&A Bot project: what exists now, how data flows through LangChain RAG, how the backend/frontend/deploy pieces connect, and what the project is trying to reach next.

Keep the guide practical, visual, and synchronized with the repository. It is not a marketing landing page.

## Source Of Truth

Before editing the guide, inspect the current repo instead of relying on memory.

Read the relevant files for the change:

- `README.md` for current user-facing setup, commands, CI, Render, and troubleshooting.
- `AGENTS.md` for project-specific rules, expected RAG behavior, and validation checklist.
- `Makefile` for supported commands.
- `render.yaml` for deployment shape.
- `backend/src/personal_docs_qa/config.py` for paths and environment behavior when relevant.
- `backend/src/personal_docs_qa/load_local_docs.py` for document loading behavior.
- `backend/src/personal_docs_qa/rag_indexing.py` for chunking, embeddings, manifest, Chroma, and rebuild/reuse behavior.
- `backend/src/personal_docs_qa/services/qa_service.py` for question rewriting, retrieval, prompts, sources, and fallback answer.
- `backend/src/personal_docs_qa/api.py` for routes, schemas, CORS, and SSE events.
- `frontend/src/App.jsx` and CSS files for chat UI, streaming, history handling, and visual state.
- `backend/eval_cases.json`, tests, or CI files when the guide mentions evaluation or validation.

Use `rg --files`, `rg`, and targeted `sed -n` reads. Do not edit generated folders such as `data/index/`, `.venv/`, `frontend/dist/`, or `frontend/node_modules/`.

## Required Guide Structure

Keep the HTML self-contained: one static `project-flow-guide.html` file with embedded CSS and no build step.

The page should usually include these sections:

1. Hero overview: plain-language promise, current high-level system map, and key facts.
2. Product goal: what the MVP is for and what principles guide it.
3. Repository map: folders, files, and ownership boundaries.
4. Ingestion flow: documents -> metadata -> chunks -> embeddings -> Chroma -> manifest.
5. Question answering flow: input validation, chat history, standalone rewrite, retrieval, context formatting, answer generation, sources.
6. API and frontend flow: `/ask`, `/ask/stream`, SSE events, React streaming, and the frontend/backend boundary.
7. LangChain checkpoints: terms such as `Document`, chunk, embedding, vector store, retriever, prompt, LCEL chain, and output parser as they appear in this repo.
8. Runtime and deploy: local commands, CI checks, Render backend/frontend services, environment variables, generated index behavior.
9. Roadmap: what the project wants to improve next, separated from what already exists.
10. Tests and commands: what is network-free, what needs `OPENAI_API_KEY`, and the common Makefile commands.

It is fine to merge or rename sections if the repo evolves, but preserve the learning arc: goal -> structure -> data ingestion -> RAG answer path -> interfaces -> validation -> future work.

## Content Rules

- Write for a beginner in Python, backend, frontend, and LangChain.
- Prefer Ukrainian for user-facing explanations, matching the project docs.
- Preserve exact project behavior when mentioned:
  - fallback answer: `Я не знайшов цього в документах`
  - answers are expected in Ukrainian
  - current chunk/search/history constants only if confirmed from code
  - `GET /health` must not imply OpenAI access
  - `/ask/stream` sends `sources`, `answer_chunk`, optional `error`, and `done`
- Separate "current state" from "future goal" so the guide does not claim planned work already exists.
- Keep HTTP layer thin in the explanation: business logic belongs in `services/qa_service.py`.
- Make generated/runtime data explicit: `data/index/` is generated and should not be committed.
- Mention secrets carefully: real `.env` files and `OPENAI_API_KEY` must stay out of git.

## Visual And HTML Rules

- Keep the page usable by opening the HTML directly or serving it statically.
- Use visual structures such as grids, flow cards, lanes, small maps, tables, and callout notes.
- Avoid nested cards and heavy decorative backgrounds.
- Keep cards at 8px border radius or less unless the existing page has changed style.
- Ensure long inline code and table/code blocks do not create page-level horizontal overflow on mobile.
- Prefer responsive CSS with `min-width: 0`, `overflow-x: auto` on wide tables/pipelines, and explicit grid breakpoints.
- Keep CSS in the same file unless the project intentionally moves this guide into the frontend app.
- Escape literal ampersands in HTML text as `&amp;`.

## Update Workflow

1. Check `git status --short` and identify unrelated user changes. Do not revert them.
2. Inspect the existing `project-flow-guide.html` structure and style.
3. Inspect source-of-truth files that changed or that are relevant to the requested update.
4. Update the guide content and CSS with `apply_patch`.
5. Keep the guide synchronized with README, AGENTS, Makefile, CI, and deployment config when they overlap.
6. Run `git diff --check -- project-flow-guide.html`.
7. If possible, preview with a local static server and browser:
   - `python3 -m http.server 8765 --bind 127.0.0.1`
   - open `http://127.0.0.1:8765/project-flow-guide.html`
   - verify nav anchors, section count, desktop layout, and mobile overflow.
8. Stop the preview server before finishing.

If browser preview is blocked or not available, still perform static checks and report that visual browser verification was not completed.

## Suggested Browser Checks

Use a read-only DOM check to confirm:

- every `nav a[href^="#"]` points to an existing element
- expected sections are present
- infographic counts make sense after the update
- `document.documentElement.scrollWidth <= document.documentElement.clientWidth` at a narrow mobile viewport

If a local preview server requires approval because of sandboxing, request approval and explain that it is only for static HTML verification.

## Final Response

Summarize:

- what changed in `project-flow-guide.html`
- what verification was run
- whether unrelated dirty files existed and were left alone

Keep the final response concise and mention the absolute file path when useful.
