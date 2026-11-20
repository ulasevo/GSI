"""Synchronize generated archive data, P53 config, and downscaled covers into Android assets."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None

ROOT = Path(__file__).resolve().parent.parent


def _referenced_cover_names(catalog_data: dict) -> set[str]:
    names: set[str] = set()
    for signal in catalog_data.get("signals") or []:
        cover = signal.get("cover") or {}
        path_value = str(cover.get("path") or "").strip()
        if path_value:
            name = Path(path_value).name
            if name:
                names.add(name)
        else:
            slug = str(signal.get("slug") or "").strip()
            if slug:
                names.add(f"{slug}.jpg")
    return names


def _downscale_cover(src: Path, dst: Path, max_edge: int) -> None:
    suffix = src.suffix.lower()
    if Image is None or suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
        shutil.copy2(src, dst)
        return

    with Image.open(src) as img:
        width, height = img.size
        if max(width, height) > max_edge:
            scale = max_edge / float(max(width, height))
            new_size = (max(1, int(round(width * scale))), max(1, int(round(height * scale))))
            resampling = getattr(Image, "Resampling", Image).LANCZOS
            img = img.resize(new_size, resampling)

        if suffix in {".jpg", ".jpeg"}:
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            img.save(dst, format="JPEG", quality=84, optimize=True)
        elif suffix == ".webp":
            img.save(dst, format="WEBP", quality=84, method=6)
        elif suffix == ".png":
            img.save(dst, format="PNG", optimize=True)
        else:
            shutil.copy2(src, dst)


def sync_android_assets(root: Path = ROOT, max_edge: int = 512) -> dict[str, int]:
    site_catalog = root / "site" / "data" / "catalog.json"
    config_path = root / "config.json"
    covers_dir = root / "covers"
    site_covers_dir = root / "site" / "covers"

    android_assets = root / "android" / "app" / "src" / "main" / "assets"
    android_data_dir = android_assets / "data"
    android_covers_dir = android_assets / "covers"
    android_data_dir.mkdir(parents=True, exist_ok=True)
    android_covers_dir.mkdir(parents=True, exist_ok=True)

    if not site_catalog.is_file():
        raise FileNotFoundError(f"Missing generated catalog: {site_catalog}")

    catalog_raw = site_catalog.read_text(encoding="utf-8")
    catalog_data = json.loads(catalog_raw)
    (android_data_dir / "catalog.json").write_text(catalog_raw, encoding="utf-8")

    if config_path.is_file():
        config = json.loads(config_path.read_text(encoding="utf-8"))
        p53_filter = ((config.get("filters") or {}).get("p53") or {})
        history = [item for item in (config.get("p53_history") or []) if isinstance(item, dict)]
        current_slug = str(
            config.get("p53_current_slug")
            or config.get("p53_track")
            or (history[-1].get("slug") if history else "")
            or ""
        )
        p53_payload = {
            "p53_current_slug": current_slug,
            "p53_about": str(p53_filter.get("description") or ""),
            "p53_history": history,
            "p53_transmission_notes": dict(config.get("p53_transmission_notes") or {}),
        }
        (android_data_dir / "p53_config.json").write_text(
            json.dumps(p53_payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    referenced = _referenced_cover_names(catalog_data)
    copied = 0
    for name in sorted(referenced):
        src = covers_dir / name
        if not src.is_file() and site_covers_dir.is_file():
            src = site_covers_dir / name
        elif not src.is_file() and (site_covers_dir / name).is_file():
            src = site_covers_dir / name
        if not src.is_file():
            continue
        _downscale_cover(src, android_covers_dir / name, max_edge=max_edge)
        copied += 1

    pruned = 0
    for existing in list(android_covers_dir.iterdir()):
        if existing.is_file() and existing.name not in referenced:
            existing.unlink()
            pruned += 1

    return {"copied_covers": copied, "pruned_covers": pruned, "signals": len(catalog_data.get("signals") or [])}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="Repository root directory")
    parser.add_argument("--max-edge", type=int, default=512, help="Maximum pixel edge for bundled covers")
    args = parser.parse_args()
    summary = sync_android_assets(root=args.root.resolve(), max_edge=args.max_edge)
    print(
        f"Synced Android assets: {summary['signals']} signals, "
        f"{summary['copied_covers']} covers ({summary['pruned_covers']} pruned)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
