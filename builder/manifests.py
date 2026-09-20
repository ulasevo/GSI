"""Build-time manifests for generated routes and local media.

Manifests are audit artifacts, not page content.  They intentionally exclude
review prose and accept explicit paths so tests can write to a temporary tree.
"""

import json
from pathlib import Path

from gsi_assets import local_image_metadata
from gsi_links import catalogue_record


BASE = Path(__file__).resolve().parents[1]


# Remove only files owned by one generated page family. User-authored files in
# other directories are never part of this cleanup.
def reconcile_generated_pages(
    directory: Path,
    expected_pages: set[str],
    label: str,
) -> list[Path]:
    """Remove stale HTML only from a directory owned by one page family."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    removed = []
    for html_path in sorted(directory.glob("*.html")):
        if html_path.name in expected_pages:
            continue
        html_path.unlink()
        removed.append(html_path)
        print(f" Removed stale generated {label}: {html_path}")
    return removed


def reconcile_generated_outputs(
    inventory: dict,
    *,
    site_dir: Path | None = None,
) -> None:
    """Reconcile managed page families while retaining historical P53 routes."""
    site_root = Path(site_dir) if site_dir is not None else BASE / "site"
    expected = inventory.get("expected_pages", {})
    for family in ("entries", "artists", "albums"):
        reconcile_generated_pages(
            site_root / family,
            set(expected.get(family, set())),
            family[:-1] if family.endswith("s") else family,
        )

    # P53 transmission slugs are permanent links. Only the replaceable landing
    # aliases are managed here; removing a historical transmission would break
    # a saved link even when it no longer appears in config.json.
    p53_dir = site_root / "p53"
    expected_p53 = set(expected.get("p53", set()))
    for alias in ("index.html", "latest.html"):
        alias_path = p53_dir / alias
        if alias_path.exists() and alias not in expected_p53:
            alias_path.unlink()
            print(f" Removed stale generated P53 alias: {alias_path}")


def write_catalog_manifest(
    items: list[dict],
    *,
    covers_dir: Path | None = None,
    output_path: Path | None = None,
) -> None:
    """Write deterministic link and local-art metadata for build-time audits."""
    # This manifest is deliberately metadata-only: it helps auditing without
    # copying any review prose into generated data.
    covers_root = Path(covers_dir) if covers_dir is not None else BASE / "covers"
    manifest_path = Path(output_path) if output_path is not None else BASE / "site" / "data" / "catalog.json"
    covers_root = covers_root.resolve()
    records = []
    for item in items:
        cover_file = (item.get("cover_file") or "").replace("\\", "/")
        cover_path = (covers_root / cover_file).resolve() if cover_file else None
        try:
            if cover_path is None:
                raise ValueError("no cover")
            cover_path.relative_to(covers_root)
        except ValueError:
            cover_metadata = {
                "exists": False,
                "valid": False,
                "width": None,
                "height": None,
                "bytes": None,
            }
        else:
            cover_metadata = local_image_metadata(cover_path)
        records.append(catalogue_record(item, covers_root, cover_metadata))

    manifest = {
        "schema": 1,
        "description": "Generated GSI media-link and local-art inventory; review prose is never included.",
        "signals": records,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote catalogue manifest: {manifest_path}")


def write_generation_manifest(
    inventory: dict,
    *,
    output_path: Path | None = None,
) -> None:
    """Write route relationships and expected page names for audit tooling."""
    # Every renderer reads the same relationships, preventing route drift.
    relationships = {
        "entries": [
            {"slug": slug, "href": href}
            for slug, href in sorted(inventory["entry_routes"].items())
        ],
        "p53": [
            {"slug": slug, "href": href}
            for slug, href in sorted(inventory["p53_routes"].items())
        ],
        "artists": [
            {"artist": artist, "href": href}
            for artist, href in sorted(inventory["artist_routes"].items())
        ],
        "albums": [
            {"artist": key[0], "album": key[1], "href": href}
            for key, href in sorted(inventory["album_routes"].items())
        ],
    }
    manifest = {
        "schema": 1,
        "description": "Generated GSI route relationships and expected outputs; review prose is never included.",
        "relationships": relationships,
        "expected_pages": {
            family: sorted(names)
            for family, names in inventory["expected_pages"].items()
        },
    }
    manifest_path = Path(output_path) if output_path is not None else BASE / "site" / "data" / "generation.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote generation manifest: {manifest_path}")
