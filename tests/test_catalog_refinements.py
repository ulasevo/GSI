import tempfile
import unittest
from pathlib import Path

from builder.catalog_pages import build_album_pages, build_artist_pages


class CatalogRefinementsTests(unittest.TestCase):
    def test_album_discography_tracker_and_sorting(self):
        tracks = [
            {
                "artist": "Metric",
                "album": "Live It Out",
                "track": "Too Little Too Late",
                "slug": "metric-too-little-too-late",
                "html_file": "metric-too-little-too-late.html",
                "cover_file": "metric-too-little-too-late.jpg",
                "accent": "#ff4fa3",
                "track_number": 4,
                "track_count": 10,
            },
            {
                "artist": "Metric",
                "album": "Live It Out",
                "track": "Empty",
                "slug": "metric-empty",
                "html_file": "metric-empty.html",
                "cover_file": "metric-empty.jpg",
                "accent": "#ff4fa3",
                "track_number": 1,
                "track_count": 10,
            },
        ]
        with tempfile.TemporaryDirectory() as temp:
            output_dir = Path(temp)
            build_album_pages(tracks, output_dir=output_dir)
            page = (output_dir / "metric-live-it-out.html").read_text(encoding="utf-8")

        # Sorted by ascending track number (Empty 01 before Too Little Too Late 04)
        self.assertTrue(page.index("Empty") < page.index("Too Little Too Late"))
        # 2 / 10 ARCHIVED badge
        self.assertIn("2 / 10 ARCHIVED", page)
        # Reviewed rows use right-side chevron ›
        self.assertIn('class="album-song-chevron"', page)
        self.assertIn(">›</b>", page)
        # Unreviewed track rows
        self.assertIn("album-song--unreviewed", page)
        self.assertIn("Track 02", page)
        self.assertIn("Track 10", page)
        self.assertIn("TRACK 02 OF 10 · UNREVIEWED", page)

    def test_artist_page_sorting_and_chevrons(self):
        tracks = [
            {
                "artist": "Metric",
                "album": "Live It Out",
                "track": "Too Little Too Late",
                "slug": "metric-too-little-too-late",
                "html_file": "metric-too-little-too-late.html",
                "cover_file": "metric-too-little-too-late.jpg",
                "accent": "#ff4fa3",
                "track_number": 4,
                "track_count": 10,
            },
            {
                "artist": "Metric",
                "album": "Live It Out",
                "track": "Empty",
                "slug": "metric-empty",
                "html_file": "metric-empty.html",
                "cover_file": "metric-empty.jpg",
                "accent": "#ff4fa3",
                "track_number": 1,
                "track_count": 10,
            },
        ]
        with tempfile.TemporaryDirectory() as temp:
            output_dir = Path(temp)
            build_artist_pages(
                {"Metric": tracks},
                {"filters": {}, "artist_notes": {}, "album_notes": {}},
                output_dir=output_dir,
                artist_assets_dir=output_dir / "artist-assets",
            )
            page = (output_dir / "metric.html").read_text(encoding="utf-8")

        self.assertTrue(page.index("Empty") < page.index("Too Little Too Late"))
        self.assertIn('class="album-entry-chevron"', page)
        self.assertIn(">›</b>", page)


if __name__ == "__main__":
    unittest.main()
