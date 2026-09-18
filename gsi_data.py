"""Source-data loading and ordering for the GSI build.

These helpers deliberately accept their input paths so the build entry point
owns filesystem locations while this module remains easy to test in isolation.
"""

import csv
import json
from pathlib import Path

from gsi_text import slugify


# Read the two editable registries without adding policy at this layer.
def load_config(config_file: Path) -> dict:
    """Load the JSON configuration used by the generators."""
    with config_file.open("r", encoding="utf-8") as file:
        return json.load(file)


def read_tracks(tracks_file: Path) -> list[dict]:
    """Read the editable track registry as dictionaries."""
    with tracks_file.open("r", encoding="utf-8") as file:
        return list(csv.DictReader(file))


# Preserve a hand-authored order when one exists; otherwise use the configured
# direction. No page markup should need to know how ordering was chosen.
def ordered_tracks(rows: list[dict], config: dict) -> list[dict]:
    """Apply explicit row ordering, falling back to the configured direction."""
    has_manual_order = any((row.get("order") or "").strip().isdigit() for row in rows)
    if has_manual_order:
        def sort_key(row: dict) -> int:
            order_text = (row.get("order") or "").strip()
            return int(order_text) if order_text.isdigit() else 999999

        return sorted(rows, key=sort_key)
    if config.get("newest_first", False):
        return list(reversed(rows))
    return rows


def artist_room_groups(tracks: list[dict], p53_history: list[dict]) -> dict[str, list[dict]]:
    """Group ordinary entries and P53-only transmissions for artist-room eligibility."""
    grouped: dict[str, list[dict]] = {}
    for item in tracks:
        grouped.setdefault(item["artist"], []).append(item)

    track_slugs = {item["slug"] for item in tracks}
    for signal in p53_history:
        if signal["slug"] in track_slugs:
            continue
        p53_item = dict(signal)
        p53_item["p53_only"] = True
        p53_item["page_url"] = f'p53/{signal["slug"]}.html'
        grouped.setdefault(signal["artist"], []).append(p53_item)

    return {
        artist: items
        for artist, items in grouped.items()
        if len(items) >= 2
    }


# Derive every route once. Renderers consume this inventory instead of inventing
# their own album, artist, or P53 eligibility rules.
def build_generation_inventory(
    tracks: list[dict],
    p53_history: list[dict],
    archive_tracks: list[dict],
    artist_groups: dict[str, list[dict]],
    current_p53_slug: str = "",
) -> dict:
    """Describe every generated relationship and expected route in one place.

    The inventory is deliberately derived from the same prepared records used by
    the renderers. It is not a second source of truth and it contains no review
    prose, only stable slugs, route names, and expected generated filenames.
    """
    entry_routes = {
        item["slug"]: f'entries/{item["html_file"]}'
        for item in tracks
        if item.get("slug") and item.get("html_file")
    }
    p53_routes = {
        item["slug"]: f'p53/{item["slug"]}.html'
        for item in p53_history
        if item.get("slug")
    }
    artist_routes = {
        artist: f'artists/{slugify(artist)}.html'
        for artist in artist_groups
        if slugify(artist)
    }

    album_groups: dict[tuple[str, str], list[dict]] = {}
    for item in archive_tracks:
        album_groups.setdefault((item["artist"], item["album"]), []).append(item)
    album_routes = {
        key: f'albums/{slugify(f"{key[0]}-{key[1]}")}.html'
        for key, items in album_groups.items()
        if len(items) >= 2 and slugify(f"{key[0]}-{key[1]}")
    }

    p53_page_names = {"index.html"} if p53_history else set()
    p53_page_names.update(f"{slug}.html" for slug in p53_routes)
    if current_p53_slug and current_p53_slug in p53_routes:
        p53_page_names.add("latest.html")

    return {
        "entry_routes": entry_routes,
        "p53_routes": p53_routes,
        "artist_routes": artist_routes,
        "album_routes": album_routes,
        "expected_pages": {
            "entries": {item["html_file"] for item in tracks if item.get("html_file")},
            "p53": p53_page_names,
            "artists": {Path(route).name for route in artist_routes.values()},
            "albums": {Path(route).name for route in album_routes.values()},
        },
    }
