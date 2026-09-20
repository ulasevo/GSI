import csv
import json
import tempfile
import unittest
from pathlib import Path

from build import reconcile_generated_pages, sync_entry_metadata
from gsi_data import build_generation_inventory
from gsi_validation import validate_generation_manifest, validate_source_contract


TRACK_FIELDS = [
    "order",
    "tags",
    "artist",
    "track",
    "album",
    "accent",
    "cover_file",
    "cover_url",
    "spotify_url",
    "apple_url",
]


def _write_sources(root: Path, rows: list[dict], config: dict) -> tuple[Path, Path, Path, Path, Path]:
    tracks_file = root / "tracks.csv"
    config_file = root / "config.json"
    entries_dir = root / "entries"
    covers_dir = root / "covers"
    artist_assets_dir = root / "artist-assets"
    entries_dir.mkdir()
    covers_dir.mkdir()
    artist_assets_dir.mkdir()
    with tracks_file.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=TRACK_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    config_file.write_text(json.dumps(config), encoding="utf-8")
    return tracks_file, config_file, entries_dir, covers_dir, artist_assets_dir


def _config(**overrides: object) -> dict:
    config = {
        "filters": {"personal": {"label": "Personal", "color": "#d64b6a"}},
        "sections": ["Charge"],
        "p53_history": [],
        "p53_current_slug": "",
        "artist_assets": {},
    }
    config.update(overrides)
    return config


def _row(**overrides: str) -> dict:
    row = {
        "order": "",
        "tags": "personal",
        "artist": "Metric",
        "track": "Empty",
        "album": "Live It Out",
        "accent": "#ff2f92",
        "cover_file": "",
        "cover_url": "",
        "spotify_url": "",
        "apple_url": "",
    }
    row.update(overrides)
    return row


