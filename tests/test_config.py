import os
import unittest
from unittest.mock import patch

from rag_zotero.config import AppConfig


class TestConfig(unittest.TestCase):
    def test_sentence_transformers_model_can_be_overridden(self) -> None:
        with patch.dict(
            os.environ,
            {"SENTENCE_TRANSFORMERS_MODEL": "sentence-transformers/all-mpnet-base-v2"},
            clear=True,
        ):
            cfg = AppConfig()

        self.assertEqual(cfg.sentence_transformers_model, "sentence-transformers/all-mpnet-base-v2")


if __name__ == "__main__":
    unittest.main()
