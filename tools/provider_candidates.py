"""Generate a review-only provider URL candidate report.

Usage:
    python tools/provider_candidates.py

Apple Search results are queried without credentials. Spotify results require
the optional ``SPOTIFY_ACCESS_TOKEN`` environment variable. The report is
written to ``audit/provider-candidates.json`` unless another output is given.
"""

import argparse
import csv
import json
from pathlib import Path
import os
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from builder.provider_candidates import collect_provider_candidates  # noqa: E402


def _source_items() -> list[dict]:
    with (ROOT / "tracks.csv").open("r", encoding="utf-8", newline="") as file:
        items = list(csv.DictReader(file))
    config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    items.extend(config.get("p53_history", []))
    return items


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate review-only provider URL candidates.")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "audit" / "provider-candidates.json",
        help="Report path (default: audit/provider-candidates.json).",
    )
    parser.add_argument(
        "--provider",
        choices=("apple", "spotify", "all"),
        default="all",
        help="Provider to query (default: all).",
    )
    parser.add_argument("--timeout", type=float, default=12, help="Per-request timeout in seconds.")
    args = parser.parse_args()

    providers = ("apple", "spotify") if args.provider == "all" else (args.provider,)
    report = collect_provider_candidates(
        _source_items(),
        providers=providers,
        spotify_token=os.environ.get("SPOTIFY_ACCESS_TOKEN", "").strip(),
        timeout=args.timeout,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote provider candidate report: {args.output}")
    print(f"Signals inspected: {len(report['signals'])}")
    for provider in providers:
        counts: dict[str, int] = {}
        for signal in report["signals"]:
            status = signal["providers"][provider]["status"]
            counts[status] = counts.get(status, 0) + 1
        summary = ", ".join(f"{status}={count}" for status, count in sorted(counts.items()))
        print(f"{provider.title()}: {summary}")


if __name__ == "__main__":
    main()
