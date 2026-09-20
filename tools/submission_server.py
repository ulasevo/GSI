"""Tiny local intake server for Recommend a Signal.

It writes validated pending JSON files only. It never edits tracks.csv,
entries, or the generated site, and it deliberately has no mail credentials.
"""

import json
import mimetypes
import sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
INBOX = ROOT / "submissions" / "inbox"
SITE = ROOT / "site"

SUPPORTED_PROVIDERS = {
    "music.apple.com", "itunes.apple.com", "open.spotify.com", "spotify.link",
    "youtube.com", "music.youtube.com", "youtu.be", "soundcloud.com",
    "bandcamp.com", "deezer.com", "tidal.com",
}


def validate(payload: dict) -> tuple[dict | None, str | None]:
    """Keep the intake small, link-oriented, and safe to inspect later."""
    link = str(payload.get("link") or "").strip()
    note = str(payload.get("note") or "").strip()
    name = str(payload.get("name") or "").strip()
    parsed = urlparse(link)
    host = (parsed.hostname or "").lower().removeprefix("www.")
    if parsed.scheme != "https" or not host:
        return None, "Use an HTTPS music link."
    if host not in SUPPORTED_PROVIDERS and not any(host.endswith(f".{domain}") for domain in SUPPORTED_PROVIDERS):
        return None, "Use a link from a supported music provider."
    if not note or len(note) > 4000:
        return None, "A note between 1 and 4000 characters is required."
    if len(name) > 80:
        return None, "The optional signature is too long."
    return {"link": link, "note": note, "name": name, "receivedAt": datetime.now(timezone.utc).isoformat()}, None


class SubmissionHandler(BaseHTTPRequestHandler):
    def _json(self, status: int, body: dict) -> None:
        encoded = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(encoded)

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler hook
        if urlparse(self.path).path != "/api/recommendations":
            return self._json(404, {"error": "not found"})
        try:
            size = min(int(self.headers.get("Content-Length", "0")), 100_000)
            payload = json.loads(self.rfile.read(size).decode("utf-8"))
        except (ValueError, json.JSONDecodeError):
            return self._json(400, {"error": "invalid JSON"})
        clean, error = validate(payload)
        if error:
            return self._json(400, {"error": error})
        INBOX.mkdir(parents=True, exist_ok=True)
        filename = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f") + ".json"
        (INBOX / filename).write_text(json.dumps(clean, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self._json(201, {"status": "received"})

    def do_GET(self) -> None:  # noqa: N802 - serve the generated room beside the intake API
        """Serve the generated site so local review needs one process."""
        relative = urlparse(self.path).path.lstrip("/") or "index.html"
        candidate = (SITE / relative).resolve()
        try:
            candidate.relative_to(SITE.resolve())
        except ValueError:
            return self._json(404, {"error": "not found"})
        if candidate.is_dir():
            candidate = candidate / "index.html"
        if not candidate.is_file():
            return self._json(404, {"error": "not found"})
        payload = candidate.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(candidate.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        return


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8021
    server = ThreadingHTTPServer(("127.0.0.1", port), SubmissionHandler)
    print(f"GSI recommendation intake listening on http://127.0.0.1:{port}")
    server.serve_forever()
