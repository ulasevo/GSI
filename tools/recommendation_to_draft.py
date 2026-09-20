"""Turn one reviewed recommendation into an isolated Markdown draft.

This is the bridge between the public intake and the private Entry Loader. It
never writes ``entries/`` or ``tracks.csv``; the resulting draft stays under
``submissions/drafts/`` until the author deliberately moves it into GSI.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
INBOX = ROOT / "submissions" / "inbox"
DRAFTS = ROOT / "submissions" / "drafts"
sys.path.insert(0, str(ROOT))

from builder.entry_drafts import DraftMetadataError, draft_record, metadata_from_link, render_empty_entry
from gsi_data import load_config


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", nargs="?", help="Pending JSON filename or path")
    parser.add_argument("--artist", default="", help="Manual artist override for unsupported links")
    parser.add_argument("--track", default="", help="Manual track override for unsupported links")
    parser.add_argument("--album", default="", help="Manual album override for unsupported links")
    parser.add_argument("--tags", default="", help="Optional comma-separated GSI tags")
    parser.add_argument("--write-draft", action="store_true", help="Write the isolated draft under submissions/drafts/")
    return parser


def _path(value: str) -> Path:
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = INBOX / candidate
    candidate = candidate.resolve()
    candidate.relative_to(INBOX.resolve())
    return candidate


def _with_recommendation(markdown: str, note: str, link: str, name: str) -> str:
    """Place the visitor's note in the existing Comment room, not a new label."""
    author = f" — {name}" if name else ""
    addition = f"{note.strip()}\n\nRecommended from{author}: <{link}>"
    marker = "## Comment\n\n"
    if marker in markdown:
        return markdown.replace(marker, marker + addition + "\n\n", 1)
    return markdown.rstrip() + f"\n\n## Comment\n\n{addition}\n"


def main() -> int:
    args = _parser().parse_args()
    if not args.file:
        files = sorted(INBOX.glob("*.json"))
        if not files:
            print("No pending signals in submissions/inbox.")
            return 0
        print("Pending signals:")
        for path in files:
            payload = json.loads(path.read_text(encoding="utf-8"))
            print(f" - {path.name}: {payload.get('link', '')} / {payload.get('name') or 'unnamed'}")
        return 0
    try:
        path = _path(args.file)
        payload = json.loads(path.read_text(encoding="utf-8"))
        link = str(payload.get("link") or "").strip()
        note = str(payload.get("note") or "").strip()
        if not link or not note:
            raise DraftMetadataError("The pending signal needs both a link and a note.")
        try:
            metadata = metadata_from_link(
                link,
                artist=args.artist,
                track=args.track,
                album=args.album,
            )
        except DraftMetadataError:
            parsed = urlsplit(link)
            if parsed.scheme != "https" or not parsed.hostname or not all((args.artist, args.track, args.album)):
                raise
            metadata = {
                "provider": "external",
                "artist": args.artist.strip(),
                "track": args.track.strip(),
                "album": args.album.strip(),
                "apple_url": "",
                "spotify_url": "",
                "cover_url": "",
            }
        record = draft_record(metadata, tags=args.tags)
        sections = load_config(ROOT / "config.json").get("sections", [])
        markdown = _with_recommendation(
            render_empty_entry(record, sections),
            note,
            link,
            str(payload.get("name") or "").strip(),
        )
    except (OSError, ValueError, KeyError, DraftMetadataError) as error:
        print(f"Draft not created: {error}")
        return 2

    print(f"Artist: {record['artist']}\nTrack:  {record['track']}\nAlbum:  {record['album']}\nSlug:   {record['slug']}")
    if not args.write_draft:
        print("Mode:   preview only")
        print("Add --write-draft after reviewing this recommendation.")
        return 0
    DRAFTS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    destination = DRAFTS / f"{stamp}-{record['slug']}.md"
    destination.write_text(markdown, encoding="utf-8")
    print(f"Wrote isolated draft: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
