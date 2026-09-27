"""Run a bounded, read-only GSI integrity and contract audit.

This deliberately checks source relationships and generated manifests rather
than rendering every page. It is safe to run before an overnight handoff and
returns a non-zero status only for concrete missing or inconsistent artefacts.
"""

from __future__ import annotations

import csv
import json
from html.parser import HTMLParser
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gsi_data import current_p53_record
from gsi_links import provider_link_audit

P53_RUNTIME_ASSET = Path("covers/P53_cover-runtime.webp")
P53_RUNTIME_ASSET_BUDGET_BYTES = 500_000


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _frontmatter_cover(entry_path: Path) -> str:
    if not entry_path.is_file():
        return ""
    for line in entry_path.read_text(encoding="utf-8").splitlines()[:30]:
        if line.lower().startswith("cover:"):
            return line.split(":", 1)[1].strip().strip('"\'').split("/")[-1]
    return ""


class _ImageAttributeParser(HTMLParser):
    """Collect image attributes without executing generated page scripts."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.images: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "img":
            return
        self.images.append({key.lower(): value or "" for key, value in attrs})


def _image_delivery_errors(site_dir: Path) -> list[str]:
    """Require generated images to declare an intentional loading strategy."""
    errors: list[str] = []
    for page in sorted(site_dir.rglob("*.html")):
        parser = _ImageAttributeParser()
        try:
            parser.feed(page.read_text(encoding="utf-8"))
        except (OSError, UnicodeError) as error:
            errors.append(f"could not inspect generated page {page.relative_to(site_dir)}: {error}")
            continue
        for index, attrs in enumerate(parser.images, start=1):
            # Script-populated placeholders intentionally have no src until a
            # filter is selected; they do not create a network request yet.
            if not attrs.get("src", "").strip():
                continue
            loading = attrs.get("loading", "").strip().lower()
            decoding = attrs.get("decoding", "").strip().lower()
            if loading not in {"eager", "lazy"}:
                errors.append(
                    f"generated image missing loading strategy: "
                    f"{page.relative_to(site_dir)} img#{index}"
                )
            if decoding != "async":
                errors.append(
                    f"generated image missing async decoding: "
                    f"{page.relative_to(site_dir)} img#{index}"
                )
    return errors


def _runtime_asset_report(root: Path, site_dir: Path) -> tuple[list[str], list[str], dict[str, int | None]]:
    """Check that the heavy P53 source has a small published runtime derivative."""
    errors: list[str] = []
    warnings: list[str] = []
    source_path = root / P53_RUNTIME_ASSET
    site_path = site_dir / P53_RUNTIME_ASSET
    source_bytes = source_path.stat().st_size if source_path.is_file() else None
    site_bytes = site_path.stat().st_size if site_path.is_file() else None
    if source_bytes is None:
        errors.append(f"missing runtime artwork source: {P53_RUNTIME_ASSET.as_posix()}")
    elif source_bytes > P53_RUNTIME_ASSET_BUDGET_BYTES:
        errors.append(
            f"runtime artwork exceeds budget: {P53_RUNTIME_ASSET.as_posix()} "
            f"is {source_bytes} bytes (budget {P53_RUNTIME_ASSET_BUDGET_BYTES})"
        )
    if site_bytes is None:
        errors.append(f"generated runtime artwork is missing: {P53_RUNTIME_ASSET.as_posix()}")
    elif source_bytes is not None and site_bytes != source_bytes:
        errors.append(
            f"generated runtime artwork is stale: {P53_RUNTIME_ASSET.as_posix()} "
            f"source={source_bytes} site={site_bytes}"
        )
    original_path = root / "covers" / "P53_cover.jpg"
    if not original_path.is_file():
        warnings.append("P53 source artwork is missing; social preview generation may be affected")
    return errors, warnings, {
        "source_bytes": source_bytes,
        "site_bytes": site_bytes,
        "original_bytes": original_path.stat().st_size if original_path.is_file() else None,
    }


def audit(root: Path = ROOT) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    tracks_path = root / "tracks.csv"
    config_path = root / "config.json"
    site_dir = root / "site"
    tracks = list(csv.DictReader(tracks_path.open("r", encoding="utf-8", newline="")))
    config = _load_json(config_path)
    provider_report_full = provider_link_audit(tracks + [
        item for item in config.get("p53_history", [])
        if isinstance(item, dict)
    ])
    provider_report = {
        "signals_inspected": provider_report_full["signals_inspected"],
        "counts": provider_report_full["counts"],
        "fallback_count": len(provider_report_full["fallbacks"]),
    }

    slugs: dict[str, list[str]] = {}
    missing_entries = []
    missing_covers = []
    for row in tracks:
        artist = (row.get("artist") or "").strip()
        track = (row.get("track") or "").strip()
        slug = re.sub(r"[^a-z0-9]+", "-", f"{artist}-{track}".lower()).strip("-")
        slugs.setdefault(slug, []).append(f"{artist} — {track}")
        if not (root / "entries" / f"{slug}.md").is_file():
            missing_entries.append(slug)
        entry_path = root / "entries" / f"{slug}.md"
        cover = (row.get("cover_file") or "").strip() or _frontmatter_cover(entry_path)
        if not cover or not (root / "covers" / cover).is_file():
            missing_covers.append(f"{slug}:{cover or '<blank>'}")

    duplicate_slugs = {slug: labels for slug, labels in slugs.items() if len(labels) > 1}
    if duplicate_slugs:
        errors.append(f"duplicate track routes: {duplicate_slugs}")
    if missing_entries:
        errors.append(f"missing source entries: {missing_entries}")
    if missing_covers:
        errors.append(f"missing local covers: {missing_covers}")

    history = [item for item in config.get("p53_history", []) if isinstance(item, dict)]
    history_slugs = {str(item.get("slug") or "").strip() for item in history}
    current = str(config.get("p53_current_slug") or "").strip()
    current_id = str(config.get("p53_current_signal_id") or "").strip()
    if current and current not in history_slugs:
        errors.append(f"P53 current slug is not in history: {current}")
    current_record = current_p53_record(config, history)
    if current_id and not current_record:
        errors.append(f"P53 current signal ID is not in history: {current_id}")
    if current_record and current_record.get("slug") != current:
        errors.append("P53 current slug and signal ID resolve to different records")
    for slug in sorted(history_slugs):
        if not (root / "site" / "p53" / f"{slug}.html").is_file():
            warnings.append(f"generated P53 page missing until next build: {slug}")

    manifest_path = site_dir / "data" / "generation.json"
    if not manifest_path.is_file():
        errors.append("site/data/generation.json is missing")
        manifest = {}
    else:
        manifest = _load_json(manifest_path)
        for family, routes in manifest.get("expected_pages", {}).items():
            for filename in routes:
                candidate = site_dir / family / filename
                if not candidate.is_file():
                    errors.append(f"generated route missing: {family}/{filename}")

    errors.extend(_image_delivery_errors(site_dir))
    runtime_errors, runtime_warnings, runtime_asset = _runtime_asset_report(root, site_dir)
    errors.extend(runtime_errors)
    warnings.extend(runtime_warnings)

    theme_css = (root / "web" / "styles" / "theme-mode.css").read_text(encoding="utf-8")
    theme_js = (root / "web" / "scripts" / "theme-mode.js").read_text(encoding="utf-8")
    loader_js = (root / "tools" / "editor" / "new-entry.js").read_text(encoding="utf-8")
    if "theme" not in theme_js or "searchParams.set(\"theme\"" not in theme_js:
        errors.append("theme URL-state contract is missing")
    if "setTheme(initial, true)" not in theme_js or "localStorage.setItem(storageKey, next)" not in theme_js:
        errors.append("theme preference persistence contract is missing")
    if "theme-toggle__track" not in theme_js or "aria-pressed" not in theme_css:
        errors.append("theme toggle contract is incomplete")
    if "art-section-ink" not in theme_css:
        errors.append("entry section contrast contract is missing")
    if "local-entry-publish" not in loader_js:
        errors.append("Entry Loader local publish contract is missing")

    return {
        "tracks": len(tracks),
        "entries": len(list((root / "entries").glob("*.md"))),
        "p53_history": len(history),
        "current_p53": current,
        "generated_families": {key: len(value) for key, value in manifest.get("expected_pages", {}).items()},
        "provider_links": provider_report,
        "p53_runtime_asset": runtime_asset,
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    report = audit()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["errors"]:
        return 1
    print("Bounded overnight audit passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
