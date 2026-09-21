"""Tiny local intake server for Recommend a Signal.

It writes validated pending JSON files only. It never edits tracks.csv,
entries, or the generated site, and it deliberately has no mail credentials.
"""

import json
import mimetypes
import re
import sys
import csv
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from builder.entry_drafts import DraftMetadataError, validate_draft_payload
from gsi_text import slugify
from tools.new_entry import publish_draft


INBOX = ROOT / "submissions" / "inbox"
DRAFTS = ROOT / "submissions" / "drafts"
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


def _tracks() -> list[dict]:
    with (ROOT / "tracks.csv").open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def _frontmatter_and_body(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    _, separator, remainder = text.partition("\n---")
    if not separator:
        return {}, text
    frontmatter_text, _, body = remainder.partition("\n")
    values: dict = {}
    for line in frontmatter_text.splitlines():
        key, marker, raw = line.partition(":")
        if not marker:
            continue
        raw = raw.strip()
        try:
            values[key.strip()] = json.loads(raw)
        except json.JSONDecodeError:
            values[key.strip()] = raw.strip('"')
    return values, body


def _entry_sections(body: str) -> list[dict]:
    matches = list(re.finditer(r"^##\s+(.+?)\s*$", body, flags=re.MULTILINE))
    sections = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        sections.append({
            "title": match.group(1).strip(),
            "prompt": "Write what belongs here.",
            "content": body[match.end():end].strip(),
        })
    return sections


def local_entry_catalog() -> list[dict]:
    catalog = []
    for row in _tracks():
        slug = slugify(f"{row.get('artist', '')}-{row.get('track', '')}")
        if not slug or not (ROOT / "entries" / f"{slug}.md").is_file():
            continue
        catalog.append({
            "slug": slug,
            "artist": row.get("artist", ""),
            "track": row.get("track", ""),
            "album": row.get("album", ""),
        })
    return catalog


def local_entry_payload(slug: str) -> tuple[dict | None, str | None]:
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        return None, "invalid entry slug"
    entry_path = ROOT / "entries" / f"{slug}.md"
    if not entry_path.is_file():
        return None, "entry not found"
    frontmatter, body = _frontmatter_and_body(entry_path.read_text(encoding="utf-8"))
    row = next((item for item in _tracks() if slugify(f"{item.get('artist', '')}-{item.get('track', '')}") == slug), {})
    config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    p53_history = {item.get("slug"): item for item in config.get("p53_history", []) if isinstance(item, dict)}
    p53_enabled = slug in p53_history
    artist_name = str(frontmatter.get("artist") or row.get("artist") or "").strip()
    album_name = str(frontmatter.get("album") or row.get("album") or "").strip()
    artist_notes = config.get("artist_notes", {})
    album_notes = config.get("album_notes", {})
    return {
        "schema": 1,
        "record": {
            "artist": str(frontmatter.get("artist") or row.get("artist") or "").strip(),
            "track": str(frontmatter.get("track") or row.get("track") or "").strip(),
            "album": str(frontmatter.get("album") or row.get("album") or "").strip(),
            "tags": str(row.get("tags") or "").strip(),
            "link": str(row.get("apple_url") or row.get("spotify_url") or "").strip(),
            "slug": slug,
            "cover": str(frontmatter.get("cover") or row.get("cover_file") or "").split("/")[-1],
            "accent": str(frontmatter.get("accent") or row.get("accent") or "").strip(),
        },
        "sections": _entry_sections(body),
        "p53": {
            "enabled": p53_enabled,
            "current": config.get("p53_current_slug") == slug,
            "note": str(config.get("p53_transmission_notes", {}).get(slug) or "").strip(),
        },
        "catalogue": {
            "artist_note": str(artist_notes.get(artist_name) or "").strip(),
            "album_note": str(album_notes.get(artist_name, {}).get(album_name) or "").strip(),
        },
    }, None


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
        path = urlparse(self.path).path
        if path not in {"/api/recommendations", "/api/entry-drafts", "/api/local-entry-drafts", "/api/local-entry-publish"}:
            return self._json(404, {"error": "not found"})
        try:
            size = min(int(self.headers.get("Content-Length", "0")), 100_000)
            payload = json.loads(self.rfile.read(size).decode("utf-8"))
        except (ValueError, json.JSONDecodeError):
            return self._json(400, {"error": "invalid JSON"})
        if path in {"/api/entry-drafts", "/api/local-entry-drafts", "/api/local-entry-publish"}:
            clean, error = validate_draft_payload(payload)
            if error or clean is None:
                return self._json(400, {"error": error or "invalid draft"})
            if path == "/api/local-entry-publish":
                edit_of = str(payload.get("editOf") or "").strip()
                if edit_of and not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", edit_of):
                    return self._json(400, {"error": "invalid edit target"})
                try:
                    result = publish_draft(ROOT, {**clean, "editOf": edit_of})
                except (DraftMetadataError, OSError, ValueError) as publish_error:
                    return self._json(409, {"error": str(publish_error)})
                return self._json(201, {"status": "built", **result})
            if path == "/api/local-entry-drafts":
                edit_of = str(payload.get("editOf") or "").strip()
                if edit_of and not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", edit_of):
                    return self._json(400, {"error": "invalid edit target"})
                clean["editOf"] = edit_of
            DRAFTS.mkdir(parents=True, exist_ok=True)
            now = datetime.now(timezone.utc)
            slug = slugify(f"{clean['record']['artist']}-{clean['record']['track']}") or "new-entry"
            prefix = "edit-" if path == "/api/local-entry-drafts" else ""
            filename = f"{now.strftime('%Y%m%d-%H%M%S-%f')}-{prefix}{slug}.json"
            clean["receivedAt"] = now.isoformat()
            (DRAFTS / filename).write_text(json.dumps(clean, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return self._json(201, {"status": "saved", "filename": filename})
        clean, error = validate(payload)
        if error:
            return self._json(400, {"error": error})
        INBOX.mkdir(parents=True, exist_ok=True)
        filename = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f") + ".json"
        (INBOX / filename).write_text(json.dumps(clean, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self._json(201, {"status": "received"})

    def do_GET(self) -> None:  # noqa: N802 - serve the generated room beside the intake API
        """Serve the generated site so local review needs one process."""
        path = urlparse(self.path).path
        if path == "/api/local-entry-catalog":
            return self._json(200, {"entries": local_entry_catalog()})
        if path == "/api/local-entry":
            return self._json(400, {"error": "a slug is required"})
        if path.startswith("/api/local-entry/"):
            payload, error = local_entry_payload(path.removeprefix("/api/local-entry/"))
            return self._json(404 if error else 200, {"error": error} if error else payload)
        if path.startswith("/__local/editor/"):
            relative_private = path.removeprefix("/__local/editor/")
            candidate = (ROOT / "tools" / "editor" / "private" / relative_private).resolve()
            try:
                candidate.relative_to((ROOT / "tools" / "editor" / "private").resolve())
            except ValueError:
                return self._json(404, {"error": "not found"})
            if not candidate.is_file():
                return self._json(404, {"error": "not found"})
            payload = candidate.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", mimetypes.guess_type(candidate.name)[0] or "application/octet-stream")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        relative = path.lstrip("/") or "index.html"
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
