"""Radio P53 page renderers.

P53 has two related but distinct surfaces: the continuous landing page and the
permanent transmission page. Their data is prepared elsewhere; this module only
turns prepared records into HTML and receives all output paths explicitly.
"""

import html
import json
from pathlib import Path

from gsi_data import current_p53_slug, load_config
from gsi_assets import artwork_palette, image_size_attrs, palette_style
from gsi_text import make_streaming_links, simple_markdown_to_html, slugify
from builder.entry_pages import excerpt_text, extract_sections_from_markdown, p53_art_context
from builder.template_renderer import render_template


def _default_base() -> Path:
    return Path(__file__).resolve().parent.parent


def _build_entry_companion_html(
    item: dict,
    track_palette: dict[str, str],
    track_accent: str,
    cover_src: str,
    entries_dir: Path,
    entry_slugs: set[str] | None,
) -> str:
    """Render a track-themed companion card when an entry exists for this factor."""
    entry_path = entries_dir / f'{item["slug"]}.md'
    has_entry = item["slug"] in entry_slugs if entry_slugs is not None else entry_path.is_file()
    if not has_entry:
        return ""
    sections: list[dict] = []
    if entry_path.is_file():
        try:
            sections = [
                section
                for section in extract_sections_from_markdown(entry_path)
                if str(section.get("content") or "").strip()
            ]
        except OSError:
            sections = []
    sections_html = ""
    excerpt_html = ""
    if sections:
        section_pills = "".join(
            f'<span>{html.escape(str(section["title"]))}</span>'
            for section in sections
        )
        sections_html = f'<div class="entry-card-sections">{section_pills}</div>'
        excerpt = excerpt_text(str(sections[0]["content"]))
        if excerpt:
            excerpt_html = f'<p class="entry-card-excerpt">{html.escape(excerpt)}</p>'
    track_card_style = html.escape(
        f'--accent:{track_accent};{palette_style(track_palette, cover_src)}',
        quote=True,
    )
    track_aria = html.escape(f'Open entry: {item["track"]}', quote=True)
    return (
        f'<a class="entry-counterpart entry-card-companion" '
        f'href="../entries/{html.escape(item["slug"], quote=True)}.html" '
        f'aria-label="{track_aria}" '
        f'style="{track_card_style}">'
        f'<div class="entry-card-header">'
        f'<span class="entry-card-kicker">Entry</span>'
        f'<strong class="entry-card-title">{html.escape(item["track"])}</strong>'
        f'</div>'
        f'{sections_html}'
        f'{excerpt_html}'
        f'<span class="entry-card-cta" aria-hidden="true">↗</span>'
        f'</a>'
    )


def _p53_art_context(config: dict, base: Path) -> tuple[dict[str, str], str]:
    """Return the playlist artwork palette and a style string for P53 rooms."""
    return p53_art_context(config, base)


