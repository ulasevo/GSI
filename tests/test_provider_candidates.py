import unittest

from builder.provider_candidates import collect_provider_candidates


class ProviderCandidateTests(unittest.TestCase):
    def test_report_ranks_candidates_without_writing_source_data(self):
        calls = []

        def fake_fetcher(url, *, headers, timeout):
            calls.append((url, headers, timeout))
            return {
                "results": [
                    {
                        "trackViewUrl": "https://music.apple.com/us/song/empty/1",
                        "artistName": "Metric",
                        "trackName": "Empty",
                        "collectionName": "Live It Out",
                    },
                    {
                        "trackViewUrl": "https://music.apple.com/us/song/other/2",
                        "artistName": "Other",
                        "trackName": "Empty",
                        "collectionName": "Other",
                    },
                ]
            }

        report = collect_provider_candidates(
            [
                {"artist": "Metric", "track": "Empty", "album": "Live It Out"},
                {"artist": "Metric", "track": "Empty", "album": "Live It Out", "slug": "duplicate"},
            ],
            providers=("apple",),
            fetcher=fake_fetcher,
        )

        self.assertEqual(len(report["signals"]), 1)
        result = report["signals"][0]["providers"]["apple"]
        self.assertEqual(result["status"], "strong-candidate")
        self.assertEqual(result["url"], "https://music.apple.com/us/song/empty/1")
        self.assertEqual(len(calls), 1)

    def test_spotify_without_token_is_explicitly_deferred(self):
        report = collect_provider_candidates(
            [{"artist": "Metric", "track": "Empty", "album": "Live It Out"}],
            providers=("spotify",),
        )
        self.assertEqual(report["signals"][0]["providers"]["spotify"]["status"], "token-required")


if __name__ == "__main__":
    unittest.main()