class SourceContractTests(unittest.TestCase):
    def test_current_sources_pass_site_only_preflight(self) -> None:
        root = Path(__file__).resolve().parents[1]
        errors, warnings = validate_source_contract(
            root / "tracks.csv",
            root / "config.json",
            root / "entries",
            root / "covers",
            root / "artist-assets",
            require_entries=True,
        )
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_duplicate_slug_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sources = _write_sources(
                root,
                [_row(artist="A/B"), _row(artist="A B")],
                _config(),
            )
            errors, _ = validate_source_contract(*sources)
            self.assertTrue(any("tracks.csv route" in error for error in errors))

    def test_unsafe_cover_path_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sources = _write_sources(root, [_row(cover_file="../outside.jpg")], _config())
            errors, _ = validate_source_contract(*sources)
            self.assertTrue(any("cover_file escapes covers" in error for error in errors))

    def test_invalid_current_p53_slug_is_blocked(self) -> None:
        history = [{"artist": "Metric", "track": "Empty", "album": "Live It Out", "slug": "metric-empty"}]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sources = _write_sources(
                root,
                [_row()],
                _config(p53_history=history, p53_current_slug="missing-signal"),
            )
            errors, _ = validate_source_contract(*sources)
            self.assertTrue(any("p53_current_slug" in error for error in errors))

    def test_site_only_requires_existing_entry_sources(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sources = _write_sources(root, [_row()], _config())
            errors, _ = validate_source_contract(*sources, require_entries=True)
            self.assertTrue(any("missing source entry metric-empty.md" in error for error in errors))


class GenerationInventoryTests(unittest.TestCase):
    def test_inventory_exposes_only_qualified_album_routes(self) -> None:
        tracks = [
            {"slug": "metric-empty", "html_file": "metric-empty.html", "artist": "Metric", "album": "Live It Out"},
            {"slug": "metric-too-little", "html_file": "metric-too-little.html", "artist": "Metric", "album": "Live It Out"},
            {"slug": "beach-house-new-year", "html_file": "beach-house-new-year.html", "artist": "Beach House", "album": "Bloom"},
        ]
        p53_history = [{"slug": "metric-empty"}]
        inventory = build_generation_inventory(
            tracks,
            p53_history,
            tracks,
            {"Metric": tracks[:2]},
            "metric-empty",
        )
        self.assertEqual(
            inventory["album_routes"][("Metric", "Live It Out")],
            "albums/metric-live-it-out.html",
        )
        self.assertNotIn(("Beach House", "Bloom"), inventory["album_routes"])
        self.assertIn("latest.html", inventory["expected_pages"]["p53"])

    def test_reconcile_removes_only_managed_stale_pages(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            (output_dir / "keep.html").write_text("keep", encoding="utf-8")
            (output_dir / "stale.html").write_text("stale", encoding="utf-8")
            removed = reconcile_generated_pages(output_dir, {"keep.html"}, "test page")
            self.assertEqual([path.name for path in removed], ["stale.html"])
            self.assertTrue((output_dir / "keep.html").exists())
            self.assertFalse((output_dir / "stale.html").exists())

    def test_generation_manifest_validates_routes_and_managed_extras(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for family in ("entries", "p53", "artists", "albums"):
                (root / family).mkdir()
            (root / "data").mkdir()
            for family, name in {
                "entries": "metric-empty.html",
                "p53": "index.html",
                "artists": "metric.html",
                "albums": "metric-live-it-out.html",
            }.items():
                (root / family / name).write_text("", encoding="utf-8")
            manifest = {
                "schema": 1,
                "relationships": {
                    "entries": [{"slug": "metric-empty", "href": "entries/metric-empty.html"}],
                    "p53": [{"slug": "metric-empty", "href": "p53/metric-empty.html"}],
                    "artists": [{"artist": "Metric", "href": "artists/metric.html"}],
                    "albums": [{"artist": "Metric", "album": "Live It Out", "href": "albums/metric-live-it-out.html"}],
                },
                "expected_pages": {
                    "entries": ["metric-empty.html"],
                    "p53": ["index.html"],
                    "artists": ["metric.html"],
                    "albums": ["metric-live-it-out.html"],
                },
            }
            (root / "data/generation.json").write_text(json.dumps(manifest), encoding="utf-8")
            errors = validate_generation_manifest(root)
            self.assertTrue(any("p53/metric-empty.html" in error for error in errors))
            (root / "p53/metric-empty.html").write_text("", encoding="utf-8")
            self.assertEqual(validate_generation_manifest(root), [])
            (root / "albums/stale.html").write_text("", encoding="utf-8")
            self.assertTrue(any("unexpected generated albums" in error for error in validate_generation_manifest(root)))


class EntryMetadataTests(unittest.TestCase):
    def test_sync_preserves_body_lines_that_resemble_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            entry_path = Path(directory) / "entry.md"
            entry_path.write_text(
                """---
artist: \"Old Artist\"
track: \"Old Track\"
album: \"Old Album\"
cover: \"../covers/old.jpg\"
accent: \"#111111\"
---

# Old Track — Old Artist

![cover](../covers/old.jpg)

**Album:** Old Album
**Accent:** `#111111`

## Reading

The lyric says **Album:** and **Accent:** in its own voice.
""",
                encoding="utf-8",
            )
            sync_entry_metadata(entry_path, 'New "Artist"', "New Track", "New Album", "new.jpg", "#222222")
            updated = entry_path.read_text(encoding="utf-8")
            self.assertIn('artist: "New \\"Artist\\""', updated)
            self.assertIn("**Album:** New Album", updated)
            self.assertIn("**Accent:** `#222222`", updated)
            self.assertIn("The lyric says **Album:** and **Accent:** in its own voice.", updated)

    def test_sync_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            entry_path = Path(directory) / "entry.md"
            entry_path.write_text(
                "# Track — Artist\n\n![cover](../covers/old.jpg)\n\n**Album:** Old\n**Accent:** `#111111`\n\n## Charge\n\nBody.\n",
                encoding="utf-8",
            )
            sync_entry_metadata(entry_path, "Artist", "Track", "New Album", "old.jpg", "#222222")
            first = entry_path.read_text(encoding="utf-8")
            sync_entry_metadata(entry_path, "Artist", "Track", "New Album", "old.jpg", "#222222")
            self.assertEqual(first, entry_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
