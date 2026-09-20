"""Generated artist and album room renderers.

These renderers keep the current GSI markup stable while making catalogue-page
ownership explicit.  The compatibility build facade supplies no hidden state;
callers may pass output/config directories when exercising the renderer.
"""

import html
import json
from pathlib import Path

from gsi_artists import artist_image_markup, resolve_artist_asset
from gsi_assets import artwork_palette, palette_style
from gsi_data import load_config
from gsi_text import simple_markdown_to_html, slugify
from builder.template_renderer import render_template


BASE = Path(__file__).resolve().parents[1]
CONFIG_FILE = BASE / "config.json"
SITE_DIR = BASE / "site"
SITE_ARTISTS_DIR = SITE_DIR / "artists"
SITE_ALBUMS_DIR = SITE_DIR / "albums"
ARTIST_ASSETS_DIR = BASE / "artist-assets"


# Artist rooms own the artist-level hierarchy: optional art, album groups, then
# the remaining song or transmission links.
def build_artist_pages(
    artist_groups: dict[str, list[dict]],
    config: dict | None = None,
    *,
    output_dir: Path | None = None,
    artist_assets_dir: Path | None = None,
) -> None:
    """Create artist rooms from one shared catalogue-eligibility inventory."""
    artist_config = config or load_config(CONFIG_FILE)
    artists_dir = Path(output_dir) if output_dir is not None else SITE_ARTISTS_DIR
    assets_dir = Path(artist_assets_dir) if artist_assets_dir is not None else ARTIST_ASSETS_DIR
    artists_dir.mkdir(parents=True, exist_ok=True)
    artist_notes = artist_config.get("artist_notes", {})
    album_notes = artist_config.get("album_notes", {})
    for artist, artist_tracks in artist_groups.items():
        artist_slug = slugify(artist)
        artist_asset = resolve_artist_asset(artist, artist_config, assets_dir)
        artist_image_html = artist_image_markup(artist_asset, artist)
        artist_palette = (artist_tracks[0].get("palette") if artist_tracks else None) or artwork_palette(Path("__missing_artwork__.jpg"), "#49d9ef")
        artist_image_src = f'../artist-assets/{artist_asset["file"]}' if artist_asset.get("file") else ""
        artist_heading_class = "artist-heading has-artist-image" if artist_image_html else "artist-heading"
        note = str(artist_notes.get(artist, "")).strip()
        note_html = f'<div class="artist-note">{simple_markdown_to_html(note)}</div>' if note else ""
        albums: dict[str, list[dict]] = {}
        for item in artist_tracks:
            albums.setdefault(item["album"], []).append(item)
        grouped_albums = [(album, items) for album, items in albums.items() if len(items) >= 2]
        grouped_slugs = {item["slug"] for _, items in grouped_albums for item in items}

        # Keep the base route separate from its query-state decoration. The
        # browser helper can then preserve the path that led to this room.
        def entry_href(item: dict) -> str:
            if item.get("p53_only"):
                return f'../p53/{html.escape(item["slug"], quote=True)}.html?artist={artist_slug}'
            return f'../entries/{html.escape(item["html_file"], quote=True)}?artist={artist_slug}'

        def entry_base_href(item: dict) -> str:
            if item.get("p53_only"):
                return f'../p53/{html.escape(item["slug"], quote=True)}.html'
            return f'../entries/{html.escape(item["html_file"], quote=True)}'

        def entry_tile(item: dict, compact: bool = False) -> str:
            transmission_label = "P53 ↗" if item.get("p53_only") else "OPEN ↗"
            entry_kind = ' data-entry-kind="transmission"' if item.get("p53_only") else ""
            if compact:
                # The album stack owns its cover; nested track rows stay text-first.
                return f'''<a class="album-entry"{entry_kind} data-entry-base-href="{entry_base_href(item)}" href="{entry_href(item)}" style="--accent:{item["accent"]}">
                    <span class="album-entry-mark" aria-hidden="true"></span><h3>{html.escape(item["track"])}</h3><b>{transmission_label}</b>
                </a>'''
            state = "P53 TRANSMISSION" if item.get("p53_only") else html.escape(item["album"])
            return f'''<a class="artist-signal" data-entry-base-href="{entry_base_href(item)}" href="{entry_href(item)}" style="--accent:{item["accent"]}">
                <img src="../covers/{html.escape(item["cover_file"], quote=True)}" alt="{html.escape(item["album"], quote=True)} cover">
                <div><h2>{html.escape(item["track"])}</h2><p>{html.escape(item["artist"])}</p><small>{state}</small></div><b>{transmission_label}</b>
            </a>'''

        # Albums are grouped only when two or more represented signals share the
        # same artist and album. Their nested rows stay text-first on purpose.
        album_sections = []
        for album, items in grouped_albums:
            album_href = f'../albums/{slugify(f"{artist}-{album}")}.html'
            album_title_link = (
                f'<a class="album-title-link" data-context-base-href="{html.escape(album_href, quote=True)}" '
                f'href="{html.escape(album_href, quote=True)}">{html.escape(album)}</a>'
            )
            album_note = str(album_notes.get(artist, {}).get(album, "")).strip()
            album_note_html = f'<div class="album-note-preview">{simple_markdown_to_html(album_note)}</div>' if album_note else ""
            album_sections.append(f'''<section class="album-stack" style="--accent:{items[0]["accent"]}">
                <header><img src="../covers/{html.escape(items[0]["cover_file"], quote=True)}" alt="{html.escape(album, quote=True)} cover"><div style="min-width:0"><span style="display:block;margin-bottom:6px;color:color-mix(in srgb,var(--accent),white 24%);font-size:9px;font-weight:950;letter-spacing:.18em">ALBUM</span><h2>{album_title_link}</h2>{album_note_html}</div></header>
                <div>{''.join(entry_tile(item, compact=True) for item in items)}</div>
            </section>''')
        albums_html = "".join(album_sections)
        remaining_html = "".join(entry_tile(item) for item in artist_tracks if item["slug"] not in grouped_slugs)
        artist_room_data = json.dumps(
            {
                "filterKeys": list(artist_config.get("filters", {}).keys()),
                "filterLabels": {
                    key: value.get("label", key)
                    for key, value in artist_config.get("filters", {}).items()
                },
                "artistSlug": artist_slug,
            },
            ensure_ascii=False,
        ).replace("</", "<\\/")
        page = render_template(
            "artist.html",
            {
                "artist": html.escape(artist),
                "artist_upper": html.escape(artist).upper(),
                "artist_heading_class": artist_heading_class,
                "artist_count": f"{len(artist_tracks):02d}",
                "note_html": note_html,
                "artist_image_html": artist_image_html,
                "albums_html": albums_html,
                "remaining_html": remaining_html,
                "artist_room_data": artist_room_data,
                "art_style": html.escape(palette_style(artist_palette, artist_image_src), quote=True),
            },
        )
        # Load the colour-field layer after the room's base stylesheet.  Keeping
        # this explicit avoids relying on CSS @import ordering in mobile browsers.
        page = page.replace(
            "</head>",
            '<link rel="stylesheet" href="../styles/artist-art.css?v=20260919-contrast"></head>',
            1,
        )
        output_path = artists_dir / f"{artist_slug}.html"
        output_path.write_text(page, encoding="utf-8")
        print(f"Built artist room: {output_path}")


