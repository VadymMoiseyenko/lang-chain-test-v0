import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class RenderConfigTests(unittest.TestCase):
    def test_backend_starts_http_server_without_blocking_on_indexing(self) -> None:
        render_config = (PROJECT_ROOT / "render.yaml").read_text(encoding="utf-8")

        backend_config = render_config.split("- type: web", maxsplit=1)[1]
        start_command = next(
            line.strip()
            for line in backend_config.splitlines()
            if line.strip().startswith("startCommand:")
        )

        self.assertIn("uvicorn personal_docs_qa.api:app", start_command)
        self.assertNotIn("personal_docs_qa.rag_indexing", start_command)


if __name__ == "__main__":
    unittest.main()
