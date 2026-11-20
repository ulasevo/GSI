import hashlib
import json
import re
import tempfile
import unittest
from pathlib import Path

from builder.catalog_pages import build_artist_pages
from builder.entry_pages import build_entry_page
from builder.home_page import build_index_html
from builder.p53_pages import build_p53_archive, build_p53_page
from builder.template_renderer import asset_version, render_template
from gsi_assets import HOME_STYLE_PARTS


class BuilderAssetAndHookTests(unittest.TestCase):
    def test_template_renderer_cache_busts_local_styles_and_scripts(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            templates_dir = root / "templates"
            web_dir = root / "web"
            templates_dir.mkdir()
            (web_dir / "styles" / "home").mkdir(parents=True)
            (web_dir / "scripts").mkdir(parents=True)

            css_path = web_dir / "styles" / "entry-room.css"
            js_path = web_dir / "scripts" / "theme-mode.js"
            css_path.write_text("body { color: #111; }\n", encoding="utf-8")
            js_path.write_text("console.log('v1');\n", encoding="utf-8")
            for part_name in HOME_STYLE_PARTS:
                (web_dir / "styles" / "home" / part_name).write_text(
                    f"/* {part_name} */",
                    encoding="utf-8",
                )

            (templates_dir / "sample.html").write_text(
                '<link rel="icon" href="covers/GSI_favicon.svg">\n'
                '<link rel="stylesheet" href="https://example.test/styles/remote.css">\n'
                '<link rel="stylesheet" href="../styles/entry-room.css?v=20260920-rim32">\n'
                '<link rel="stylesheet" href="styles/gsi-home.css">\n'
                '<script src="../scripts/theme-mode.js?v=20260921-persist"></script>\n'
                '<div>@@PROSE@@</div>\n',
                encoding="utf-8",
            )

            rendered_v1 = render_template(
                "sample.html",
                {"prose": '<a href="styles/entry-room.css">prose</a>'},
                template_dir=templates_dir,
                web_dir=web_dir,
            )
            css_hash_v1 = hashlib.sha256(css_path.read_bytes()).hexdigest()[:10]
            js_hash_v1 = hashlib.sha256(js_path.read_bytes()).hexdigest()[:10]
            home_hash_v1 = asset_version("styles/gsi-home.css", web_dir=web_dir)

            self.assertIsNotNone(home_hash_v1)
            self.assertIn(f'href="../styles/entry-room.css?v={css_hash_v1}"', rendered_v1)
            self.assertNotIn("20260920-rim32", rendered_v1)
            self.assertIn(f'href="styles/gsi-home.css?v={home_hash_v1}"', rendered_v1)
            self.assertIn(f'src="../scripts/theme-mode.js?v={js_hash_v1}"', rendered_v1)
            self.assertNotIn("20260921-persist", rendered_v1)
            self.assertIn('href="covers/GSI_favicon.svg"', rendered_v1)
            self.assertIn('href="https://example.test/styles/remote.css"', rendered_v1)
            self.assertIn('<a href="styles/entry-room.css">prose</a>', rendered_v1)

            js_path.write_text("console.log('v2');\n", encoding="utf-8")
            (web_dir / "styles" / "home" / HOME_STYLE_PARTS[0]).write_text(
                "/* updated */",
                encoding="utf-8",
            )
            rendered_v2 = render_template(
                "sample.html",
                {"prose": ""},
                template_dir=templates_dir,
                web_dir=web_dir,
            )
            js_hash_v2 = hashlib.sha256(js_path.read_bytes()).hexdigest()[:10]
            home_hash_v2 = asset_version("styles/gsi-home.css", web_dir=web_dir)
            self.assertNotEqual(js_hash_v1, js_hash_v2)
            self.assertNotEqual(home_hash_v1, home_hash_v2)
            self.assertIn(f'src="../scripts/theme-mode.js?v={js_hash_v2}"', rendered_v2)
            self.assertIn(f'href="styles/gsi-home.css?v={home_hash_v2}"', rendered_v2)

    def test_artist_album_kicker_has_no_inline_color_override(self):
        tracks = [
            {
                "artist": "Metric",
                "album": "Live It Out",
                "track": "Empty",
                "slug": "metric-empty",
                "html_file": "metric-empty.html",
                "cover_file": "metric-empty.jpg",
                "accent": "#ff4fa3",
            },
            {
                "artist": "Metric",
                "album": "Live It Out",
                "track": "Too Little Too Late",
                "slug": "metric-too-little-too-late",
                "html_file": "metric-too-little-too-late.html",
                "cover_file": "metric-too-little-too-late.jpg",
                "accent": "#ff4fa3",
            },
        ]
        with tempfile.TemporaryDirectory() as temp:
            output_dir = Path(temp)
            build_artist_pages(
                {"Metric": tracks},
                {"filters": {}, "artist_notes": {}, "album_notes": {}},
                output_dir=output_dir,
                artist_assets_dir=output_dir / "artist-assets",
            )
            page = (output_dir / "metric.html").read_text(encoding="utf-8")

        self.assertIn('class="album-stack-kicker"', page)
        match = re.search(r'<span class="album-stack-kicker"[^>]*>ALBUM</span>', page)
        self.assertIsNotNone(match)
        self.assertNotIn("color:", match.group(0))

    def test_p53_context_exports_full_track_palette_roles(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config_path = root / "config.json"
            output_dir = root / "site" / "p53"
            entries_dir = root / "entries"
            output_dir.mkdir(parents=True)
            entries_dir.mkdir(parents=True)
            config_path.write_text(
                json.dumps({
                    "filters": {},
                    "p53_history": [
                        {
                            "artist": "Metric",
                            "track": "Empty",
                            "album": "Live It Out",
                            "slug": "metric-empty",
                        }
                    ],
                    "p53_current_slug": "metric-empty",
                }),
                encoding="utf-8",
            )
            build_p53_page(
                {
                    "artist": "Metric",
                    "track": "Empty",
                    "album": "Live It Out",
                    "slug": "metric-empty",
                    "accent": "#ff4fa3",
                },
                "metric-empty.html",
                config_file=config_path,
                output_dir=output_dir,
                entries_dir=entries_dir,
            )
            page = (output_dir / "metric-empty.html").read_text(encoding="utf-8")

        match = re.search(
            r'<script id="p53-transmission-context" type="application/json">(.*?)</script>',
            page,
            re.DOTALL,
        )
        self.assertIsNotNone(match)
        payload = json.loads(match.group(1))
        self.assertEqual(
            set(payload["trackPalette"]),
            {"primary", "secondary", "glow", "field", "soft", "surface", "ink"},
        )

    def test_homepage_emits_filter_color_and_omits_current_transmission_label(self):
        tracks = [
            {
                "artist": "Metric",
                "track": "Empty",
                "album": "Live It Out",
                "slug": "metric-empty",
                "html_file": "metric-empty.html",
                "cover_file": "",
                "accent": "#ff4fa3",
                "tags": "personal,p53",
                "page_url": "entries/metric-empty.html",
                "p53_order": 1,
            }
        ]
        config = {
            "project_title": "GSI",
            "page_title": "GSI",
            "intro": "A personal signal room.",
            "filters": {
                "personal": {"label": "Personal", "description": "One room.", "color": "#d8d34a"},
            },
            "p53_history": [
                {"artist": "Metric", "track": "Empty", "album": "Live It Out", "slug": "metric-empty"}
            ],
            "p53_current_slug": "metric-empty",
        }
        with tempfile.TemporaryDirectory() as temp:
            config_path = Path(temp) / "config.json"
            output_path = Path(temp) / "site" / "index.html"
            config_path.write_text(json.dumps(config), encoding="utf-8")
            build_index_html(tracks, config_file=config_path, output_path=output_path)
            page = output_path.read_text(encoding="utf-8")

        self.assertIn('style="--filter-color: #d8d34a;"', page)
        self.assertIn('class="p53-broadcast"', page)
        self.assertNotIn("Current transmission", page)

    def test_p53_archive_uses_factors_active_previous_without_open_cta(self):
        history = [
            {"artist": "Metric", "track": "Empty", "album": "Live It Out", "slug": "metric-empty", "cover_file": ""},
            {"artist": "Wet Leg", "track": "mangetout", "album": "Moisturizer", "slug": "wet-leg-mangetout", "cover_file": ""},
        ]
        with tempfile.TemporaryDirectory() as temp:
            output_dir = Path(temp) / "site" / "p53"
            output_dir.mkdir(parents=True)
            build_p53_archive(history, "metric-empty", output_dir=output_dir)
            page = (output_dir / "index.html").read_text(encoding="utf-8")

        self.assertIn("02 FACTORS", page)
        self.assertIn('aria-label="Radio P53 factors"', page)
        self.assertIn('<span class="signal-state">ACTIVE</span>', page)
        self.assertIn('<span class="signal-state">PREVIOUS</span>', page)
        self.assertNotIn("TRANSMISSIONS", page)
        self.assertNotIn("Open transmission", page)

    def test_p53_factor_page_renders_unlabelled_note_album_link_and_entry_companion(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config_path = root / "config.json"
            output_dir = root / "site" / "p53"
            entries_dir = root / "entries"
            output_dir.mkdir(parents=True)
            entries_dir.mkdir(parents=True)
            (entries_dir / "wet-leg-mangetout.md").write_text(
                "---\nartist: Wet Leg\ntrack: mangetout\nalbum: Moisturizer\n---\n"
                "# mangetout — Wet Leg\n\n"
                "## Charge\n\n<!-- prompt -->\n\n"
                "## Sonical Attraction\n\nThe vocal carries dry humor into the chorus.\n\n"
                "## Reading\n\nWordplay over green beans.\n",
                encoding="utf-8",
            )
            config_path.write_text(
                json.dumps({
                    "filters": {},
                    "p53_history": [
                        {"artist": "Wet Leg", "track": "mangetout", "album": "Moisturizer", "slug": "wet-leg-mangetout"},
                        {"artist": "Metric", "track": "Empty", "album": "Live It Out", "slug": "metric-empty"},
                    ],
                    "p53_current_slug": "metric-empty",
                    "p53_transmission_notes": {
                        "wet-leg-mangetout": "Bienvenue.",
                    },
                }),
                encoding="utf-8",
            )
            album_routes = {("Wet Leg", "Moisturizer"): "albums/wet-leg-moisturizer.html"}

            build_p53_page(
                {
                    "artist": "Wet Leg",
                    "track": "mangetout",
                    "album": "Moisturizer",
                    "slug": "wet-leg-mangetout",
                    "accent": "#6f4730",
                },
                "wet-leg-mangetout.html",
                {"wet-leg-mangetout", "metric-empty"},
                {"wet-leg"},
                album_routes=album_routes,
                config_file=config_path,
                output_dir=output_dir,
                entries_dir=entries_dir,
            )
            previous_page = (output_dir / "wet-leg-mangetout.html").read_text(encoding="utf-8")

            # Sparse/missing markdown file with entry_slugs present should still succeed cleanly.
            build_p53_page(
                {
                    "artist": "Metric",
                    "track": "Empty",
                    "album": "Live It Out",
                    "slug": "metric-empty",
                    "accent": "#ff4fa3",
                },
                "metric-empty.html",
                {"metric-empty"},
                {"metric"},
                album_routes=album_routes,
                config_file=config_path,
                output_dir=output_dir,
                entries_dir=entries_dir,
            )
            active_sparse_page = (output_dir / "metric-empty.html").read_text(encoding="utf-8")

        prev_ctx = json.loads(
            re.search(
                r'<script id="p53-transmission-context" type="application/json">(.*?)</script>',
                previous_page,
                re.DOTALL,
            ).group(1)
        )
        active_ctx = json.loads(
            re.search(
                r'<script id="p53-transmission-context" type="application/json">(.*?)</script>',
                active_sparse_page,
                re.DOTALL,
            ).group(1)
        )

        self.assertEqual(prev_ctx["signalLabel"], "PREVIOUS")
        self.assertIn('<div class="transmission-note" dir="auto"><p>Bienvenue.</p></div>', previous_page)
        self.assertNotIn("A note", previous_page)
        self.assertIn('<a class="album-link" href="../albums/wet-leg-moisturizer.html">Moisturizer</a>', previous_page)
        self.assertIn('class="entry-counterpart entry-card-companion"', previous_page)
        self.assertIn('href="../entries/wet-leg-mangetout.html"', previous_page)
        self.assertIn('aria-label="Open entry: mangetout"', previous_page)
        self.assertIn('--accent:#6f4730;--art-primary:', previous_page)
        self.assertIn('<span>Sonical Attraction</span><span>Reading</span>', previous_page)
        self.assertIn('The vocal carries dry humor into the chorus.', previous_page)
        self.assertIn('<span class="entry-card-cta" aria-hidden="true">↗</span>', previous_page)
        self.assertNotIn("Read the entry", previous_page)

        self.assertEqual(active_ctx["signalLabel"], "ACTIVE")
        self.assertIn('class="entry-counterpart entry-card-companion"', active_sparse_page)
        self.assertIn('aria-label="Open entry: Empty"', active_sparse_page)
        self.assertIn('<span class="entry-card-cta" aria-hidden="true">↗</span>', active_sparse_page)
        self.assertNotIn("Read the entry", active_sparse_page)
        self.assertNotIn("entry-card-sections", active_sparse_page)
        self.assertNotIn('<a class="album-link"', active_sparse_page)

    def test_entry_page_omits_entry_index_and_renders_p53_companion_card(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            entries_dir = root / "entries"
            output_dir = root / "site" / "entries"
            entries_dir.mkdir(parents=True)
            for slug, track in (("metric-empty", "Empty"), ("metric-combat-baby", "Combat Baby")):
                (entries_dir / f"{slug}.md").write_text(
                    f"---\nartist: Metric\ntrack: {track}\nalbum: Live It Out\n---\n"
                    f"# {track} — Metric\n\n## Charge\n\nA stored feeling.\n\n"
                    "## Sonical Attraction\n\nA sharp pulse.\n\n## Lore\n\nA place in time.\n",
                    encoding="utf-8",
                )
            config_path = root / "config.json"
            config_path.write_text(
                json.dumps({
                    "filters": {},
                    "section_info": {},
                    "p53_history": [
                        {"artist": "Metric", "track": "Empty", "album": "Live It Out", "slug": "metric-empty"}
                    ],
                    "p53_current_slug": "metric-empty",
                    "p53_transmission_notes": {"metric-empty": "Held on loop **all** week."},
                }),
                encoding="utf-8",
            )
            build_entry_page(
                {
                    "artist": "Metric",
                    "track": "Empty",
                    "album": "Live It Out",
                    "slug": "metric-empty",
                    "entry_file": "metric-empty.md",
                    "html_file": "metric-empty.html",
                    "cover_file": "",
                    "accent": "#ff4fa3",
                    "tags": "personal,p53",
                },
                config_file=config_path,
                entries_dir=entries_dir,
                output_dir=output_dir,
            )
            build_entry_page(
                {
                    "artist": "Metric",
                    "track": "Combat Baby",
                    "album": "Live It Out",
                    "slug": "metric-combat-baby",
                    "entry_file": "metric-combat-baby.md",
                    "html_file": "metric-combat-baby.html",
                    "cover_file": "",
                    "accent": "#eaff26",
                    "tags": "personal",
                },
                config_file=config_path,
                entries_dir=entries_dir,
                output_dir=output_dir,
            )
            p53_entry = (output_dir / "metric-empty.html").read_text(encoding="utf-8")
            plain_entry = (output_dir / "metric-combat-baby.html").read_text(encoding="utf-8")

        self.assertNotIn('class="entry-index"', p53_entry)
        self.assertIn('class="section-card" id="section-charge"', p53_entry)
        self.assertIn('class="p53-counterpart p53-card-companion"', p53_entry)
        self.assertIn('data-base-href="../p53/metric-empty.html"', p53_entry)
        self.assertIn('aria-label="Radio P53: Empty"', p53_entry)
        self.assertIn('<div class="p53-card-art"><img src="../covers/P53_cover-runtime.webp"', p53_entry)
        self.assertIn('<span class="p53-card-kicker">RADIO P53</span>', p53_entry)
        self.assertIn('<strong class="p53-card-title">Empty</strong>', p53_entry)
        self.assertIn('<p class="p53-card-note">Held on loop all week.</p>', p53_entry)
        self.assertIn('<span class="p53-card-cta" aria-hidden="true">↗</span>', p53_entry)
        self.assertNotIn("Current on Radio P53", p53_entry)

        self.assertNotIn('class="p53-card-companion"', plain_entry)


if __name__ == "__main__":
    unittest.main()
