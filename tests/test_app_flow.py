import json
from unittest.mock import patch
import unittest

from fastapi.testclient import TestClient
from langchain_core.documents import Document

from personal_docs_qa.api import app
from personal_docs_qa.main import ANSWER_NOT_FOUND, build_sources, normalize_answer
from personal_docs_qa.rag_indexing import split_into_chunks


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
