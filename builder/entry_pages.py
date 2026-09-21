"""Generated entry reading-room pages.

The renderer owns the current entry composition while the source Markdown remains
the authoring source. It accepts paths explicitly so the page family can be
checked in isolation without importing the build orchestrator.
"""

import html
import json
import re
from pathlib import Path
from urllib.parse import quote

from gsi_data import load_config
from gsi_assets import artwork_palette, palette_style
from gsi_text import make_streaming_links, simple_markdown_to_html, slugify
from builder.template_renderer import render_template


# Markdown is intentionally reduced to the small section structure GSI uses;
# authored prose remains in the source file and is never rewritten here.
def extract_sections_from_markdown(entry_path: Path) -> list[dict]:
    text = entry_path.read_text(encoding = "utf-8")
    text = re.sub(r"<!--.*?-->", "", text, flags = re.DOTALL)
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            text = parts[2] #split, keep body
    text = re.sub(r"!\[cover\]\(.*?\)", "", text) # remove generated cover line
    text = re.sub(r"\*\*Album:\*\*.*", "", text) # remove generated album line
    text = re.sub(r"\*\*Accent:\*\*.*", "", text) # remove generated accent line
    text = re.sub(r"^# .*$", "", text, flags=re.MULTILINE) # remove main title line
    matches = list(re.finditer(r"^## (.+)$", text, flags = re.MULTILINE)) #FIND SECTION HEADINGS??
    if not matches:
        return [{"title": "Note", "content": text.strip()}]
    sections = []
    for i, match in enumerate(matches):
        title = match.group(1).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content = text[start:end].strip()
        sections.append({"title": title, "content": content})
    return sections


