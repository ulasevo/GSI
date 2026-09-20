"""Focused checks for the artwork roles and safe recommendation intake."""

import tempfile
import unittest
from pathlib import Path

from PIL import Image

from gsi_assets import artwork_palette
from tools.submission_server import validate


class ArtworkAndRecommendationTests(unittest.TestCase):
    def test_artwork_palette_is_deterministic_and_named(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cover.png"
            Image.new("RGB", (12, 12), (210, 40, 120)).save(path)
            first = artwork_palette(path)
            second = artwork_palette(path)
        self.assertEqual(first, second)
        self.assertEqual(
            set(first),
            {
                "primary", "secondary", "field", "field_soft", "field_ink",
                "edge_top", "edge_right", "edge_bottom", "edge_left",
                "rim_gradient",
                "surface", "soft", "ink", "glow",
                "light_surface", "light_surface_2", "dark_surface", "light_ink", "dark_ink",
                "control", "control_hover", "control_ink", "edge", "focus",
            },
        )

    def test_recommendation_validation_requires_a_supported_provider(self):
        clean, error = validate({"link": "https://open.spotify.com/track/abc", "note": "A signal."})
        self.assertIsNone(error)
        self.assertEqual(clean["name"], "")
        other, error = validate({"link": "https://example.com/song", "note": "A signal."})
        self.assertIsNone(other)
        self.assertIn("supported music provider", error)
        self.assertIsNone(validate({"link": "http://music.apple.com/song", "note": "A signal."})[0])


if __name__ == "__main__":
    unittest.main()