def build_album_pages(
    tracks: list[dict],
    artist_groups: dict[str, list[dict]] | None = None,
    album_routes: dict[tuple[str, str], str] | None = None,
    *,
    output_dir: Path | None = None,
) -> None:
    """Build a focused room for albums represented by at least two signals."""
    # Album rooms are generated from the shared route inventory so an album link
    # cannot appear unless the corresponding page is actually written.
    config = load_config(CONFIG_FILE)
    albums_dir = Path(output_dir) if output_dir is not None else SITE_ALBUMS_DIR
    albums_dir.mkdir(parents=True, exist_ok=True)
    notes = config.get("album_notes", {})
    grouped: dict[tuple[str, str], list[dict]] = {}
    for item in tracks:
        grouped.setdefault((item["artist"], item["album"]), []).append(item)
    for (artist, album), items in grouped.items():
        if len(items) < 2:
            continue
        route = (album_routes or {}).get((artist, album))
        slug = slugify(f"{artist}-{album}")
        if album_routes is not None and not route:
            continue
        accent = items[0]["accent"]
        art_style = html.escape(
            palette_style(items[0].get("palette") or artwork_palette(Path("__missing_artwork__.jpg"), accent), f'../covers/{items[0].get("cover_file", "")}'),
            quote=True,
        )
        artist_room_exists = artist in (artist_groups or {}) if artist_groups is not None else sum(1 for item in tracks if item.get("artist") == artist) >= 2
        artist_href = f"../artists/{slugify(artist)}.html"
        artist_nav = (
            f'<a id="album-artist-return" class="artist-link" data-artist-base-href="{html.escape(artist_href, quote=True)}" href="{html.escape(artist_href, quote=True)}">{html.escape(artist.upper())}</a>'
            if artist_room_exists else f'<strong>{html.escape(artist.upper())}</strong>'
        )
        artist_display = (
            f'<a class="artist-link" data-artist-base-href="{html.escape(artist_href, quote=True)}" href="{html.escape(artist_href, quote=True)}">{html.escape(artist)}</a>'
            if artist_room_exists else html.escape(artist)
        )
        cover = items[0].get("cover_file", "")
        cover_html = f'<img class="album-cover" src="../covers/{html.escape(cover, quote=True)}" alt="{html.escape(album, quote=True)} cover">' if cover else ""
        song_links = []
        for item in items:
            target = item.get("page_url") or f'entries/{item["html_file"]}'
            song_links.append(f'<a class="album-song" data-entry-base-href="../{html.escape(target, quote=True)}" href="../{html.escape(target, quote=True)}"><span>{html.escape(item["track"])}</span><b>OPEN ↗</b></a>')
        note = str(notes.get(artist, {}).get(album, "")).strip()
        note_html = f'<section class="album-note"><span>MY TAKE</span>{simple_markdown_to_html(note)}</section>' if note else ""
        album_room_data = json.dumps(
            {"filterKeys": list(config.get("filters", {}).keys())},
            ensure_ascii=False,
        ).replace("</", "<\\/")
        page = render_template(
            "album.html",
            {
                "album": html.escape(album),
                # The breadcrumb is a title, not an operational label: preserve
                # the source's exact album casing here as well as in the hero.
                "album_upper": html.escape(album),
                "accent": html.escape(str(accent), quote=True),
                "artist_nav": artist_nav,
                "cover_html": cover_html,
                "signal_count": f"{len(items):02d}",
                "artist_display": artist_display,
                "note_html": note_html,
                "song_links_html": "".join(song_links),
                "album_room_data": album_room_data,
                "art_style": art_style,
            },
        )
        # Load the colour-field layer after the room's base stylesheet.  Keeping
        # this explicit avoids relying on CSS @import ordering in mobile browsers.
        page = page.replace(
            "</head>",
            '<link rel="stylesheet" href="../styles/album-art.css?v=20260919-contrast"></head>',
            1,
        )
        path = SITE_DIR / route if route else albums_dir / f"{slug}.html"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(page, encoding="utf-8")
        print(f"Built album room: {path}")
