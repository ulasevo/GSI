"""Export represented entry prose into a build-generated Android asset.

The source Markdown remains authoritative. The app's bundled catalogue decides
which entries are included, so an unrelated local draft is never packaged just
because it exists in the entries directory.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from builder.entry_pages import extract_sections_from_markdown


def export_reviews(catalog: Path, entries: Path) -> dict:
    data = json.loads(catalog.read_text(encoding="utf-8"))
    signals = data.get("signals")
    if not isinstance(signals, list):
        raise ValueError("Android catalogue must have a signals list")
    reviews = {}
    seen_ids = set()
    for signal in signals:
        if not isinstance(signal, dict):
            raise ValueError("Android catalogue contains an invalid signal")
        signal_id = str(signal.get("signal_id") or "").strip()
        if not signal_id or signal_id in seen_ids:
            raise ValueError(f"Android catalogue contains a missing or repeated signal ID: {signal_id!r}")
        seen_ids.add(signal_id)
        route = str(signal.get("page_url") or "")
        if not route.startswith("entries/"):
            continue
        relative = PurePosixPath(route)
        if (
            len(relative.parts) != 2
            or relative.suffix != ".html"
            or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", relative.stem)
            or signal.get("slug") != relative.stem
        ):
            raise ValueError(f"Invalid entry route in Android catalogue: {route!r}")
        entry = entries / f"{relative.stem}.md"
        if not entry.is_file():
            raise FileNotFoundError(f"Catalogue entry source is missing: {entry}")
        sections = [section for section in extract_sections_from_markdown(entry) if section["content"].strip()]
        if sections:
            reviews[signal_id] = sections
    return {"schema": 1, "reviews": reviews}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--entries", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = export_reviews(args.catalog, args.entries)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Exported {len(data['reviews'])} Android reviews to {args.output}")


if __name__ == "__main__":
    main()
