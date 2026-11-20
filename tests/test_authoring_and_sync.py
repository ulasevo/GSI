"""Regression tests for authoring helpers, plural formatting, link escaping, P53 sorting, and Android sync."""

from __future__ import annotations

import argparse
import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from builder.catalog_pages import build_album_pages
from builder.p53_pages import build_p53_archive
from gsi_data import read_tracks
from gsi_links import catalogue_record, streaming_link_markup
from tools.new_entry import (
    TRACK_COLUMNS,
    _interactive_namespace,
    _replace_track,
    _update_catalogue_notes,
    _update_p53,
    publish_draft,
)
from tools.sync_android_assets import sync_android_assets


class AuthoringAndSyncRegressionTests(unittest.TestCase):
    def test_replace_track_falls_back_to_append_track_when_row_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tracks_path = root / "tracks.csv"
            with tracks_path.open("w", encoding="utf-8", newline="") as fh:
                writer = csv.DictWriter(fh, fieldnames=TRACK_COLUMNS, lineterminator="\n")
                writer.writeheader()

            record = {
                "signal_id": "GSI-101",
                "slug": "metric-combat-baby",
                "artist": "Metric",
                "track": "Combat Baby",
                "album": "Old World Underground",
                "tags": "bite",
                "cover_file": "metric-combat-baby.jpg",
            }
            _replace_track(root, record)
            rows = read_tracks(tracks_path)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["track"], "Combat Baby")

    def test_interactive_namespace_preserves_artist_and_album_note_attrs(self):
        ns = argparse.Namespace()
        inputs = iter(["https://open.spotify.com/track/123", "Artist", "Track", "Album", "bite", "y", "", "n", "n"])
        with patch("builtins.input", side_effect=lambda *_args: next(inputs)):
            out = _interactive_namespace(ns, {"sections": ["Charge"]})
        self.assertEqual(out.artist_note, "")
        self.assertEqual(out.album_note, "")

    def test_update_p53_moves_promoted_current_track_to_tail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = {
                "p53_history": [
                    {"slug": "first-track", "signal_id": "GSI-001", "artist": "A", "track": "1", "album": "Al"},
                    {"slug": "second-track", "signal_id": "GSI-002", "artist": "B", "track": "2", "album": "Al"},
                ],
                "p53_transmission_notes": {},
            }
            (root / "config.json").write_text(json.dumps(config), encoding="utf-8")
            _update_p53(
                root,
                {
                    "slug": "first-track",
                    "signal_id": "GSI-001",
                    "artist": "A",
                    "track": "1",
                    "album": "Al",
                    "cover_file": "first.jpg",
                    "spotify_url": "",
                    "apple_url": "",
                    "preview_url": "",
                    "accent": "#ff65ad",
                },
                enabled=True,
                note="Promoted note",
                current=True,
            )
            updated = json.loads((root / "config.json").read_text(encoding="utf-8"))
            self.assertEqual([item["slug"] for item in updated["p53_history"]], ["second-track", "first-track"])
            self.assertEqual(updated["p53_current_slug"], "first-track")

    def test_update_catalogue_notes_clears_and_prunes_empty_dicts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = {
                "artist_notes": {"Metric": "Old artist note"},
                "album_notes": {"Metric": {"Live It Out": "Old album note"}},
            }
            (root / "config.json").write_text(json.dumps(config), encoding="utf-8")
            _update_catalogue_notes(
                root,
                {"artist": "Metric", "album": "Live It Out"},
                artist_note="",
                album_note="",
                allow_clear=True,
            )
            updated = json.loads((root / "config.json").read_text(encoding="utf-8"))
            self.assertNotIn("Metric", updated.get("artist_notes", {}))
            self.assertNotIn("Metric", updated.get("album_notes", {}))

    def test_publish_draft_rollback_removes_newly_written_artist_artwork(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow is required for artist artwork rollback test")

        import base64
        import io
        from builder.entry_drafts import DraftMetadataError

        buf = io.BytesIO()
        Image.new("RGB", (600, 600), (120, 40, 140)).save(buf, format="JPEG", quality=85)
        data_url = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "entries").mkdir()
            (root / "covers").mkdir()
            with (root / "tracks.csv").open("w", encoding="utf-8", newline="") as fh:
                writer = csv.DictWriter(fh, fieldnames=TRACK_COLUMNS, lineterminator="\n")
                writer.writeheader()
            (root / "config.json").write_text(json.dumps({"sections": ["Charge"]}), encoding="utf-8")

            draft = {
                "schema": 1,
                "record": {
                    "signal_id": "GSI-500",
                    "artist": "Rollback Artist",
                    "track": "Rollback Song",
                    "album": "Rollback Album",
                    "tags": "personal",
                    "link": "https://open.spotify.com/track/rollback",
                    "slug": "rollback-artist-rollback-song",
                    "cover": "rollback.jpg",
                    "cover_file": "rollback.jpg",
                    "cover_url": "",
                    "accent": "#ff65ad",
                },
                "artwork": {"data_url": data_url},
                "sections": [{"title": "Charge", "content": "Note"}],
                "p53": {"enabled": False, "current": False, "note": ""},
                "catalogue": {
                    "artist_note": "",
                    "album_note": "",
                    "artist_artwork": {"data_url": data_url},
                },
            }
            with patch("tools.new_entry._update_catalogue_notes", side_effect=RuntimeError("boom")):
                with self.assertRaises(DraftMetadataError):
                    publish_draft(root, draft, build_site=False)

            artist_assets_dir = root / "artist-assets"
            remaining = list(artist_assets_dir.glob("*")) if artist_assets_dir.exists() else []
            self.assertEqual(remaining, [])

    def test_streaming_link_markup_does_not_double_escape_and_catalogue_record_omits_rim_gradient(self):
        item = {
            "slug": "test-song",
            "signal_id": "GSI-001",
            "artist": "A & B",
            "track": "Rock & Roll",
            "album": "Live & Loud",
            "tags": ["bite"],
            "cover_file": "test.jpg",
            "spotify_url": "https://open.spotify.com/track/1?a=1&b=2",
            "apple_url": "https://music.apple.com/tr/album/1?i=2&l=tr",
            "preview_url": "https://cdns-preview.dzcdn.net/stream/1.mp3?hdnea=exp=1&acl=/*",
            "accent": "#ff65ad",
            "has_entry": True,
        }
        markup = streaming_link_markup(item)
        self.assertNotIn("&amp;amp;", markup)
        self.assertIn('aria-pressed="false"', markup)
        self.assertIn('aria-hidden="true">▶</span>', markup)

        item["palette"] = {
            "primary": "#ff65ad",
            "rim_gradient": "radial-gradient(huge)",
        }
        record = catalogue_record(
            item,
            covers_dir=Path("."),
            cover_metadata={"exists": False, "valid": False, "width": None, "height": None, "bytes": None},
        )
        self.assertNotIn("rim_gradient", record["palette"])

    def test_p53_archive_sorts_newest_history_after_active_and_uses_singular_factor(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            p53_items = [
                {
                    "slug": "older-song",
                    "signal_id": "GSI-001",
                    "artist": "Artist 1",
                    "track": "Older Song",
                    "album": "Album 1",
                    "cover_file": "",
                    "accent": "#ff65ad",
                },
                {
                    "slug": "newer-song",
                    "signal_id": "GSI-002",
                    "artist": "Artist 2",
                    "track": "Newer Song",
                    "album": "Album 2",
                    "cover_file": "",
                    "accent": "#35c9e9",
                },
                {
                    "slug": "active-song",
                    "signal_id": "GSI-003",
                    "artist": "Artist 3",
                    "track": "Active Song",
                    "album": "Album 3",
                    "cover_file": "",
                    "accent": "#8c5de8",
                },
            ]
            out_dir = root / "site" / "p53"
            build_p53_archive(p53_items[:1], "older-song", output_dir=out_dir)
            single_html = (out_dir / "index.html").read_text(encoding="utf-8")
            self.assertIn("01 FACTOR", single_html)
            self.assertNotIn("01 FACTORS", single_html)

            build_p53_archive(p53_items, "active-song", output_dir=out_dir)
            multi_html = (out_dir / "index.html").read_text(encoding="utf-8")
            self.assertIn("03 FACTORS", multi_html)
            active_pos = multi_html.index("Active Song")
            older_pos = multi_html.index("Older Song")
            newer_pos = multi_html.index("Newer Song")
            self.assertLess(active_pos, older_pos)
            self.assertLess(older_pos, newer_pos)

    def test_build_album_pages_respects_output_dir_with_album_routes_and_singular_signal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out_dir = root / "custom_albums"
            items = [
                {
                    "slug": "metric-empty",
                    "html_file": "metric-empty.html",
                    "signal_id": "GSI-001",
                    "artist": "Metric",
                    "track": "Empty",
                    "album": "Live It Out",
                    "tags": "personal",
                    "cover_file": "",
                    "accent": "#ff65ad",
                    "has_entry": True,
                }
            ]
            routes = {("Metric", "Live It Out"): "albums/metric-live-it-out.html"}
            build_album_pages(items, {"Metric": items}, album_routes=routes, output_dir=out_dir)
            self.assertTrue((out_dir / "metric-live-it-out.html").is_file())
            html = (out_dir / "metric-live-it-out.html").read_text(encoding="utf-8")
            self.assertIn("01 SIGNAL", html)
            self.assertNotIn("01 SIGNALS", html)

    def test_sync_android_assets_downscales_covers_and_prunes_orphans(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow is required for Android asset sync test")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "site" / "data").mkdir(parents=True)
            (root / "covers").mkdir(parents=True)
            android_covers = root / "android" / "app" / "src" / "main" / "assets" / "covers"
            android_covers.mkdir(parents=True)
            (android_covers / "orphan.jpg").write_bytes(b"stale")

            Image.new("RGB", (1400, 1400), (200, 80, 120)).save(root / "covers" / "active.jpg", format="JPEG")
            catalog = {
                "signals": [
                    {
                        "slug": "active",
                        "signal_id": "GSI-001",
                        "cover": {"path": "covers/active.jpg"},
                    }
                ]
            }
            (root / "site" / "data" / "catalog.json").write_text(json.dumps(catalog), encoding="utf-8")
            (root / "config.json").write_text(
                json.dumps(
                    {
                        "p53_history": [{"slug": "active"}],
                        "filters": {"p53": {"description": "P53 description"}},
                        "p53_transmission_notes": {"active": "Note"},
                    }
                ),
                encoding="utf-8",
            )

            summary = sync_android_assets(root=root, max_edge=512)
            self.assertEqual(summary["copied_covers"], 1)
            self.assertEqual(summary["pruned_covers"], 1)
            self.assertFalse((android_covers / "orphan.jpg").exists())
            with Image.open(android_covers / "active.jpg") as synced_img:
                self.assertEqual(synced_img.size, (512, 512))
            p53_cfg = json.loads(
                (root / "android" / "app" / "src" / "main" / "assets" / "data" / "p53_config.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(p53_cfg["p53_current_slug"], "active")


if __name__ == "__main__":
    unittest.main()
