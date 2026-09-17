"""Source-data loading and ordering for the GSI build.

These helpers deliberately accept their input paths so the build entry point
owns filesystem locations while this module remains easy to test in isolation.
"""

import csv
import json
from pathlib import Path


def load_config(config_file: Path) -> dict:
    """Load the JSON configuration used by the generators."""
    with config_file.open("r", encoding="utf-8") as file:
        return json.load(file)


def read_tracks(tracks_file: Path) -> list[dict]:
    """Read the editable track registry as dictionaries."""
    with tracks_file.open("r", encoding="utf-8") as file:
        return list(csv.DictReader(file))


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
