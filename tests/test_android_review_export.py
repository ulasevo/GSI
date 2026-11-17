import json
import tempfile
import unittest
from pathlib import Path

from tools.export_android_reviews import export_reviews


class AndroidReviewExportTest(unittest.TestCase):
    def test_exports_only_catalogued_authored_sections_in_order(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            entries = root / "entries"
            entries.mkdir()
            (entries / "song.md").write_text(
                '---\nartist: "Artist"\n---\n# Song\n\n'
                '## Version of ulaş\n\nHis **voice**.\n\nSecond paragraph.\n\n'
                '## Empty\n\n<!-- a prompt, not writing -->\n\n'
                '## Comment\n\nA final thought.\n', encoding="utf-8"
            )
            (entries / "private-draft.md").write_text("## Comment\nprivate", encoding="utf-8")
            catalog = root / "catalog.json"
            catalog.write_text(json.dumps({"signals": [
                {"signal_id": "sig-1", "slug": "song", "page_url": "entries/song.html"},
                {"signal_id": "sig-2", "page_url": "p53/other.html"},
            ]}), encoding="utf-8")
            result = export_reviews(catalog, entries)
            self.assertEqual(result, {"schema": 1, "reviews": {"sig-1": [
                {"title": "Version of ulaş", "content": "His **voice**.\n\nSecond paragraph."},
                {"title": "Comment", "content": "A final thought."},
            ]}})

    def test_missing_sources_and_unsafe_paths_fail(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            catalog = root / "catalog.json"
            catalog.write_text(json.dumps({"signals": [{"signal_id": "a", "slug": "missing", "page_url": "entries/missing.html"}]}))
            with self.assertRaises(FileNotFoundError):
                export_reviews(catalog, root)
            catalog.write_text(json.dumps({"signals": [{"signal_id": "a", "page_url": "entries/../../secret.html"}]}))
            with self.assertRaises(ValueError):
                export_reviews(catalog, root)
            catalog.write_text(json.dumps({"signals": [{"signal_id": "a", "slug": "other", "page_url": "entries/..\\\\secret.html"}]}))
            with self.assertRaises(ValueError):
                export_reviews(catalog, root)


if __name__ == "__main__":
    unittest.main()
