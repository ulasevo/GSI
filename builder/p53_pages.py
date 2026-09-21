"""Radio P53 page renderers.

P53 has two related but distinct surfaces: the continuous landing page and the
permanent transmission page. Their data is prepared elsewhere; this module only
turns prepared records into HTML and receives all output paths explicitly.
"""

import html
import json
from pathlib import Path

from gsi_data import load_config
from gsi_assets import artwork_palette, palette_style
from gsi_text import make_streaming_links, simple_markdown_to_html, slugify
from builder.template_renderer import render_template


def _default_base() -> Path:
    return Path(__file__).resolve().parent.parent


def _p53_art_context(config: dict, base: Path) -> tuple[dict[str, str], str]:
    """Return the playlist artwork palette and a style string for P53 rooms."""
    settings = config.get("p53") or {}
    cover_value = str(settings.get("playlist_cover") or "covers/P53_cover.jpg").strip()
    cover_path = base / cover_value
    palette = artwork_palette(cover_path, "#ff65ad")
    browser_cover = cover_value.replace("\\", "/")
    if browser_cover.startswith("covers/"):
        browser_cover = "../" + browser_cover
    style = (
        f'--accent:{palette.get("primary", "#ff65ad")};'
        f'--p53-accent:{palette.get("primary", "#ff65ad")};'
        f'{palette_style(palette, browser_cover)}'
    )
    return palette, style


# Permanent transmissions receive one prepared context object for routing and
# sharing; the template remains a simple layout skeleton.
def build_p53_page(
    item: dict,
    output_name: str,
    entry_slugs: set[str] | None = None,
    artist_slugs: set[str] | None = None,
    *,
    config_file: Path | None = None,
    output_dir: Path | None = None,
    entries_dir: Path | None = None,
) -> None:
    """Build one permanent P53 transmission from explicitly editable P53 copy."""
    base = _default_base()
    config_file = config_file or base / "config.json"
    output_dir = output_dir or base / "site" / "p53"
    entries_dir = entries_dir or base / "entries"
    config = load_config(config_file)
    p53_palette, p53_style = _p53_art_context(config, base)
    signal_label = "CURRENT TRANSMISSION" if item["slug"] == (config.get("p53_current_slug") or "").strip() else "PAST TRANSMISSION"
    artist_slug = slugify(item["artist"])
    has_artist_room = artist_slug in (artist_slugs or set())
    artist_display = (
        f'<a class="artist-link" href="../artists/{artist_slug}.html">{html.escape(item["artist"])}</a>'
        if has_artist_room else html.escape(item["artist"])
    )
    p53_context_json = json.dumps({
        "filterLabels": {key: settings.get("label", key) for key, settings in config.get("filters", {}).items()},
        "expectedArtistRoute": slugify(item["artist"]),
        "artistName": item["artist"],
        "hasArtistRoom": has_artist_room,
        "shareTitle": f"Radio P53 — {item['track']}",
        "accent": str(p53_palette.get("primary") or item.get("accent") or "#ff65ad"),
        "signalLabel": signal_label,
    }, ensure_ascii=False).replace("</", "<\\/")
    site_url = (config.get("site_url") or "").rstrip("/")
    p53_permalink = f"{site_url}/p53/{item['slug']}.html" if site_url else ""
    p53_description = f"Radio P53 transmission: {item['track']} by {item['artist']}."
    sharing_meta = ""
    if p53_permalink:
        sharing_meta = f'''\n    <link rel="canonical" href="{html.escape(p53_permalink, quote=True)}">
    <meta property="og:url" content="{html.escape(p53_permalink, quote=True)}">
    <meta property="og:type" content="website">
    <meta property="og:site_name" content="GSI / Radio P53">
    <meta property="og:title" content="{html.escape(f'Radio P53 — {item["track"]}', quote=True)}">
    <meta property="og:description" content="{html.escape(p53_description, quote=True)}">
    <meta property="og:image" content="{html.escape(site_url + '/covers/P53_cover.jpg', quote=True)}">
    <meta name="twitter:card" content="summary_large_image">'''
    about_text = (config.get("p53_about") or "").strip()
    transmission_note = str((config.get("p53_transmission_notes") or {}).get(item["slug"], "")).strip()
    cover_src = f'../covers/{item["cover_file"]}' if item.get("cover_file") else ""
    art_style = html.escape(p53_style, quote=True)
    cover_html = f'<img class="signal-cover" src="{cover_src}" alt="{html.escape(item["album"], quote=True)} cover" loading="eager" fetchpriority="high" decoding="async">' if cover_src else ""
    note_html = (
        f'<section class="transmission-note"><h2>TRANSMISSION NOTES</h2>{simple_markdown_to_html(transmission_note)}</section>'
        if transmission_note else ""
    )
    entry_counterpart_html = ""
    has_entry = item["slug"] in entry_slugs if entry_slugs is not None else (entries_dir / f'{item["slug"]}.md').exists()
    if has_entry:
        entry_counterpart_html = f'<a class="entry-counterpart" href="../entries/{html.escape(item["slug"], quote=True)}.html">INSIDE GSI / READ ENTRY ↗</a>'
    html_page = render_template(
        "p53-transmission.html",
        {
            "p53_description": html.escape(p53_description, quote=True),
            "sharing_meta": sharing_meta,
            "p53_title": html.escape(f'P53 — {item["track"]}'),
            "signal_label": html.escape(signal_label),
            "cover_html": cover_html,
            "track": html.escape(item["track"]),
            "artist": artist_display,
            "album": html.escape(item["album"]),
            "streaming_links_html": make_streaming_links(item),
            "entry_counterpart_html": entry_counterpart_html,
            "about_text": html.escape(about_text),
            "note_html": note_html,
            "p53_context_json": p53_context_json,
            "art_style": art_style,
        },
    )
    output_path = output_dir / output_name
    output_path.write_text(html_page, encoding="utf-8")
    print(f"Built P53 transmission: {output_path}")


