import unittest

from tools.submission_server import (
    _entry_sections,
    bearer_token_matches,
    is_loopback_host,
    private_path,
)


class SubmissionServerBoundaryTests(unittest.TestCase):
    def test_loopback_detection_is_strict(self):
        self.assertTrue(is_loopback_host("127.0.0.1"))
        self.assertTrue(is_loopback_host("[::1]"))
        self.assertFalse(is_loopback_host("0.0.0.0"))
        self.assertFalse(is_loopback_host("192.168.1.20"))

    def test_only_private_editor_paths_are_guarded(self):
        self.assertTrue(private_path("/__local/editor/edit-entry.html"))
        self.assertTrue(private_path("/api/local-entry-publish"))
        self.assertTrue(private_path("/api/entry-drafts"))
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

    def test_cross_origin_cookie_post_is_rejected(self):
        from unittest.mock import MagicMock
        from tools.submission_server import SubmissionHandler

        server = MagicMock()
        server.gsi_auth_token = "secret123"
        server.server_address = ("0.0.0.0", 8021)

        handler = SubmissionHandler.__new__(SubmissionHandler)
        handler.server = server
        handler.path = "/api/local-entry-publish"
        sent = {}
        handler._json = lambda status, body: sent.update({"status": status, "body": body})

        handler.headers = {
            "Cookie": "gsi_auth_token=secret123",
            "Host": "192.168.1.20:8021",
            "Origin": "https://evil.example",
        }
        self.assertFalse(handler._guard_private_path("/api/local-entry-publish", is_post=True))
        self.assertEqual(sent.get("status"), 403)

        sent.clear()
        handler.headers = {
            "Cookie": "gsi_auth_token=secret123",
            "Host": "192.168.1.20:8021",
            "Origin": "http://192.168.1.20:8021",
        }
        self.assertTrue(handler._guard_private_path("/api/local-entry-publish", is_post=True))

    def test_entry_sections_strip_html_comments(self):
        body = "## Charge\n<!--Write what belongs here.-->\nReal note.\n\n## Sonic Attraction\n<!--Prompt-->\nSecond note.\n"
        sections = _entry_sections(body)
        self.assertEqual(
            [(s["title"], s["content"]) for s in sections],
            [("Charge", "Real note."), ("Sonic Attraction", "Second note.")],
        )

    def test_editor_cookie_has_httponly_and_editor_config_serves_live_sections(self):
        import io
        import json
        from unittest.mock import MagicMock
        from tools.submission_server import SubmissionHandler

        server = MagicMock()
        server.gsi_auth_token = "secret123"
        server.server_address = ("0.0.0.0", 8021)

        handler = SubmissionHandler.__new__(SubmissionHandler)
        handler.server = server
        handler.headers = {"Authorization": "Bearer secret123"}
        handler.path = "/__local/editor/edit-entry.html"
        sent_headers = []
        handler.send_response = lambda code: None
        handler.send_header = lambda k, v: sent_headers.append((k, v))
        handler.end_headers = lambda: None
        handler.wfile = io.BytesIO()
        handler.do_GET()
        cookie_headers = [v for k, v in sent_headers if k == "Set-Cookie"]
        self.assertTrue(cookie_headers)
        self.assertIn("HttpOnly", cookie_headers[0])

        handler2 = SubmissionHandler.__new__(SubmissionHandler)
        handler2.server = server
        handler2.headers = {"Authorization": "Bearer secret123"}
        handler2.path = "/__local/editor/editor-config.json"
        captured = {}
        handler2._json = lambda status, body: captured.update({"status": status, "body": body})
        handler2.do_GET()
        self.assertEqual(captured.get("status"), 200)
        self.assertIn("Sonic Attraction", captured["body"]["sections"])

    def test_local_entry_payload_normalizes_backslash_cover_paths(self):
        from unittest.mock import patch
        from tools.submission_server import local_entry_payload

        fake_row = {
            "artist": "Example Artist",
            "track": "Example Track",
            "album": "Example Album",
            "signal_id": "GSI-999",
            "tags": "personal",
            "cover_file": "..\\..\\secret\\outside.jpg",
        }
        with patch("tools.submission_server._tracks", return_value=[fake_row]):
            payload, error = local_entry_payload("example-artist-example-track")
        self.assertIsNone(error)
        self.assertEqual(payload["record"]["cover_file"], "outside.jpg")


if __name__ == "__main__":
    unittest.main()
