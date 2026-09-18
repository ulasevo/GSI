import unittest

from gsi_links import provider_link_audit


class ProviderLinkAuditTests(unittest.TestCase):
    def test_audit_deduplicates_p53_repeats_and_counts_fallbacks(self):
        audit = provider_link_audit([
            {
                "artist": "Metric",
                "track": "Empty",
                "album": "Live It Out",
                "spotify_url": "https://open.spotify.com/track/example",
                "apple_url": "",
            },
            {
                "artist": "Metric",
                "track": "Empty",
                "album": "Live It Out",
                "spotify_url": "https://open.spotify.com/track/example",
                "apple_url": "",
            },
            {
                "artist": "Beach House",
                "track": "New Year",
                "album": "Bloom",
                "spotify_url": "",
                "apple_url": "https://music.apple.com/us/song/new-year/example",
            },
        ])

        self.assertEqual(audit["signals_inspected"], 2)
        self.assertEqual(audit["counts"]["spotify"], {"canonical": 1, "search": 1})
        self.assertEqual(audit["counts"]["apple"], {"canonical": 1, "search": 1})
        self.assertEqual(len(audit["fallbacks"]), 2)


if __name__ == "__main__":
    unittest.main()