# Permanent transmissions receive one prepared context object for routing and
# sharing; the template remains a simple layout skeleton.
def build_p53_page(
    item: dict,
    output_name: str,
    entry_slugs: set[str] | None = None,
    artist_slugs: set[str] | None = None,
    album_routes: dict[tuple[str, str], str] | None = None,
    *,
    config_file: Path | None = None,
    output_dir: Path | None = None,
    entries_dir: Path | None = None,
) -> None:
    """Build one permanent P53 factor page from explicitly editable P53 copy."""
    base = _default_base()
    config_file = config_file or base / "config.json"
    output_dir = output_dir or base / "site" / "p53"
    entries_dir = entries_dir or base / "entries"
    config = load_config(config_file)
    p53_palette, p53_style = _p53_art_context(config, base)
    signal_label = "ACTIVE" if item["slug"] == current_p53_slug(config, config.get("p53_history", [])) else "PREVIOUS"
    artist_slug = slugify(item["artist"])
    has_artist_room = artist_slug in (artist_slugs or set())
    artist_display = (
        f'<a class="artist-link" href="../artists/{artist_slug}.html">{html.escape(item["artist"])}</a>'
        if has_artist_room else html.escape(item["artist"])
    )
    album_route = (album_routes or {}).get((item.get("artist", ""), item.get("album", "")))
    if album_route:
        album_href = album_route if album_route.startswith("../") else f"../{album_route.lstrip('/')}"
        album_display = (
            f'<a class="album-link" href="{html.escape(album_href, quote=True)}">'
            f'{html.escape(item["album"])}</a>'
        )
    else:
        album_display = html.escape(item["album"])
    about_text = (config.get("p53_about") or "").strip()
    transmission_note = str((config.get("p53_transmission_notes") or {}).get(item["slug"], "")).strip()
    cover_src = f'../covers/{item["cover_file"]}' if item.get("cover_file") else ""
    track_cover_file = item.get("cover_file")
    track_cover_path = base / "covers" / track_cover_file if track_cover_file else None
    track_palette = (
        artwork_palette(track_cover_path, fallback=item.get("accent") or "#ff65ad")
        if track_cover_path and track_cover_path.is_file()
        else artwork_palette(Path("__missing_artwork__.jpg"), fallback=item.get("accent") or "#ff65ad")
    )
    track_accent = str(item.get("accent") or track_palette.get("primary") or "#ff65ad")
    p53_accent = str(p53_palette.get("primary") or "#ff65ad")
    p53_context_json = json.dumps({
        "filterLabels": {key: settings.get("label", key) for key, settings in config.get("filters", {}).items()},
        "expectedArtistRoute": slugify(item["artist"]),
        "artistName": item["artist"],
        "hasArtistRoom": has_artist_room,
        "shareTitle": f"Radio P53 — {item['track']}",
        "accent": str(p53_palette.get("primary") or item.get("accent") or "#ff65ad"),
        "trackAccent": track_accent,
        "p53Accent": p53_accent,
        "cyanAccent": "#35c9e9",
        "trackPalette": {
            "primary": track_palette.get("primary", track_accent),
            "secondary": track_palette.get("secondary", "#8a8292"),
            "glow": track_palette.get("glow", "#6d6475"),
            "field": track_palette.get("field", "#120c18"),
            "soft": track_palette.get("soft", "#d4c8db"),
            "surface": track_palette.get("surface", "#16111c"),
            "ink": track_palette.get("ink", "#f8f5ef"),
        },
        "signalLabel": signal_label,
        "track": item["track"],
        "album": item["album"],
        "slug": item["slug"],
        "coverSrc": cover_src,
        "p53CoverSrc": "../covers/P53_cover-runtime.webp",
        "transmissionNote": transmission_note,
    }, ensure_ascii=False).replace("</", "<\\/")
    site_url = (config.get("site_url") or "").rstrip("/")
    p53_permalink = f"{site_url}/p53/{item['slug']}.html" if site_url else ""
    p53_description = f"Radio P53 transmission: {item['track']} by {item['artist']}."
    sharing_meta = ""
    if p53_permalink:
        og_asset = "/covers/P53_cover-og.jpg" if (base / "covers" / "P53_cover.jpg").is_file() else "/covers/P53_cover-runtime.webp"
        sharing_meta = f'''\n    <link rel="canonical" href="{html.escape(p53_permalink, quote=True)}">
    <meta property="og:url" content="{html.escape(p53_permalink, quote=True)}">
    <meta property="og:type" content="website">
    <meta property="og:site_name" content="Chaperone / Radio P53">
    <meta property="og:title" content="{html.escape(f'Radio P53 — {item["track"]}', quote=True)}">
    <meta property="og:description" content="{html.escape(p53_description, quote=True)}">
    <meta property="og:image" content="{html.escape(site_url + og_asset, quote=True)}">
    <meta name="twitter:card" content="summary_large_image">'''
    art_style = html.escape(p53_style, quote=True)
    cover_size_attrs = image_size_attrs(track_cover_path) if cover_src else ""
    cover_html = f'<img class="signal-cover" src="{html.escape(cover_src, quote=True)}" alt="{html.escape(item["album"], quote=True)} cover" loading="eager" fetchpriority="high" decoding="async" {cover_size_attrs}>' if cover_src else '<div class="cover-missing signal-cover" aria-hidden="true"></div>'
    note_html = (
        f'<div class="transmission-note" dir="auto">{simple_markdown_to_html(transmission_note)}</div>'
        if transmission_note else ""
    )
    entry_counterpart_html = _build_entry_companion_html(
        item,
        track_palette,
        track_accent,
        cover_src,
        entries_dir,
        entry_slugs,
    )
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
            "album": album_display,
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
        current, remaining = remaining[-1], remaining[:-1]
    remaining = list(reversed(remaining))
    transmissions = [current, *remaining] if current else remaining

    # Only the first image is eager; later covers can wait until the reader gets
    # near them.
    def cover(item: dict, eager: bool = False) -> str:
        if item.get("cover_file"):
            loading = 'loading="eager" fetchpriority="high" decoding="async"' if eager else 'loading="lazy" decoding="async"'
            size_attrs = image_size_attrs(base / "covers" / item["cover_file"])
            return f'<img src="../covers/{html.escape(item["cover_file"], quote=True)}" alt="{html.escape(item["album"], quote=True)} cover" {loading} {size_attrs}>'
        return '<div class="cover-missing" aria-hidden="true">P53</div>'

    transmission_notes = config.get("p53_transmission_notes", {})

    def transmission_card(item: dict, index: int) -> str:
        number = str(index + 1).zfill(2)
        state = "ACTIVE" if index == 0 else "PREVIOUS"
        current_class = " is-current" if index == 0 else ""
        current_attr = 'aria-current="true"' if index == 0 else ""
        note = str(transmission_notes.get(item["slug"], "")).strip()
        note_html = f'<blockquote class="transmission-intercept">“{html.escape(note)}”</blockquote>' if note else ""
        return f'''<li class="transmission-card{current_class}" id="signal-{number}" data-index="{index}">
    <a class="transmission-card-link" {current_attr} data-base-href="{html.escape(item["slug"], quote=True)}.html" href="{html.escape(item["slug"], quote=True)}.html">
        <div class="transmission-art">{cover(item, eager=index == 0)}</div>
        <div class="transmission-copy"><span class="transmission-arrow" aria-hidden="true"><svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M4.5 11.5 11.5 4.5M6 4.5h5.5V10"/></svg></span><div class="copy-content"><span class="signal-state">{state}</span><h2>{html.escape(item["track"])}</h2><p>{html.escape(item["artist"])}</p><small>{html.escape(item["album"])}</small>{note_html}</div></div>
    </a>
</li>'''

    cards_html = "".join(transmission_card(item, index) for index, item in enumerate(transmissions))
    landing_context = json.dumps({
        "filterLabels": filter_labels or {},
        "artistSlugs": sorted(artist_slugs or set()),
    }, ensure_ascii=False).replace("</", "<\\/")
    total_factors = len(transmissions)
    count_label = f"{total_factors:,}" if total_factors >= 1000 else str(total_factors).zfill(2)
    page = render_template(
        "p53-landing.html",
        {
            "transmission_count": count_label,
            "factor_unit": "FACTOR" if total_factors == 1 else "FACTORS",
            "cards_html": cards_html,
            "landing_context": landing_context,
            "p53_style": html.escape(p53_style, quote=True),
        },
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "index.html"
    output_path.write_text(page, encoding="utf-8")
    print(f"Built Radio P53 landing: {output_path}")
