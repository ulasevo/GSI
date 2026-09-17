import argparse # command-line options such as the source-safe site build
import json #so I can change the categories at ease via config.json
import re # so I can clean file names?
import html # escapes review text before placing it
from pathlib import Path # cross OS handling
from urllib.parse import quote, quote_plus # allows search text to be URL safe
import requests # web requests
from gsi_assets import copy_site_covers, copy_site_scripts, copy_site_styles, dominant_color, local_image_metadata, playlist_visuals
from gsi_artists import artist_catalogue_records, artist_image_markup, copy_site_artist_assets, resolve_artist_asset, write_artist_manifest
from gsi_data import artist_room_groups, load_config, ordered_tracks, read_tracks
from gsi_links import catalogue_record, normalize_provider_url, resolve_provider_links
from gsi_text import make_streaming_links, simple_markdown_to_html, slugify
from gsi_validation import validate_generated_links

BASE = Path(__file__).resolve().parent # THIS folder
ENTRIES_DIR = BASE / "entries" # markdown file generation path
COVERS_DIR = BASE / "covers" # album cover saving path
SITE_DIR = BASE / "site" #HTML index creation path
SITE_ENTRIES_DIR = SITE_DIR / "entries" #review page
SITE_COVERS_DIR = SITE_DIR / "covers"
SITE_P53_DIR = SITE_DIR / "p53"
SITE_ARTISTS_DIR = SITE_DIR / "artists"
ARTIST_ASSETS_DIR = BASE / "artist-assets"
SITE_ARTIST_ASSETS_DIR = SITE_DIR / "artist-assets"
SITE_ALBUMS_DIR = SITE_DIR / "albums"
SITE_DATA_DIR = SITE_DIR / "data"
WEB_DIR = BASE / "web"
SITE_SCRIPTS_DIR = SITE_DIR / "scripts"
SITE_STYLES_DIR = SITE_DIR / "styles"

TRACKS_FILE = BASE / "tracks.csv" #list of song inputs
CONFIG_FILE = BASE / "config.json" #settings file

ENTRIES_DIR.mkdir(exist_ok = True) #creates entry folder, but not on repeat
COVERS_DIR.mkdir(exist_ok = True)
SITE_DIR.mkdir(exist_ok = True)
SITE_ENTRIES_DIR.mkdir(exist_ok = True) #creates entries
SITE_P53_DIR.mkdir(exist_ok = True)
SITE_ARTISTS_DIR.mkdir(exist_ok = True)
ARTIST_ASSETS_DIR.mkdir(exist_ok = True)
SITE_ALBUMS_DIR.mkdir(exist_ok = True)
SITE_DATA_DIR.mkdir(exist_ok = True)

def search_itunes_cover(artist: str, track: str, album: str) -> str | None: #retrieves cover link
    query = quote_plus(f"{artist} {track} {album}")
    url = f"https://itunes.apple.com/search?term={query}&entity=song&limit=25"  # inspect several results instead of trusting the first

    response = requests.get(url, timeout = 15)
    response.raise_for_status() # yields error

    data = response.json()
    if data["resultCount"] == 0:
        return None
    wanted_artist = slugify(artist)
    wanted_track = slugify(track)
    wanted_album = slugify(album)

    def result_score(result: dict) -> int:
        result_artist = slugify(result.get("artistName", ""))
        result_track = slugify(result.get("trackName", ""))
        result_album = slugify(result.get("collectionName", ""))
        score = 0
        if result_artist == wanted_artist:
            score += 8
        if result_track == wanted_track:
            score += 10
        if result_album == wanted_album:
            score += 7
        elif wanted_album and (wanted_album in result_album or result_album in wanted_album):
            score += 4
        return score

    ranked_results = sorted(data["results"], key = result_score, reverse = True)
    best_result = ranked_results[0]
    if result_score(best_result) < 12:
        return None
    artwork_url = best_result.get("artworkUrl100") # gives 100x100 cover
    if artwork_url is None:
        return None
    return artwork_url.replace("100x100bb", "600x600bb") # ENLARGE

def download_cover(url: str, save_path: Path) -> bool: # downloads cover; returns True if successful, False if failed
    try: # prevents one bad cover URL from crashing the entire build
        headers = {"User-Agent": "Mozilla/5.0"} # some sites reject default Python requests
        response = requests.get(url, timeout=15, headers=headers) # fetch image with browser-like header
        response.raise_for_status() # raises error for 403/404/etc.
        save_path.write_bytes(response.content) # save image if request worked
        return True # tell build_entries that download succeeded

    except requests.RequestException as error: # catches 403, 404, timeout, connection errors
        print(f" Cover download failed: {url}") # show which URL failed
        print(f" Reason: {error}") # show the actual error
        return False # tell build_entries to fall back safely

def make_frontmatter(artist: str, track: str, album: str, cover_file: str, accent: str) -> str: #markdown file metadata
    return f"""---
artist: "{artist}"
track: "{track}"
album: "{album}"
cover: "../covers/{cover_file}"
accent: "{accent}"
---
"""

def make_section_prompt(section: str) -> str: # returns a small invisible writing prompt for each section
    prompts = { # section-specific prompts; only affects newly created Markdown files
        "Charge": "What state does this song trigger?",
        "Sonical Attraction": "What sound detail pulls you in? Rhythm, bass, vocal texture, distortion, switch, silence.",
        "Lyric/Vocal Detail": "Any line, delivery, breath, pronunciation, or vocal moment worth preserving?",
        "Version of ulaş": "What version of me does this song store? Time period, grind, breakup, desire, motion.",
        "Lore": "Any personal history, repeated use, place, habit, person attached to this track?",
        "Reading": "What do I think the song is doing or narrating?",
        "Comment": "Free field. Final take, vibe, joke, conclusion, or whatever does not fit elsewhere."
    }

    return prompts.get(section, "Write whatever belongs here.") # fallback for any new custom section


def make_markdown_template(artist: str, track: str, album: str, cover_file: str, accent: str, sections: list[str]) -> str:  # creates new Markdown entry
    section_text = "\n\n".join(
        [f"## {section}\n\n<!-- {make_section_prompt(section)} -->\n" for section in sections]
    ) # headings plus invisible prompts; prompts are ignored in generated HTML

    cover_markdown = "" # default to empty cover line
    if cover_file: # if cover exists
        cover_markdown = f"![cover](../covers/{cover_file})\n\n"  # Markdown image syntax

    return f"""{make_frontmatter(artist, track, album, cover_file, accent)}

# {track} — {artist}

{cover_markdown}**Album:** {album}
**Accent:** `{accent}`

{section_text}
"""

