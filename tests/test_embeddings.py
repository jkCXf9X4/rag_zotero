import tempfile
import unittest
from pathlib import Path

from rag_zotero.embeddings import resolve_embeddings


class TestEmbeddings(unittest.TestCase):
    def test_local_sentence_transformers_model_path_is_resolved(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            model_dir = Path(td) / "local-model"
            model_dir.mkdir()

            embedder, backend = resolve_embeddings(
                openai_api_key=None,
                openai_model="text-embedding-3-small",
                sentence_transformers_model=str(model_dir),
            )

        self.assertEqual(backend, "sentence-transformers")
        self.assertEqual(embedder.model_name, str(model_dir.resolve()))

    def test_local_sentence_transformers_model_path_must_be_directory(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            model_file = Path(td) / "model.bin"
            model_file.write_text("not a model dir", encoding="utf-8")

            with self.assertRaises(RuntimeError):
                resolve_embeddings(
                    openai_api_key=None,
                    openai_model="text-embedding-3-small",
                    sentence_transformers_model=str(model_file),
                )


if __name__ == "__main__":
    unittest.main()
