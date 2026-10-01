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

    def test_handler_authorizes_query_param_and_cookie(self):
        from unittest.mock import MagicMock
        from tools.submission_server import SubmissionHandler

        server = MagicMock()
        server.gsi_auth_token = "secret123"
        server.server_address = ("0.0.0.0", 8021)

        handler = SubmissionHandler.__new__(SubmissionHandler)
        handler.server = server
        handler.headers = {}

        handler.path = "/__local/editor/edit-entry.html"
        self.assertFalse(handler._private_authorized())

        handler.path = "/__local/editor/edit-entry.html?token=secret123"
        self.assertTrue(handler._private_authorized())

        handler.path = "/__local/editor/edit-entry.html?token=wrong"
        self.assertFalse(handler._private_authorized())

        handler.path = "/__local/editor/edit-entry.html"
        handler.headers = {"Cookie": "gsi_auth_token=secret123; other=value"}
        self.assertTrue(handler._private_authorized())

        handler.headers = {"Authorization": "Bearer secret123"}
        self.assertTrue(handler._private_authorized())


if __name__ == "__main__":
    unittest.main()
