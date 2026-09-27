"""Artist artwork fetcher for GSI.

Fetches high-resolution artist portraits (1000x1000) via Deezer's public API
and records them safely in config.json and artist-assets/.
Existing manual artwork (such as Metric's metric.webp) is strictly preserved.
"""

import argparse
import csv
import json
import ssl
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gsi_assets import local_image_metadata
from gsi_data import load_config
from gsi_text import slugify

SSL_CTX = ssl.create_default_context()
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def query_deezer_artist(artist_name: str) -> dict | None:
    """Query Deezer for an artist and return portrait URLs if found."""
    url = f"https://api.deezer.com/search/artist?q={urllib.parse.quote(artist_name)}"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=12, context=SSL_CTX) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            items = data.get("data", [])
            if not items:
                return None
            # Find best match (exact or first)
            for item in items:
                if item.get("name", "").strip().casefold() == artist_name.strip().casefold():
                    return item
            return items[0]
    except Exception as e:
        print(f"  [!] Deezer search error for '{artist_name}': {e}")
        return None


def fetch_and_register_artist_asset(
    artist: str,
    root: Path | None = None,
    force: bool = False,
) -> dict | None:
    """Fetch and register an artist portrait if not already present."""
    base_root = root or ROOT
    config_path = base_root / "config.json"
    assets_dir = base_root / "artist-assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    config = load_config(config_path)
    artist_assets = config.setdefault("artist_assets", {})

    existing = artist_assets.get(artist)
    if existing and not force:
        image_file = existing.get("image_file")
        if image_file:
            target = assets_dir / image_file
            meta = local_image_metadata(target)
            if meta.get("valid") and meta.get("exists"):
                return existing

    result = query_deezer_artist(artist)
    if not result:
        print(f"  [-] No Deezer portrait found for: {artist}")
        return None

    img_url = result.get("picture_xl") or result.get("picture_big")
    if not img_url:
        print(f"  [-] No portrait image URL in Deezer result for: {artist}")
        return None

    slug = slugify(artist)
    target_file = assets_dir / f"{slug}.jpg"

    try:
        req = urllib.request.Request(img_url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15, context=SSL_CTX) as resp:
            content = resp.read()
            target_file.write_bytes(content)
    except Exception as e:
        print(f"  [!] Failed to download portrait for '{artist}': {e}")
        return None

    meta = local_image_metadata(target_file)
    if not meta.get("valid"):
        print(f"  [!] Downloaded file for '{artist}' is not a valid image.")
        target_file.unlink(missing_ok=True)
        return None

    asset_record = {
        "image_file": target_file.name,
        "alt": f"{artist} artist image",
        "source": "deezer",
        "source_url": img_url,
    }
    artist_assets[artist] = asset_record
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"  [+] Saved {artist} portrait: {target_file.name} ({meta.get('width')}x{meta.get('height')})")
    return asset_record


def fetch_all_artist_portraits(root: Path | None = None, force: bool = False) -> None:
    base_root = root or ROOT
    tracks_file = base_root / "tracks.csv"
    with tracks_file.open("r", encoding="utf-8") as f:
        tracks = list(csv.DictReader(f))
    config_path = base_root / "config.json"
    cfg = load_config(config_path) if config_path.exists() else {}
    artist_set = {t["artist"].strip() for t in tracks if t.get("artist") and t["artist"].strip()}
    for item in cfg.get("p53_history", []):
        if isinstance(item, dict) and item.get("artist"):
            artist_set.add(item["artist"].strip())
    artists = sorted(artist_set)

    print(f"Processing artist portraits for {len(artists)} artists...")
    success_count = 0
    for artist in artists:
        rec = fetch_and_register_artist_asset(artist, root=base_root, force=force)
        if rec:
            success_count += 1
    print(f"\nDone: {success_count}/{len(artists)} artists have portraits registered.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch artist portraits from Deezer for GSI.")
    parser.add_argument("--artist", help="Specific artist to fetch")
    parser.add_argument("--force", action="store_true", help="Force re-fetch even if image already exists")
    args = parser.parse_args()

    if args.artist:
        fetch_and_register_artist_asset(args.artist, force=args.force)
    else:
        fetch_all_artist_portraits(force=args.force)