def sync_entry_metadata(entry_path: Path, artist: str, track: str, album: str, cover_file: str, accent: str) -> None:
    text = entry_path.read_text(encoding  = "utf-8")
    new_frontmatter = make_frontmatter(artist, track, album, cover_file, accent).strip()
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            body = parts[2].lstrip()
            text = f"{new_frontmatter}\n\n{body}"
    else:
        text = f"{new_frontmatter}\n\n{text}"
    text = re.sub(
        r"^# .*$",
        f"# {track} — {artist}",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    text = re.sub(r"^\*{2}Album:.*$", ################### ^ means “beginning of a line.”
                                                        #  $ means “end of a line.”
                                                        # .* means “the remaining characters on that line.”
                                                        # re.MULTILINE allows ^ and $ to work on individual lines instead of only the whole file.
                                                        # The f before the replacement string inserts the real album or accent value.
                                                        # Backticks around {accent} preserve the existing Markdown code styling.
                  f"**Album:** {album}",
                  text, count = 1,
                  flags = re.MULTILINE
    ) 
    text = re.sub( r"^\*\*Accent:\*\*.*$",
                  f"**Accent:** `{accent}`",
                  text, count = 1, flags = re.MULTILINE)
    if cover_file and "![cover](" not in text:
        title_line = f"# {track} — {artist}"
        cover_line = f"![cover](../covers/{cover_file})"
        if title_line in text:
            text = text.replace(title_line, f"{title_line}\n\n{cover_line}", 1)
    entry_path.write_text(text, encoding = "utf-8")


def remove_stale_entry_pages(tracks: list[dict]) -> None:
    expected_pages = {item["html_file"] for item in tracks}
    for html_path in SITE_ENTRIES_DIR.glob("*.html"):
        if html_path.name not in expected_pages:
            html_path.unlink()
            print(f" Removed stale generated page: {html_path}")


def append_missing_sections(entry_path: Path, sections: list[str]) -> None:  # add new settings
    text = entry_path.read_text(encoding = "utf-8")
    missing_sections = [] # sections that exist in config but not in this entry
    for section in sections: # check in line
        heading = f"## {section}" # markdown syntax for heading..
        if heading not in text:
            missing_sections.append(section) # recall if empty
    if not missing_sections: # if all is well
        return

    addition = "\n\n" + "\n\n".join(
        [f"## {section}\n\n<!-- {make_section_prompt(section)} -->\n" for section in missing_sections]
         ) # NEW ONES ONLY + invisible ones
    entry_path.write_text(text.rstrip() + addition + "\n", encoding = "utf-8") # append but don't overwrite

def build_entries(write_sources: bool = True) -> list[dict]: # collect tracks, optionally updating source files
    config = load_config(CONFIG_FILE) #read settings
    sections = config["sections"]
    site_url = (config.get("site_url") or "").rstrip("/")
    force_refresh_covers = config.get("force_refresh_covers", False)
    built_tracks = [] #store metadata for HTML gallery

    for row in ordered_tracks(read_tracks(TRACKS_FILE), config): #loop songs in tracks.csv
        artist = row["artist"].strip()
        track = row["track"].strip()
        album = row["album"].strip() #cleanup
        manual_cover_url = (row.get("cover_url") or "").strip()
        manual_cover_file = (row.get("cover_file") or "").strip()
        tags = (row.get("tags") or "").strip()
        manual_accent = (row.get("accent") or "").strip()
        spotify_url = (row.get("spotify_url") or "").strip() #optional
        apple_url = (row.get("apple_url") or "").strip()
        normalized_spotify_url = normalize_provider_url(spotify_url, "spotify")
        normalized_apple_url = normalize_provider_url(apple_url, "apple")
        if spotify_url and not normalized_spotify_url:
            print(f" Invalid Spotify URL for {track}; using a search fallback.")
        if apple_url and not normalized_apple_url:
            print(f" Invalid Apple Music URL for {track}; using a search fallback.")

        slug = slugify(f"{artist}-{track}") # base filename
        entry_path = ENTRIES_DIR / f"{slug}.md"
        cover_path = COVERS_DIR / f"{slug}.jpg" #paths
        if manual_cover_file:
            local_cover_path = COVERS_DIR / manual_cover_file
            if local_cover_path.exists():
                cover_path = local_cover_path
            else:
                print(f" Local cover file not found for {track}: {manual_cover_file}")
                manual_cover_file = ""

        has_local_cover = bool(manual_cover_file)
        needs_download = force_refresh_covers or not cover_path.exists()
        should_download_cover = write_sources and (not has_local_cover) and needs_download

        if should_download_cover:
            if manual_cover_url:
                cover_url = manual_cover_url
            else:
                try:
                    cover_url = search_itunes_cover(artist, track, album)
                except requests.RequestException as error:
                    print(f" iTunes cover search failed for {track}.")
                    print(f" Reason: {error}")
                    cover_url = None

            if cover_url is None:
                print(f" No cover found for {track}.")
                if cover_path.exists():
                    print(f" Using cached cover for {track}.")
                    accent = dominant_color(cover_path)
                    cover_file = cover_path.name
                else:
                    accent = "#444444"
                    cover_file = ""
            else:
                download_ok = download_cover(cover_url, cover_path) # try to download cover without crashing
                if download_ok: # if cover downloaded successfully
                    accent = dominant_color(cover_path)
                    cover_file = cover_path.name
                else: # if manual/auto cover failed
                    if cover_path.exists():
                        print(f" Using cached cover for {track}.")
                        accent = dominant_color(cover_path)
                        cover_file = cover_path.name
                    else:
                        accent = "#444444"
                        cover_file = ""
        else:
            if cover_path.exists():
                accent = dominant_color(cover_path) # use existing cover
                cover_file = cover_path.name
            else:
                accent = "#444444"
                cover_file = ""
        if manual_accent: # manual accent from tracks.csv beats automatic cover extraction
            accent = manual_accent
        if not entry_path.exists() and not write_sources:
            raise FileNotFoundError(
                f"Safe build stopped: missing source entry {entry_path.name}"
            )
        if not entry_path.exists():
            note = make_markdown_template(artist, track, album, cover_file, accent, sections)
            entry_path.write_text(note, encoding = "utf-8")
            print(f" Created entry: {entry_path}")
        elif write_sources:
            sync_entry_metadata(entry_path, artist, track, album, cover_file, accent)
            append_missing_sections(entry_path, sections)
            print(f" Updated metadata and checked sections: {entry_path}")
        else:
            print(f" Read entry without modifying source: {entry_path}")

        built_tracks.append({  # save data needed for the index
            "tags": tags,
            "artist": artist,
            "track": track,
            "album": album,
            "slug": slug,
            "entry_file": entry_path.name,
            "html_file": f"{slug}.html",
            "cover_file": cover_file,
            "accent": accent,
            "site_url": site_url,
            "spotify_url": normalized_spotify_url,
            "apple_url": normalized_apple_url
        })
    return built_tracks # HTML builder save
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
def build_entry_page(item: dict, artist_counts: dict[str, int] | None = None) -> None: #HTML review page
    config = load_config(CONFIG_FILE)
    section_info = config.get("section_info", {})
    entry_path = ENTRIES_DIR / item["entry_file"]
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
    if item["cover_file"]:
        cover_src = f"../covers/{item['cover_file']}"
        cover_html = f'<img class = "cover" src = "{cover_src}" alt = "{html.escape(item["album"])} cover">'
        bg_style = f'background-image: linear-gradient(120deg, rgba(0,0,0,.78), rgba(0,0,0,.96)), url("{cover_src}");'
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
    entry_index_html = ""
    if len(section_index) >= 3:
        index_links = "".join(
            f'<a href="#{html.escape(section_id, quote=True)}">{html.escape(title)}</a>'
            for section_id, title in section_index
        )
        entry_index_html = f'''<aside class="entry-index" aria-label="Entry sections"><span>SECTIONS</span><nav>{index_links}</nav></aside>'''
    entry_layout_class = "entry-reading-layout has-entry-index" if entry_index_html else "entry-reading-layout"
    streaming_links_html = make_streaming_links(item) ##
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
    also_paths = []
    artist_room_exists = (artist_counts or {}).get(item["artist"], 0) >= 2
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
    if artist_room_exists:
        also_paths.append(f'<a data-artist-base-href="{artist_href}" href="{artist_href}">ARTIST PAGE : {html.escape(item["artist"])}</a>')
    if in_p53:
        also_paths.append(f'<a href="../p53/{item["slug"]}.html">RADIO P53</a>')
    if filter_receipt_links:
        also_paths.append(filter_receipt_links)
    also_appears_html = ""
    if also_paths:
        also_appears_html = f'<aside class="also-appears" id="also-appears"><span>ALSO APPEARS IN</span><div>{"".join(also_paths)}</div></aside>'

    html_page = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="{safe_page_description}">
    <meta name="theme-color" content="{html.escape(item['accent'], quote = True)}">
    <meta property="og:type" content="article">
    <meta property="og:site_name" content="GSI">
    <meta property="og:title" content="{safe_page_title}">
    <meta property="og:description" content="{safe_page_description}">{sharing_meta}
    <link rel="icon" href="../covers/GSI_favicon.svg" type="image/svg+xml">
    <link rel="stylesheet" href="../styles/gsi-tokens.css">
    <title>{safe_page_title}</title>
    <style>
        :root {{
            --accent: {item["accent"]};
        }}

        body {{
            margin: 0;
            min-height: 100vh;
            font-family: var(--gsi-reading-font, Arial, sans-serif);
            color: #f2f2f2;
            background: #101010;
            {bg_style}
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}

        .page {{
            max-width: 1050px;
            margin: 0 auto;
            padding: 34px 22px 80px;
        }}

        .back {{
            display: inline-block;
            margin-bottom: 22px;
            color: color-mix(in srgb, var(--accent), white 35%);
            text-decoration: none;
        }}

        .hero {{
            display: grid;
            grid-template-columns: 300px 1fr;
            gap: 28px;
            align-items: center;
            padding: 24px;
            border-radius: 28px;
            border: 1px solid color-mix(in srgb, var(--accent), white 16%);
            background: color-mix(in srgb, #171717, var(--accent) 10%);
            box-shadow: 0 0 80px color-mix(in srgb, var(--accent), transparent 70%);
        }}

        .cover {{
            width: 100%;
            border-radius: 20px;
            box-shadow: 0 0 45px color-mix(in srgb, var(--accent), transparent 55%);
        }}

        .meta h1 {{
            margin: 0 0 10px;
            font-size: 44px;
            letter-spacing: -0.04em;
        }}

        .meta p {{
            margin: 6px 0;
            color: #ddd;
            font-size: 18px;
        }}

        .album {{
            color: color-mix(in srgb, var(--accent), white 35%);
        }}
        .stream-block {{
            margin-top: 22px;
        }}
        .stream-label {{
            margin-bottom: 9px;
            color: color-mix(in srgb, var(--accent), white 48%);
            font-size: 13px;
            font-weight: 650;
            letter-spacing: .02em;
        }}
        .stream-links {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }}
        .stream-link {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            padding: 8px 12px;
            border-radius: 10px;
            color: #f3f3f3;
            text-decoration: none;
            font-weight: 300;
            font-size: 14px;
            background:
                linear-gradient(180deg, rgba(255,255,255,.055), rgba(0,0,0,.16)),
                rgba(10,10,10,.42);
            border: 1px solid color-mix(in srgb, var(--accent), white 22%);
            box-shadow: 0 0 18px color-mix(in srgb, var(--accent), transparent 82%);
            transition: transform .15s ease, box-shadow .15s ease, border-color .15s ease, background .15s ease;
        }}
        .stream-link:hover {{
            transform: translateY(-2px);
            border-color: color-mix(in srgb, var(--accent), white 42%);
            background:
                linear-gradient(180deg, rgba(255,255,255,.09), rgba(0,0,0,.12)),
                color-mix(in srgb, var(--accent), #101010 84%);
            box-shadow: 0 0 34px color-mix(in srgb, var(--accent), transparent 55%);
        }}

        .sections {{
            margin-top: 24px;
            display: grid;
            gap: 18px;
        }}

        .section-card {{
            padding: 22px;
            border-radius: 22px;
            background: rgba(18, 18, 18, 0.90);
            border: 1px solid color-mix(in srgb, var(--accent), white 10%);
            box-shadow: 0 0 35px rgba(0,0,0,.25);
        }}

        .section-card h2 {{
            margin: 0 0 14px;
            color: color-mix(in srgb, var(--accent), white 25%);
            font-size: 22px;
        }}

        .section-card p {{
            line-height: 1.62;
            font-size: 17px;
            color: #e6e6e6;
        }}

        /* GSI 1.09 entry room: structured like a close-view archive sheet. */
        body {{
            background-attachment: fixed;
            background-color: #0b0b0c;
            background-blend-mode: normal;
        }}
        body::before {{
            content: "";
            position: fixed;
            inset: 0;
            pointer-events: none;
            background:
                repeating-linear-gradient(0deg, transparent 0 5px, rgba(255,255,255,.018) 5px 6px),
                radial-gradient(circle at 82% 10%, color-mix(in srgb, var(--accent), transparent 78%), transparent 34%);
            mix-blend-mode: screen;
        }}
        .page {{
            position: relative;
            max-width: 1180px;
            padding-top: 22px;
        }}
        .entry-nav {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 18px;
            min-height: 48px;
            margin-bottom: 14px;
            padding: 0 14px;
            border: 1px solid rgba(255,255,255,.12);
            border-radius: 18px 6px 18px 6px;
            background: rgba(10,10,11,.74);
            backdrop-filter: blur(12px);
        }}
        .back {{
            margin: 0;
            padding: 11px 4px;
            font-size: 13px;
            font-weight: 900;
            letter-spacing: .12em;
            transition: color 180ms ease, transform 360ms cubic-bezier(.2,.8,.2,1);
        }}
        .back:hover,
        .back:focus-visible {{
            color: #fff;
            transform: translateX(-4px);
        }}
        .entry-signal {{
            color: rgba(255,255,255,.46);
            font-size: 10px;
            font-weight: 850;
            letter-spacing: .18em;
            text-transform: uppercase;
        }}
        .hero {{
            grid-template-columns: minmax(260px, 430px) minmax(0, 1fr);
            align-items: stretch;
            gap: 0;
            padding: 0;
            overflow: hidden;
            border-radius: 38px 10px 38px 10px;
            border-color: color-mix(in srgb, var(--accent), white 24%);
            background:
                linear-gradient(125deg, rgba(255,255,255,.06), transparent 36%),
                color-mix(in srgb, #111113, var(--accent) 12%);
        }}
        .cover-frame {{
            position: relative;
            min-height: 100%;
            background: color-mix(in srgb, var(--accent), #080808 82%);
        }}
        .cover-frame::after {{
            content: "";
            position: absolute;
            inset: 0;
            pointer-events: none;
            border: 1px solid rgba(255,255,255,.18);
            box-shadow: inset -18px 0 46px rgba(0,0,0,.28);
        }}
        .cover {{
            height: 100%;
            min-height: 430px;
            border-radius: 0;
            object-fit: cover;
            box-shadow: none;
        }}
        .meta {{
            position: relative;
            display: flex;
            flex-direction: column;
            justify-content: center;
            padding: clamp(28px, 5vw, 68px);
            overflow: hidden;
        }}
        .meta::before {{
            content: "GSI";
            position: absolute;
            right: -18px;
            top: -28px;
            color: color-mix(in srgb, var(--accent), transparent 82%);
            font-family: Impact, Haettenschweiler, "Arial Black", sans-serif;
            font-size: clamp(120px, 20vw, 260px);
            line-height: 1;
            transform: rotate(7deg);
            pointer-events: none;
        }}
        .entry-kicker {{
            position: relative;
            margin-bottom: 12px;
            color: color-mix(in srgb, var(--accent), white 48%);
            font-size: 11px;
            font-weight: 900;
            letter-spacing: .22em;
        }}
        .meta h1 {{
            position: relative;
            max-width: 760px;
            font-size: clamp(44px, 7vw, 92px);
            line-height: .92;
            letter-spacing: -.055em;
            text-wrap: balance;
        }}
        .meta p {{
            position: relative;
        }}
        .stream-block {{
            position: relative;
            margin-top: 30px;
        }}
        .stream-link {{
            min-height: 38px;
            padding-inline: 16px;
            border-radius: 18px 6px 18px 6px;
            font-weight: 760;
            transition:
                transform 360ms cubic-bezier(.2,.8,.2,1),
                border-radius 360ms cubic-bezier(.2,.8,.2,1),
                box-shadow 180ms ease;
        }}
        .stream-link:hover,
        .stream-link:focus-visible {{
            border-radius: 6px 18px 6px 18px;
            transform: translateY(-3px) scale(1.02);
        }}
        .sections {{
            grid-template-columns: repeat(12, minmax(0, 1fr));
            gap: 16px;
            margin-top: 18px;
        }}
        .section-card {{
            grid-column: span 7;
            padding: clamp(22px, 4vw, 38px);
            border-radius: 26px 8px 26px 8px;
            background:
                linear-gradient(145deg, rgba(255,255,255,.055), transparent 36%),
                rgba(14,14,15,.92);
            border-color: color-mix(in srgb, var(--accent), white 16%);
        }}
        .section-card:nth-child(even) {{
            grid-column: 5 / span 8;
            border-radius: 8px 26px 8px 26px;
        }}
        .section-heading {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .section-card h2 {{
            margin: 0;
            font-size: clamp(22px, 3vw, 34px);
            letter-spacing: -.025em;
        }}
        .section-info-button {{
            width: 30px;
            height: 30px;
            flex: 0 0 30px;
            border: 1px solid color-mix(in srgb, var(--accent), white 30%);
            border-radius: 50%;
            background: color-mix(in srgb, var(--accent), #111 78%);
            color: #fff;
            cursor: pointer;
            font: 900 14px/1 Georgia, serif;
            transition: transform 360ms cubic-bezier(.2,.8,.2,1), border-radius 360ms cubic-bezier(.2,.8,.2,1);
        }}
        .section-info-button:hover,
        .section-info-button:focus-visible,
        .section-info-button[aria-expanded="true"] {{
            transform: rotate(10deg) scale(1.12);
            border-radius: 10px 50% 50% 50%;
        }}
        .section-help {{
            margin: 14px 0 2px;
            padding: 12px 14px;
            border-left: 3px solid var(--accent);
            color: color-mix(in srgb, var(--accent), white 70%) !important;
            font-size: 14px !important;
            background: color-mix(in srgb, var(--accent), transparent 90%);
        }}

        @media (max-width: 760px) {{
            .entry-nav {{
                position: sticky;
                top: 8px;
                z-index: 10;
            }}
            .entry-signal {{
                max-width: 42%;
                overflow: hidden;
                white-space: nowrap;
                text-overflow: ellipsis;
            }}
            .hero {{
                grid-template-columns: 1fr;
                border-radius: 28px 8px 28px 8px;
            }}
            .cover {{
                min-height: 0;
                aspect-ratio: 1;
            }}
            .meta {{
                padding: 26px 22px 30px;
            }}
            .meta h1 {{
                font-size: 34px;
            }}
            .sections {{
                display: grid;
                grid-template-columns: 1fr;
            }}
            .section-card,
            .section-card:nth-child(even) {{
                grid-column: 1;
            }}
        }}

        /* GSI 1.09 listening shrine: quieter than the archive wall, but from the same signal system. */
        .page {{ max-width: 1240px; }}
        .entry-nav {{
            min-height: 44px;
            margin-bottom: 10px;
            border-radius: 22px 7px 22px 7px;
            background: linear-gradient(90deg, color-mix(in srgb,var(--accent),#111 88%), rgba(10,10,11,.78));
            box-shadow: inset 4px 0 0 color-mix(in srgb,var(--accent),white 22%);
        }}
        .hero {{
            grid-template-columns: minmax(280px, 380px) minmax(0,1fr);
            min-height: 390px;
            border-radius: 34px 9px 34px 9px;
        }}
        .cover {{ min-height: 390px; }}
        .meta {{
            justify-content: flex-end;
            min-height: 390px;
            padding: clamp(30px,4.5vw,58px);
            isolation: isolate;
        }}
        .meta::before {{ content:none; }}
        .entry-architecture {{
            position:absolute;
            inset:0;
            z-index:-1;
            overflow:hidden;
            box-sizing:border-box;
            pointer-events:none;
            font-family:Impact,Haettenschweiler,"Arial Black",sans-serif;
            line-height:.72;
        }}
        .entry-architecture span {{
            position:absolute;
            white-space:nowrap;
            color:rgba(255,255,255,.045);
            font-size:clamp(78px,10vw,154px);
            letter-spacing:-.045em;
        }}
        .entry-architecture span:nth-child(1) {{ top:-10px; right:-8px; }}
        .entry-architecture span:nth-child(2) {{ top:36%; left:-18px; color:transparent; -webkit-text-stroke:2px color-mix(in srgb,var(--accent),white 8%); transform:scaleX(1.08); }}
        .entry-architecture span:nth-child(3) {{ right:-10px; bottom:-8px; color:color-mix(in srgb,var(--accent),transparent 87%); }}
        .meta h1 {{
            max-width:820px;
            font-size:clamp(42px,6vw,76px);
            line-height:.9;
            text-wrap:balance;
        }}
        .meta > p {{ font-size:17px; }}
        .meta .album {{ color:color-mix(in srgb,var(--accent),white 60%); }}
        .stream-block {{ margin-top:22px; }}
        .stream-links {{ gap:7px; }}
        .stream-link {{
            position:relative;
            padding-right:34px;
            border-radius:20px 6px 20px 6px;
        }}
        .stream-link::after {{ content:"↗"; position:absolute; right:13px; transition:transform 240ms ease; }}
        .stream-link:hover::after,.stream-link:focus-visible::after {{ transform:translate(3px,-3px); }}
        .sections {{
            position:relative;
            display:flex;
            flex-direction:column;
            gap:14px;
            max-width:1080px;
            margin:24px auto 0;
            padding-left:52px;
        }}
        .sections::before {{
            content:"";
            position:absolute;
            left:19px;
            top:18px;
            bottom:18px;
            width:2px;
            background:linear-gradient(var(--accent),color-mix(in srgb,var(--accent),transparent 72%));
            box-shadow:0 0 18px color-mix(in srgb,var(--accent),transparent 45%);
        }}
        .section-card,
        .section-card:nth-child(even) {{
            grid-column:auto;
            position:relative;
            width:min(88%,900px);
            margin:0;
            padding:clamp(22px,3.4vw,34px);
            border-radius:28px 8px 28px 8px;
            background:linear-gradient(135deg,rgba(255,255,255,.055),transparent 38%),rgba(13,13,15,.94);
            box-shadow:0 18px 50px rgba(0,0,0,.23);
            transition:border-radius 480ms cubic-bezier(.2,.8,.2,1),transform 360ms cubic-bezier(.2,.8,.2,1),border-color 220ms ease;
        }}
        .section-card:nth-child(even) {{
            align-self:flex-end;
            border-radius:8px 28px 8px 28px;
        }}
        .section-card::before {{
            content:"";
            position:absolute;
            left:-43px;
            top:29px;
            width:14px;
            height:14px;
            border:3px solid #0b0b0c;
            border-radius:50%;
            background:var(--accent);
            box-shadow:0 0 0 2px color-mix(in srgb,var(--accent),white 22%),0 0 18px var(--accent);
        }}
        .section-card:hover {{
            transform:translateX(4px);
            border-radius:8px 28px 8px 28px;
            border-color:color-mix(in srgb,var(--accent),white 35%);
        }}
        .section-card:nth-child(even):hover {{ transform:translateX(-4px); border-radius:28px 8px 28px 8px; }}
        .section-heading {{ justify-content:space-between; }}
        .section-card h2 {{ font-size:clamp(24px,2.7vw,34px); }}
        .section-info-button {{
            position:relative;
            width:34px;
            height:34px;
            flex-basis:34px;
            overflow:visible;
            transition:transform 420ms cubic-bezier(.2,.8,.2,1),border-radius 420ms cubic-bezier(.2,.8,.2,1),background 220ms ease;
        }}
        .section-info-button::after {{
            content:"";
            position:absolute;
            inset:-5px;
            border:2px solid transparent;
            border-top-color:color-mix(in srgb,var(--accent),white 44%);
            border-radius:50%;
            opacity:0;
        }}
        .section-info-button[aria-expanded="true"] {{
            transform:rotate(45deg) scale(.94);
            border-radius:50% 22% 50% 50%;
            background:color-mix(in srgb,var(--accent),#111 58%);
        }}
        .section-info-button[aria-expanded="true"]::after {{ opacity:1; animation:info-orbit 720ms cubic-bezier(.2,.8,.2,1) both; }}
        @keyframes info-orbit {{ from {{ transform:rotate(-160deg) scale(.7); }} to {{ transform:rotate(0) scale(1); }} }}
        .section-help {{
            display:grid;
            grid-template-rows:0fr;
            margin:0;
            padding:0;
            border:0;
            opacity:0;
            transform:translateY(-8px) scale(.985);
            background:transparent;
            transition:grid-template-rows 420ms cubic-bezier(.2,.8,.2,1),opacity 260ms ease,transform 420ms cubic-bezier(.2,.8,.2,1),margin 420ms ease;
        }}
        .section-help > div {{ overflow:hidden; }}
        .section-help p {{
            margin:0;
            padding:14px 16px;
            color:color-mix(in srgb,var(--accent),white 82%) !important;
            font-size:14px !important;
            line-height:1.45;
            border:1px solid color-mix(in srgb,var(--accent),transparent 44%);
            border-left:4px solid var(--accent);
            border-radius:5px 18px 18px 5px;
            background:color-mix(in srgb,var(--accent),#111 82%);
            box-shadow:inset 0 0 24px color-mix(in srgb,var(--accent),transparent 88%);
        }}
        .section-help.open {{
            grid-template-rows:1fr;
            margin:14px 0 2px;
            opacity:1;
            transform:none;
        }}
        @media(max-width:760px) {{
            .hero {{ grid-template-columns:1fr; min-height:0; }}
            .cover {{ min-height:0; }}
            .meta {{ min-height:270px; justify-content:flex-end; }}
            .entry-architecture span {{ font-size:clamp(68px,24vw,108px); }}
            .sections {{ padding-left:34px; }}
            .sections::before {{ left:9px; }}
            .section-card,.section-card:nth-child(even) {{ width:100%; align-self:stretch; }}
            .section-card::before {{ left:-32px; }}
        }}

        /* Correction pass: preserve cover art and make every review panel part of one room. */
        .cover-frame {{
            display:grid;
            place-items:center;
            min-height:720px;
            padding:0;
            overflow:hidden;
        }}
        .page {{ max-width:1480px; }}
        .hero {{
            grid-template-columns:minmax(620px,720px) minmax(0,1fr);
            min-height:720px;
        }}
        .cover {{
            width:100%;
            height:auto;
            min-height:0;
            aspect-ratio:1;
            object-fit:contain;
        }}
        .entry-architecture span:nth-child(2) {{
            top:35%;
            color:rgba(255,255,255,.038);
            -webkit-text-stroke:0;
            transform:scaleX(1.08);
        }}
        .sections {{
            display:grid;
            grid-template-columns:repeat(2,minmax(0,1fr));
            align-items:stretch;
            gap:14px;
            max-width:none;
            margin-top:14px;
            padding:0;
        }}
        .sections::before {{ content:none; }}
        .section-card,
        .section-card:nth-child(even) {{
            box-sizing:border-box;
            width:auto;
            min-width:0;
            height:100%;
            align-self:stretch;
            margin:0;
            border:1px solid color-mix(in srgb,var(--accent),white 17%);
            border-top:3px solid color-mix(in srgb,var(--accent),white 22%);
            border-radius:30px 9px 30px 9px;
            background:
                linear-gradient(145deg,color-mix(in srgb,var(--accent),transparent 92%),transparent 40%),
                rgba(13,13,15,.95);
            box-shadow:inset 0 1px 0 rgba(255,255,255,.055),0 20px 54px rgba(0,0,0,.25);
        }}
        .meta {{ box-sizing:border-box; }}
        .section-card::before {{ content:none; }}
        .section-card:hover,
        .section-card:nth-child(even):hover {{
            transform:none;
            border-radius:9px 30px 9px 30px;
        }}
        .section-heading {{
            min-height:38px;
            padding-bottom:12px;
            border-bottom:1px solid color-mix(in srgb,var(--accent),transparent 68%);
        }}
        /* One visible path is clearer than a duplicate back button plus a tiny breadcrumb. */
        .entry-nav {{ margin-bottom:14px; }}
        .signal-trace {{
            display:flex;
            align-items:center;
            gap:10px;
            overflow:auto;
            padding:14px 16px;
            border:1px solid color-mix(in srgb,var(--accent),transparent 62%);
            border-radius:20px 6px 20px 6px;
            background:rgba(12,11,15,.82);
            color:rgba(255,255,255,.64);
            font-size:12px;
            font-weight:900;
            letter-spacing:.14em;
            white-space:nowrap;
        }}
        .signal-trace a {{ color:color-mix(in srgb,var(--accent),white 42%); text-decoration:none; }}
        .signal-trace a:hover,.signal-trace a:focus-visible {{ color:#fff; }}
        .signal-trace .hidden {{ display:none; }}
        .signal-trace .trace-separator {{ color:rgba(255,255,255,.28); }}
        .signal-trace .trace-current {{ min-width:0; overflow:hidden; color:rgba(255,255,255,.78); text-overflow:ellipsis; white-space:nowrap; }}
        .entry-reading-layout {{ margin-top:14px; }}
        /* The index is an orientation strip, not a competing sidebar. */
        .entry-reading-layout.has-entry-index {{ display:block; }}
        .entry-index {{
            display:flex;
            align-items:center;
            gap:10px;
            min-width:0;
            margin-bottom:14px;
            padding:9px 11px;
            border:1px solid color-mix(in srgb,var(--accent),transparent 68%);
            border-radius:18px 5px 18px 5px;
            background:rgba(12,11,15,.58);
        }}
        .entry-index > span {{ flex:0 0 auto; margin:0; color:color-mix(in srgb,var(--accent),white 26%); font-size:9px; font-weight:950; letter-spacing:.18em; }}
        .entry-index nav {{ display:flex; flex:1 1 auto; flex-wrap:wrap; gap:6px; min-width:0; }}
        .entry-index a {{ display:block; padding:6px 8px; color:rgba(255,255,255,.68); border:1px solid color-mix(in srgb,var(--accent),transparent 70%); border-radius:10px 3px 10px 3px; background:rgba(255,255,255,.025); font-size:10px; font-weight:800; line-height:1.1; text-decoration:none; }}
        .entry-index a:hover,.entry-index a:focus-visible {{ color:#fff; border-color:color-mix(in srgb,var(--accent),white 20%); }}
        .section-card {{ scroll-margin-top:24px; }}
        .entry-reading-layout .sections {{ margin-top:0; }}
        .p53-counterpart {{
            display:inline-flex;
            gap:8px;
            margin:10px 0 0;
            padding:7px 9px;
            color:color-mix(in srgb,var(--accent),white 35%);
            border:1px solid color-mix(in srgb,var(--accent),transparent 36%);
            border-radius:16px 5px 16px 5px;
            background:color-mix(in srgb,var(--accent),transparent 90%);
            font-size:9px;
            font-weight:950;
            letter-spacing:.11em;
            text-decoration:none;
            transition:transform 240ms ease,border-radius 300ms ease;
        }}
        .p53-counterpart:hover,.p53-counterpart:focus-visible {{ transform:translateY(-2px); border-radius:5px 16px 5px 16px; }}
        .artist-link {{ color:inherit; text-decoration:none; }}
        .artist-link:hover,.artist-link:focus-visible {{ color:color-mix(in srgb,var(--accent),white 30%); text-decoration:underline; }}
        .also-appears {{
            display:flex;
            align-items:baseline;
            flex-wrap:wrap;
            gap:8px 13px;
            margin-top:14px;
            padding:12px 2px 0;
            border-top:1px solid color-mix(in srgb,var(--accent),transparent 60%);
        }}
        .also-appears > span {{ color:rgba(255,255,255,.4); font-size:9px; font-weight:950; letter-spacing:.16em; }}
        .also-appears div {{ display:flex; flex-wrap:wrap; gap:7px; }}
        .also-appears a {{ color:color-mix(in srgb,var(--accent),white 30%); font-size:11px; font-weight:850; text-decoration:none; }}
        .also-appears a:not(:last-child)::after {{ content:" ·"; color:rgba(255,255,255,.32); }}
        @media(max-width:760px) {{
            .cover-frame {{ min-height:0; }}
            .cover {{ min-height:0; aspect-ratio:1; object-fit:contain; }}
            .hero {{ grid-template-columns:1fr; min-height:0; }}
            .sections {{ grid-template-columns:1fr; padding:0; }}
            .section-card,.section-card:nth-child(even) {{ width:auto; }}
            .signal-trace {{ width:100%; min-width:0; font-size:11px; overscroll-behavior-inline:contain; scrollbar-width:none; }}
            .entry-index {{ overflow-x:auto; padding:9px 11px; scrollbar-width:none; }}
            .entry-index nav {{ flex-wrap:nowrap; width:max-content; }}
            .entry-index a {{ white-space:nowrap; }}
            .also-appears {{ align-items:flex-start; flex-direction:column; }}
        }}
        @media(min-width:761px) and (max-width:1100px) {{
            .hero {{ grid-template-columns:minmax(350px,46%) minmax(0,1fr); min-height:430px; }}
            .cover-frame {{ min-height:430px; }}
        }}
        @media(prefers-reduced-motion:reduce) {{
            .section-info-button[aria-expanded="true"]::after {{ animation:none; }}
        }}
    </style>
</head>
<body>
    <main class="page">
        <header class="entry-nav">
            <nav class="signal-trace" aria-label="GSI path">
                <a id="trace-archive" href="../index.html">GSI</a>
                <span id="trace-context-separator" class="trace-separator hidden">→</span>
                <a id="trace-filter" class="hidden" href="../index.html"></a>
                <span id="trace-filter-separator" class="trace-separator hidden">→</span>
                <a id="trace-artist" class="hidden" href="../index.html"></a>
                <span class="trace-entry-separator trace-separator">→</span>
                <span class="trace-current">{html.escape(item["track"])}</span>
            </nav>
        </header>

        <section class="hero">
            <div class="cover-frame">{cover_html}</div>
            <div class="meta">
                <div class="entry-architecture" aria-hidden="true"><span>GENOME</span><span>STABILITY</span><span>INDUCER</span></div>
                <h1>{html.escape(item["track"])}</h1>
                <p>{artist_display}</p>
                <p class="album">{html.escape(item["album"])}</p>
                {p53_counterpart_html}
                {streaming_links_html}
            </div>
        </section>

        <div class="{entry_layout_class}">
            {entry_index_html}
            <div class="sections">
                {''.join(section_cards)}
            </div>
        </div>
        {also_appears_html}
    </main>
    <script id="gsi-entry-context" type="application/json">{entry_context_json}</script>
    <script src="../scripts/gsi-context.js"></script>
    <script src="../scripts/entry-page.js"></script>
</body>
</html>
"""

    output_path = SITE_ENTRIES_DIR / item["html_file"] # final generated review page path
    output_path.write_text(html_page, encoding="utf-8") # save page)


def prepare_p53_history(config: dict, tracks: list[dict], download_missing: bool = True) -> list[dict]:
    """Resolve P53 history without creating or changing Markdown entry sources."""
    tracks_by_slug = {item["slug"]: item for item in tracks}
    prepared = []
    for record in config.get("p53_history", []):
        slug = (record.get("slug") or slugify(f'{record.get("artist", "")} {record.get("track", "")}')).strip()
        item = dict(tracks_by_slug.get(slug, {}))
        item.update(record)
        item["slug"] = slug
        for provider, key in (("spotify", "spotify_url"), ("apple", "apple_url")):
            raw_url = (item.get(key) or "").strip()
            normalized_url = normalize_provider_url(raw_url, provider)
            if raw_url and not normalized_url:
                print(f" Invalid {provider.title()} URL for P53 signal {item.get('track', slug)}; using a search fallback.")
            item[key] = normalized_url
        item.setdefault("accent", "")
        cover_file = (item.get("cover_file") or f"{slug}.jpg").strip()
        cover_path = COVERS_DIR / cover_file
        if not cover_path.exists() and download_missing:
            try:
                cover_url = search_itunes_cover(item["artist"], item["track"], item["album"])
            except requests.RequestException as error:
                print(f" P53 cover search failed for {item['track']}: {error}")
                cover_url = None
            if cover_url and download_cover(cover_url, cover_path):
                print(f" Cached P53 cover: {cover_path}")
            else:
                print(f" No verified P53 cover found for {item['track']}.")
        item["cover_file"] = cover_file if cover_path.exists() else ""
        if cover_path.exists() and not item.get("accent"):
            item["accent"] = dominant_color(cover_path)
        item["accent"] = item.get("accent") or "#444444"
        prepared.append(item)
    return prepared


def merge_p53_into_archive(tracks: list[dict], p53_history: list[dict]) -> list[dict]:
    """Expose opted-in P53 signals as cards without manufacturing Markdown reviews."""
    merged = [dict(item) for item in tracks]
    by_slug = {item["slug"]: item for item in merged}
    for p53_order, signal in enumerate(p53_history):
        if not signal.get("show_in_archive", False):
            continue
        existing = by_slug.get(signal["slug"])
        if existing:
            tags = [tag.strip() for tag in existing.get("tags", "").split(",") if tag.strip()]
            if "p53" not in [tag.lower() for tag in tags]:
                tags.append("p53")
            existing["tags"] = ",".join(tags)
            existing["page_url"] = f'entries/{existing["html_file"]}'
            existing["p53_order"] = p53_order
            continue

        archive_item = dict(signal)
        archive_item["tags"] = "p53"
        archive_item["page_url"] = f'p53/{signal["slug"]}.html'
        archive_item["p53_order"] = p53_order
        archive_item.setdefault("spotify_url", "")
        archive_item.setdefault("apple_url", "")
        merged.append(archive_item)
        by_slug[archive_item["slug"]] = archive_item

    for item in merged:
        if not item.get("page_url"):
            item["page_url"] = f'entries/{item["html_file"]}'
        item.setdefault("p53_order", 999)
    return merged


def build_p53_page(item: dict, output_name: str) -> None:
    """Build one permanent P53 transmission from explicitly editable P53 copy."""
    config = load_config(CONFIG_FILE)
    p53_context_json = json.dumps({
        "filterLabels": {key: settings.get("label", key) for key, settings in config.get("filters", {}).items()},
        "expectedArtistRoute": slugify(item["artist"]),
        "artistName": item["artist"],
        "shareTitle": f"Radio P53 — {item['track']}",
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
    signal_label = "CURRENT TRANSMISSION" if item["slug"] == (config.get("p53_current_slug") or "").strip() else "PAST TRANSMISSION"
    about_text = (config.get("p53_about") or "").strip()
    transmission_notes = config.get("p53_transmission_notes") or {}
    transmission_note = str(transmission_notes.get(item["slug"], "")).strip()
    cover_src = f'../covers/{item["cover_file"]}' if item.get("cover_file") else ""
    cover_html = f'<img class="signal-cover" src="{cover_src}" alt="{html.escape(item["album"], quote = True)} cover">' if cover_src else ""
    note_html = (
        f'<section class="transmission-note"><h2>TRANSMISSION NOTES</h2>{simple_markdown_to_html(transmission_note)}</section>'
        if transmission_note else ""
    )
    streaming_links_html = make_streaming_links(item)
    entry_counterpart_html = ""
    if (ENTRIES_DIR / f'{item["slug"]}.md').exists():
        entry_counterpart_html = f'<a class="entry-counterpart" href="../entries/{html.escape(item["slug"], quote=True)}.html">INSIDE GSI / READ ENTRY ↗</a>'
    page_title = html.escape(f'P53 — {item["track"]}')
    html_page = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="theme-color" content="#25152b">
    <meta name="description" content="{html.escape(p53_description, quote=True)}">{sharing_meta}
    <link rel="icon" href="../covers/GSI_favicon.svg" type="image/svg+xml">
    <link rel="stylesheet" href="../styles/gsi-tokens.css">
    <link rel="stylesheet" href="../styles/p53-transmission.css">
    <title>{page_title}</title>
    <style>
        :root {{ --accent: {item["accent"]}; --p53: #ff58a6; --cyan: #35c9e9; }}
        .signal-panel::before {{ content: {json.dumps(signal_label)}; }}
    </style>
</head>
<body>
    <main class="p53-page">
        <header class="p53-nav">
            <nav class="p53-trace" aria-label="P53 path">
                <a id="p53-trace-archive" href="../index.html">GSI</a><span class="trace-separator">→</span>
                <a id="p53-trace-filter" class="hidden" href="../index.html"></a><span id="p53-trace-filter-separator" class="trace-separator hidden">→</span>
                <a id="p53-trace-artist" class="hidden" href="../index.html"></a><span id="p53-trace-artist-separator" class="trace-separator hidden">→</span>
                <a id="p53-radio-index" href="index.html">RADIO P53</a>
            </nav>
            <button class="share-transmission" id="share-transmission" type="button">SHARE</button>
        </header>
        <section class="transmission">
            <div class="protein-panel"><img src="../covers/P53_cover.jpg" alt="Expressive P53 protein artwork"></div>
            <div class="signal-panel">
                {cover_html}
                <h1>{html.escape(item["track"])}</h1>
                <p class="artist">{html.escape(item["artist"])}</p>
                <p class="album">{html.escape(item["album"])}</p>
                {streaming_links_html}
                {entry_counterpart_html}
            </div>
        </section>
        <div class="p53-details">
            <aside class="p53-about">
                <h2>WHY P53?</h2>
                <p>{html.escape(about_text)}</p>
            </aside>
            {note_html}
        </div>
    </main>
    <script id="p53-transmission-context" type="application/json">{p53_context_json}</script>
    <script src="../scripts/gsi-context.js"></script>
    <script src="../scripts/p53-transmission.js"></script>
</body>
</html>
"""
    output_path = SITE_P53_DIR / output_name
    output_path.write_text(html_page, encoding = "utf-8")
    print(f"Built P53 transmission: {output_path}")


def build_p53_archive(history: list[dict], current_slug: str) -> None:
    """Build the Radio P53 landing page as a readable, continuous transmission field."""
    current = next((item for item in history if item["slug"] == current_slug), None)
    remaining = [item for item in history if item["slug"] != current_slug]
    if current is None and remaining:
        current, remaining = remaining[0], remaining[1:]

    transmissions = [current, *remaining] if current else remaining
    total = len(transmissions)

    def cover(item: dict, eager: bool = False) -> str:
        if item.get("cover_file"):
            loading = 'loading="eager" fetchpriority="high"' if eager else 'loading="lazy" decoding="async"'
            return f'<img src="../covers/{html.escape(item["cover_file"], quote = True)}" alt="{html.escape(item["album"], quote = True)} cover" {loading}>'
        return '<div class="cover-missing" aria-hidden="true">P53</div>'

    def transmission_card(item: dict, index: int) -> str:
        number = str(index + 1).zfill(2)
        state = "CURRENT TRANSMISSION" if index == 0 else "PAST TRANSMISSION"
        current_class = " is-current" if index == 0 else ""
        watermark = '<div class="card-watermark" aria-hidden="true"><span>RADIO</span><span>P53</span></div>' if index == 0 else ""
        return f'''<li class="transmission-card{current_class}" id="signal-{number}" data-index="{index}" style="--accent:{item["accent"]}">
    <a class="transmission-card-link" {'aria-current="true"' if index == 0 else ''} data-base-href="{html.escape(item["slug"], quote = True)}.html" href="{html.escape(item["slug"], quote = True)}.html">
        <div class="transmission-art">{cover(item, eager=index == 0)}</div>
        <div class="transmission-copy">{watermark}<div class="copy-content"><span class="signal-state">{state}</span><h2>{html.escape(item["track"])}</h2><p>{html.escape(item["artist"])}</p><small>{html.escape(item["album"])}</small><b>ENTER TRANSMISSION ↗</b></div></div>
    </a>
</li>'''

    cards_html = "".join(transmission_card(item, index) for index, item in enumerate(transmissions))
    page = f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#25152b"><link rel="icon" href="../covers/GSI_favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="../styles/gsi-tokens.css">
<title>Radio P53 — GSI</title><link rel="stylesheet" href="../styles/p53-landing.css"></head><body><main class="p53-landing"><nav class="p53-path" aria-label="GSI path"><a id="p53-home-return" href="../index.html">GSI</a><span>→ RADIO P53</span></nav><header><span>{str(total).zfill(2)} TRANSMISSIONS</span><h1>RADIO P53</h1><div class="p53-intro"><p id="p53-description">The ever-changing list of songs that hold a current value, scroll down to travel back in time.</p></div></header><ol class="transmission-list" aria-label="Radio P53 transmissions">{cards_html}</ol></main><script src="../scripts/gsi-context.js"></script><script src="../scripts/p53-landing.js"></script></body></html>'''
    output_path = SITE_P53_DIR / "index.html"
    output_path.write_text(page, encoding = "utf-8")
    print(f"Built Radio P53 landing: {output_path}")


def build_artist_pages(artist_groups: dict[str, list[dict]], config: dict | None = None) -> None:
    """Create artist rooms from one shared catalogue-eligibility inventory."""
    expected_pages = {f"{slugify(artist)}.html" for artist in artist_groups}
    for old_page in SITE_ARTISTS_DIR.glob("*.html"):
        if old_page.name not in expected_pages:
            old_page.unlink()
            print(f" Removed stale generated artist room: {old_page}")

    artist_config = config or load_config(CONFIG_FILE)
    artist_notes = artist_config.get("artist_notes", {})
    album_notes = artist_config.get("album_notes", {})
    for artist, artist_tracks in artist_groups.items():
        artist_slug = slugify(artist)
        artist_asset = resolve_artist_asset(artist, artist_config, ARTIST_ASSETS_DIR)
        artist_image_html = artist_image_markup(artist_asset, artist)
        artist_heading_class = "artist-heading has-artist-image" if artist_image_html else "artist-heading"
        note = str(artist_notes.get(artist, "")).strip()
        note_html = f'<div class="artist-note">{simple_markdown_to_html(note)}</div>' if note else ""
        albums: dict[str, list[dict]] = {}
        for item in artist_tracks:
            albums.setdefault(item["album"], []).append(item)
        grouped_albums = [(album, items) for album, items in albums.items() if len(items) >= 2]
        grouped_slugs = {item["slug"] for _, items in grouped_albums for item in items}

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

        album_sections = []
        for album, items in grouped_albums:
            album_href = f'../albums/{slugify(f"{artist}-{album}")}.html'
            album_title_link = (
                f'<a class="album-title-link" data-context-base-href="{html.escape(album_href, quote=True)}" '
                f'href="{html.escape(album_href, quote=True)}">{html.escape(album)}</a>'
            )
            album_note = str(album_notes.get(artist, {}).get(album, "")).strip()
            album_note_html = f'<div style="margin:9px 0 0;color:rgba(255,255,255,.64);font-size:13px;line-height:1.4">{simple_markdown_to_html(album_note)}</div>' if album_note else ""
            album_sections.append(f'''<section class="album-stack" style="--accent:{items[0]["accent"]}">
                <header><img src="../covers/{html.escape(items[0]["cover_file"], quote=True)}" alt="{html.escape(album, quote=True)} cover"><div style="min-width:0"><span style="display:block;margin-bottom:6px;color:color-mix(in srgb,var(--accent),white 24%);font-size:9px;font-weight:950;letter-spacing:.18em">ALBUM</span><h2>{album_title_link}</h2>{album_note_html}</div></header>
                <div>{''.join(entry_tile(item, compact=True) for item in items)}</div>
            </section>''')
        albums_html = "".join(album_sections)
        remaining_html = "".join(entry_tile(item) for item in artist_tracks if item["slug"] not in grouped_slugs)
        page = f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><meta name="theme-color" content="#0d0d0f"><link rel="icon" href="../covers/GSI_favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="../styles/gsi-tokens.css"><title>{html.escape(artist)} — GSI</title><style>
*{{box-sizing:border-box}}body{{margin:0;min-height:100vh;color:#f2f2f2;font-family:var(--gsi-reading-font,Arial,sans-serif);background:radial-gradient(circle at 82% 12%,rgba(99,199,255,.12),transparent 27%),repeating-linear-gradient(90deg,rgba(255,255,255,.025) 0 1px,transparent 1px 13px),#0d0d0f}}main{{width:min(1120px,calc(100% - 36px));margin:auto;padding:22px 0 80px}}nav{{display:flex;align-items:center;gap:9px;padding:13px 16px;border:1px solid rgba(255,255,255,.16);border-radius:20px 6px;background:rgba(13,13,15,.86)}}nav a{{color:#ff8bc2;text-decoration:none;font-size:12px;font-weight:950;letter-spacing:.14em}}nav span{{color:rgba(255,255,255,.35)}}nav strong{{color:rgba(255,255,255,.72);font-size:11px;letter-spacing:.14em}}.artist-heading{{padding:clamp(48px,9vw,112px) 0 32px}}.artist-heading>span{{color:#ff8bc2;font-size:10px;font-weight:950;letter-spacing:.18em}}.artist-heading h1{{max-width:900px;margin:12px 0 0;font-size:clamp(64px,12vw,154px);line-height:.78;letter-spacing:-.065em;overflow-wrap:anywhere}}.artist-note{{max-width:620px;margin:22px 0 0;color:rgba(255,255,255,.68);line-height:1.55}}.artist-note p{{margin:0}}.album-stack{{margin:0 0 14px;overflow:hidden;border:1px solid color-mix(in srgb,var(--accent),white 22%);border-radius:30px 8px 30px 8px;background:linear-gradient(135deg,color-mix(in srgb,var(--accent),transparent 84%),rgba(13,13,15,.95))}}.album-stack>header{{display:grid;grid-template-columns:116px 1fr;align-items:center;gap:18px;padding:0 20px 0 0;border-bottom:1px solid color-mix(in srgb,var(--accent),transparent 68%)}}.album-stack>header img{{width:116px;height:116px;object-fit:cover}}.album-stack>header h2{{margin:0;font-size:clamp(30px,5vw,60px);line-height:.88;letter-spacing:-.04em}}.album-stack>div{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:8px;padding:12px}}.album-entry,.artist-signal{{display:grid;align-items:center;min-height:76px;overflow:hidden;color:#fff;text-decoration:none;border:1px solid color-mix(in srgb,var(--accent),white 18%);border-radius:18px 5px 18px 5px;background:rgba(0,0,0,.2);transition:transform .24s ease,border-radius .3s ease}}.album-entry{{grid-template-columns:16px minmax(0,1fr) auto;gap:10px;padding:0 12px}}.album-entry-mark{{width:8px;height:8px;border-radius:2px 7px 2px 7px;background:color-mix(in srgb,var(--accent),white 34%);box-shadow:0 0 12px color-mix(in srgb,var(--accent),transparent 45%)}}.album-entry h3{{min-width:0;margin:0;font-size:17px;line-height:.96;overflow-wrap:anywhere}}.album-entry b{{display:block;padding-left:8px;color:color-mix(in srgb,var(--accent),white 34%);font-size:9px;letter-spacing:.12em;white-space:nowrap}}.album-entry[data-entry-kind="transmission"] b{{color:color-mix(in srgb,var(--accent),white 55%)}}.album-entry:hover,.artist-signal:hover,.album-entry:focus-visible,.artist-signal:focus-visible{{transform:translateY(-3px);border-radius:5px 18px 5px 18px}}.artist-signal{{grid-template-columns:64px 1fr}}.artist-signal img{{width:64px;height:76px;object-fit:cover}}.artist-signal>div{{min-width:0;padding:10px}}.artist-signal h2{{margin:0;font-size:17px;line-height:.96}}.artist-signal p{{margin:5px 0 0;color:rgba(255,255,255,.55);font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}.artist-signal{{grid-template-columns:104px 1fr auto;min-height:112px;margin-top:9px;border-radius:22px 7px 22px 7px;background:linear-gradient(135deg,color-mix(in srgb,var(--accent),transparent 88%),rgba(13,13,15,.92))}}.artist-signal img{{width:104px;height:112px}}.artist-signal h2{{font-size:clamp(23px,3vw,37px)}}.artist-signal b{{padding:16px;color:color-mix(in srgb,var(--accent),white 34%);font-size:10px;letter-spacing:.12em}}@media(max-width:700px){{main{{width:min(100% - 24px,620px);padding-top:12px}}.artist-heading{{padding:52px 0 26px}}.album-stack>header{{grid-template-columns:88px 1fr;padding-right:14px}}.album-stack>header img{{width:88px;height:88px}}.album-stack>header img{{width:88px;height:88px}}.album-stack>div{{grid-template-columns:1fr}}.album-entry{{min-height:68px}}.album-entry b{{display:none}}.album-entry[data-entry-kind="transmission"] b{{display:block;padding:0 8px 0 0;font-size:9px}}.artist-signal{{grid-template-columns:82px 1fr}}.artist-signal img{{width:82px;height:104px}}.artist-signal b{{display:none}}}}@media(prefers-reduced-motion:reduce){{*,*::before,*::after{{animation-duration:.01ms!important;transition-duration:.01ms!important}}}}
/* Optional artist art is opt-in and sits inside the same identity field as the name. */
.artist-heading-copy{{position:relative;z-index:1;min-width:0}}
.artist-heading.has-artist-image{{position:relative;display:grid;grid-template-columns:minmax(0,1fr) minmax(260px,38%);align-items:center;gap:clamp(28px,5vw,76px);margin:clamp(42px,8vw,96px) 0 clamp(30px,5vw,52px);padding:clamp(30px,5vw,58px) clamp(24px,5vw,66px);overflow:hidden;border:1px solid color-mix(in srgb,#ff4fa3,white 22%);border-radius:34px 8px 34px 8px;background:linear-gradient(118deg,rgba(255,79,163,.12),rgba(73,217,239,.055) 74%),repeating-linear-gradient(90deg,rgba(255,255,255,.028) 0 1px,transparent 1px 14px),rgba(13,13,15,.72);box-shadow:0 24px 60px rgba(0,0,0,.28);isolation:isolate}}
.artist-heading.has-artist-image::before{{position:absolute;inset:12px;z-index:0;border:1px solid rgba(255,255,255,.09);border-radius:24px 5px 24px 5px;content:"";pointer-events:none}}
.artist-heading.has-artist-image::after{{position:absolute;right:-12%;bottom:-52%;width:66%;height:100%;z-index:0;background:radial-gradient(ellipse,color-mix(in srgb,#49d9ef,transparent 85%),transparent 68%);content:"";pointer-events:none}}
.artist-heading.has-artist-image .artist-heading-copy{{order:1}}
.artist-heading.has-artist-image h1{{font-size:clamp(60px,8vw,116px);line-height:.84;letter-spacing:-.06em}}
.artist-image-header{{position:relative;z-index:1;display:flex;align-items:center;justify-content:center;min-width:0;min-height:clamp(220px,30vw,420px);margin:0;padding:0;border:0;background:none;box-shadow:none}}
.artist-image-header::after{{display:none}}
.artist-image{{display:block;width:auto;max-width:100%;height:auto;max-height:clamp(220px,32vw,420px);object-fit:contain;border-radius:10px 3px 10px 3px;filter:drop-shadow(0 18px 24px rgba(0,0,0,.32))}}
.album-title-link{{color:inherit;text-decoration:none}}
.album-title-link:hover,.album-title-link:focus-visible{{color:color-mix(in srgb,var(--accent),white 28%);text-decoration:underline;text-decoration-thickness:2px;text-underline-offset:5px}}
@media(max-width:700px){{.artist-heading.has-artist-image{{grid-template-columns:1fr;gap:24px;margin:38px 0 30px;padding:24px 18px 30px;border-radius:26px 7px 26px 7px}}.artist-heading.has-artist-image .artist-image-header{{order:1}}.artist-heading.has-artist-image .artist-heading-copy{{order:2}}.artist-heading.has-artist-image::before{{inset:9px;border-radius:18px 4px 18px 4px}}.artist-image-header{{min-height:260px}}.artist-image{{max-height:260px}}}}
/* Album headings use their own padding and rounded cover, so the label is never mistaken for an overflow artifact. */
.album-stack>header{{grid-template-columns:120px minmax(0,1fr);align-items:center;gap:16px;padding:16px;border-bottom:1px solid color-mix(in srgb,var(--accent),transparent 68%)}} .album-stack>header img{{width:120px;height:120px;border-radius:14px 4px 14px 4px}} .album-stack>header h2{{font-size:clamp(32px,5vw,60px)}} .album-stack>header p{{margin:0}} @media(max-width:700px){{.album-stack>header{{grid-template-columns:88px minmax(0,1fr);gap:13px;padding:13px}} .album-stack>header img{{width:88px;height:88px;border-radius:11px 3px 11px 3px}} .album-stack>header h2{{font-size:32px}}}}
</style></head><body><main><nav aria-label="GSI path"><a id="artist-archive-return" href="../index.html">GSI</a><span>→</span><a id="artist-filter-return" hidden href="../index.html"></a><span id="artist-filter-separator" hidden>→</span><strong>{html.escape(artist).upper()}</strong></nav><header class="{artist_heading_class}"><div class="artist-heading-copy"><span>ARTIST SIGNALS / {len(artist_tracks):02d}</span><h1>{html.escape(artist)}</h1>{note_html}</div>{artist_image_html}</header>{albums_html}<section class="artist-signals">{remaining_html}</section></main><script id="artist-room-data" type="application/json">{json.dumps({"filterKeys": list(artist_config.get("filters", {}).keys()), "filterLabels": {key: value.get("label", key) for key, value in artist_config.get("filters", {}).items()}, "artistSlug": artist_slug}, ensure_ascii=False).replace("</", "<\\/")}</script><script src="../scripts/gsi-context.js"></script><script src="../scripts/artist-room.js"></script></body></html>'''
        output_path = SITE_ARTISTS_DIR / f"{artist_slug}.html"
        output_path.write_text(page, encoding="utf-8")
        print(f"Built artist room: {output_path}")


def build_album_pages(tracks: list[dict], artist_groups: dict[str, list[dict]] | None = None) -> None:
    """Build a focused room for albums represented by at least two signals."""
    config = load_config(CONFIG_FILE)
    notes = config.get("album_notes", {})
    grouped: dict[tuple[str, str], list[dict]] = {}
    for item in tracks:
        grouped.setdefault((item["artist"], item["album"]), []).append(item)
    for (artist, album), items in grouped.items():
        if len(items) < 2:
            continue
        slug = slugify(f"{artist}-{album}")
        accent = items[0]["accent"]
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
        page = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="../styles/gsi-tokens.css"><title>{html.escape(album)} — GSI</title><style>
*{{box-sizing:border-box}}body{{margin:0;min-height:100vh;color:#f2f2f2;font-family:var(--gsi-reading-font,Arial,sans-serif);background:radial-gradient(circle at 80% 10%,color-mix(in srgb,{accent},transparent 72%),transparent 34%),repeating-linear-gradient(90deg,rgba(255,255,255,.025) 0 1px,transparent 1px 14px),#0d0d0f}}main{{width:min(980px,calc(100% - 32px));margin:auto;padding:24px 0 80px}}nav{{display:flex;gap:10px;align-items:center;padding:13px 16px;border:1px solid color-mix(in srgb,{accent},white 20%);border-radius:20px 6px;background:rgba(13,13,15,.85);font-size:11px;font-weight:900;letter-spacing:.14em}}nav a{{color:color-mix(in srgb,{accent},white 35%);text-decoration:none}}nav span{{color:rgba(255,255,255,.35)}}header{{display:grid;grid-template-columns:minmax(260px,42%) 1fr;gap:38px;align-items:center;padding:clamp(52px,10vw,120px) 0 42px}}.album-cover{{display:block;width:100%;aspect-ratio:1;object-fit:cover;border:2px solid {accent};border-radius:30px 8px 30px 8px;box-shadow:0 0 34px color-mix(in srgb,{accent},transparent 65%)}}.kicker{{color:color-mix(in srgb,{accent},white 28%);font-size:10px;font-weight:950;letter-spacing:.18em}}h1{{margin:12px 0 8px;font-size:clamp(46px,8vw,104px);line-height:.86;letter-spacing:-.06em;overflow-wrap:anywhere}}.artist{{margin:0;color:rgba(255,255,255,.66);font-size:20px}}.artist-link{{color:inherit;text-decoration:none}}.artist-link:hover,.artist-link:focus-visible{{color:color-mix(in srgb,{accent},white 35%);text-decoration:underline;text-underline-offset:5px}}.songs{{display:grid;gap:12px}}.album-song{{display:flex;justify-content:space-between;align-items:center;gap:14px;padding:21px 24px;color:#fff;text-decoration:none;border:1px solid color-mix(in srgb,{accent},white 18%);border-radius:22px 7px 22px 7px;background:linear-gradient(110deg,color-mix(in srgb,{accent},transparent 86%),rgba(13,13,15,.82));font-size:clamp(20px,3vw,30px);font-weight:850;transition:transform .2s ease,border-radius .25s ease,background .25s ease}}.album-song:hover,.album-song:focus-visible{{transform:translateX(6px);border-radius:7px 22px 7px 22px;background:linear-gradient(110deg,color-mix(in srgb,{accent},transparent 76%),rgba(13,13,15,.82))}}.album-song b{{color:color-mix(in srgb,{accent},white 32%);font-size:9px;letter-spacing:.12em;white-space:nowrap}}.album-note{{max-width:700px;margin:34px 0 0;padding:22px 26px 24px;border-left:3px solid {accent};border-radius:4px 20px 20px 4px;background:linear-gradient(100deg,color-mix(in srgb,{accent},transparent 88%),rgba(13,13,15,.46));color:rgba(255,255,255,.8);font-size:clamp(16px,2vw,20px);line-height:1.5}}.album-note>span{{display:block;margin-bottom:10px;color:color-mix(in srgb,{accent},white 30%);font-size:9px;font-weight:950;letter-spacing:.16em}}.album-note p{{margin:0}}@media(max-width:680px){{main{{width:min(100% - 24px,560px);padding-top:12px}}header{{grid-template-columns:1fr;gap:22px;padding-top:54px}}.album-cover{{max-width:380px}}.album-note{{font-size:16px;padding:18px 19px 20px}}.album-song{{padding:17px 16px}}}}
</style></head><body><main><nav aria-label="GSI path"><a id="album-archive-return" href="../index.html">GSI</a><span>→</span>{artist_nav}<span>→</span><strong>{html.escape(album.upper())}</strong></nav><header>{cover_html}<div><span class="kicker">ALBUM / {len(items):02d} SIGNALS</span><h1>{html.escape(album)}</h1><p class="artist">{artist_display}</p>{note_html}</div></header><section class="songs" aria-label="Songs in this album">{"".join(song_links)}</section></main><script id="album-room-data" type="application/json">{json.dumps({"filterKeys": list(config.get("filters", {}).keys())}, ensure_ascii=False).replace("</", "<\\/")}</script><script src="../scripts/gsi-context.js"></script><script src="../scripts/album-room.js"></script></body></html>'''
        path = SITE_ALBUMS_DIR / f"{slug}.html"
        path.write_text(page, encoding="utf-8")
        print(f"Built album room: {path}")


def build_index_html(tracks: list[dict]) -> None:  #sample homepage
    config = load_config(CONFIG_FILE)
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
    cards = [] # stores HTML chunks for every song card

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
        card = f"""
        <a class="card"
            data-tags="{tags_for_attr}"
            data-artist="{html.escape(item["artist"], quote = True)}"
            data-album="{html.escape(item["album"], quote = True)}"
            data-album-href="albums/{slugify(item["artist"] + '-' + item["album"])}.html"
            data-p53-order="{p53_order}"
            aria-label="{safe_card_label}"
            data-base-href="{html.escape(item["page_url"], quote = True)}"
            href="{html.escape(item["page_url"], quote = True)}" style="--accent: {item["accent"]}; --p53-order: {p53_order};">
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
        playlist_src, playlist_color = playlist_visuals(playlist_cover, color, BASE)
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

    p53_slug = (config.get("p53_current_slug") or "").strip()
    p53_item = next((item for item in tracks if item["slug"] == p53_slug), None)
    p53_html = ""
    if p53_item:
        p53_html = f"""
        <a class="p53-broadcast" data-base-href="p53/index.html" href="p53/index.html" aria-label="Open Radio P53: current and previous transmissions" style="--signal-accent:{p53_item['accent']}">
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

    filter_data_json = json.dumps(filter_data).replace("</", "<\\/") # turns Python dict into JavaScript object text
    index_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="{safe_meta_description}">
    <meta name="theme-color" content="#0d0d0f">
    <meta property="og:type" content="website">
    <meta property="og:site_name" content="GSI">
    <meta property="og:title" content="{safe_page_title}">
    <meta property="og:description" content="{safe_meta_description}">{homepage_url_meta}{share_image_meta}
    <link rel="icon" href="covers/GSI_favicon.svg" type="image/svg+xml">
    <link rel="stylesheet" href="styles/gsi-tokens.css">
    <link rel="stylesheet" href="styles/gsi-home.css">
    <title>{safe_project_title}</title>
</head>
<body data-view="wall">
    <div class="signal-transform" aria-hidden="true"></div>
    <header class="site-hero">
        <div class="hero-copy">
            <div class="hero-architecture" aria-hidden="true">
                <span>GENOME</span><span>STABILITY</span><span>INDUCERS</span>
            </div>
            <div class="wordmark">GSI</div>
            {intro_html}
        </div>
        {p53_html}
    </header>
    {filters_html}
    <div class="layout-format-controls">
      <div class="view-control" role="group" aria-label="Layout">
        <span class="view-control-label">LAYOUT</span>

        <button class="view-btn" data-view="poster" aria-pressed="false">
            Poster
        </button>

        <button class="view-btn active" data-view="wall" aria-pressed="true">
            Wall
        </button>

        <button class="view-btn" data-view="gallery" aria-pressed="false">
            Gallery
        </button>
      </div>
      <div class="format-control" role="group" aria-label="Format">
        <button class="format-option" data-format-option="songs" type="button" aria-pressed="true">SONGS</button>
        <button class="format-option" data-format-option="albums" type="button" aria-pressed="false">ALBUMS</button>
        <button class="format-option" data-format-option="artists" type="button" aria-pressed="false" disabled aria-disabled="true">ARTISTS</button>
      </div>
      <a class="playlist-card mini-playlist-card hidden" id="playlist-card" href="#" target="_blank" rel="noopener noreferrer">
        <img id="playlist-cover" alt="Playlist cover">
        <span class="playlist-card-text" id="playlist-cta"></span>
      </a>
    </div>
    <div class="grid">
        {''.join(cards)}
    </div>
<script src="scripts/gsi-context.js"></script>
<script id="gsi-filter-data" type="application/json">{filter_data_json}</script>
<script src="scripts/home-page.js"></script>
</body>
</html>
"""  # full HTML page as one string

    index_path = SITE_DIR / "index.html"
    index_path.write_text(index_html, encoding = "utf-8")
    print(f"\nBuilt visual index: {index_path}")

def build_404_page(tracks: list[dict]) -> None:
    config = load_config(CONFIG_FILE)
    copy = config.get("not_found", {}) # editable 404 wording lives in config.json
    site_url = (config.get("site_url") or "").rstrip("/")
    site_path = "/" + site_url.split("/", 3)[-1].split("/", 1)[-1].strip("/") + "/" if ".github.io/" in site_url else "/"
    def recommendation_record(item: dict) -> dict:
        links = resolve_provider_links(item)
        return {
            "track": item["track"],
            "artist": item["artist"],
            "album": item["album"],
            "cover": item.get("cover_file", ""),
            "url": item.get("page_url") or f'entries/{item["html_file"]}',
            "accent": item["accent"],
            "spotify": links["spotify"]["url"],
            "apple": links["apple"]["url"],
        }

    recommendations = [recommendation_record(item) for item in tracks]
    recommendation_json = json.dumps(recommendations, ensure_ascii = False).replace("</", "<\\/")
    not_found_title = html.escape(copy.get("title", "THIS FREQUENCY DOES NOT EXIST."))
    not_found_title = not_found_title.replace(" NOT ", ' <em>NOT</em> ')
    protein_drops = "".join(
        f'<span style="--x:{(index * 17) % 101}%;--delay:-{index * .73:.2f}s;--speed:{9 + index % 7}s;--size:{34 + index % 5 * 13}px"></span>'
        for index in range(18)
    )
    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="robots" content="noindex">
    <meta name="theme-color" content="#0d0d0f">
    <link rel="icon" id="favicon" href="/covers/GSI_favicon.svg" type="image/svg+xml">
    <title>Signal Lost — GSI</title>
    <style>
        :root {{ --pink:#ff4fa3; --cyan:#39c8e8; --paper:#f1ede3; --ink:#0d0d0f; }}
        * {{ box-sizing:border-box; }}
        body {{ margin:0; min-height:100vh; overflow:hidden; color:var(--paper); font-family:Arial,sans-serif; background:#0d0d0f; }}
        body::before {{ content:""; position:fixed; inset:0; background:repeating-linear-gradient(92deg, transparent 0 54px, rgba(255,255,255,.025) 55px), radial-gradient(circle at 72% 20%, rgba(255,79,163,.16), transparent 36%); }}
        .protein-rain {{ position:fixed; inset:0; overflow:hidden; opacity:.3; pointer-events:none; }}
        .protein-rain span {{ position:absolute; left:var(--x); top:-100px; width:var(--size); aspect-ratio:1; background:url("covers/P53_cover.jpg") center/420%; border-radius:62% 38% 67% 33% / 42% 58% 42% 58%; clip-path:polygon(46% 0,64% 11%,72% 30%,95% 41%,83% 58%,96% 78%,72% 92%,51% 78%,30% 100%,18% 73%,0 58%,17% 39%,8% 17%,32% 21%); filter:grayscale(.6) contrast(1.35) drop-shadow(7px 4px 0 rgba(255,79,163,.45)); animation:dissolve var(--speed) linear var(--delay) infinite; }}
        .protein-rain span:nth-child(3n) {{ background-position:20% 74%; }}
        .protein-rain span:nth-child(3n+1) {{ background-position:78% 28%; }}
        @keyframes dissolve {{ 0% {{ transform:translateY(-15vh) rotate(0); opacity:0; }} 12% {{ opacity:.8; }} 72% {{ opacity:.34; filter:blur(0) drop-shadow(9px 4px 0 rgba(255,79,163,.5)); }} 100% {{ transform:translateY(125vh) rotate(220deg) scale(.35); opacity:0; filter:blur(5px); }} }}
        main {{ position:relative; z-index:1; width:min(1160px, calc(100% - 36px)); min-height:100vh; margin:auto; display:grid; grid-template-columns:minmax(0,1.25fr) minmax(280px,.75fr); align-items:center; gap:clamp(24px,6vw,80px); }}
        .eyebrow {{ color:var(--pink); font-size:12px; font-weight:900; letter-spacing:.24em; }}
        h1 {{ max-width:820px; margin:16px 0 22px; font-family:Impact,Haettenschweiler,"Arial Black",sans-serif; font-size:clamp(62px,8.8vw,142px); line-height:.79; letter-spacing:-.045em; text-shadow:8px 5px 0 rgba(0,0,0,.9), 12px 5px 0 rgba(255,79,163,.72), -6px -2px 0 rgba(57,200,232,.7); transform:skew(-4deg); }}
        h1 em {{ display:block; width:max-content; color:var(--pink); font-style:normal; font-size:1.36em; line-height:.68; transform:translateX(clamp(18px,6vw,82px)) skew(7deg); text-shadow:7px 5px 0 #000, -5px 0 0 var(--cyan); }}
        .message {{ max-width:620px; font-size:clamp(17px,2vw,23px); line-height:1.5; color:rgba(241,237,227,.72); }}
        .home {{ display:inline-flex; margin-top:24px; padding:15px 22px; color:var(--ink); background:var(--paper); border-radius:24px 7px 24px 7px; font-size:12px; font-weight:900; letter-spacing:.15em; text-decoration:none; transition:transform .25s ease,border-radius .35s ease; }}
        .home:hover,.home:focus-visible {{ transform:translateY(-4px) rotate(-1deg); border-radius:7px 24px 7px 24px; }}
        .recommendation {{ overflow:hidden; color:var(--paper); border:2px solid var(--accent,var(--pink)); border-radius:18px 52px 18px 52px; background:#141417; box-shadow:10px 10px 0 color-mix(in srgb,var(--accent),transparent 65%); }}
        .recommendation img {{ display:block; width:100%; aspect-ratio:1; object-fit:cover; background:#222; }}
        .signal-copy {{ padding:20px; }}
        .signal-copy span {{ color:color-mix(in srgb,var(--accent),white 44%); font-size:10px; font-weight:900; letter-spacing:.2em; }}
        .signal-copy strong {{ display:block; margin-top:10px; font-size:clamp(25px,4vw,44px); line-height:.95; }}
        .signal-copy small {{ display:block; margin-top:8px; color:rgba(255,255,255,.64); font-size:15px; }}
        .signal-actions {{ display:grid; grid-template-columns:1fr 1fr; gap:7px; margin-top:16px; }}
        .signal-actions a {{ padding:11px 10px; color:var(--paper); border:1px solid rgba(255,255,255,.22); border-radius:16px 5px 16px 5px; font-size:10px; font-weight:900; letter-spacing:.08em; text-align:center; text-decoration:none; transition:transform .22s ease,border-radius .3s ease; }}
        .signal-actions a:hover,.signal-actions a:focus-visible {{ transform:translateY(-3px); border-radius:5px 16px 5px 16px; }}
        .signal-actions .read {{ grid-column:1/-1; color:color-mix(in srgb,var(--accent),white 45%); }}
        @media(max-width:760px) {{ body {{ overflow-x:hidden; overflow-y:auto; }} main {{ min-height:100svh; grid-template-columns:1fr; padding:58px 0; }} h1 {{ font-size:clamp(58px,20.5vw,90px); }} .recommendation {{ width:min(100%,390px); }} }}
        @media(prefers-reduced-motion:reduce) {{ *,*::before,*::after {{ animation-duration:.01ms!important; transition-duration:.01ms!important; }} }}
    </style>
</head>
<body>
    <div class="protein-rain" aria-hidden="true">{protein_drops}</div>
    <main>
        <section>
            <div class="eyebrow">{html.escape(copy.get("eyebrow", "SIGNAL LOST / 404"))}</div>
            <h1>{not_found_title}</h1>
            <p class="message">{html.escape(copy.get("message", "The page slipped out of GSI."))}</p>
            <a class="home" id="home-link" href="./">RETURN TO GSI</a>
        </section>
        <article class="recommendation" id="recommendation" style="--accent:#ff4fa3">
            <img id="signal-cover" alt="">
            <div class="signal-copy">
                <span>{html.escape(copy.get("recommendation_label", "INTERCEPTED SIGNAL"))}</span>
                <strong id="signal-track"></strong>
                <small id="signal-artist"></small>
                <div class="signal-actions">
                    <a id="signal-spotify" href="#" target="_blank" rel="noopener noreferrer">SPOTIFY ↗</a>
                    <a id="signal-apple" href="#" target="_blank" rel="noopener noreferrer">APPLE MUSIC ↗</a>
                    <a class="read" id="signal-read" href="#">OPEN SIGNAL IN GSI</a>
                </div>
            </div>
        </article>
    </main>
    <script>
        const tracks = {recommendation_json};
        const deployedRoot = {json.dumps(site_path)};
        const root = location.hostname.endsWith("github.io") ? deployedRoot : "/";
        const selected = tracks[Math.floor(Math.random() * tracks.length)]; // new signal on every 404 visit
        document.querySelector("#favicon").href = root + "covers/GSI_favicon.svg";
        document.querySelector("#home-link").href = root;
        const card = document.querySelector("#recommendation");
        card.style.setProperty("--accent", selected.accent);
        const cover = document.querySelector("#signal-cover");
        cover.src = root + "covers/" + selected.cover;
        cover.alt = selected.album + " cover";
        document.querySelector("#signal-track").textContent = selected.track;
        document.querySelector("#signal-artist").textContent = selected.artist;
        document.querySelector("#signal-spotify").href = selected.spotify;
        document.querySelector("#signal-apple").href = selected.apple;
        document.querySelector("#signal-read").href = root + selected.url;
    </script>
</body>
</html>
"""
    not_found_path = SITE_DIR / "404.html"
    not_found_path.write_text(page, encoding = "utf-8")
    print(f"Built playful 404 page: {not_found_path}")


def write_catalog_manifest(items: list[dict]) -> None:
    """Write deterministic link and local-art metadata for build-time auditing."""
    cover_root = COVERS_DIR.resolve()
    records = []
    for item in items:
        cover_file = (item.get("cover_file") or "").replace("\\", "/")
        cover_path = (COVERS_DIR / cover_file).resolve() if cover_file else None
        try:
            if cover_path is None:
                raise ValueError("no cover")
            cover_path.relative_to(cover_root)
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
        records.append(catalogue_record(item, COVERS_DIR, cover_metadata))

    manifest = {
        "schema": 1,
        "description": "Generated GSI media-link and local-art inventory; review prose is never included.",
        "signals": records,
    }
    manifest_path = SITE_DATA_DIR / "catalog.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii = False, indent = 2) + "\n",
        encoding = "utf-8",
    )
    print(f"Wrote catalogue manifest: {manifest_path}")

def main() -> None:
    parser = argparse.ArgumentParser(description = "Build the GSI static website.")
    parser.add_argument(
        "--site-only",
        action = "store_true",
        help = "Generate site files without creating or updating entries and covers.",
    )
    parser.add_argument(
        "--validate-links",
        action = "store_true",
        help = "Check generated internal pages, assets, and stable route attributes after building.",
    )
    args = parser.parse_args()
    tracks = build_entries(write_sources = not args.site_only)
    config = load_config(CONFIG_FILE)
    p53_history = prepare_p53_history(config, tracks, download_missing = not args.site_only)
    archive_tracks = merge_p53_into_archive(tracks, p53_history)
    artist_groups = artist_room_groups(tracks, p53_history)
    artist_counts = {
        artist: len(items)
        for artist, items in artist_groups.items()
    }
    copy_site_covers(COVERS_DIR, SITE_COVERS_DIR)
    copy_site_artist_assets(ARTIST_ASSETS_DIR, SITE_ARTIST_ASSETS_DIR)
    copy_site_scripts(WEB_DIR, SITE_SCRIPTS_DIR)
    copy_site_styles(WEB_DIR, SITE_STYLES_DIR)
    write_catalog_manifest(archive_tracks)
    write_artist_manifest(
        artist_catalogue_records(artist_groups, config, ARTIST_ASSETS_DIR),
        SITE_DATA_DIR / "artists.json",
    )
    remove_stale_entry_pages(tracks)
    for item in tracks:
        build_entry_page(item, artist_counts)
    p53_slug = (config.get("p53_current_slug") or "").strip()
    for item in p53_history:
        build_p53_page(item, f'{item["slug"]}.html')
    p53_item = next((item for item in p53_history if item["slug"] == p53_slug), None)
    if p53_item:
        build_p53_page(p53_item, "latest.html")
    if p53_history:
        build_p53_archive(p53_history, p53_slug)
    build_artist_pages(artist_groups, config)
    build_album_pages(archive_tracks, artist_groups)
    build_index_html(archive_tracks)
    build_404_page(archive_tracks)
    if args.validate_links:
        link_errors = validate_generated_links(SITE_DIR)
        if link_errors:
            print("\nGenerated link validation failed:")
            for error in link_errors:
                print(f" - {error}")
            raise SystemExit(1)
        print("\nValidated generated local links and assets.")
    print("\nDone.")

if __name__ == "__main__":
    main()


