import unittest

from rag_zotero.indexer import _sanitize_metadata


class TestSanitizeMetadata(unittest.TestCase):
    def test_drops_none_and_stringifies_sequences(self) -> None:
        meta = _sanitize_metadata(
            {
                "title": "T",
                "year": 2020,
                "creators": ["Ada Lovelace", "Alan Turing"],
                "empty_list": [],
                "none_value": None,
                "obj": {"a": 1},
            }
        )
        self.assertEqual(meta["title"], "T")
        self.assertEqual(meta["year"], 2020)
        self.assertEqual(meta["creators"], "Ada Lovelace; Alan Turing")
        self.assertNotIn("none_value", meta)
        self.assertNotIn("empty_list", meta)
        self.assertEqual(meta["obj"], "{'a': 1}")


if __name__ == "__main__":
    unittest.main()

