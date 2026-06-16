import json
from unittest.mock import patch
import unittest

from fastapi.testclient import TestClient
from langchain_core.documents import Document

from personal_docs_qa.api import app
from personal_docs_qa.rag_indexing import create_embeddings, split_into_chunks
from personal_docs_qa.services.qa_service import (
    ANSWER_NOT_FOUND,
    add_context_to_inputs,
    build_answer_prompt,
    build_generation_chain,
    build_question_rewrite_prompt,
    build_retrieval_chain,
    build_sources,
    format_chat_history,
    normalize_chat_history,
    normalize_answer,
    prepare_answer_generation,
    rewrite_question,
)
from langchain_core.runnables import RunnableLambda


class MainFlowTests(unittest.TestCase):
    def test_split_into_chunks_adds_chunk_metadata(self) -> None:
        documents = [
            Document(
                page_content="A" * 500,
                metadata={"source": "demo.md", "length": 500},
            )
        ]

        chunks = split_into_chunks(documents, chunk_size=120, chunk_overlap=20)

        self.assertGreater(len(chunks), 1)
        self.assertEqual(chunks[0].metadata["chunk_index"], 1)
        self.assertIn("chunk_chars", chunks[0].metadata)

    def test_create_embeddings_loads_local_settings_before_client_init(self) -> None:
        with patch("personal_docs_qa.rag_indexing.load_settings") as mocked_load_settings:
            with patch("personal_docs_qa.rag_indexing.OpenAIEmbeddings") as mocked_embeddings:
                create_embeddings()

        mocked_load_settings.assert_called_once_with()
        mocked_embeddings.assert_called_once()

    def test_build_sources_returns_api_friendly_shape(self) -> None:
        results = [
            Document(
                page_content="Mazda MX-5 NA is the first generation of the roadster.",
                metadata={"source": "docs/mazda-mx5-na.md", "chunk_index": 2},
            )
        ]

        sources = build_sources(results)

        self.assertEqual(sources[0]["source"], "docs/mazda-mx5-na.md")
        self.assertEqual(sources[0]["chunk_index"], 2)
        self.assertIn("Mazda MX-5", sources[0]["preview"])

    def test_normalize_answer_keeps_exact_fallback(self) -> None:
        self.assertEqual(normalize_answer(f"{ANSWER_NOT_FOUND}."), ANSWER_NOT_FOUND)

    def test_add_context_to_inputs_formats_retrieved_documents(self) -> None:
        inputs = {
            "question": "Що відомо про NA?",
            "search_results": [
                Document(
                    page_content="MX-5 NA is the first generation.",
                    metadata={"source": "docs/mazda-mx5-na.md", "chunk_index": 1},
                )
            ],
        }

        prepared = add_context_to_inputs(inputs)

        self.assertIn("[Fragment 1]", prepared["context"])
        self.assertIn("docs/mazda-mx5-na.md", prepared["context"])

    def test_build_answer_prompt_contains_question_and_context_variables(self) -> None:
        prompt_value = build_answer_prompt().invoke(
            {
                "question": "Що відомо про ND?",
                "context": "source: docs/mazda-mx5-nd.txt",
            }
        )

        prompt_text = prompt_value.to_string()
        self.assertIn("Що відомо про ND?", prompt_text)
        self.assertIn("docs/mazda-mx5-nd.txt", prompt_text)

    def test_build_generation_chain_returns_plain_text(self) -> None:
        fake_llm = RunnableLambda(lambda _: "Коротка відповідь")
        chain = build_generation_chain(fake_llm)

        answer = chain.invoke(
            {
                "question": "Що відомо про NC?",
                "context": "source: docs/mazda-mx5-nc.md",
            }
        )

        self.assertEqual(answer, "Коротка відповідь")

    def test_format_chat_history_returns_readable_dialogue(self) -> None:
        chat_history = [
            {"role": "user", "content": "Що таке MX-5 NA?"},
            {"role": "assistant", "content": "Це перше покоління MX-5."},
        ]

        formatted_history = format_chat_history(chat_history)

        self.assertIn("Користувач: Що таке MX-5 NA?", formatted_history)
        self.assertIn("Бот: Це перше покоління MX-5.", formatted_history)

    def test_normalize_chat_history_keeps_latest_non_empty_messages(self) -> None:
        chat_history = [
            {"role": "assistant", "content": "  "},
            {"role": "user", "content": "Питання 1"},
            {"role": "assistant", "content": "Відповідь 1"},
            {"role": "user", "content": "Питання 2"},
            {"role": "assistant", "content": "Відповідь 2"},
            {"role": "user", "content": "Питання 3"},
            {"role": "assistant", "content": "Відповідь 3"},
            {"role": "user", "content": "Питання 4"},
        ]

        normalized_history = normalize_chat_history(chat_history)

        self.assertEqual(len(normalized_history), 6)
        self.assertEqual(normalized_history[0]["content"], "Відповідь 1")
        self.assertEqual(normalized_history[-1]["content"], "Питання 4")

    def test_normalize_chat_history_rejects_unknown_roles(self) -> None:
        with self.assertRaises(ValueError):
            normalize_chat_history([{"role": "system", "content": "Привіт"}])

    def test_build_question_rewrite_prompt_contains_history_and_question(self) -> None:
        prompt_value = build_question_rewrite_prompt().invoke(
            {
                "chat_history": "Користувач: Що таке MX-5 NA?",
                "question": "А чим вона відрізняється від ND?",
            }
        )

        prompt_text = prompt_value.to_string()
        self.assertIn("Що таке MX-5 NA?", prompt_text)
        self.assertIn("А чим вона відрізняється від ND?", prompt_text)

    def test_rewrite_question_uses_history_to_make_follow_up_standalone(self) -> None:
        fake_llm = RunnableLambda(lambda _: "Чим MX-5 NA відрізняється від ND?")

        rewritten_question = rewrite_question(
            "А чим вона відрізняється від ND?",
            [
                {"role": "user", "content": "Що таке MX-5 NA?"},
                {"role": "assistant", "content": "MX-5 NA - перше покоління."},
            ],
            llm=fake_llm,
        )

        self.assertEqual(rewritten_question, "Чим MX-5 NA відрізняється від ND?")

    def test_build_retrieval_chain_adds_documents_and_context(self) -> None:
        fake_retriever = RunnableLambda(
            lambda question: [
                Document(
                    page_content=f"Знайдений фрагмент для: {question}",
                    metadata={"source": "docs/example.md", "chunk_index": 1},
                )
            ]
        )
        retrieval_chain = build_retrieval_chain(fake_retriever)

        prepared = retrieval_chain.invoke(
            {
                "question": "А що там про нього?",
                "standalone_question": "Що є в документах про MX-5 NA?",
            }
        )

        self.assertEqual(len(prepared["search_results"]), 1)
        self.assertIn("MX-5 NA", prepared["search_results"][0].page_content)
        self.assertIn("docs/example.md", prepared["context"])

    def test_prepare_answer_generation_uses_rewritten_question_for_retrieval(self) -> None:
        fake_retriever = RunnableLambda(
            lambda question: [
                Document(
                    page_content=f"Пошук спрацював для: {question}",
                    metadata={"source": "docs/mazda-mx5-na.md", "chunk_index": 1},
                )
            ]
        )

        with patch(
            "personal_docs_qa.services.qa_service.get_ready_retriever",
            return_value=fake_retriever,
        ):
            prepared = prepare_answer_generation(
                "А чим вона відрізняється від ND?",
                chat_history=[
                    {"role": "user", "content": "Що таке MX-5 NA?"},
                    {"role": "assistant", "content": "MX-5 NA - перше покоління."},
                ],
                rewriter_llm=RunnableLambda(
                    lambda _: "Чим MX-5 NA відрізняється від ND?"
                ),
            )

        self.assertEqual(
            prepared["standalone_question"],
            "Чим MX-5 NA відрізняється від ND?",
        )
        self.assertIn(
            "Чим MX-5 NA відрізняється від ND?",
            prepared["context"],
        )


class ApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.frontend_origin = "http://localhost:5173"
        self.frontend_origin_127 = "http://127.0.0.1:5173"

    def test_root_endpoint_returns_status_message(self) -> None:
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("running", response.json()["message"])

    def test_ask_endpoint_returns_mocked_answer(self) -> None:
        fake_result = {
            "answer": "Знайшов відповідь у документах.",
            "sources": [
                {
                    "source": "docs/example.md",
                    "chunk_index": 1,
                    "preview": "Demo preview",
                }
            ],
        }

        with patch("personal_docs_qa.api.answer_question", return_value=fake_result):
            response = self.client.post(
                "/ask",
                json={"question": "Що є в документах?"},
                headers={"Origin": self.frontend_origin},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["answer"], fake_result["answer"])
        self.assertEqual(response.json()["sources"][0]["source"], "docs/example.md")
        self.assertEqual(
            response.headers["access-control-allow-origin"],
            self.frontend_origin,
        )

    def test_ask_endpoint_forwards_chat_history(self) -> None:
        fake_result = {
            "answer": "Порівняння знайдено у документах.",
            "sources": [],
        }

        with patch("personal_docs_qa.api.answer_question", return_value=fake_result) as mocked_answer:
            response = self.client.post(
                "/ask",
                json={
                    "question": "А чим вона відрізняється від ND?",
                    "chat_history": [
                        {"role": "user", "content": "Що таке MX-5 NA?"},
                        {"role": "assistant", "content": "Це перше покоління MX-5."},
                    ],
                },
            )

        self.assertEqual(response.status_code, 200)
        mocked_answer.assert_called_once_with(
            "А чим вона відрізняється від ND?",
            chat_history=[
                {"role": "user", "content": "Що таке MX-5 NA?"},
                {"role": "assistant", "content": "Це перше покоління MX-5."},
            ],
        )

    def test_ask_endpoint_rejects_empty_question(self) -> None:
        response = self.client.post("/ask", json={"question": ""})

        self.assertEqual(response.status_code, 422)

    def test_ask_stream_returns_sources_chunks_and_done_events(self) -> None:
        def fake_stream():
            yield "Перший фрагмент "
            yield "і другий."

        fake_sources = [
            {
                "source": "docs/example.md",
                "chunk_index": 1,
                "preview": "Demo preview",
            }
        ]

        with patch(
            "personal_docs_qa.api.stream_answer_chunks",
            return_value=(fake_sources, fake_stream()),
        ):
            with self.client.stream(
                "POST",
                "/ask/stream",
                json={"question": "Що є в документах?"},
                headers={"Origin": self.frontend_origin},
            ) as response:
                body = response.read().decode()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers["access-control-allow-origin"],
            self.frontend_origin,
        )
        self.assertIn("event: sources", body)
        self.assertIn("event: answer_chunk", body)
        self.assertIn("event: done", body)
        self.assertIn(json.dumps({"sources": fake_sources}, ensure_ascii=False), body)
        self.assertIn(
            json.dumps({"content": "Перший фрагмент "}, ensure_ascii=False),
            body,
        )
        self.assertIn(
            json.dumps({"content": "і другий."}, ensure_ascii=False),
            body,
        )

    def test_ask_stream_forwards_chat_history(self) -> None:
        with patch(
            "personal_docs_qa.api.stream_answer_chunks",
            return_value=([], iter(["Готово"])),
        ) as mocked_stream:
            with self.client.stream(
                "POST",
                "/ask/stream",
                json={
                    "question": "А чим вона відрізняється від ND?",
                    "chat_history": [
                        {"role": "user", "content": "Що таке MX-5 NA?"},
                        {"role": "assistant", "content": "Це перше покоління MX-5."},
                    ],
                },
            ) as response:
                _ = response.read().decode()

        self.assertEqual(response.status_code, 200)
        mocked_stream.assert_called_once_with(
            "А чим вона відрізняється від ND?",
            chat_history=[
                {"role": "user", "content": "Що таке MX-5 NA?"},
                {"role": "assistant", "content": "Це перше покоління MX-5."},
            ],
        )

    def test_ask_stream_returns_error_event_when_stream_fails(self) -> None:
        def broken_stream():
            yield "Початок"
            raise RuntimeError("Stream failed")

        with patch(
            "personal_docs_qa.api.stream_answer_chunks",
            return_value=([], broken_stream()),
        ):
            with self.client.stream(
                "POST",
                "/ask/stream",
                json={"question": "Що є в документах?"},
            ) as response:
                body = response.read().decode()

        self.assertEqual(response.status_code, 200)
        self.assertIn("event: error", body)
        self.assertIn(
            json.dumps({"message": "Stream failed"}, ensure_ascii=False),
            body,
        )

    def test_ask_endpoint_allows_cors_preflight_from_local_frontend(self) -> None:
        response = self.client.options(
            "/ask",
            headers={
                "Origin": self.frontend_origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers["access-control-allow-origin"],
            self.frontend_origin,
        )
        self.assertIn("POST", response.headers["access-control-allow-methods"])

    def test_ask_stream_endpoint_allows_cors_preflight_from_local_frontend(self) -> None:
        response = self.client.options(
            "/ask/stream",
            headers={
                "Origin": self.frontend_origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers["access-control-allow-origin"],
            self.frontend_origin,
        )
        self.assertIn("POST", response.headers["access-control-allow-methods"])

    def test_ask_endpoint_allows_cors_from_127_vite_origin(self) -> None:
        fake_result = {
            "answer": "Знайшов відповідь у документах.",
            "sources": [],
        }

        with patch("personal_docs_qa.api.answer_question", return_value=fake_result):
            response = self.client.post(
                "/ask",
                json={"question": "Що є в документах?"},
                headers={"Origin": self.frontend_origin_127},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers["access-control-allow-origin"],
            self.frontend_origin_127,
        )


if __name__ == "__main__":
    unittest.main()