def build_p53_archive(
    history: list[dict],
    current_slug: str,
    filter_labels: dict[str, str] | None = None,
    artist_slugs: set[str] | None = None,
    *,
    output_dir: Path | None = None,
) -> None:
    """Build the Radio P53 landing page as a readable, continuous field."""
    # Keep the live signal first, then let ordinary document scrolling reveal
    # historical signals without inventing episode numbers.
    output_dir = output_dir or _default_base() / "site" / "p53"
    base = _default_base()
    config = load_config(base / "config.json")
    _p53_palette, p53_style = _p53_art_context(config, base)
    current = next((item for item in history if item["slug"] == current_slug), None)
    remaining = [item for item in history if item["slug"] != current_slug]
    if current is None and remaining:
        current, remaining = remaining[0], remaining[1:]
    transmissions = [current, *remaining] if current else remaining

    # Only the first image is eager; later covers can wait until the reader gets
    # near them.
    def cover(item: dict, eager: bool = False) -> str:
        if item.get("cover_file"):
            loading = 'loading="eager" fetchpriority="high" decoding="async"' if eager else 'loading="lazy" decoding="async"'
            return f'<img src="../covers/{html.escape(item["cover_file"], quote=True)}" alt="{html.escape(item["album"], quote=True)} cover" {loading}>'
        return '<div class="cover-missing" aria-hidden="true">P53</div>'

    def transmission_card(item: dict, index: int) -> str:
        number = str(index + 1).zfill(2)
        state = "CURRENT TRANSMISSION" if index == 0 else "PAST TRANSMISSION"
        current_class = " is-current" if index == 0 else ""
        current_attr = 'aria-current="true"' if index == 0 else ""
        palette = html.escape(p53_style, quote=True)
        return f'''<li class="transmission-card{current_class}" id="signal-{number}" data-index="{index}" style="{palette}">
    <a class="transmission-card-link" {current_attr} data-base-href="{html.escape(item["slug"], quote=True)}.html" href="{html.escape(item["slug"], quote=True)}.html">
        <div class="transmission-art">{cover(item, eager=index == 0)}</div>
        <div class="transmission-copy"><div class="copy-content"><span class="signal-state">{state}</span><h2>{html.escape(item["track"])}</h2><p>{html.escape(item["artist"])}</p><small>{html.escape(item["album"])}</small><b>ENTER TRANSMISSION ↗</b></div></div>
    </a>
</li>'''

    cards_html = "".join(transmission_card(item, index) for index, item in enumerate(transmissions))
    landing_context = json.dumps({
        "filterLabels": filter_labels or {},
        "artistSlugs": sorted(artist_slugs or set()),
    }, ensure_ascii=False).replace("</", "<\\/")
    page = render_template(
        "p53-landing.html",
        {
            "transmission_count": str(len(transmissions)).zfill(2),
            "cards_html": cards_html,
            "landing_context": landing_context,
            "p53_style": html.escape(p53_style, quote=True),
        },
    )
    output_path = output_dir / "index.html"
    output_path.write_text(page, encoding="utf-8")
    print(f"Built Radio P53 landing: {output_path}")
