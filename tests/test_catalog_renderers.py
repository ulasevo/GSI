import tempfile
import unittest
import json
from pathlib import Path

from builder.catalog_pages import build_album_pages, build_artist_pages
from builder.entry_pages import build_entry_page, extract_sections_from_markdown
from builder.error_pages import build_404_page
from builder.home_page import build_index_html
from builder.manifests import write_generation_manifest


def sample_tracks():
    return [
        {
            "artist": "Metric",
            "album": "Live It Out",
            "track": "Empty",
            "slug": "metric-empty",
            "html_file": "metric-empty.html",
            "cover_file": "metric-empty.jpg",
            "accent": "#ff4fa3",
        },
        {
            "artist": "Metric",
            "album": "Live It Out",
            "track": "Too Little Too Late",
            "slug": "metric-too-little-too-late",
            "html_file": "metric-too-little-too-late.html",
            "cover_file": "metric-too-little-too-late.jpg",
            "accent": "#ff4fa3",
        },
    ]


class CatalogueRendererTests(unittest.TestCase):
    def test_artist_room_writes_album_stack_and_text_first_song_links(self):
        with tempfile.TemporaryDirectory() as temp:
            output_dir = Path(temp)
            build_artist_pages(
                {"Metric": sample_tracks()},
                {"filters": {}, "artist_notes": {}, "album_notes": {}},
                output_dir=output_dir,
                artist_assets_dir=output_dir / "artist-assets",
            )
            page = (output_dir / "metric.html").read_text(encoding="utf-8")

        self.assertIn('class="album-stack"', page)
        self.assertIn('class="album-entry"', page)
        self.assertIn("Empty", page)
        self.assertIn("Too Little Too Late", page)
        self.assertNotIn('class="artist-signal"', page)

    def test_album_room_writes_shared_artist_link_and_all_songs(self):
        with tempfile.TemporaryDirectory() as temp:
            output_dir = Path(temp)
            build_album_pages(sample_tracks(), output_dir=output_dir)
            page = (output_dir / "metric-live-it-out.html").read_text(encoding="utf-8")

        self.assertIn('id="album-artist-return"', page)
        self.assertIn("Metric", page)
        self.assertIn("Empty", page)
        self.assertIn("Too Little Too Late", page)
        self.assertIn("ALBUM / 02 SIGNALS", page)
        self.assertIn(">Live It Out</strong>", page)

    def test_generation_manifest_can_target_an_isolated_output(self):
        inventory = {
            "entry_routes": {"metric-empty": "entries/metric-empty.html"},
            "p53_routes": {"metric-empty": "p53/metric-empty.html"},
            "artist_routes": {"Metric": "artists/metric.html"},
            "album_routes": {("Metric", "Live It Out"): "albums/metric-live-it-out.html"},
            "expected_pages": {"entries": {"metric-empty.html"}, "p53": {"index.html"}},
        }
        with tempfile.TemporaryDirectory() as temp:
            output_path = Path(temp) / "data" / "generation.json"
            write_generation_manifest(inventory, output_path=output_path)
            manifest = output_path.read_text(encoding="utf-8")

        self.assertIn('"metric-empty.html"', manifest)
        self.assertIn('"Live It Out"', manifest)

    def test_entry_room_reads_authored_sections_and_uses_explicit_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            entries_dir = root / "entries"
            output_dir = root / "site" / "entries"
            entries_dir.mkdir(parents=True)
            entry_path = entries_dir / "metric-empty.md"
            entry_path.write_text(
                "---\nartist: Metric\ntrack: Empty\nalbum: Live It Out\n---\n"
                "# Empty — Metric\n\n## Charge\n\nA stored feeling.\n\n"
                "## Sonical Attraction\n\nA sharp pulse.\n\n## Lore\n\nA place in time.\n",
                encoding="utf-8",
            )
            config_path = root / "config.json"
            config_path.write_text(
                json.dumps({"filters": {}, "section_info": {}}),
                encoding="utf-8",
            )
            sections = extract_sections_from_markdown(entry_path)
            build_entry_page(
                {
                    "artist": "Metric",
                    "track": "Empty",
                    "album": "Live It Out",
                    "slug": "metric-empty",
                    "entry_file": entry_path.name,
                    "html_file": "metric-empty.html",
                    "cover_file": "",
                    "accent": "#ff4fa3",
                    "tags": "",
                },
                config_file=config_path,
                entries_dir=entries_dir,
                output_dir=output_dir,
            )
            page = (output_dir / "metric-empty.html").read_text(encoding="utf-8")

        self.assertEqual([section["title"] for section in sections], ["Charge", "Sonical Attraction", "Lore"])
        self.assertIn('class="entry-index"', page)
        self.assertIn("A stored feeling.", page)
        self.assertIn("A sharp pulse.", page)

    def test_homepage_renderer_can_target_an_explicit_output(self):
        tracks = [
            {
                "artist": "Metric",
                "track": "Empty",
                "album": "Live It Out",
                "slug": "metric-empty",
                "html_file": "metric-empty.html",
                "cover_file": "",
                "accent": "#ff4fa3",
                "tags": "personal",
                "page_url": "entries/metric-empty.html",
                "p53_order": 999,
            }
        ]
        config = {
            "project_title": "GSI",
            "page_title": "GSI",
            "intro": "A personal signal room.",
            "filters": {"personal": {"label": "Personal", "description": "One room."}},
            "p53_current_slug": "",
        }
        with tempfile.TemporaryDirectory() as temp:
            config_path = Path(temp) / "config.json"
            output_path = Path(temp) / "site" / "index.html"
            config_path.write_text(json.dumps(config), encoding="utf-8")
            build_index_html(tracks, config_file=config_path, output_path=output_path)
            page = output_path.read_text(encoding="utf-8")

        self.assertIn('class="layout-format-controls"', page)
        self.assertIn('data-filter="personal"', page)
        self.assertIn("A personal signal room.", page)
        self.assertIn("Empty", page)

    def test_404_renderer_can_target_an_explicit_output(self):
        tracks = [
            {
                "artist": "Metric",
                "track": "Empty",
                "album": "Live It Out",
                "html_file": "metric-empty.html",
                "page_url": "entries/metric-empty.html",
                "cover_file": "metric-empty.jpg",
                "accent": "#ff4fa3",
            }
        ]
        config = {
            "site_url": "",
            "not_found": {
                "title": "THIS SIGNAL IS NOT HERE.",
                "message": "The page slipped out of GSI.",
            },
        }
        with tempfile.TemporaryDirectory() as temp:
            config_path = Path(temp) / "config.json"
            output_path = Path(temp) / "site" / "404.html"
            config_path.write_text(json.dumps(config), encoding="utf-8")
            build_404_page(tracks, config_file=config_path, output_path=output_path)
            page = output_path.read_text(encoding="utf-8")

        self.assertIn("THIS SIGNAL IS <em>NOT</em> HERE.", page)
        self.assertIn("metric-empty.html", page)
        self.assertIn("OPEN SIGNAL IN GSI", page)


if __name__ == "__main__":
    unittest.main()
