import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock, patch

from builder.entry_drafts import (
    DraftMetadataError,
    apple_track_id,
    draft_record,
    metadata_from_link,
    metadata_from_apple_link,
    provider_for_url,
    render_authored_entry,
    render_empty_entry,
    validate_draft_payload,
)
from tools.new_entry import publish_draft


class _Response:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.payload


class EntryDraftTests(unittest.TestCase):
    def test_provider_and_track_id(self):
        url = "https://music.apple.com/tr/album/foo/123?i=456&ls"
        self.assertEqual(provider_for_url(url), "apple")
        self.assertEqual(apple_track_id(url), "456")

    def test_invalid_apple_link_requires_track_id(self):
        with self.assertRaises(DraftMetadataError):
            apple_track_id("https://music.apple.com/tr/album/foo/123")

    def test_apple_lookup_maps_song_and_artwork(self):
        payload = {
            "resultCount": 1,
            "results": [{
                "kind": "song",
                "artistName": "Example Artist",
                "trackName": "Example Track",
                "collectionName": "Example Album",
                "artworkUrl100": "https://example.test/100x100bb.jpg",
            }],
        }
        opener = Mock(return_value=_Response(payload))
        metadata = metadata_from_apple_link(
            "https://music.apple.com/tr/album/foo/123?i=456&ls",
            opener=opener,
        )
        self.assertEqual(metadata["artist"], "Example Artist")
        self.assertEqual(metadata["track"], "Example Track")
        self.assertTrue(metadata["cover_url"].endswith("600x600bb.jpg"))
        opener.assert_called_once()

    def test_spotify_link_accepts_explicit_names_without_api_lookup(self):
        metadata = metadata_from_link(
            "https://open.spotify.com/track/abc123",
            artist="Artist",
            track="Track",
            album="Album",
        )
        self.assertEqual(metadata["spotify_url"], "https://open.spotify.com/track/abc123")

    def test_apple_link_accepts_complete_manual_metadata_offline(self):
        metadata = metadata_from_link(
            "https://music.apple.com/tr/album/foo/123?i=456",
            artist="Artist",
            track="Track",
            album="Album",
        )
        self.assertEqual(metadata["apple_url"], "https://music.apple.com/tr/album/foo/123?i=456")
        self.assertEqual(metadata["artist"], "Artist")

    def test_draft_record_and_all_sections_render(self):
        record = draft_record({
            "artist": "Artist",
            "track": "Track",
            "album": "Album",
            "cover_url": "",
            "spotify_url": "",
            "apple_url": "https://music.apple.com/tr/album/a/1?i=2",
        }, tags="dreamy")
        markdown = render_empty_entry(record, ["Charge", "Custom Note"])
        self.assertEqual(record["slug"], "artist-track")
        self.assertIn("## Charge", markdown)
        self.assertIn("## Custom Note", markdown)
        self.assertIn("What state does this song trigger?", markdown)

    def test_browser_draft_contract_preserves_p53_note(self):
        clean, error = validate_draft_payload({
            "schema": 1,
            "record": {
                "artist": "Artist",
                "track": "Track",
                "album": "Album",
                "link": "https://open.spotify.com/track/abc123",
                "tags": "p53",
                "accent": "#112233",
                "cover": "artist-track.jpg",
                "cover_url": "https://cdn.example.test/600x600.jpg",
            },
            "sections": [{"title": "Charge", "prompt": "Prompt", "content": "A memory."}],
            "p53": {"enabled": True, "current": True, "note": "Transmission note."},
            "catalogue": {"artist_note": "Artist context.", "album_note": "Album context."},
        })
        self.assertIsNone(error)
        self.assertEqual(clean["p53"]["note"], "Transmission note.")
        self.assertEqual(clean["catalogue"]["album_note"], "Album context.")
        markdown = render_authored_entry({**clean["record"], "cover_file": "artist-track.jpg"}, clean["sections"])
        self.assertIn("A memory.", markdown)

    def test_current_p53_requires_enabled_flag(self):
        clean, error = validate_draft_payload({
            "record": {"artist": "Artist", "track": "Track", "album": "Album", "link": "https://open.spotify.com/track/abc123"},
            "sections": [{"title": "Charge", "content": "A memory."}],
            "p53": {"enabled": False, "current": True},
        })
        self.assertIsNone(clean)
        self.assertIn("enabled", error)

    def test_local_publish_restores_sources_when_build_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "entries").mkdir()
            (root / "covers").mkdir()
            original_config = '{"sections": ["Charge"]}\n'
            original_tracks = "order,tags,artist,track,album,accent,cover_file,cover_url,spotify_url,apple_url\n"
            (root / "config.json").write_text(original_config, encoding="utf-8")
            (root / "tracks.csv").write_text(original_tracks, encoding="utf-8")
            payload = {
                "schema": 1,
                "record": {
                    "artist": "Example Artist",
                    "track": "New Signal",
                    "album": "Example Album",
                    "link": "https://open.spotify.com/track/example",
                    "tags": "",
                    "accent": "",
                    "cover": "example-artist-new-signal.jpg",
                    "cover_url": "https://cdn.example.test/600x600.jpg",
                },
                "sections": [{"title": "Charge", "content": "A note."}],
                "p53": {"enabled": False, "current": False, "note": ""},
                "catalogue": {"artist_note": "Artist note.", "album_note": "Album note."},
            }

            def fake_download(_url, path):
                path.write_bytes(b"new cover")
                return True

            failed_build = SimpleNamespace(returncode=1, stdout="build failed", stderr="")
            recovery_build = SimpleNamespace(returncode=0, stdout="restored", stderr="")
            with patch("tools.new_entry.download_cover", side_effect=fake_download), \
                patch("tools.new_entry.dominant_color", return_value="#112233"), \
                patch("tools.new_entry.subprocess.run", side_effect=[failed_build, recovery_build]):
                with self.assertRaises(DraftMetadataError) as raised:
                    publish_draft(root, payload)

            self.assertIn("Source files were restored", str(raised.exception))
            self.assertEqual((root / "config.json").read_text(encoding="utf-8"), original_config)
            self.assertEqual((root / "tracks.csv").read_text(encoding="utf-8"), original_tracks)
            self.assertFalse((root / "entries" / "example-artist-new-signal.md").exists())
            self.assertFalse((root / "covers" / "example-artist-new-signal.jpg").exists())


if __name__ == "__main__":
    unittest.main()
