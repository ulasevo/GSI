"""Create a review-ready GSI entry from an Apple Music or Spotify link.

The default mode is preview-only. ``--write`` is the explicit point at which
the Markdown entry and catalogue row are created. This keeps a pasted link
from silently changing the site while metadata is still being reviewed.
"""

import argparse
import csv
import json
from pathlib import Path
import subprocess
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
    render_authored_entry,
    render_empty_entry,
    slugify,
    validate_draft_payload,
)
from builder.source_pipeline import download_cover
from gsi_assets import copy_site_editor, dominant_color
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


def _install_browser_editor(root: Path) -> None:
    """Copy the safe browser authoring surface into the generated site."""
    source_dir = root / "tools" / "editor"
    destination = root / "site" / "tools"
    config = load_config(root / "config.json")
    try:
        copy_site_editor(
            source_dir,
            destination,
            config.get("sections", []),
            config.get("section_info", {}),
        )
    except FileNotFoundError as error:
        raise DraftMetadataError(str(error)) from error


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("link", nargs="?", help="Apple Music or Spotify song URL")
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
    parser.add_argument(
        "--sections",
        nargs="+",
        default=[],
        help="Add headings as one comma-separated or space-separated group",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Walk through link, metadata, headings, and write confirmation",
    )
    parser.add_argument(
        "--install-editor",
        action="store_true",
        help="Install the browser authoring editor into site/tools/",
    )
    parser.add_argument(
        "--from-draft",
        type=Path,
        help="Load a browser Entry Loader JSON draft without changing sources until --write is supplied",
    )
    parser.add_argument("--p53", action="store_true", help="Also add an explicit P53 history record")
    parser.add_argument("--p53-note", default="", help="Transmission note to store for a P53 record")
    parser.add_argument("--p53-current", action="store_true", help="Make this P53 record the current transmission")
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


def _flatten_sections(repeated: list[str], grouped: list[str]) -> list[str]:
    """Accept both repeated flags and a forgiving comma/space list."""
    values: list[str] = []
    for value in [*repeated, *grouped]:
        values.extend(piece.strip() for piece in value.split(",") if piece.strip())
    return values


def _interactive_namespace(args: argparse.Namespace, config: dict) -> argparse.Namespace:
    """Collect authoring choices without hiding the final write decision."""
    print("GSI entry draft")
    print("Paste the raw provider URL, not a Markdown link.\n")
    args.link = input("Apple Music or Spotify link: ").strip()
    args.artist = input("Artist (leave blank to resolve): ").strip()
    args.track = input("Track (leave blank to resolve): ").strip()
    args.album = input("Album (leave blank to resolve): ").strip()
    args.tags = input("Filters/tags, comma separated (optional): ").strip()

    configured = [str(section).strip() for section in config.get("sections", []) if str(section).strip()]
    print("\nConfigured review headings:")
    for index, section in enumerate(configured, start=1):
        print(f"  {index}. {section}")
    selected = input("Use all headings? [Y/n]: ").strip().casefold()
    if selected in {"n", "no"}:
        choices = input("Heading numbers, comma separated: ").strip()
        indexes = {int(value.strip()) for value in choices.split(",") if value.strip().isdigit()}
        args._selected_sections = [
            configured[index - 1] for index in sorted(indexes) if 1 <= index <= len(configured)
        ]
    else:
        args._selected_sections = configured
    custom = input("Additional headings, comma separated (optional): ").strip()
    args.section = [value.strip() for value in custom.split(",") if value.strip()]
    args.p53 = input("Add to P53 history? [y/N]: ").strip().casefold() in {"y", "yes"}
    args.write = input("Write the source entry now? [y/N]: ").strip().casefold() in {"y", "yes"}
    return args


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


