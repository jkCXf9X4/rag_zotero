import json
import tempfile
import unittest
from pathlib import Path

from rag_zotero.zotero_export import load_zotero_export


class TestZoteroExport(unittest.TestCase):
    def _load(self, payload) -> object:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "export.json"
            p.write_text(json.dumps(payload), encoding="utf-8")
            return load_zotero_export(p)

    def test_zotero_json_api_style_data_wrapper(self) -> None:
        export = self._load(
            [
                {
                    "key": "PARENT1",
                    "data": {
                        "itemType": "journalArticle",
                        "title": "My Paper",
                        "creators": [{"firstName": "Ada", "lastName": "Lovelace"}],
                        "date": "2020-01-02",
                        "DOI": "10.1234/abc",
                        "url": "https://example.com",
                    },
                },
                {
                    "key": "ATTACH1",
                    "data": {
                        "itemType": "attachment",
                        "parentItem": "PARENT1",
                        "path": "storage:ATTACH1/paper.pdf",
                    },
                },
            ]
        )
        meta = export.metadata_for_attachment("ATTACH1")
        self.assertEqual(meta.get("item_key"), "PARENT1")
        self.assertEqual(meta.get("title"), "My Paper")
        self.assertEqual(meta.get("year"), 2020)
        self.assertEqual(meta.get("doi"), "10.1234/abc")
        self.assertEqual(meta.get("url"), "https://example.com")

    def test_better_bibtex_nested_attachments(self) -> None:
        export = self._load(
            {
                "items": [
                    {
                        "itemKey": "PARENT2",
                        "itemType": "journalArticle",
                        "title": "Another Paper",
                        "creators": [{"name": "Alan Turing"}],
                        "date": "2019",
                        "citationKey": "Turing2019",
                        "attachments": [{"path": "storage:ATTACH2/file.pdf"}],
                    }
                ]
            }
        )
        meta = export.metadata_for_attachment("ATTACH2")
        self.assertEqual(meta.get("item_key"), "PARENT2")
        self.assertEqual(meta.get("title"), "Another Paper")
        self.assertEqual(meta.get("year"), 2019)
        self.assertEqual(meta.get("citekey"), "Turing2019")

    def test_attachments_as_strings_and_absolute_local_path(self) -> None:
        export = self._load(
            [
                {
                    "itemKey": "PARENT4",
                    "itemType": "report",
                    "title": "String Attachments",
                    "date": "2021",
                    "attachments": [
                        "storage:ABCD1234/file.pdf",
                        {"localPath": "/home/me/Zotero/storage/EFGH5678/other.pdf"},
                    ],
                }
            ]
        )
        meta4 = export.metadata_for_attachment("ABCD1234")
        self.assertEqual(meta4.get("title"), "String Attachments")
        self.assertEqual(meta4.get("year"), 2021)
        meta5 = export.metadata_for_attachment("EFGH5678")
        self.assertEqual(meta5.get("title"), "String Attachments")

    def test_csl_issued_date_parts(self) -> None:
        export = self._load(
            [
                {
                    "key": "PARENT3",
                    "data": {
                        "itemType": "journalArticle",
                        "title": "CSL Paper",
                        "issued": {"date-parts": [[2018, 5, 1]]},
                        "attachments": [{"path": "storage:ATTACH3/file.pdf"}],
                    },
                }
            ]
        )
        meta = export.metadata_for_attachment("ATTACH3")
        self.assertEqual(meta.get("year"), 2018)


if __name__ == "__main__":
    unittest.main()
