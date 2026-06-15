from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from personal_docs_qa.load_local_docs import load_text_files, make_preview


class LoadLocalDocsTests(unittest.TestCase):
    def test_load_text_files_reads_only_md_and_txt(self) -> None:
        with TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            (folder / "note.md").write_text("# Hello\nWorld", encoding="utf-8")
            (folder / "car.txt").write_text("Mazda MX-5", encoding="utf-8")
            (folder / "ignore.json").write_text('{"a": 1}', encoding="utf-8")

            documents = load_text_files(folder)

        self.assertEqual(len(documents), 2)
        self.assertTrue(documents[0].metadata["source"].endswith("car.txt"))
        self.assertTrue(documents[1].metadata["source"].endswith("note.md"))
        self.assertEqual(documents[0].metadata["length"], len("Mazda MX-5"))

    def test_make_preview_normalizes_whitespace_and_truncates(self) -> None:
        preview = make_preview("Hello\n\nworld   from   docs", max_chars=12)
        self.assertEqual(preview, "Hello world ...")

if __name__ == "__main__":
    unittest.main()