def _replace_track(root: Path, record: dict) -> None:
    """Update one existing catalogue row after an explicitly reviewed edit."""
    rows = read_tracks(root / "tracks.csv")
    target = next((row for row in rows if slugify(f"{row.get('artist', '')}-{row.get('track', '')}") == record["slug"]), None)
    if target is None:
        raise DraftMetadataError(f"tracks.csv does not contain this edit target: {record['slug']}")
    original_cover = target.get("cover_file", "")
    target.update({column: record.get(column, "") for column in TRACK_COLUMNS if column != "order"})
    target["cover_file"] = original_cover or record.get("cover_file", "")
    with (root / "tracks.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=TRACK_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows({column: row.get(column, "") for column in TRACK_COLUMNS} for row in rows)


def _append_p53(root: Path, record: dict, *, note: str = "", current: bool = False) -> None:
    config_path = root / "config.json"
    config = load_config(config_path)
    history = config.setdefault("p53_history", [])
    if any(item.get("slug") == record["slug"] for item in history if isinstance(item, dict)):
        raise DraftMetadataError(f"config.json already contains this P53 slug: {record['slug']}")
    history.append(p53_record_from_draft(record))
    if note:
        notes = config.setdefault("p53_transmission_notes", {})
        notes[record["slug"]] = note
    if current:
        config["p53_current_slug"] = record["slug"]
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _update_p53(root: Path, record: dict, *, enabled: bool, note: str = "", current: bool = False) -> None:
    """Apply P53 state from a private edit without touching unrelated history."""
    config_path = root / "config.json"
    config = load_config(config_path)
    history = config.setdefault("p53_history", [])
    existing = next((item for item in history if isinstance(item, dict) and item.get("slug") == record["slug"]), None)
    if enabled and existing is None:
        history.append(p53_record_from_draft(record))
    elif not enabled and existing is not None:
        history.remove(existing)
    if enabled:
        existing = next((item for item in history if isinstance(item, dict) and item.get("slug") == record["slug"]), None)
        if existing is not None:
            existing.update(p53_record_from_draft(record))
        notes = config.setdefault("p53_transmission_notes", {})
        if note:
            notes[record["slug"]] = note
        else:
            notes.pop(record["slug"], None)
        if current:
            config["p53_current_slug"] = record["slug"]
        elif config.get("p53_current_slug") == record["slug"]:
            config.pop("p53_current_slug", None)
    else:
        config.setdefault("p53_transmission_notes", {}).pop(record["slug"], None)
        if config.get("p53_current_slug") == record["slug"]:
            config.pop("p53_current_slug", None)
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _update_catalogue_notes(root: Path, record: dict, *, artist_note: str = "", album_note: str = "") -> None:
    """Persist the optional notes owned by the generated artist/album rooms."""
    config_path = root / "config.json"
    config = load_config(config_path)
    artist_notes = config.setdefault("artist_notes", {})
    if artist_note:
        artist_notes[record["artist"]] = artist_note
    album_notes = config.setdefault("album_notes", {})
    artist_albums = album_notes.setdefault(record["artist"], {})
    if album_note:
        artist_albums[record["album"]] = album_note
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _snapshot_files(paths: list[Path]) -> dict[Path, bytes | None]:
    """Capture the small source-file boundary touched by one local publish."""
    return {path: path.read_bytes() if path.is_file() else None for path in paths}


def _restore_files(snapshot: dict[Path, bytes | None]) -> None:
    """Restore a publish snapshot, removing files that did not previously exist."""
    for path, contents in snapshot.items():
        if contents is None:
            if path.is_file():
                path.unlink()
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(contents)


def _rebuild_after_rollback(root: Path) -> str:
    """Best-effort regeneration after restoring source files."""
    try:
        result = subprocess.run(
            [sys.executable, str(root / "build.py"), "--site-only"],
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=180,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return str(error)
    output = (result.stdout or "") + (result.stderr or "")
    return "" if result.returncode == 0 else output[-1200:]


def publish_draft(root: Path, payload: dict, *, build_site: bool = True) -> dict:
    """Write one validated browser draft, cache its cover, and rebuild locally.

    This is intentionally a local-only handoff used by ``submission_server``.
    The public Pages site never receives this endpoint or its private editor.
    """
    clean, error = validate_draft_payload(payload)
    if error or clean is None:
        raise DraftMetadataError(error or "invalid draft")
    record_data = dict(clean["record"])
    edit_of = str(payload.get("editOf") or "").strip()
    metadata = metadata_from_link(
        record_data["link"],
        artist=record_data["artist"],
        track=record_data["track"],
        album=record_data["album"],
    )
    record = draft_record(metadata, tags=record_data["tags"], accent=record_data["accent"])
    if clean["p53"]["enabled"]:
        tags = [tag.strip() for tag in record.get("tags", "").split(",") if tag.strip()]
        if not any(tag.casefold() == "p53" for tag in tags):
            tags.append("p53")
        record["tags"] = ",".join(tags)
    # Preserve the browser's resolved artwork URL when the provider lookup is
    # unavailable on the local server, while keeping the canonical identity.
    record["cover_url"] = record_data.get("cover_url") or record.get("cover_url", "")
    record["cover_file"] = record_data.get("cover_file") or record["cover_file"]
    if edit_of:
        if edit_of != record["slug"]:
            raise DraftMetadataError("private edits cannot change artist/track route slugs")
        if not (root / "entries" / f"{edit_of}.md").is_file():
            raise DraftMetadataError(f"edit target does not exist: {edit_of}")
    else:
        _assert_new_slug(root, record["slug"])

    covers_dir = root / "covers"
    covers_dir.mkdir(exist_ok=True)
    cover_path = covers_dir / record["cover_file"]
    entry_path = root / "entries" / f"{record['slug']}.md"
    snapshot = _snapshot_files([root / "tracks.csv", root / "config.json", entry_path, cover_path])
    build_output = ""
    try:
        if not cover_path.exists():
            cover_url = record.get("cover_url", "").strip()
            if not cover_url or not download_cover(cover_url, cover_path):
                raise DraftMetadataError("the provider resolved the entry, but its cover could not be cached")
        if not record.get("accent"):
            record["accent"] = dominant_color(cover_path)

        entry_path.write_text(
            render_authored_entry(record, clean["sections"]),
            encoding="utf-8",
        )
        if edit_of:
            _replace_track(root, record)
            _update_p53(
                root,
                record,
                enabled=clean["p53"]["enabled"],
                note=clean["p53"]["note"],
                current=clean["p53"]["current"],
            )
        else:
            _append_track(root, record)
            if clean["p53"]["enabled"]:
                _append_p53(
                    root,
                    record,
                    note=clean["p53"]["note"],
                    current=clean["p53"]["current"],
                )
        _update_catalogue_notes(
            root,
            record,
            artist_note=clean["catalogue"]["artist_note"],
            album_note=clean["catalogue"]["album_note"],
        )

        if build_site:
            try:
                result = subprocess.run(
                    [sys.executable, str(root / "build.py"), "--site-only", "--validate-links"],
                    cwd=root,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    timeout=180,
                    check=False,
                )
            except (OSError, subprocess.TimeoutExpired) as error:
                raise DraftMetadataError(f"local build could not run: {error}") from error
            build_output = (result.stdout or "") + (result.stderr or "")
            if result.returncode:
                raise DraftMetadataError(f"local build failed:\n{build_output[-3000:]}")
    except Exception as error:
        try:
            _restore_files(snapshot)
            rollback_output = _rebuild_after_rollback(root) if build_site else ""
        except Exception as rollback_error:
            raise DraftMetadataError(
                f"local publish failed and rollback was incomplete: {rollback_error}"
            ) from error
        suffix = " Source files were restored."
        if rollback_output:
            suffix += f" The recovery build reported:\n{rollback_output}"
        if isinstance(error, DraftMetadataError):
            raise DraftMetadataError(f"{error}{suffix}") from error
        raise DraftMetadataError(f"local publish failed: {error}.{suffix}") from error

    artist_slug = slugify(record["artist"])
    album_slug = slugify(f"{record['artist']}-{record['album']}")
    return {
        "slug": record["slug"],
        "entry": f"/entries/{record['slug']}.html",
        "p53": f"/p53/{record['slug']}.html" if clean["p53"]["enabled"] else "",
        "artist": f"/artists/{artist_slug}.html" if artist_slug else "",
        "album": f"/albums/{album_slug}.html" if album_slug else "",
        "cover": f"/covers/{record['cover_file']}",
        "buildOutput": build_output[-1200:],
    }


def _load_browser_draft(path: Path) -> dict:
    """Read and validate one private browser-to-local draft handoff."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise DraftMetadataError(f"unable to read draft {path}: {error}") from error
    clean, error = validate_draft_payload(payload)
    if error or clean is None:
        raise DraftMetadataError(error or "invalid draft")
    if isinstance(payload.get("editOf"), str) and payload["editOf"].strip():
        clean["editOf"] = payload["editOf"].strip()
    return clean


def main() -> int:
    args = _parse_args()
    root = _root()
    config = load_config(root / "config.json")
    draft_sections = None
    draft_p53 = {"enabled": False, "current": False, "note": ""}
    edit_of = ""
    if args.from_draft:
        try:
            draft = _load_browser_draft(args.from_draft)
        except DraftMetadataError as error:
            print(f"Draft not created: {error}")
            return 2
        draft_record_data = draft["record"]
        args.link = draft_record_data["link"]
        args.artist = draft_record_data["artist"]
        args.track = draft_record_data["track"]
        args.album = draft_record_data["album"]
        args.tags = draft_record_data["tags"]
        args.accent = draft_record_data["accent"]
        draft_sections = draft["sections"]
        draft_p53 = draft["p53"]
        edit_of = draft.get("editOf", "")
        args.p53 = draft_p53["enabled"]
        args.p53_current = draft_p53["current"]
        args.p53_note = draft_p53["note"]
    if args.install_editor:
        try:
            _install_browser_editor(root)
        except DraftMetadataError as error:
            print(f"Editor not installed: {error}")
            return 2
        if not args.link and not args.interactive:
            return 0
    if args.interactive:
        try:
            args = _interactive_namespace(args, config)
        except (EOFError, KeyboardInterrupt):
            print("\nDraft cancelled.")
            return 130
    elif not args.link:
        print("Draft not created: provide a provider link or use --interactive.")
        return 2
    try:
        metadata = metadata_from_link(
            args.link,
            artist=args.artist,
            track=args.track,
            album=args.album,
            timeout=args.timeout,
        )
        record = draft_record(metadata, tags=args.tags, accent=args.accent)
        if args.from_draft:
            record["cover_url"] = draft_record_data.get("cover_url") or record.get("cover_url", "")
            record["cover_file"] = draft_record_data.get("cover_file") or record["cover_file"]
        sections = _ensure_unique_sections(
            getattr(args, "_selected_sections", config.get("sections", [])),
            _flatten_sections(args.section, args.sections),
        )
        if edit_of:
            if edit_of != record["slug"]:
                raise DraftMetadataError("private edits cannot change artist/track route slugs")
            if not (root / "entries" / f"{edit_of}.md").exists():
                raise DraftMetadataError(f"edit target does not exist: {edit_of}")
        else:
            _assert_new_slug(root, record["slug"])
        if args.p53_current and not args.p53:
            raise DraftMetadataError("--p53-current requires --p53")
        if args.p53:
            tags = [tag.strip() for tag in record.get("tags", "").split(",") if tag.strip()]
            if not any(tag.casefold() == "p53" for tag in tags):
                tags.append("p53")
            record["tags"] = ",".join(tags)
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
    if args.p53:
        print(f"P53:    {'CURRENT TRANSMISSION' if args.p53_current else 'history'}")
        if args.p53_note:
            print("Note:   transmission note supplied")
    print("Mode:   write" if args.write else "Mode:   preview only")

    if not args.write:
        return 0

    entry_path = root / "entries" / f"{record['slug']}.md"
    entry_path.write_text(
        render_authored_entry(record, draft_sections)
        if draft_sections is not None
        else render_empty_entry(record, sections),
        encoding="utf-8",
    )
    if edit_of:
        _replace_track(root, record)
        _update_p53(root, record, enabled=args.p53, note=args.p53_note, current=args.p53_current)
        print(f"Updated source entry: {entry_path}")
    else:
        _append_track(root, record)
        if args.p53:
            _append_p53(root, record, note=args.p53_note, current=args.p53_current)
        print(f"Created source entry: {entry_path}")
    if args.from_draft:
        _update_catalogue_notes(
            root,
            record,
            artist_note=draft.get("catalogue", {}).get("artist_note", ""),
            album_note=draft.get("catalogue", {}).get("album_note", ""),
        )
    print("Next: run the normal build and source validator.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