# Build one intimate reading room from prepared metadata plus the original entry.
def build_entry_page(
    item: dict,
    artist_counts: dict[str, int] | None = None,
    album_pages: dict[tuple[str, str], str] | None = None,
    *,
    config_file: Path | None = None,
    entries_dir: Path | None = None,
    output_dir: Path | None = None,
) -> None:
    """Build one entry reading room from prepared metadata and authored Markdown."""
    base = Path(__file__).resolve().parents[1]
    config_file = config_file or base / "config.json"
    entries_dir = entries_dir or base / "entries"
    output_dir = output_dir or base / "site" / "entries"
    output_dir.mkdir(parents=True, exist_ok=True)
    config = load_config(config_file)
    section_info = config.get("section_info", {})
    entry_path = entries_dir / item["entry_file"]
    sections = extract_sections_from_markdown(entry_path)
    page_title_text = f'{item["track"]} — {item["artist"]}'
    page_description_text = f'{item["track"]} by {item["artist"]}, from {item["album"]}, in GSI.'
    safe_page_title = html.escape(page_title_text)
    safe_page_description = html.escape(page_description_text, quote = True)
    site_url = item.get("site_url", "")
    entry_url = f'{site_url}/entries/{item["html_file"]}' if site_url else ""
    cover_url = f'{site_url}/covers/{quote(item["cover_file"])}' if site_url and item["cover_file"] else ""
    sharing_meta = ""
    if entry_url:
        sharing_meta = f"""
    <link rel="canonical" href="{html.escape(entry_url, quote = True)}">
    <meta property="og:url" content="{html.escape(entry_url, quote = True)}">
    """
    if cover_url:
        sharing_meta += f"""
    <meta property="og:image" content="{html.escape(cover_url, quote = True)}">
    <meta name="twitter:card" content="summary_large_image">
    """
    cover_html = ""
    bg_style = ""
    art_image_src = ""
    if item["cover_file"]:
        cover_src = f"../covers/{item['cover_file']}"
        art_image_src = cover_src
        # Entry covers are the reading-room hero, so keep the first visual
        # request eager while allowing the browser to decode it off the main
        # thread.  The explicit priority avoids the cover arriving after the
        # prose on slower mobile connections.
        cover_html = f'<img class = "cover" src = "{cover_src}" alt = "{html.escape(item["album"])} cover" loading="eager" fetchpriority="high" decoding="async">'
        # Keep the cover treatment as a custom property on the page body. This
        # lets the shared stylesheet stay static while the URL remains escaped.
        bg_style = html.escape(
            f'--entry-background:linear-gradient(120deg, rgba(0,0,0,.78), rgba(0,0,0,.96)), url("{cover_src}");',
            quote=True,
        )
    # Empty sections do not become doors in the reading room.
    section_cards = []
    section_index = []
    for section in sections:
        if not section["content"].strip():
            continue
        section_title = section["title"]
        section_id = f"section-{slugify(section_title)}"
        section_index.append((section_id, section_title))
        section_help = (section_info.get(section_title) or "").strip()
        help_button = ""
        help_panel = ""
        if section_help:
            safe_section_help = html.escape(section_help)
            safe_section_label = html.escape(f"About {section_title}", quote = True)
            help_id = f'section-help-{slugify(section_title)}'
            help_button = f'<button class="section-info-button" type="button" aria-label="{safe_section_label}" aria-controls="{help_id}" aria-expanded="false">i</button>'
            help_panel = f'<div class="section-help" id="{help_id}" aria-hidden="true"><div><p>{safe_section_help}</p></div></div>'
        section_cards.append(f"""
        <section class="section-card" id="{section_id}">
            <div class="section-heading">
                <h2>{html.escape(section_title)}</h2>
                {help_button}
            </div>
            {help_panel}
            {simple_markdown_to_html(section["content"])}
        </section>
        """)
    # The section strip appears only when there are enough real sections to aid
    # orientation; short entries stay visually quiet.
    entry_index_html = ""
    if len(section_index) >= 3:
        index_links = "".join(
            f'<a href="#{html.escape(section_id, quote=True)}">{html.escape(title)}</a>'
            for section_id, title in section_index
        )
        entry_index_html = f'''<aside class="entry-index" aria-label="Entry sections"><span>SECTIONS</span><nav>{index_links}</nav></aside>'''
    entry_layout_class = "entry-reading-layout has-entry-index" if entry_index_html else "entry-reading-layout"
    streaming_links_html = make_streaming_links(item)
    p53_current_slug = (config.get("p53_current_slug") or "").strip()
    in_p53 = any(record.get("slug") == item["slug"] for record in config.get("p53_history", []))
    p53_counterpart_html = ""
    if in_p53:
        p53_label = "CURRENT P53 TRANSMISSION" if item["slug"] == p53_current_slug else "P53 TRANSMISSION"
        p53_counterpart_html = f'<a class="p53-counterpart" data-base-href="../p53/{item["slug"]}.html" href="../p53/{item["slug"]}.html">{p53_label} <span>OPEN ↗</span></a>'
    filter_labels = {
        key: settings.get("label", key)
        for key, settings in config.get("filters", {}).items()
    }
    filter_keys = [
        tag.strip().lower()
        for tag in item.get("tags", "").split(",")
        if tag.strip().lower() in filter_labels
    ]
    filter_receipt_links = "".join(
        f'<a data-filter-route="{html.escape(filter_key, quote=True)}" href="../index.html?filter={quote(filter_key)}">{html.escape(filter_labels[filter_key])}</a>'
        for filter_key in filter_keys
        if filter_key != "p53"
    )
    # These are factual exits from the entry, not recommendations or inferred
    # similarities.
    also_paths = []
    artist_room_exists = (artist_counts or {}).get(item["artist"], 0) >= 1
    artist_slug = slugify(item["artist"])
    artist_href = f'../artists/{slugify(item["artist"])}.html'
    entry_context_json = json.dumps({
        "filterLabels": filter_labels,
        "artistSlug": artist_slug,
        "artistName": item["artist"],
        "hasArtistRoom": artist_room_exists,
    }).replace("</", "<\\/")
    artist_display = (
        f'<a class="artist-link" data-artist-base-href="{artist_href}" href="{artist_href}">{html.escape(item["artist"])}</a>'
        if artist_room_exists else html.escape(item["artist"])
    )
    album_href = (album_pages or {}).get((item["artist"], item["album"]))
    album_display = (
        f'<a class="album-link" data-album-base-href="{html.escape(album_href, quote=True)}" href="{html.escape(album_href, quote=True)}">{html.escape(item["album"])}</a>'
        if album_href else html.escape(item["album"])
    )
    if artist_room_exists:
        also_paths.append(f'<a data-artist-base-href="{artist_href}" href="{artist_href}">ARTIST PAGE : {html.escape(item["artist"])}</a>')
    if album_href:
        also_paths.append(f'<a data-album-base-href="{html.escape(album_href, quote=True)}" href="{html.escape(album_href, quote=True)}">ALBUM PAGE : {html.escape(item["album"])}</a>')
    if in_p53:
        also_paths.append(f'<a href="../p53/{item["slug"]}.html">RADIO P53</a>')
    if filter_receipt_links:
        also_paths.append(filter_receipt_links)
    also_appears_html = ""
    if also_paths:
        also_appears_html = f'<aside class="also-appears" id="also-appears"><span>ALSO APPEARS IN</span><div>{"".join(also_paths)}</div></aside>'

    safe_accent = html.escape(str(item["accent"]), quote=True)
    art_style = html.escape(
        palette_style(item.get("palette") or artwork_palette(Path("__missing_artwork__.jpg"), item["accent"]), art_image_src),
        quote=True,
    )
    html_page = render_template(
        "entry.html",
        {
            "safe_page_description": safe_page_description,
            "accent": safe_accent,
            "safe_page_title": safe_page_title,
            "sharing_meta": sharing_meta,
            "bg_style": bg_style,
            "art_style": art_style,
            "track": html.escape(item["track"]),
            "cover_html": cover_html,
            "artist_display": artist_display,
            "album_display": album_display,
            "p53_counterpart_html": p53_counterpart_html,
            "streaming_links_html": streaming_links_html,
            "entry_layout_class": entry_layout_class,
            "entry_index_html": entry_index_html,
            "section_cards_html": "".join(section_cards),
            "also_appears_html": also_appears_html,
            "entry_context_json": entry_context_json,
        },
    )

    output_path = output_dir / item["html_file"] # final generated review page path
    output_path.write_text(html_page, encoding="utf-8") # save page)
