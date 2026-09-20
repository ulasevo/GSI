"""Generated GSI homepage renderer.

The homepage owns catalogue presentation and emits the existing filter, layout,
format, playlist, and P53 context without changing their visual contract.
"""

import html
import json
from pathlib import Path

from gsi_assets import artwork_palette, palette_style, playlist_visuals
from gsi_data import load_config
from builder.template_renderer import render_template


def build_index_html(
    tracks: list[dict],
    album_routes: dict[tuple[str, str], str] | None = None,
    *,
    config_file: Path | None = None,
    output_path: Path | None = None,
) -> None:
    """Build the visual index from prepared catalogue records."""
    base = Path(__file__).resolve().parents[1]
    config_file = config_file or base / "config.json"
    output_path = output_path or base / "site" / "index.html"
    config = load_config(config_file)
    # Config supplies authored copy and colors; this renderer only escapes it
    # and arranges it into the homepage structure.
    project_title = config.get("project_title", "GSI")
    page_title = config.get("page_title", project_title)
    intro = config.get("intro", "")
    filters = config.get("filters", {})
    safe_project_title = html.escape(project_title)
    safe_page_title = html.escape(page_title)
    safe_intro = html.escape(intro)
    safe_meta_description = html.escape(intro, quote = True)
    site_url = (config.get("site_url") or "").rstrip("/")
    homepage_url = f"{site_url}/" if site_url else ""
    homepage_url_meta = ""
    share_image_meta = ""
    if homepage_url:
        safe_homepage_url = html.escape(homepage_url, quote = True)
        homepage_url_meta = f"""
    <link rel="canonical" href="{safe_homepage_url}">
    <meta property="og:url" content="{safe_homepage_url}">
    """
        share_image_url = f"{site_url}/covers/GSI_share.png"
        share_image_meta = f"""
    <meta property="og:image" content="{html.escape(share_image_url, quote = True)}">
    <meta property="og:image:width" content="1200">
    <meta property="og:image:height" content="630">
    <meta name="twitter:card" content="summary_large_image">
    """
    # Each card keeps the stable route and the metadata used by browser filters.
    cards = []

    for item in tracks:
        safe_track = html.escape(item["track"])
        safe_artist = html.escape(item["artist"])
        safe_album = html.escape(item["album"])
        safe_card_label = html.escape(f'{item["track"]} — {item["artist"]}', quote = True)
        cover_html = ""
        if item["cover_file"]:
            cover_html = f'<img src="covers/{item["cover_file"]}" alt="{safe_album} cover" loading="lazy" decoding="async">'  # image tag
        tags = item.get("tags", "")
        tags_for_attr = tags.lower().replace(","," ")
        p53_order = int(item.get("p53_order", 999))
        album_route = (album_routes or {}).get((item["artist"], item["album"]), "")
        # Homepage cards use the same named palette roles as entry rooms.  The
        # card itself remains a lightweight link, while the inline variables
        # let CSS paint its metadata surface from the actual cover artwork.
        card_palette = item.get("palette") or artwork_palette(Path("__missing_artwork__.jpg"), item["accent"])
        card_art_style = palette_style(
            card_palette,
            f'covers/{item["cover_file"]}' if item.get("cover_file") else "",
        )
        card_style = html.escape(
            f'--accent: {item["accent"]}; --p53-order: {p53_order}; {card_art_style}',
            quote=True,
        )
        card = f"""
        <a class="card"
            data-tags="{tags_for_attr}"
            data-artist="{html.escape(item["artist"], quote = True)}"
            data-album="{html.escape(item["album"], quote = True)}"
            data-album-href="{html.escape(album_route, quote=True)}"
            data-p53-order="{p53_order}"
            aria-label="{safe_card_label}"
            data-base-href="{html.escape(item["page_url"], quote = True)}"
            href="{html.escape(item["page_url"], quote = True)}" style="{card_style}">
            {cover_html}
            <div class="info">
                <h2>{safe_track}</h2>
                <p>{safe_artist}</p>
                <span>{safe_album}</span>
            </div>
        </a>
        """  # one visual card, colored by album accent

        cards.append(card)  # add this card to the gallery
    intro_html = ""
    if intro.strip():
        intro_html = f"""
        <section class = "intro">
            <p>{safe_intro}</p>
        </section>
        """
    # Filter data is emitted once as JSON so the browser script does not need
    # another copy of the catalogue or its descriptions.
    filter_buttons = []

    filter_data = {}


    for filter_key, filter_settings in filters.items(): # build one button per config filter
        label = filter_settings.get("label", filter_key) # visible button text
        safe_filter_key = html.escape(filter_key, quote = True) # quote protects quotation marks in insertion to html
        safe_label = html.escape(label)
        description = filter_settings.get("description", "") # panel text
        color = filter_settings.get("color", "#ffffff") # page tint color
        playlist_url = (filter_settings.get("playlist_url") or "").strip()
        playlist_cover = (filter_settings.get("playlist_cover") or "").strip()
        playlist_cta = (filter_settings.get("playlist_cta") or "Want more of the same?").strip()
        playlist_src, playlist_color = playlist_visuals(playlist_cover, color, base)
        filter_tracks = [
            item for item in tracks
            if filter_key in [tag.strip().lower() for tag in item.get("tags", "").split(",")]
        ]
        filter_buttons.append(
            f'<button class="filter-btn filter-{safe_filter_key}" data-filter="{safe_filter_key}" aria-pressed="false"><span>{safe_label}</span></button>'
        )

        filter_data[filter_key] = {
            "label": label,
            "description": description,
            "color": color,
            "playlist_url": playlist_url,
            "playlist_cover": playlist_src,
            "playlist_color": playlist_color,
            "playlist_cta": playlist_cta,
            "count": len(filter_tracks),
            "room_label_lines": filter_settings.get("room_label_lines") or [label]
        }

    filters_html = f"""
    <section class="filter-panel">
        <div class="filter-row">
            {''.join(filter_buttons)}
        </div>
        <div class="filter-description hidden" id="filter-description-box">
            <div class="filter-room-label" id="filter-room-label" aria-hidden="true"></div>
            <div class="filter-decor" id="filter-decor" aria-hidden="true"></div>
            <div class="filter-copy">
                <div class="filter-count" id="filter-count"></div>
                <h2 id="filter-title"></h2>
                <p id="filter-description"></p>
            </div>
        </div>
    </section>
    """

    # The homepage points to the Radio P53 landing surface, not directly to a
    # transmission; the landing page owns the historical sequence.
    p53_slug = (config.get("p53_current_slug") or "").strip()
    p53_item = next((item for item in tracks if item["slug"] == p53_slug), None)
    p53_html = ""
    if p53_item:
        p53_settings = config.get("p53") or {}
        p53_cover_value = str(p53_settings.get("playlist_cover") or "covers/P53_cover.jpg").strip()
        p53_cover_path = base / p53_cover_value
        p53_palette = artwork_palette(p53_cover_path, p53_item.get("accent", "#ff65ad"))
        p53_style = (
            f'--signal-accent:{p53_palette.get("primary", p53_item.get("accent", "#ff65ad"))};'
            f'--p53-accent:{p53_palette.get("primary", p53_item.get("accent", "#ff65ad"))};'
            f'{palette_style(p53_palette, p53_cover_value)}'
        )
        p53_html = f"""
        <a class="p53-broadcast" data-base-href="p53/index.html" href="p53/index.html" aria-label="Open Radio P53: current and previous transmissions" style="{html.escape(p53_style, quote=True)}">
            <div class="p53-art">
                <img src="covers/P53_cover.jpg" alt="P53 protein artwork">
            </div>
            <div class="p53-overlay">
                <img class="p53-album" src="covers/{html.escape(p53_item['cover_file'], quote = True)}" alt="{html.escape(p53_item['album'], quote = True)} cover">
                <div class="p53-signal-copy">
                    <span>CURRENT TRANSMISSION</span>
                    <strong>{html.escape(p53_item['track'])}</strong>
                    <small>{html.escape(p53_item['artist'])}</small>
                    <b aria-hidden="true">↗</b>
                </div>
                <div class="p53-radio">RADIO P53</div>
            </div>
        </a>
        """

    filter_data_json = json.dumps(filter_data).replace("</", "<\\/")
    index_html = render_template(
        "index.html",
        {
            "safe_meta_description": safe_meta_description,
            "safe_page_title": safe_page_title,
            "homepage_url_meta": homepage_url_meta,
            "share_image_meta": share_image_meta,
            "safe_project_title": safe_project_title,
            "intro_html": intro_html,
            "p53_html": p53_html,
            "filters_html": filters_html,
            "cards_html": "".join(cards),
            "filter_data_json": filter_data_json,
        },
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    index_path = output_path
    index_path.write_text(index_html, encoding = "utf-8")
    print(f"\nBuilt visual index: {index_path}")
