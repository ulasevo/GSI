"""Create a review-ready GSI entry from an Apple Music or Spotify link.

The default mode is preview-only. ``--write`` is the explicit point at which
the Markdown entry and catalogue row are created. This keeps a pasted link
from silently changing the site while metadata is still being reviewed.
"""

import argparse
import csv
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from builder.entry_drafts import (
    DraftMetadataError,
    draft_record,
    metadata_from_link,
    p53_record_from_draft,
    render_empty_entry,
    slugify,
)
try:
    from gsi_data import load_config, read_tracks
except ModuleNotFoundError:
    # Compatibility for the pre-migration main checkout.
    def load_config(config_file: Path) -> dict:
        return json.loads(config_file.read_text(encoding="utf-8"))

    def read_tracks(tracks_file: Path) -> list[dict]:
        with tracks_file.open("r", encoding="utf-8", newline="") as file:
            return list(csv.DictReader(file))


TRACK_COLUMNS = [
    "order",
    "tags",
    "artist",
    "track",
    "album",
    "accent",
    "cover_file",
    "cover_url",
    "spotify_url",
    "apple_url",
]


def _root() -> Path:
    return ROOT


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("link", help="Apple Music or Spotify song URL")
    parser.add_argument("--artist", default="", help="Override the resolved artist name")
    parser.add_argument("--track", default="", help="Override the resolved track name")
    parser.add_argument("--album", default="", help="Override the resolved album name")
    parser.add_argument("--tags", default="", help="Comma-separated GSI filter tags")
    parser.add_argument("--accent", default="", help="Optional six-digit accent override")
    parser.add_argument(
        "--section",
        action="append",
        default=[],
        help="Add one extra review heading after the configured sections",
    )
    parser.add_argument("--p53", action="store_true", help="Also add an explicit P53 history record")
    parser.add_argument("--write", action="store_true", help="Write the draft and catalogue data")
    parser.add_argument("--timeout", type=int, default=15, help="Provider lookup timeout in seconds")
    return parser.parse_args()


def _ensure_unique_sections(config_sections: list[str], extras: list[str]) -> list[str]:
    sections = list(config_sections)
    existing = {section.casefold() for section in sections}
    for section in extras:
        clean = section.strip()
        if clean and clean.casefold() not in existing:
            sections.append(clean)
            existing.add(clean.casefold())
    return sections


def _assert_new_slug(root: Path, slug: str) -> None:
    if (root / "entries" / f"{slug}.md").exists():
        raise DraftMetadataError(f"An entry already exists for this artist/track: {slug}.md")
    for row in read_tracks(root / "tracks.csv"):
        if (row.get("artist", "") + "-" + row.get("track", "")).strip().casefold() == "":
            continue
        if slugify(f"{row.get('artist', '')}-{row.get('track', '')}") == slug:
            raise DraftMetadataError(f"tracks.csv already contains this artist/track: {slug}")


def _append_track(root: Path, record: dict) -> None:
    with (root / "tracks.csv").open("a", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=TRACK_COLUMNS, lineterminator="\n")
        writer.writerow({column: record.get(column, "") for column in TRACK_COLUMNS})


def _append_p53(root: Path, record: dict) -> None:
    config_path = root / "config.json"
    config = load_config(config_path)
    history = config.setdefault("p53_history", [])
    if any(item.get("slug") == record["slug"] for item in history if isinstance(item, dict)):
        raise DraftMetadataError(f"config.json already contains this P53 slug: {record['slug']}")
    history.append(p53_record_from_draft(record))
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    args = _parse_args()
    root = _root()
    config = load_config(root / "config.json")
    try:
        metadata = metadata_from_link(
            args.link,
            artist=args.artist,
            track=args.track,
            album=args.album,
            timeout=args.timeout,
        )
        record = draft_record(metadata, tags=args.tags, accent=args.accent)
        sections = _ensure_unique_sections(config.get("sections", []), args.section)
        _assert_new_slug(root, record["slug"])
    except DraftMetadataError as error:
        print(f"Draft not created: {error}")
        return 2

    print(f"Artist: {record['artist']}")
    print(f"Track:  {record['track']}")
    print(f"Album:  {record['album']}")
    print(f"Slug:   {record['slug']}")
    print(f"Sections: {', '.join(sections)}")
    print(f"Entry:  entries/{record['slug']}.md")
    print(f"Cover:  covers/{record['cover_file']}")
    print("Mode:   write" if args.write else "Mode:   preview only")

    if not args.write:
        return 0

    entry_path = root / "entries" / f"{record['slug']}.md"
    entry_path.write_text(render_empty_entry(record, sections), encoding="utf-8")
    _append_track(root, record)
    if args.p53:
        _append_p53(root, record)
    print(f"Created source entry: {entry_path}")
    print("Next: review the blank headings, then run the normal build and source validator.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
