"""Artist-level artwork and catalogue metadata for generated GSI rooms.

Artist imagery is deliberately opt-in.  The static build can use a local,
reviewed image declared in ``config.json`` without making browser requests or
exposing an Apple Music credential.  A missing image remains a valid state and
is represented as a fallback in the generated manifest.
"""

import html
import json
import shutil
from pathlib import Path

from gsi_assets import local_image_metadata
from gsi_text import slugify


def _safe_asset_path(asset_root: Path, asset_file: str) -> Path | None:
    """Resolve an artist image only when it remains inside the asset root."""
    normalized = (asset_file or "").replace("\\", "/").strip()
    if not normalized:
        return None
    candidate = (asset_root / normalized).resolve()
    try:
        candidate.relative_to(asset_root.resolve())
    except ValueError:
        return None
    return candidate


def resolve_artist_asset(artist: str, config: dict, asset_root: Path) -> dict:
    """Return a safe local artist-image record, or an explicit fallback state."""
    configured = config.get("artist_assets", {}).get(artist, {})
    if not isinstance(configured, dict):
        configured = {}
    image_file = str(configured.get("image_file", "")).replace("\\", "/").strip()
    image_path = _safe_asset_path(asset_root, image_file)
    metadata = local_image_metadata(image_path) if image_path else {
        "exists": False,
        "valid": False,
        "width": None,
        "height": None,
        "bytes": None,
    }
    if image_path and not metadata["valid"]:
        print(f" Artist image unavailable or invalid for {artist}: {image_file}")
        image_file = ""
    return {
        "file": image_file,
        "alt": str(configured.get("alt", f"{artist} artist image")).strip(),
        "source": str(configured.get("source", "manual")).strip() or "manual",
        "source_url": str(configured.get("source_url", "")).strip(),
        "metadata": metadata if image_file else {
            "exists": False,
            "valid": False,
            "width": None,
            "height": None,
            "bytes": None,
        },
        "status": "local" if image_file else "fallback",
    }


def copy_site_artist_assets(asset_root: Path, site_asset_root: Path) -> None:
    """Copy optional local artist imagery into generated output."""
    if site_asset_root.exists():
        shutil.rmtree(site_asset_root)
    if asset_root.exists():
        shutil.copytree(asset_root, site_asset_root)
    else:
        site_asset_root.mkdir(parents=True, exist_ok=True)


def artist_catalogue_records(artist_groups: dict[str, list[dict]], config: dict, asset_root: Path) -> list[dict]:
    """Build deterministic artist metadata without including review prose."""
    records = []
    for artist in sorted(artist_groups, key=str.casefold):
        items = artist_groups[artist]
        records.append({
            "artist": artist,
            "slug": slugify(artist),
            "page_url": f"artists/{slugify(artist)}.html",
            "signal_count": len(items),
            "albums": sorted({item.get("album", "") for item in items if item.get("album")}, key=str.casefold),
            "image": resolve_artist_asset(artist, config, asset_root),
        })
    return records


def write_artist_manifest(records: list[dict], output_path: Path) -> None:
    """Write the generated artist inventory used by later image/room work."""
    output_path.write_text(
        json.dumps({
            "schema": 1,
            "description": "Generated artist inventory; review prose is never included.",
            "artists": records,
        }, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote artist manifest: {output_path}")


def artist_image_markup(asset: dict, artist: str) -> str:
    """Render optional artist art for an artist-room heading."""
    if asset.get("status") != "local" or not asset.get("file"):
        return ""
    metadata = asset.get("metadata") or {}
    width = metadata.get("width")
    height = metadata.get("height")
    dimensions = (
        f' width="{int(width)}" height="{int(height)}"'
        if isinstance(width, int) and isinstance(height, int) and width > 0 and height > 0
        else ""
    )
    return (
        f'<figure class="artist-image-header"><img class="artist-image" '
        f'src="../artist-assets/{html.escape(asset["file"], quote=True)}" '
        f'alt="{html.escape(asset.get("alt") or f"{artist} artist image", quote=True)}" '
        f'{dimensions} loading="eager" fetchpriority="high" decoding="async"></figure>'
    )
