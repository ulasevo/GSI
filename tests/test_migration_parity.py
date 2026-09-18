"""Regression checks for the template/styles/scripts migration baseline."""

import html
import json
import re
import unittest
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "archive" / "baselines" / "migration-parity-2026-09-17" / "site"
CURRENT = ROOT / "site"
TEMPLATES = ROOT / "templates"
WEB = ROOT / "web"
_TAG_RE = re.compile(r"<[^>]+>")
_SCRIPT_STYLE_RE = re.compile(r"<(?:script|style)\b.*?</(?:script|style)>", re.I | re.S)
_LINK_RE = re.compile(r"(?:href|src)=\"([^\"]+)\"")


def _relationships(site_root: Path) -> dict[str, list[dict]]:
    manifest = json.loads((site_root / "data" / "generation.json").read_text(encoding="utf-8"))
    return manifest["relationships"]


def _semantic_links(site_root: Path) -> dict[str, set[str]]:
    links: dict[str, set[str]] = {}
    for page in sorted(site_root.rglob("*.html")):
        relative = page.relative_to(site_root).as_posix()
        values = set()
        for value in _LINK_RE.findall(page.read_text(encoding="utf-8")):
            parsed = urlsplit(value)
            asset_path = parsed.path.replace("\\", "/")
            if (
                not value
                or value.startswith("#")
                or parsed.scheme
                or value.startswith("//")
                or any(segment in asset_path for segment in ("covers/", "artist-assets/", "styles/", "scripts/"))
            ):
                continue
            values.add(value)
        links[relative] = values
    return links


def _visible_text(page: Path) -> str:
    text = _SCRIPT_STYLE_RE.sub("", page.read_text(encoding="utf-8"))
    text = _TAG_RE.sub(" ", text)
    return " ".join(html.unescape(text).split())


def _referenced_assets(site_root: Path) -> set[str]:
    assets = set()
    for page in sorted(site_root.rglob("*.html")):
        relative_page = page.relative_to(site_root).parent
        for value in _LINK_RE.findall(page.read_text(encoding="utf-8")):
            if not value.startswith(("covers/", "artist-assets/", "styles/", "scripts/", "../covers/", "../artist-assets/", "../styles/", "../scripts/")):
                continue
            candidate = (page.parent / value.split("?", 1)[0]).resolve()
            try:
                relative = candidate.relative_to(site_root.resolve()).as_posix()
            except ValueError:
                continue
            assets.add(relative)
    return assets


class MigrationParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not BASELINE.exists():
            raise unittest.SkipTest(f"migration baseline missing: {BASELINE}")

    def test_route_inventory_and_counts_match_baseline(self):
        baseline = _relationships(BASELINE)
        current = _relationships(CURRENT)
        self.assertEqual(
            {key: [(item.get("slug"), item.get("href")) for item in value] for key, value in baseline.items()},
            {key: [(item.get("slug"), item.get("href")) for item in value] for key, value in current.items()},
        )

    def test_semantic_internal_links_match_baseline(self):
        self.assertEqual(_semantic_links(BASELINE), _semantic_links(CURRENT))

    def test_referenced_assets_are_present_and_image_inventory_is_stable(self):
        baseline_refs = _referenced_assets(BASELINE)
        current_refs = _referenced_assets(CURRENT)
        self.assertTrue(baseline_refs <= current_refs)
        for relative in current_refs:
            self.assertTrue((CURRENT / relative).is_file(), relative)
        for directory in ("covers", "artist-assets"):
            baseline_files = {path.relative_to(BASELINE / directory).as_posix() for path in (BASELINE / directory).rglob("*") if path.is_file()}
            current_files = {path.relative_to(CURRENT / directory).as_posix() for path in (CURRENT / directory).rglob("*") if path.is_file()}
            self.assertEqual(baseline_files, current_files, directory)

    def test_entry_visible_prose_matches_baseline(self):
        baseline_entries = _relationships(BASELINE)["entries"]
        for item in baseline_entries:
            relative = item["href"]
            self.assertEqual(
                _visible_text(BASELINE / relative),
                _visible_text(CURRENT / relative),
                relative,
            )

    def test_template_and_asset_boundaries_are_explicit(self):
        expected_templates = {
            "index.html",
            "entry.html",
            "p53-landing.html",
            "p53-transmission.html",
            "artist.html",
            "album.html",
            "404.html",
        }
        self.assertEqual(
            expected_templates,
            {path.name for path in TEMPLATES.glob("*.html")},
        )
        index_template = (TEMPLATES / "index.html").read_text(encoding="utf-8")
        script_order = [
            'src="scripts/gsi-context.js"',
            'src="scripts/home-state.js"',
            'src="scripts/home-layout.js"',
            'src="scripts/home-format.js"',
            'src="scripts/home-filters.js"',
            'src="scripts/home-page.js"',
        ]
        positions = [index_template.index(marker) for marker in script_order]
        self.assertEqual(positions, sorted(positions))
        self.assertTrue((WEB / "styles").is_dir())
        self.assertTrue((WEB / "scripts").is_dir())
        home_parts = [
            "01-foundation.css",
            "02-hero-and-filter-room.css",
            "03-filter-and-controls.css",
            "04-cards-and-responsive.css",
        ]
        self.assertEqual(
            home_parts,
            [path.name for path in sorted((WEB / "styles" / "home").glob("*.css"))],
        )
        assembled_home = (CURRENT / "styles" / "gsi-home.css").read_text(encoding="utf-8")
        self.assertIn("Generated from web/styles/home/*.css", assembled_home)
        self.assertEqual(
            [],
            [path.name for path in WEB.iterdir() if path.is_file() and path.suffix in {".css", ".js"}],
        )
        for template in sorted(TEMPLATES.glob("*.html")):
            text = template.read_text(encoding="utf-8")
            self.assertNotRegex(text, r"<style\b")
            for tag in re.findall(r"<script\b[^>]*>", text, flags=re.I):
                if 'type="application/json"' in tag or "type='application/json'" in tag:
                    continue
                self.assertIn("src=", tag, template.name)


if __name__ == "__main__":
    unittest.main()
