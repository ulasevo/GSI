import unittest

from tools.submission_server import bearer_token_matches, is_loopback_host, private_path


class SubmissionServerBoundaryTests(unittest.TestCase):
    def test_loopback_detection_is_strict(self):
        self.assertTrue(is_loopback_host("127.0.0.1"))
        self.assertTrue(is_loopback_host("[::1]"))
        self.assertFalse(is_loopback_host("0.0.0.0"))
        self.assertFalse(is_loopback_host("192.168.1.20"))

    def test_only_private_editor_paths_are_guarded(self):
        self.assertTrue(private_path("/__local/editor/edit-entry.html"))
        self.assertTrue(private_path("/api/local-entry-publish"))
        self.assertFalse(private_path("/index.html"))
        self.assertFalse(private_path("/api/recommendations"))

    def test_bearer_tokens_use_exact_constant_time_comparison(self):
        self.assertTrue(bearer_token_matches("Bearer secret-token", "secret-token"))
        self.assertFalse(bearer_token_matches("Bearer secret-token ", "different"))
        self.assertFalse(bearer_token_matches("Basic secret-token", "secret-token"))
        self.assertFalse(bearer_token_matches("Bearer secret-token", ""))


if __name__ == "__main__":
    unittest.main()
