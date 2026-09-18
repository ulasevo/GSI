import json
import unittest
from unittest.mock import Mock

from builder.entry_drafts import (
    DraftMetadataError,
    apple_track_id,
    draft_record,
    metadata_from_link,
    metadata_from_apple_link,
    provider_for_url,
    render_empty_entry,
)


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


if __name__ == "__main__":
    unittest.main()
