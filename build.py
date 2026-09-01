import argparse # command-line options such as the source-safe site build
import csv #so I can read csv files per rows of organized data
import json #so I can change the categories at ease via config.json
import re # so I can clean file names?
import html # escapes review text before placing it
import colorsys # we need proper accent colors for material you effect
import shutil # for copying files and folders
from pathlib import Path # cross OS handling
from urllib.parse import quote, quote_plus # allows search text to be URL safe
import requests # web requests
from PIL import Image # read covers and extract colors

BASE = Path(__file__).resolve().parent # THIS folder
ENTRIES_DIR = BASE / "entries" # markdown file generation path
COVERS_DIR = BASE / "covers" # album cover saving path
SITE_DIR = BASE / "site" #HTML index creation path
SITE_ENTRIES_DIR = SITE_DIR / "entries" #review page
SITE_COVERS_DIR = SITE_DIR / "covers"
SITE_P53_DIR = SITE_DIR / "p53"

TRACKS_FILE = BASE / "tracks.csv" #list of song inputs
CONFIG_FILE = BASE / "config.json" #settings file

ENTRIES_DIR.mkdir(exist_ok = True) #creates entry folder, but not on repeat
COVERS_DIR.mkdir(exist_ok = True)
SITE_DIR.mkdir(exist_ok = True)
SITE_ENTRIES_DIR.mkdir(exist_ok = True) #creates entries
SITE_P53_DIR.mkdir(exist_ok = True)

def slugify(text: str) -> str: #safe file name
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text) #nonletters replaced with "-"
    return text.strip("-") #remove extra "-" from the start

def load_config() -> dict: #settings loaded as a dictionary
    with open(CONFIG_FILE, "r", encoding = "utf-8") as file: #Turkish character wall
        return json.load(file)

def read_tracks() -> list[dict]:
    with open(TRACKS_FILE, "r", encoding = "utf-8") as file:
        return list(csv.DictReader(file))

def ordered_tracks(rows: list[dict], config: dict) -> list[dict]:
    has_manual_order = False
    for row in rows:
        order_text = (row.get("order") or "").strip()
        if order_text.isdigit():
            has_manual_order = True
            break
    if has_manual_order:
        def sort_key(row: dict) -> int:
            order_text = (row.get("order") or "").strip()
            if order_text.isdigit():
                return int(order_text)
            return 999999

        return sorted(rows, key = sort_key)
    if config.get("newest_first", False):
        return list(reversed(rows))
    return rows


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

def dominant_color(image_path: Path) -> str:
    try: # catch corrupt images that PILLOW cannot identify
        image = Image.open(image_path).convert("RGB")
    except (OSError, ValueError) as error:
        print(f" Could not read image: {image_path}")
        print(f" Reason: {error}")
        return "#888888"
    image = image.resize((120, 120)) # SHRINK FOR FASTER

    reduced = image.quantize(colors = 14).convert("RGB") #SIX MAIN COLORS!!
    colors = reduced.getcolors(120 * 120)  #for quantification check

    if colors is None:
        return "#888888" #some color
    best_color = None
    best_score = -1
    for count, (r, g, b) in colors:
        h, s, v = colorsys.rgb_to_hsv(r /255, g /255, b /255) #SATURATION, WE NEED BRIGHT
        if v < 0.18: #reject dark shit
            continue
        if v > 0.94 and s < 0.25: # eliminate white and gray
            continue
        if s < 0.18: # reject more gray
            continue
        score = (s * 2.4 + v * 0.8) * (count ** 0.45) #FAVOR VIVID ONES OMMMMG
        if score > best_score: #hierarchy
            best_score = score
            best_color = (r, g, b)
    if best_color is None:
         colors.sort(reverse = True) # Most common comes first
         best_color = colors[0][1] # extract values
    r, g, b = best_color
    return f"#{r:02x}{g:02x}{b:02x}" # hex color code
def copy_site_covers() -> None:
    if SITE_COVERS_DIR.exists():
        shutil.rmtree(SITE_COVERS_DIR) # remove old covers
    shutil.copytree(COVERS_DIR, SITE_COVERS_DIR) # copy new covers
    print(f" Copied covers into generated site: {SITE_COVERS_DIR}")
def playlist_visuals(playlist_cover: str, fallback_color: str) -> tuple[str, str]:
    playlist_cover = (playlist_cover or "").strip()
    if not playlist_cover:
        return "", fallback_color
    cover_path = BASE / playlist_cover
    if not cover_path.exists():
        print(f" Playlist cover not found: {playlist_cover}")
        return "", fallback_color #prevent crash
    browser_src = playlist_cover.replace("\\","/")
    playlist_color = dominant_color(cover_path)
    return browser_src, playlist_color #extract and return color
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
    config = load_config() #read settings
    sections = config["sections"]
    site_url = (config.get("site_url") or "").rstrip("/")
    force_refresh_covers = config.get("force_refresh_covers", False)
    built_tracks = [] #store metadata for HTML gallery

    for row in ordered_tracks(read_tracks(), config): #loop songs in tracks.csv
        artist = row["artist"].strip()
        track = row["track"].strip()
        album = row["album"].strip() #cleanup
        manual_cover_url = (row.get("cover_url") or "").strip()
        manual_cover_file = (row.get("cover_file") or "").strip()
        tags = (row.get("tags") or "").strip()
        manual_accent = (row.get("accent") or "").strip()
        spotify_url = (row.get("spotify_url") or "").strip() #optional
        apple_url = (row.get("apple_url") or "").strip()

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
            "spotify_url": spotify_url,
            "apple_url": apple_url
        })
    return built_tracks # HTML builder save
def simple_markdown_to_html(markdown_text: str) -> str:
    text = html.escape(markdown_text.strip())
    text = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", text) #apparently allows bold writing with **
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()] #blank lines as paragraph breaks
    return "\n".join([f"<p>{p.replace(chr(10), '<br>')}</p>" for p in paragraphs]) #keep single line breaks
def make_streaming_links(item: dict) -> str:
    search_text = f"{item['artist']} {item['track']}"
    spotify_query = quote(search_text, safe="")
    apple_query = quote_plus(search_text)

    spotify_url = item.get("spotify_url") or f"https://open.spotify.com/search/{spotify_query}"
    apple_url = item.get("apple_url") or f"https://music.apple.com/search?term={apple_query}"
    return f"""
                <div class="stream-block">
                    <div class= "stream-label">Have a listen on:</div>
                    <div class= "stream-links">
                        <a class="stream-link" href="{html.escape(spotify_url, quote=True)}" target="_blank" rel="noopener noreferrer">Spotify</a>
                        <a class="stream-link" href="{html.escape(apple_url, quote=True)}" target="_blank" rel="noopener noreferrer">Apple Music</a>
                    </div>
                </div>
"""
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
def build_entry_page(item: dict) -> None: #HTML review page
    config = load_config()
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
    for section in sections:
        if not section["content"].strip():
            continue
        section_title = section["title"]
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
        <section class="section-card">
            <div class="section-heading">
                <h2>{html.escape(section_title)}</h2>
                {help_button}
            </div>
            {help_panel}
            {simple_markdown_to_html(section["content"])}
        </section>
        """)
    streaming_links_html = make_streaming_links(item) ##

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
    <title>{safe_page_title}</title>
    <style>
        :root {{
            --accent: {item["accent"]};
        }}

        body {{
            margin: 0;
            min-height: 100vh;
            font-family: Arial, sans-serif;
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
        @media(max-width:760px) {{
            .cover-frame {{ min-height:0; }}
            .cover {{ min-height:0; aspect-ratio:1; object-fit:contain; }}
            .hero {{ grid-template-columns:1fr; min-height:0; }}
            .sections {{ grid-template-columns:1fr; padding:0; }}
            .section-card,.section-card:nth-child(even) {{ width:auto; }}
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
            <a class="back" href="../index.html"><span aria-hidden="true">←</span> GSI</a>
            <span class="entry-signal">SIGNAL / {html.escape(item["artist"])}</span>
        </header>

        <section class="hero">
            <div class="cover-frame">{cover_html}</div>
            <div class="meta">
                <div class="entry-architecture" aria-hidden="true"><span>GENOME</span><span>STABILITY</span><span>INDUCER</span></div>
                <h1>{html.escape(item["track"])}</h1>
                <p>{html.escape(item["artist"])}</p>
                <p class="album">{html.escape(item["album"])}</p>
                {streaming_links_html}
            </div>
        </section>

        <div class="sections">
            {''.join(section_cards)}
        </div>
    </main>
    <script>
        document.querySelectorAll(".section-info-button").forEach(button => {{
            button.addEventListener("click", () => {{
                const help = button.closest(".section-card").querySelector(".section-help");
                const willOpen = button.getAttribute("aria-expanded") !== "true";
                help.classList.toggle("open", willOpen);
                help.setAttribute("aria-hidden", String(!willOpen));
                button.setAttribute("aria-expanded", String(willOpen));
            }});
        }});
    </script>
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
        item.setdefault("spotify_url", "")
        item.setdefault("apple_url", "")
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


def build_p53_page(item: dict, output_name: str) -> None:
    """Build one permanent P53 transmission from explicitly editable P53 copy."""
    config = load_config()
    signal_label = "CURRENT SIGNAL" if item["slug"] == (config.get("p53_current_slug") or "").strip() else "ARCHIVED SIGNAL"
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
    page_title = html.escape(f'P53 — {item["track"]}')
    html_page = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="theme-color" content="#25152b">
    <link rel="icon" href="../covers/GSI_favicon.svg" type="image/svg+xml">
    <title>{page_title}</title>
    <style>
        :root {{ --accent: {item["accent"]}; --p53: #ff58a6; --cyan: #35c9e9; }}
        * {{ box-sizing: border-box; }}
        body {{
            margin: 0;
            min-height: 100vh;
            overflow-x: hidden;
            color: #faf6ee;
            font-family: Arial, sans-serif;
            background:
                linear-gradient(118deg, rgba(8,10,9,.88), rgba(31,15,36,.92)),
                url("../covers/P53_cover.png") center / cover fixed;
        }}
        body::before {{
            content: "";
            position: fixed;
            inset: 0;
            pointer-events: none;
            background:
                repeating-linear-gradient(0deg, transparent 0 6px, rgba(255,255,255,.035) 6px 7px),
                radial-gradient(circle at 84% 14%, rgba(255,88,166,.23), transparent 30%);
            mix-blend-mode: screen;
        }}
        .p53-page {{
            position: relative;
            width: min(1240px, calc(100% - 36px));
            margin: 0 auto;
            padding: 22px 0 80px;
        }}
        .p53-nav {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 16px;
            margin-bottom: 14px;
            padding: 13px 16px;
            border: 1px solid rgba(255,255,255,.18);
            border-radius: 20px 6px 20px 6px;
            background: rgba(13,10,17,.82);
        }}
        .p53-nav a {{
            color: #ff8bc2;
            text-decoration: none;
            font-size: 12px;
            font-weight: 950;
            letter-spacing: .14em;
            transition: transform 360ms cubic-bezier(.2,.8,.2,1), color 180ms ease;
        }}
        .p53-nav a:hover,
        .p53-nav a:focus-visible {{ color: #fff; transform: translateX(-4px); }}
        .p53-nav span {{ color: rgba(255,255,255,.5); font-size: 10px; font-weight: 900; letter-spacing: .18em; }}
        .transmission {{
            display: grid;
            grid-template-columns: minmax(300px, .9fr) minmax(0, 1.1fr);
            min-height: 650px;
            overflow: hidden;
            border: 2px solid #ff65ad;
            border-radius: 18px 62px 18px 62px;
            background: rgba(16,12,22,.91);
            box-shadow: 10px 10px 0 rgba(53,201,233,.42), -7px -5px 0 rgba(255,88,166,.28), 0 40px 100px rgba(0,0,0,.46);
        }}
        .protein-panel {{
            position: relative;
            min-height: 100%;
            overflow: hidden;
        }}
        .protein-panel > img {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
        .protein-panel::after {{
            content: "P53";
            position: absolute;
            left: 18px;
            bottom: 10px;
            color: rgba(255,255,255,.78);
            font-family: Impact, Haettenschweiler, "Arial Black", sans-serif;
            font-size: clamp(90px, 15vw, 220px);
            line-height: .8;
            text-shadow: 7px 0 var(--p53), -6px 0 var(--cyan);
            animation: protein-pulse 5s ease-in-out infinite;
        }}
        .signal-panel {{
            position: relative;
            display: grid;
            align-content: end;
            padding: clamp(30px, 6vw, 76px);
            background:
                linear-gradient(150deg, color-mix(in srgb, var(--accent), transparent 82%), transparent 44%),
                rgba(14,11,20,.94);
        }}
        .signal-panel::before {{
            content: "{signal_label}";
            position: absolute;
            right: 24px;
            top: 22px;
            color: #ff82bd;
            font-size: 10px;
            font-weight: 950;
            letter-spacing: .22em;
        }}
        .signal-cover {{
            width: min(230px, 54%);
            margin-bottom: 26px;
            border: 2px solid color-mix(in srgb, var(--accent), white 30%);
            border-radius: 30px 8px 30px 8px;
            box-shadow: 0 22px 54px rgba(0,0,0,.4);
            transform: rotate(-2deg);
        }}
        .signal-code {{ color: var(--cyan); font-size: 11px; font-weight: 950; letter-spacing: .2em; }}
        h1 {{ margin: 10px 0 8px; font-size: clamp(58px, 9vw, 126px); line-height: .82; letter-spacing: -.055em; text-wrap: balance; }}
        .artist {{ margin: 0; font-size: clamp(20px, 3vw, 32px); }}
        .album {{ margin: 6px 0 0; color: color-mix(in srgb, var(--accent), white 66%); }}
        .stream-block {{ margin-top: 28px; }}
        .stream-label {{ margin-bottom: 9px; color: #ff96c8; font-size: 12px; font-weight: 800; }}
        .stream-links {{ display: flex; flex-wrap: wrap; gap: 8px; }}
        .stream-link {{
            padding: 11px 16px;
            color: #fff;
            text-decoration: none;
            font-weight: 800;
            border: 1px solid rgba(255,255,255,.24);
            border-radius: 18px 5px 18px 5px;
            background: rgba(255,255,255,.07);
            transition: transform 360ms cubic-bezier(.2,.8,.2,1), border-radius 360ms cubic-bezier(.2,.8,.2,1);
        }}
        .stream-link:hover,
        .stream-link:focus-visible {{ transform: translateY(-3px); border-radius: 5px 18px 5px 18px; }}
        .p53-details {{ display: grid; grid-template-columns: .7fr 1.3fr; gap: 16px; margin-top: 18px; }}
        .p53-details > :only-child {{ grid-column: 1 / -1; }}
        .p53-about,
        .transmission-note {{
            padding: clamp(22px, 4vw, 38px);
            border: 1px solid rgba(255,255,255,.16);
            border-radius: 28px 8px 28px 8px;
            background: rgba(12,11,15,.88);
        }}
        .p53-about h2,
        .transmission-note h2 {{ margin: 0 0 14px; color: #ff7fbb; font-size: 24px; }}
        .p53-about p,
        .transmission-note p {{ margin: 0; color: rgba(255,255,255,.76); line-height: 1.6; }}
        @keyframes protein-pulse {{
            0%, 82%, 100% {{ transform: scale(1); filter: none; }}
            88% {{ transform: scale(1.035); filter: saturate(1.2); }}
            92% {{ transform: scale(.99); }}
        }}
        @media (max-width: 760px) {{
            .transmission {{ grid-template-columns: 1fr; min-height: 0; border-radius: 14px 38px 14px 38px; }}
            .protein-panel {{ min-height: 360px; }}
            .signal-panel {{ padding: 30px 22px 34px; }}
            .signal-cover {{ width: 150px; }}
            .p53-details {{ grid-template-columns: 1fr; }}
        }}
        @media (prefers-reduced-motion: reduce) {{
            *, *::before, *::after {{ animation-duration: .01ms !important; transition-duration: .01ms !important; }}
        }}
    </style>
</head>
<body>
    <main class="p53-page">
        <header class="p53-nav">
            <a href="../index.html">← GSI</a>
            <span>P53 / TRANSMISSION</span>
            <a href="index.html">ARCHIVE →</a>
        </header>
        <section class="transmission">
            <div class="protein-panel"><img src="../covers/P53_cover.png" alt="Expressive P53 protein artwork"></div>
            <div class="signal-panel">
                {cover_html}
                <span class="signal-code">GENOME GUARD / ACTIVE</span>
                <h1>{html.escape(item["track"])}</h1>
                <p class="artist">{html.escape(item["artist"])}</p>
                <p class="album">{html.escape(item["album"])}</p>
                {streaming_links_html}
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
</body>
</html>
"""
    output_path = SITE_P53_DIR / output_name
    output_path.write_text(html_page, encoding = "utf-8")
    print(f"Built P53 transmission: {output_path}")


def build_p53_archive(history: list[dict], current_slug: str) -> None:
    """Build the stable Radio P53 history doorway, newest signal first."""
    cards = []
    for index, item in enumerate(history):
        current_label = '<span class="current">CURRENT SIGNAL</span>' if item["slug"] == current_slug else f'<span class="sequence">SIGNAL {index + 1:02d}</span>'
        cover_html = (
            f'<img src="../covers/{html.escape(item["cover_file"], quote = True)}" alt="{html.escape(item["album"], quote = True)} cover">'
            if item.get("cover_file") else '<div class="cover-missing" aria-hidden="true">P53</div>'
        )
        cards.append(f'''
        <a class="archive-card" href="{html.escape(item["slug"], quote = True)}.html" style="--accent:{item["accent"]}">
            {cover_html}
            <div>{current_label}<h2>{html.escape(item["track"])}</h2><p>{html.escape(item["artist"])}</p><small>{html.escape(item["album"])}</small></div>
        </a>''')
    page = f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#25152b"><link rel="icon" href="../covers/GSI_favicon.svg" type="image/svg+xml">
<title>Radio P53 Archive — GSI</title><style>
*{{box-sizing:border-box}} body{{margin:0;min-height:100vh;color:#faf6ee;font-family:Arial,sans-serif;background:linear-gradient(118deg,rgba(8,10,9,.9),rgba(31,15,36,.94)),url("../covers/P53_cover.png") center/cover fixed}}
main{{width:min(1240px,calc(100% - 36px));margin:auto;padding:22px 0 80px}} nav{{display:flex;justify-content:space-between;align-items:center;padding:13px 16px;border:1px solid rgba(255,255,255,.18);border-radius:20px 6px;background:rgba(13,10,17,.86)}} nav a{{color:#ff8bc2;text-decoration:none;font-size:12px;font-weight:950;letter-spacing:.14em}}
header{{padding:clamp(42px,8vw,96px) 0 38px}} header span,.current,.sequence{{color:#ff7fbb;font-size:10px;font-weight:950;letter-spacing:.2em}} h1{{margin:10px 0 0;font-size:clamp(64px,12vw,160px);line-height:.8;letter-spacing:-.06em}} header p{{max-width:660px;color:rgba(255,255,255,.66);line-height:1.6}}
.archive-grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}} .archive-card{{display:grid;grid-template-columns:150px 1fr;min-height:150px;overflow:hidden;color:#fff;text-decoration:none;border:1px solid color-mix(in srgb,var(--accent),white 22%);border-radius:28px 8px 28px 8px;background:linear-gradient(135deg,color-mix(in srgb,var(--accent),transparent 82%),rgba(12,11,15,.94));transition:transform .3s ease,border-radius .3s ease}} .archive-card:hover{{transform:translateY(-4px);border-radius:8px 28px 8px 28px}} .archive-card img,.cover-missing{{width:150px;height:150px;object-fit:cover}} .cover-missing{{display:grid;place-items:center;background:#17131b;color:#ff69ad;font-size:42px;font-weight:950}} .archive-card>div{{display:flex;flex-direction:column;justify-content:center;padding:18px}} .archive-card h2{{margin:8px 0 3px;font-size:clamp(24px,3vw,38px);line-height:.9}} .archive-card p{{margin:0 0 5px}} .archive-card small{{color:rgba(255,255,255,.58)}}
@media(max-width:760px){{.archive-grid{{grid-template-columns:1fr}}.archive-card{{grid-template-columns:112px 1fr;min-height:112px}}.archive-card img,.cover-missing{{width:112px;height:112px}}}}
</style></head><body><main><nav><a href="../index.html">← GSI</a><span>RADIO P53 / ARCHIVE</span><a href="latest.html">LATEST →</a></nav><header><span>EXTRACELLULAR SIGNALS / RETAINED</span><h1>RADIO P53</h1><p>Tracks I have or had on loop. The current transmission stays at the top; older signals remain here instead of dissolving from the archive.</p></header><section class="archive-grid">{''.join(cards)}</section></main></body></html>'''
    output_path = SITE_P53_DIR / "index.html"
    output_path.write_text(page, encoding = "utf-8")
    print(f"Built P53 archive: {output_path}")


def build_index_html(tracks: list[dict]) -> None:  #sample homepage
    config = load_config()
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
            cover_html = f'<img src="covers/{item["cover_file"]}" alt="{safe_album} cover">'  # image tag
        tags = item.get("tags", "")
        tags_for_attr = tags.lower().replace(","," ")
        card = f"""
        <a class="card"
            data-tags="{tags_for_attr}"
            aria-label="{safe_card_label}"
            href="entries/{item["html_file"]}" style="--accent: {item["accent"]};">
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
        playlist_src, playlist_color = playlist_visuals(playlist_cover, color)
        filter_tracks = [
            item for item in tracks
            if filter_key in [tag.strip().lower() for tag in item.get("tags", "").split(",")]
        ]
        start_track = filter_tracks[0] if filter_tracks else None
        preview_covers = [
            f'covers/{item["cover_file"]}'
            for item in filter_tracks
            if item.get("cover_file")
        ][:4]
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
            "start_title": start_track["track"] if start_track else "",
            "start_artist": start_track["artist"] if start_track else "",
            "start_url": "p53/latest.html" if filter_key == "p53" and start_track else (f'entries/{start_track["html_file"]}' if start_track else ""),
            "preview_covers": preview_covers
            ,"room_label_lines": filter_settings.get("room_label_lines") or [label]
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
                <a class="filter-start hidden" id="filter-start" href="#">
                    <span>START HERE</span>
                    <strong id="filter-start-title"></strong>
                    <small id="filter-start-artist"></small>
                </a>
                <div class="filter-fragments" id="filter-fragments" aria-hidden="true"></div>
            </div>
            <a class="playlist-card hidden" id="playlist-card" href="#" target="_blank" rel="noopener noreferrer">
                <img id="playlist-cover" alt="Playlist cover">
                <div class="playlist-card-text" id="playlist-cta"></div>
            </a>
        </div>
    </section>
    """

    p53_slug = (config.get("p53_current_slug") or "").strip()
    p53_item = next((item for item in tracks if item["slug"] == p53_slug), None)
    p53_html = ""
    if p53_item:
        p53_html = f"""
        <a class="p53-broadcast" href="p53/latest.html" aria-label="Open the current P53 signal: {html.escape(p53_item['track'], quote = True)} by {html.escape(p53_item['artist'], quote = True)}">
            <div class="p53-art">
                <img src="covers/P53_cover.png" alt="P53 protein artwork">
            </div>
            <div class="p53-overlay">
                <img class="p53-album" src="covers/{html.escape(p53_item['cover_file'], quote = True)}" alt="{html.escape(p53_item['album'], quote = True)} cover">
                <div class="p53-signal-copy">
                    <span>CURRENT SIGNAL</span>
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
    <title>{safe_project_title}</title>
    <style>
        body {{
            --chrome: #f2f2f2;
            --danger: #ff2f6d;
            --electric: #63c7ff;
            --asphalt: #0d0d0f;
            transition: background 0.25s ease;
            margin: 0;
            min-height: 100vh;
            padding: 40px;
            font-family: Arial, sans-serif;
            background:
                radial-gradient(circle at 10% 7%, rgba(255,47,109,.18), transparent 24%),
                radial-gradient(circle at 88% 12%, rgba(99,199,255,.13), transparent 26%),
                radial-gradient(circle at 48% 96%, rgba(255,255,255,.08), transparent 34%),
                linear-gradient(135deg, rgba(255,255,255,.045) 0 1px, transparent 1px 18px),
                #0d0d0f;
            color: #eee;
            overflow-x: hidden;
            position: relative;
        }}
        body::before {{
            content: "";
            position: fixed;
            inset: 0;
            pointer-events: none;
            z-index: 0;
            background:
                repeating-linear-gradient(
                    90deg,
                    rgba(255,255,255,.035) 0 1px,
                    transparent 1px 11px
                ),
                repeating-linear-gradient(
                    0deg,
                    transparent 0 23px,
                    rgba(255,255,255,.025) 23px 24px
                );
            opacity: .42;
            mix-blend-mode: screen;
        }}
        body::after {{
            content: "";
            position: fixed;
            inset: -20%;
            pointer-events: none;
            z-index: 0;
            background:
                radial-gradient(circle at 22% 18%, rgba(255,47,109,.13), transparent 22%),
                radial-gradient(circle at 80% 20%, rgba(99,199,255,.11), transparent 24%),
                radial-gradient(circle at 65% 86%, rgba(255,180,70,.09), transparent 28%);
            filter: blur(18px) saturate(1.25);
            opacity: .8;
            transition: background .35s ease, opacity .35s ease;
        }}
        body.filter-active::after {{
            background:
                radial-gradient(
                    circle at 68% 28%,
                    color-mix(in srgb, var(--page-tint, #ffffff), transparent 70%),
                    transparent 36%
                ),
                radial-gradient(
                    circle at 18% 78%,
                    color-mix(in srgb, var(--page-tint, #ffffff), transparent 84%),
                    transparent 30%
                );
            opacity: 1;
        }}
        body > * {{
            position: relative;
            z-index: 1;
        }}

        .site-hero {{
            margin: 0 0 30px;
            padding: 8px 0 4px;
            position: relative;
            isolation: isolate;
        }}
        .site-hero::before {{
            content: "GENOME STABILITY INDUCERS";
            display: block;
            margin: 0 0 10px 4px;
            color: rgba(255,255,255,.52);
            font-size: 12px;
            font-weight: 800;
            letter-spacing: .32em;
            text-transform: uppercase;
        }}
        .site-hero::after {{
            content: "ARCHIVE";
            position: absolute;
            left: 8px;
            bottom: -10px;
            color: rgba(99,199,255,.62);
            font-size: 11px;
            font-weight: 900;
            letter-spacing: .22em;
            text-transform: uppercase;
            transform: skew(-12deg);
        }}
        .wordmark {{
            position: relative;
            display: inline-block;
            font-family: Impact, Haettenschweiler, "Arial Black", sans-serif;
            font-size: clamp(76px, 14vw, 168px);
            line-height: .78;
            font-weight: 950;
            letter-spacing: -0.075em;
            text-transform: uppercase;
            color: #f2f2f2;
            -webkit-text-stroke: 1px rgba(255,255,255,.22);
            text-shadow:
                5px 5px 0 rgba(255,47,109,.34),
                -5px 4px 0 rgba(99,199,255,.28),
                0 0 26px rgba(255,255,255,.18),
                0 0 82px rgba(255,47,109,.13);
            transform: skew(-9deg) rotate(-1deg);
            animation: wordmark-idle 5.4s infinite;
        }}
        .wordmark::before {{
            content: "GSI";
            position: absolute;
            inset: 0;
            z-index: -1;
            color: transparent;
            -webkit-text-stroke: 2px rgba(255,47,109,.72);
            transform: translate(-7px, 5px);
            clip-path: polygon(0 0, 100% 0, 100% 32%, 0 46%);
            opacity: .78;
        }}
        .wordmark::after {{
            content: "GSI";
            position: absolute;
            inset: 0;
            z-index: -2;
            color: transparent;
            -webkit-text-stroke: 2px rgba(99,199,255,.62);
            transform: translate(7px, -4px);
            clip-path: polygon(0 52%, 100% 38%, 100% 100%, 0 100%);
            opacity: 0.72;
        }}
        .wordmark:hover {{
            animation: wordmark-wobble .38s steps(2, end);
            text-shadow:
                7px 5px 0 rgba(255,47,109,.46),
                -7px 5px 0 rgba(99,199,255,.38),
                0 0 34px rgba(255,255,255,.26),
                0 0 100px rgba(255,47,109,.18);
        }}
        .subtitle {{
            margin-top: 16px;
            max-width: 780px;
            font-size: 20px;
            line-height: 1.35;
            color: #d7d7d7;
            letter-spacing: .02em;
            text-shadow: 0 2px 10px rgba(0,0,0,.55);
        }}
        @keyframes wordmark-wobble {{
            0% {{transform: skew(-9deg) rotate(-1deg) translate(0,0); }}
            25% {{transform: skew(-15deg) rotate(-1deg) translate(-3px,2px); }}
            50% {{transform: skew(-6deg) rotate(-2deg) translate(4px,-1px); }}
            75% {{transform: skew(-13deg) rotate(0deg) translate(-2px,-2px); }}
            100% {{transform: skew(-9deg) rotate(-1deg) translate(0,0); }}
        }}
        @keyframes wordmark-idle {{
            0%, 88%, 100% {{ filter: none; }}
            90% {{ filter: brightness(1.18) contrast(1.16);}}
            92% {{ filter: brightness(.88) contrast(1.3);}}
            94% {{ filter: none; }}
        }}
        .intro {{
            max-width: 850px;
            margin: 0 0 30px;
            padding: 20px 22px;
            border-radius: 24px;
            background: rgba(28, 28, 28, .86);
            border: 1px solid rgba(255, 255, 255, .09);
            box-shadow: 0 0 35px rgba(0,0,0,.22);
            max-height: 400px;
            overflow: hidden;
            opacity: 1;
            transform: translateY(0);
            transition:
                max-height .35s ease,
                opacity .22s ease,
                transform .35s ease,
                margin .35s ease,
                padding .35s ease,
                border-width .35s ease;
        }}

        .intro p {{
            margin: 0;
            line-height: 1.6;
            color: #d8d8d8;
            font-size: 16px;
        }}
        body.filter-active .intro{{
            max-height: 0;
            margin-bottom: 0;
            padding-top: 0;
            padding-bottom: 0;
            border-width: 0;
            opacity: 0;
            transform: translateY(-12px);
        }}
        .filter-panel {{
            margin: 0 0 34px;
            padding: 16px 0 4px;
            border-top: 1px solid rgba(255,255,255,.08);
            border-bottom: 1px solid rgba(255,255,255,.06);
        }}

        .filter-row {{
            display: flex;
            flex-wrap: wrap;
            gap: 11px;
            margin-bottom: 16px;
        }}

        .filter-btn {{
            border: 1px solid rgba(255,255,255,.16);
            border-radius: 8px;
            padding: 10px 14px;
            background:
                linear-gradient(180deg, rgba(255,255,255,.08), transparent),
                #171717;
            color: #eaeaea;
            cursor: pointer;
            font-weight: 850;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            transform: skew(-8deg);
            box-shadow: 0 10px 22px rgba(0,0,0,.24);
            transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease, background 0.15s ease;
        }}

        .filter-btn:hover,
        .filter-btn:focus-visible {{
            transform: skew(-8deg) translateY(-3px);
            border-color: color-mix(in srgb, var(--page-tint, #ffffff), white 30%);
            box-shadow: 0 0 20px color-mix(in srgb, var(--page-tint, #ffffff), transparent 66%),
            0 14px 28px rgba(0,0,0,.28);
        }}

        .filter-btn.active {{
            border-color: color-mix(in srgb, var(--page-tint, #ffffff), white 44%);
            background:
                linear-gradient(180deg, rgba(255,255,255,.13), transparent),
                color-mix(in srgb, var(--page-tint, #ffffff), #111 72%);
            box-shadow: 0 0 24px color-mix(in srgb, var(--page-tint, #ffffff), transparent 55%),
            0 14px 30px rgba(0,0,0,.32);
        }}
        .filter-description {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-sizing: border-box;
            gap: 24px;
            max-height:520px;
            overflow: hidden;
            opacity: 1;
            transform: translateY(0);
            transition:
                max-height .38s ease,
                opacity .24s ease,
                transform .38s ease;
        }}
        body.filter-active .filter-description{{
            padding: 22px;
            border-radius: 24px;
            background:
                linear-gradient(135deg, rgba(255,255,255,.055), rgba(0,0,0,.18)),
                color-mix(in srgb, var(--page-tint, #ffffff), #111 88%);
                border: 1px solid color-mix(in srgb, var(--page-tint, #ffffff), white 18%);
                box-shadow: 0 0 44px color-mix(in srgb, var(--page-tint, #ffffff), transparent 78%),
                0 20px 46px rgba(0,0,0,.26);
        }}
        .filter-copy {{
            flex: 1;
            min-width: 0;
        }}
        .playlist-card {{
            --playlist-accent: var(--page-tint, #ffffff);
            width: min(210px, 26vw);
            min-width: 150px;
            display: flex;
            flex-direction: column;
            align-self: flex-start;
            overflow: hidden;
            text-decoration: none;
            color: #f4f4f4;
            border-radius: 18px;
            background:
                linear-gradient(180deg, rgba(255,255,255,.06), rgba(0,0,0,.22)),
                color-mix(in srgb, var(--playlist-accent), #111 84%);
            border: 1px solid color-mix(in srgb, var(--playlist-accent), white 28%);
            box-shadow:
                0 0 26px color-mix(in srgb, var(--playlist-accent), transparent 68%),
                0 18px 34px rgba(0,0,0,.28);
            transition: transform .16s ease, box-shadow .16s, border-color .16s ease;
        }}
        .playlist-card:hover,
        .playlist-card:focus-visible {{
            transform: translateY(-4px) rotate(-0.4deg);
            border-color: color-mix(in srgb, var(--playlist-accent), white 48%);
            box-shadow:
                0 0 34px color-mix(in srgb, var(--playlist-accent), transparent 50%),
                0 22px 42px rgba(0,0,0,.34);
        }}
        .playlist-card.hidden {{
            display: none;
        }}
        .playlist-card img {{
            width: 100%;
            aspect-ratio: 1/1;
            object-fit: cover;
            display:block;
        }}
        .playlist-card-text {{
            padding: 13px 14px;
            font-size: 14px;
            font-weight: 800;
            line-height: 1.25;
            text-shadow: 0 2px 8px rgba(0,0,0,.75);
        }}

        .filter-description h2 {{
            margin: 0 0 8px;
            font-size: 22px;
            color: color-mix(in srgb, var(--page-tint, #ffffff), white 35%);
        }}

        .filter-description p {{
            margin: 0;
            max-width: 760px;
            line-height: 1.55;
            color: #d8d8d8;
        }}
        .filter-description.hidden {{
            max-height: 0;
            opacity: 0;
            transform: translateY(-12px);
            pointer-events: none;
        }}
        .view-control {{
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 8px;
            margin: 0 0 20px;
        }}
        .view-control-label {{
            margin-right:4px;
            color: rgba(255, 255, 255, .48);
            font-size: 11px;
            font-weight: 900;
            letter-spacing: .2em;
        }}

        .view-btn {{
            padding: 7px 10px;
            border: 1px solid rgba(255, 255, 255, .14);
            border-radius: 6px;
            background: #171719;
            color: #aaa;
            cursor: pointer;
            font-size: 11px;
            font-weight: 900;
            letter-spacing: .08em;
            text-transform: uppercase;
            transform: skew(-7deg);
            transition:
                color .16s ease,
                border-color .16s ease,
                background .16s ease,
                box-shadow .16s ease,
                transform .16s ease;
        }}

        .view-btn:hover,
        .view-btn:focus-visible {{
            color: #fff;
            border-color: rgba(255, 255, 255, .4);
            transform: skew(-7deg) translateY(-2px);
        }}

        .view-btn.active {{
            color: #fff;
            border-color: color-mix(
                in srgb,
                var(--page-tint, #ffffff),
                white 32%
            );
            background: color-mix(
                in srgb,
                var(--page-tint, #ffffff),
                #151515 82%
            );
            box-shadow:
                0 0 16px color-mix(
                    in srgb,
                    var(--page-tint, #ffffff),
                    transparent 68%
                );
        }}

        .grid {{
            display: grid;
            opacity: 1;
            transform: translateY(0);
            transition: opacity 120ms ease, transform 120ms ease;
        }}
        .grid.view-switching {{
            opacity: .18;
            transform: translateY(5px);
        }}

        body[data-view="poster"] .grid {{
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 24px;
        }}

        body[data-view="wall"] .grid {{
            grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
            gap: 16px;
        }}

        body[data-view="gallery"] .grid {{
            grid-template-columns: repeat(auto-fill, minmax(105px, 1fr));
            gap: 9px;
        }}

        body[data-view="gallery"] .card {{
            border-radius: 10px;
        }}

        body[data-view="gallery"] .card .info {{
            display: none;
        }}
        .card {{
            display: flex;
            flex-direction: column;
            text-decoration: none;
            color: #eee;
            background:
                linear-gradient(180deg, rgba(255,255,255,.035), transparent 34%),
                color-mix(in srgb, var(--accent), #1b1b1b 86%);
            border: 2px solid color-mix(in srgb, var(--accent), white 12%);
            border-radius: 20px;
            overflow: hidden;
            box-shadow:
                0 0 24px color-mix(in srgb, var(--accent), transparent 76%),
                0 18px 42px rgba(0,0,0,.25);
            transition: transform 0.16s ease, box-shadow 0.16s ease, border-color 0.16s ease;
        }}

        .card:hover,
        .card:focus-visible {{
            transform: translateY(-7px) scale(1.018) rotate(-0.35deg);
            border-color: color-mix(in srgb, var(--accent), white 35%);
            box-shadow:
                0 0 28px color-mix(in srgb, var(--accent), transparent 42%),
                0 0 80px color-mix(in srgb, var(--accent), transparent 72%),
                0 24px 52px rgba(0,0,0,.35);
        }}
        .filter-btn:focus-visible,
        .playlist-card:focus-visible,
        .card:focus-visible {{
            outline: 2px solid color-mix(in srgb, var(--page-tint, #ffffff), white 35%);
            outline-offset: 4px;
        }}

        .card img {{
            width: 100%;
            aspect-ratio: 1 / 1;
            object-fit: cover;
            display: block;
        }}

        .info {{
            flex: 1;
            padding: 18px;
            background:
                linear-gradient(180deg, rgba(0,0,0,.08), rgba(0,0,0,.28));
        }}

        .info h2 {{
            margin: 0 0 8px;
            font-size: 22px;
            color: #f7f7f7;
            text-shadow: 0 2px 12px rgba(0,0,0,.72);
        }}

        .info p {{
            margin: 0 0 7px;
            color: #d6d6d6;
            text-shadow: 0 2px 10px rgba(0,0,0,.62);
        }}

        .info span {{
            display: block;
            max-width: 100%;
            margin-top: 8px;
            padding: 0;
            overflow: hidden;
            white-space: nowrap;
            text-overflow: ellipsis;
            font-size: 12px;
            font-weight: 750;
            letter-spacing: .035em;
            color: color-mix(in srgb, var(--accent), white 70%);
            background: none;
            border: none;
            box-shadow: none;
            text-shadow: 0 2px 8px rgba(0,0,0,.85);
        }}
        @media (max-width: 760px) {{
            body {{
                padding: 22px;
            }}
            .wordmark {{
                font-size: clamp(68px, 28vw, 110px);
            }}
            .filter-description {{
                flex-direction: column;
                align-items: stretch;
                gap: 18px;
            }}
            body.filter-active .filter-description {{
                padding: 18px;
            }}
            .playlist-card {{
                width: min(100%, 240px);
                min-width: 0;
                align-self: flex-start;
            }}
        body[data-view="poster"] .grid {{
            grid-template-columns: minmax(0, 1fr);
            gap: 18px;
        }}

        body[data-view="wall"] .grid {{
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 11px;
        }}

        body[data-view="gallery"] .grid {{
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 6px;
        }}

        body[data-view="wall"] .info {{
            padding: 12px;
        }}

        body[data-view="wall"] .info h2 {{
            margin-bottom: 6px;
            font-size: 16px;
            line-height: 1.15;
        }}

        body[data-view="wall"] .info p {{
            margin-bottom: 5px;
            font-size: 13px;
        }}

        body[data-view="wall"] .info span {{
            font-size: 10px;
        }}

        body[data-view="gallery"] .card {{
            border-width: 1px;
            border-radius: 7px;
        }}
        }}
        /* GSI 1.09: expressive controls mounted onto a distressed signal wall. */
        body {{
            --surface: #101012;
            --paper: #e8e2d3;
            --ink: #111114;
            --signal-pink: #ff4f9a;
            --signal-cyan: #32c9e8;
            padding: clamp(18px, 4vw, 54px);
            background:
                radial-gradient(circle at 78% 4%, color-mix(in srgb, var(--page-tint, #687080), transparent 80%), transparent 32%),
                linear-gradient(118deg, rgba(255,255,255,.035), transparent 28%),
                repeating-linear-gradient(96deg, rgba(255,255,255,.018) 0 1px, transparent 1px 16px),
                #0b0b0d;
        }}
        body::before {{
            opacity: .28;
            mix-blend-mode: soft-light;
        }}
        body::after {{
            inset: 0;
            filter: none;
            opacity: .72;
            background:
                linear-gradient(90deg, transparent 0 48%, rgba(255,255,255,.018) 48% 49%, transparent 49%),
                radial-gradient(circle at 18% 88%, color-mix(in srgb, var(--page-tint, #ffffff), transparent 90%), transparent 34%);
        }}
        .signal-transform {{
            position: fixed;
            inset: -15%;
            z-index: 20;
            pointer-events: none;
            opacity: 0;
            background:
                linear-gradient(104deg, transparent 0 34%, color-mix(in srgb, var(--page-tint), transparent 48%) 42%, transparent 50%),
                repeating-linear-gradient(0deg, transparent 0 8px, rgba(255,255,255,.08) 8px 9px);
            mix-blend-mode: screen;
            transform: translateX(-65%) skewX(-12deg);
        }}
        body.signal-transforming .signal-transform {{
            animation: signal-sweep 700ms cubic-bezier(.2,.8,.2,1) both;
        }}
        @keyframes signal-sweep {{
            0% {{ opacity: 0; transform: translateX(-65%) skewX(-12deg); }}
            28% {{ opacity: .72; }}
            100% {{ opacity: 0; transform: translateX(65%) skewX(-12deg); }}
        }}
        .site-hero {{
            display: grid;
            grid-template-columns: minmax(0, 1.25fr) minmax(310px, .75fr);
            gap: clamp(20px, 4vw, 54px);
            align-items: stretch;
            margin-bottom: 24px;
            padding: 0;
        }}
        .site-hero::before,
        .site-hero::after {{
            content: none;
        }}
        .hero-copy {{
            position: relative;
            display: flex;
            flex-direction: column;
            justify-content: center; /* balance the desktop panel against the tall P53 artwork */
            min-height: 330px;
            padding: clamp(22px, 4vw, 48px);
            overflow: hidden;
            border: 1px solid rgba(255,255,255,.13);
            border-radius: 52px 14px 52px 14px;
            background:
                linear-gradient(140deg, rgba(255,255,255,.07), transparent 38%),
                linear-gradient(115deg, color-mix(in srgb, var(--page-tint, #fff), transparent 91%), transparent 58%),
                rgba(14,14,16,.86);
            box-shadow: 0 28px 80px rgba(0,0,0,.3);
            isolation: isolate;
            transition: background 520ms ease, border-radius 520ms cubic-bezier(.2,.8,.2,1), border-color 300ms ease;
        }}
        body.filter-active .hero-copy {{
            border-color: color-mix(in srgb, var(--page-tint), white 20%);
            border-radius: 18px 58px 18px 58px;
        }}
        .hero-architecture {{
            position: absolute;
            inset: 0;
            z-index: -1;
            overflow: hidden;
            pointer-events: none;
            font-family: Impact, Haettenschweiler, "Arial Black", sans-serif;
            line-height: .72;
            transition: transform 650ms cubic-bezier(.2,.8,.2,1), opacity 300ms ease;
        }}
        .hero-architecture span {{
            position: absolute;
            color: color-mix(in srgb, var(--page-tint, #fff), transparent 89%);
            font-size: clamp(72px, 9vw, 142px);
            letter-spacing: -.04em;
            white-space: nowrap;
        }}
        .hero-architecture span:nth-child(1) {{ top: -10px; right: -18px; transform: none; }}
        .hero-architecture span:nth-child(2) {{ top: 39%; left: -26px; color: transparent; -webkit-text-stroke: 2px color-mix(in srgb, var(--page-tint, #fff), transparent 82%); transform: scaleX(1.18); }}
        .hero-architecture span:nth-child(3) {{ right: -16px; bottom: -10px; transform: skew(-10deg); }}
        body.signal-transforming .hero-architecture {{ transform: translateX(12px) skew(-2deg); opacity: .72; }}
        body.signal-transforming .hero-copy {{
            box-shadow: inset 8px 0 0 color-mix(in srgb, var(--page-tint), transparent 34%), 0 28px 80px rgba(0,0,0,.3);
        }}
        .wordmark {{
            align-self: flex-start;
            padding: 12px 28px 16px 22px;
            border-radius: 44px 12px 44px 12px;
            color: var(--ink);
            background: var(--paper);
            -webkit-text-stroke: 0;
            text-shadow: 6px 0 0 var(--signal-pink), -5px 0 0 var(--signal-cyan);
            box-shadow: 12px 12px 0 color-mix(in srgb, var(--page-tint, #7b5cff), #000 34%);
            transform: rotate(-2deg);
            animation: none;
            transition:
                border-radius 500ms cubic-bezier(.2,.8,.2,1),
                transform 500ms cubic-bezier(.2,.8,.2,1),
                box-shadow 240ms ease;
        }}
        .wordmark::before,
        .wordmark::after {{
            content: none;
        }}
        .wordmark:hover {{
            animation: none;
            border-radius: 12px 44px 12px 44px;
            transform: rotate(1deg) scale(1.025);
            text-shadow: 6px 0 0 var(--signal-pink), -5px 0 0 var(--signal-cyan);
        }}
        .hero-copy .intro {{
            max-width: 760px;
            max-height: none;
            margin: 28px 0 0;
            padding: 0;
            border: 0;
            border-radius: 0;
            background: none;
            box-shadow: none;
        }}
        .hero-copy .intro p {{
            margin: 0;
            color: rgba(255,255,255,.72);
            font-size: clamp(14px, 1.6vw, 18px);
            line-height: 1.55;
        }}
        body.filter-active .hero-copy .intro {{
            max-height: none;
            margin-top: 28px;
            padding: 0;
            opacity: .36;
            transform: none;
        }}
        .p53-broadcast {{
            position: relative;
            display: block;
            min-height: 330px;
            overflow: hidden;
            color: #f8f5eb;
            text-decoration: none;
            border: 2px solid #ff72b5;
            border-radius: 16px 54px 16px 54px;
            background: #283625;
            box-shadow: 0 0 0 6px rgba(255,79,154,.08), 0 26px 70px rgba(0,0,0,.38);
            transition:
                transform 520ms cubic-bezier(.2,.8,.2,1),
                border-radius 520ms cubic-bezier(.2,.8,.2,1),
                box-shadow 220ms ease;
        }}
        .p53-broadcast:hover,
        .p53-broadcast:focus-visible {{
            transform: translateY(-7px) rotate(.5deg);
            border-radius: 54px 16px 54px 16px;
            box-shadow: 8px 8px 0 #22bce3, -7px -5px 0 rgba(255,79,154,.52), 0 32px 80px rgba(0,0,0,.42);
        }}
        .p53-art {{
            position: absolute;
            inset: 0;
            overflow: hidden;
        }}
        .p53-art img {{
            width: 100%;
            height: 100%;
            min-height: 100%;
            object-fit: cover;
            display: block;
            transition: transform 900ms cubic-bezier(.2,.8,.2,1), filter 300ms ease;
        }}
        .p53-broadcast:hover .p53-art img {{
            transform: scale(1.045) rotate(-1deg);
            filter: saturate(1.12) contrast(1.04);
        }}
        .p53-overlay {{
            position: absolute;
            inset: 0;
            display: grid;
            grid-template-columns: auto minmax(0, 1fr);
            grid-template-rows: 1fr auto;
            align-items: end;
            gap: 14px;
            padding: 20px;
            background: linear-gradient(180deg, transparent 34%, rgba(12,10,18,.22) 55%, rgba(12,10,18,.94) 100%);
        }}
        .p53-album {{
            grid-row: 2;
            width: 82px;
            aspect-ratio: 1;
            object-fit: cover;
            border: 2px solid rgba(255,255,255,.78);
            border-radius: 15px 5px 15px 5px;
            box-shadow: 6px 6px 0 rgba(53,201,233,.58);
            transform: rotate(-3deg);
        }}
        .p53-signal-copy {{
            grid-column: 2;
            grid-row: 1;
            align-self: end;
            justify-self: end;
            max-width: 72%;
            text-align: right;
        }}
        .p53-signal-copy span {{
            color: #5ee4fa;
            font-size: 10px;
            font-weight: 950;
            letter-spacing: .17em;
        }}
        .p53-signal-copy strong {{
            display: block;
            margin-top: 6px;
            font-size: clamp(21px, 2.1vw, 31px);
            line-height: 1;
        }}
        .p53-signal-copy small {{
            display: block;
            margin-top: 5px;
            color: rgba(255,255,255,.68);
        }}
        .p53-signal-copy b {{
            display: inline-grid;
            place-items: center;
            width: 32px;
            height: 32px;
            margin-top: 10px;
            border-radius: 50% 50% 16% 50%;
            color: #111;
            background: #ff79bb;
            font-size: 18px;
        }}
        .p53-radio {{
            grid-column: 2;
            grid-row: 2;
            align-self: end;
            justify-self: end;
            color: #f4ed50;
            font-family: Impact, Haettenschweiler, "Arial Black", sans-serif;
            font-size: clamp(36px, 4.6vw, 68px);
            line-height: .78;
            letter-spacing: -.035em;
            text-align: right;
            text-shadow: 4px 0 0 rgba(255,79,163,.72), -3px 0 0 rgba(53,201,233,.7);
        }}
        .filter-panel {{
            margin-bottom: 20px;
            padding: clamp(14px, 2vw, 22px);
            border: 1px solid rgba(255,255,255,.12);
            border-radius: 28px 8px 28px 8px;
            background: rgba(12,12,14,.82);
        }}
        .filter-row {{
            display: flex;
            flex-wrap: wrap;
            gap: 5px;
            margin-bottom: 0;
        }}
        .filter-btn {{
            flex: 1 1 112px;
            min-height: 52px;
            padding: 12px 16px;
            border-radius: 20px 7px 20px 7px;
            transform: none;
            box-shadow: none;
            transition:
                flex-grow 520ms cubic-bezier(.2,.8,.2,1),
                border-radius 520ms cubic-bezier(.2,.8,.2,1),
                transform 360ms cubic-bezier(.2,.8,.2,1),
                color 180ms ease,
                background 220ms ease;
        }}
        .filter-btn span {{
            display: inline-block;
            transition: transform 420ms cubic-bezier(.2,.8,.2,1), letter-spacing 420ms cubic-bezier(.2,.8,.2,1);
        }}
        .filter-btn:hover,
        .filter-btn:focus-visible {{
            transform: translateY(-3px);
            border-radius: 7px 20px 7px 20px;
        }}
        .filter-btn.active {{
            flex-grow: 2.25;
            border-radius: 32px 8px 32px 8px;
            transform: translateY(-2px);
        }}
        .filter-btn.active span {{
            transform: scale(1.08);
            letter-spacing: .14em;
        }}
        .filter-btn.filter-p53 {{
            color: #160d18;
            border-color: #ff78b9;
            background: linear-gradient(110deg, #ff64aa, #57d6e9);
        }}
        .filter-description {{
            position: relative;
            display: grid;
            grid-template-columns: minmax(0, 1fr) minmax(250px, 340px);
            align-items: stretch;
            gap: clamp(18px, 4vw, 52px);
            isolation: isolate;
        }}
        body.filter-active .filter-description {{
            min-height: 350px;
            margin-top: 16px;
            padding: clamp(24px, 4vw, 46px);
            overflow: hidden;
            border-radius: 42px 10px 42px 10px;
        }}
        .filter-room-label {{
            position: absolute;
            left: -12px;
            bottom: -34px;
            z-index: -1;
            color: color-mix(in srgb, var(--page-tint), transparent 85%);
            font-family: Impact, Haettenschweiler, "Arial Black", sans-serif;
            font-size: clamp(100px, 19vw, 270px);
            line-height: .8;
            text-transform: uppercase;
            transform: skew(-8deg);
            pointer-events: none;
        }}
        .filter-room-label span {{
            display: block;
            white-space: nowrap;
        }}
        .filter-room-label span + span {{ margin-left: .16em; }}
        .filter-decor {{
            position: absolute;
            inset: 0;
            z-index: -1;
            overflow: hidden;
            pointer-events: none;
        }}
        .filter-decor::before,
        .filter-decor::after {{
            content: "";
            position: absolute;
        }}
        .filter-description[data-filter="bassline"] .filter-room-label {{
            filter: drop-shadow(8px 0 0 color-mix(in srgb, var(--page-tint), transparent 90%));
            letter-spacing: -.05em;
            transform-origin: center bottom;
            animation: bass-pressure 1.9s linear infinite;
        }}
        .filter-description[data-filter="bassline"] .filter-decor::before,
        .filter-description[data-filter="bassline"] .filter-decor::after {{
            inset: 18%;
            border: 2px solid color-mix(in srgb,var(--page-tint),transparent 72%);
            border-radius: 42px 10px 42px 10px;
            animation: bass-wave 1.9s linear infinite;
        }}
        .filter-description[data-filter="bassline"] .filter-decor::after {{ animation-delay:.18s; }}
        @keyframes bass-pressure {{ 0%,50%,100% {{ transform:skew(-8deg) scale(1,.98); }} 18%,68% {{ transform:skew(-8deg) scale(1.055,.91); }} 32%,82% {{ transform:skew(-8deg) scale(.985,1.025); }} }}
        @keyframes bass-wave {{ 0% {{ opacity:0; transform:scale(.9); }} 18% {{ opacity:.48; }} 50% {{ opacity:0; transform:scale(1.08); }} 51% {{ transform:scale(.9); }} 68% {{ opacity:.42; }} 100% {{ opacity:0; transform:scale(1.08); }} }}
        .filter-description[data-filter="dreamy"] .filter-room-label {{
            left: auto; right: -12%; bottom: -12%;
            color: transparent;
            -webkit-text-stroke: 3px color-mix(in srgb, var(--page-tint), transparent 72%);
            animation: dreamy-drift 8.5s linear infinite;
        }}
        @keyframes dreamy-drift {{ 0% {{ transform:translate(0,0) rotate(-14deg) scale(1.14); }} 25% {{ transform:translate(-35vw,-170px) rotate(-7deg) scale(1.2); }} 50% {{ transform:translate(-88vw,-430px) rotate(10deg) scale(1.02); }} 75% {{ transform:translate(-46vw,-145px) rotate(2deg) scale(1.18); }} 100% {{ transform:translate(0,0) rotate(-14deg) scale(1.14); }} }}
        .filter-description[data-filter="bite"] .filter-room-label span:last-child {{
            margin-left:-.08em;
        }}
        .filter-description[data-filter="pop"] .filter-room-label {{ display:none; }}
        .filter-description[data-filter="pop"] .filter-decor span {{
            position:absolute;
            left:var(--pop-x); top:var(--pop-y);
            color: color-mix(in srgb, var(--page-tint), transparent 78%);
            font:900 var(--pop-size)/1 Arial,sans-serif;
            animation:pop-signal var(--pop-speed) cubic-bezier(.18,.85,.25,1.12) var(--pop-delay) infinite;
        }}
        @keyframes pop-signal {{ 0%,18% {{ opacity:0; transform:scale(.18) rotate(-9deg); }} 38% {{ opacity:.78; transform:scale(1.14) rotate(3deg); }} 52% {{ opacity:.58; transform:scale(1); }} 72%,100% {{ opacity:0; transform:scale(.82) translateY(-12px); }} }}
        .filter-description[data-filter="distortion"] .filter-decor {{
            background:repeating-linear-gradient(0deg,transparent 0 17px,color-mix(in srgb,var(--page-tint),transparent 88%) 18px 20px,transparent 21px 38px);
            animation:distortion-scan 2.6s steps(6,end) infinite;
        }}
        .filter-description[data-filter="distortion"] .filter-decor::before {{
            content:"DISTORTION";
            inset:20% auto auto -4%;
            color:transparent;
            -webkit-text-stroke:3px color-mix(in srgb,var(--page-tint),transparent 68%);
            font:900 clamp(90px,16vw,230px)/.8 Impact,Haettenschweiler,"Arial Black",sans-serif;
            letter-spacing:-.045em;
            animation:distortion-echo 2.6s steps(5,end) infinite;
        }}
        .filter-description[data-filter="distortion"] .playlist-card img {{ animation:distorted-cover 2.6s steps(7,end) infinite; }}
        @keyframes distortion-scan {{ 0% {{ transform:translateY(-12px); opacity:.25; }} 50% {{ transform:translateY(8px); opacity:.62; }} 100% {{ transform:translateY(-12px); opacity:.25; }} }}
        @keyframes distortion-echo {{ 0%,100% {{ transform:translate(0); opacity:.28; }} 24% {{ transform:translate(11px,-3px) skewX(-4deg); opacity:.5; }} 27% {{ transform:translate(-8px,4px); }} 70% {{ transform:translate(4px); opacity:.34; }} }}
        @keyframes distorted-cover {{ 0%,100% {{ transform:translate(0) scale(1.01); filter:saturate(1); }} 22% {{ transform:translate(5px,-2px) scale(1.025); filter:saturate(1.35) contrast(1.12); }} 25% {{ transform:translate(-4px,2px) scale(1.02); filter:hue-rotate(12deg) contrast(1.18); }} 64% {{ transform:translate(2px) scale(1.015); filter:saturate(.86); }} }}
        .filter-description[data-filter="ulas"] .filter-decor::before,
        .filter-description[data-filter="ulas"] .filter-decor::after {{
            width:90px; height:90px; border-color:color-mix(in srgb,var(--page-tint),transparent 42%); border-style:solid; border-radius:30px 8px 30px 8px;
        }}
        .filter-description[data-filter="ulas"] .filter-decor::before {{ left:18px; top:18px; border-width:4px 0 0 4px; }}
        .filter-description[data-filter="ulas"] .filter-decor::after {{ right:18px; bottom:18px; border-width:0 4px 4px 0; }}
        @media (max-width:760px) {{
            .filter-room-label {{ font-size:clamp(82px,28vw,150px); }}
            .filter-description[data-filter="ulas"] .filter-room-label {{ font-size:clamp(66px,22vw,118px); }}
            .hero-architecture span {{ font-size:clamp(62px,24vw,112px); }}
        }}
        .filter-copy {{
            display: flex;
            flex-direction: column;
            align-items: flex-start;
            justify-content: center;
            min-height: 0;
        }}
        .filter-count {{
            margin-bottom: 12px;
            color: color-mix(in srgb, var(--page-tint), white 60%);
            font-size: 11px;
            font-weight: 950;
            letter-spacing: .2em;
        }}
        .filter-description h2 {{
            margin: 0 0 14px;
            font-size: clamp(44px, 8vw, 104px);
            line-height: .82;
            letter-spacing: -.055em;
            text-wrap: balance;
        }}
        .filter-description p {{
            max-width: 680px;
            font-size: 16px;
        }}
        .filter-start {{
            display: grid;
            grid-template-columns: auto 1fr;
            column-gap: 12px;
            align-items: center;
            margin-top: 24px;
            padding: 12px 16px;
            color: #fff;
            text-decoration: none;
            border: 1px solid color-mix(in srgb, var(--page-tint), white 28%);
            border-radius: 20px 6px 20px 6px;
            background: color-mix(in srgb, var(--page-tint), #111 82%);
            transition: transform 360ms cubic-bezier(.2,.8,.2,1), border-radius 360ms cubic-bezier(.2,.8,.2,1);
        }}
        .filter-start:hover,
        .filter-start:focus-visible {{
            transform: translateX(5px);
            border-radius: 6px 20px 6px 20px;
        }}
        .filter-start > span {{
            grid-row: span 2;
            color: color-mix(in srgb, var(--page-tint), white 60%);
            font-size: 9px;
            font-weight: 950;
            letter-spacing: .15em;
        }}
        .filter-start strong {{ font-size: 15px; }}
        .filter-start small {{ color: rgba(255,255,255,.58); }}
        .filter-start.hidden {{ display: none; }}
        .filter-fragments {{
            display: flex;
            min-height: 54px;
            margin-top: 20px;
            padding-left: 8px;
        }}
        .filter-fragments img {{
            width: 58px;
            height: 58px;
            object-fit: cover;
            margin-left: -8px;
            border: 2px solid color-mix(in srgb, var(--page-tint), white 36%);
            border-radius: 16px 4px 16px 4px;
            transform: rotate(calc((var(--fragment-index) - 1.5) * 3deg));
            box-shadow: 0 8px 16px rgba(0,0,0,.3);
        }}
        .playlist-card {{
            width: 100%;
            min-width: 0;
            align-self: center;
            border-radius: 14px 38px 14px 38px;
            transform: rotate(1.2deg);
            transition: transform 520ms cubic-bezier(.2,.8,.2,1), border-radius 520ms cubic-bezier(.2,.8,.2,1), box-shadow 220ms ease;
        }}
        .playlist-card:hover,
        .playlist-card:focus-visible {{
            transform: translateY(-7px) rotate(-.6deg) scale(1.015);
            border-radius: 38px 14px 38px 14px;
        }}
        .playlist-card-text {{
            padding: 16px 18px;
        }}
        .view-control {{
            width: fit-content;
            gap: 4px;
            padding: 5px;
            border: 1px solid rgba(255,255,255,.1);
            border-radius: 20px 7px 20px 7px;
            background: rgba(10,10,12,.74);
        }}
        .view-btn {{
            min-height: 38px;
            padding-inline: 14px;
            border-radius: 15px 5px 15px 5px;
            transform: none;
        }}
        .view-btn:hover,
        .view-btn:focus-visible {{
            transform: translateY(-2px);
            border-radius: 5px 15px 5px 15px;
        }}
        .view-btn.active {{
            border-radius: 18px 5px 18px 5px;
            transform: scale(1.04);
        }}
        .card {{
            border-radius: 24px 8px 24px 8px;
            transition:
                transform 420ms cubic-bezier(.2,.8,.2,1),
                border-radius 420ms cubic-bezier(.2,.8,.2,1),
                box-shadow 220ms ease,
                border-color 180ms ease;
        }}
        .card:hover,
        .card:focus-visible {{
            border-radius: 8px 24px 8px 24px;
            transform: translateY(-8px) scale(1.02) rotate(-.35deg);
        }}
        body.view-rearranging .card {{
            pointer-events: none;
            will-change: transform, opacity;
        }}
        body[data-view="gallery"] .card {{
            border-radius: 12px 4px 12px 4px;
        }}
        @media (max-width: 820px) {{
            .site-hero {{
                grid-template-columns: 1fr;
            }}
            .hero-copy {{
                min-height: 0;
            }}
            .p53-broadcast {{
                min-height: 280px; /* leave room for Radio P53 and the album transmission */
                border-radius: 12px 34px 12px 34px;
            }}
            .p53-art img {{ min-height: 100%; }}
            .filter-btn {{ flex-basis: calc(33.333% - 5px); }}
            .filter-btn.active {{ flex-grow: 1.8; }}
            .filter-description {{ grid-template-columns: 1fr; }}
            body.filter-active .filter-description {{ min-height: 0; }}
            .playlist-card {{
                width: min(100%, 330px);
                justify-self: start;
            }}
        }}
        @media (max-width: 520px) {{
            .wordmark {{
                font-size: clamp(72px, 25vw, 108px);
                padding: 9px 20px 13px 15px;
            }}
            .hero-copy .intro p {{ font-size: 14px; }}
            .p53-overlay {{ padding: 15px; gap: 10px; }}
            .p53-album {{ width: 68px; }}
            .p53-signal-copy {{ max-width: 78%; }}
            .p53-radio {{ font-size: 38px; }}
            .filter-btn {{
                flex-basis: calc(50% - 5px);
                min-height: 48px;
            }}
            .filter-btn.active {{ flex-basis: 100%; }}
            body.filter-active .filter-description {{
                max-height:none;
                padding:24px 18px;
            }}
            .filter-description h2 {{ font-size: clamp(42px, 17vw, 74px); }}
            .playlist-card {{ width:min(100%,260px); }}
            .view-control {{ width: auto; }}
            .view-btn {{ flex: 1; }}
        }}

        @media (prefers-reduced-motion: reduce) {{
            *, *::before, *::after {{
                animation-duration: .01ms !important;
                animation-iteration-count: 1 !important;
                transition-duration: .01ms !important;
                scroll-behavior: auto !important;
            }}
        }}
    </style>
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
    <div class="view-control" role="group" aria-label="Archive view">
        <span class="view-control-label">VIEW</span>

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
    <div class="grid">
        {''.join(cards)}
    </div>
<script>
    document.addEventListener("DOMContentLoaded", () => {{ // wait until the page exists before selecting buttons/cards
        const viewButtons = document.querySelectorAll(".view-btn");
        const allowedViews = new Set(["poster", "wall", "gallery"]);
        const filterInfo = {filter_data_json}; // filter data generated from config.json
        const buttons = document.querySelectorAll(".filter-btn"); // all clickable filter buttons
        const cards = document.querySelectorAll(".card"); // all song cards
        const grid = document.querySelector(".grid");
        const box = document.querySelector("#filter-description-box"); // whole description box
        const title = document.querySelector("#filter-title"); // filter description title
        const description = document.querySelector("#filter-description"); // filter description text
        const playlistCard = document.querySelector("#playlist-card");
        const playlistCover = document.querySelector("#playlist-cover");
        const playlistCta = document.querySelector("#playlist-cta");
        const filterCount = document.querySelector("#filter-count");
        const filterStart = document.querySelector("#filter-start");
        const filterStartTitle = document.querySelector("#filter-start-title");
        const filterStartArtist = document.querySelector("#filter-start-artist");
        const filterFragments = document.querySelector("#filter-fragments");
        const filterRoomLabel = document.querySelector("#filter-room-label");
        const filterDecor = document.querySelector("#filter-decor");

        let activeFilter = null; // no filter is active when page first loads
        function storeView(viewName) {{
            try {{
                localStorage.setItem("gsi-view", viewName);
            }} catch (error) {{
                // the view still works if storage is unavailable.
            }}
        }}
        let viewSwitchTimer = null;
        function applyView(viewName, animate = true) {{
            if (!allowedViews.has(viewName)) {{
                viewName = "wall"; // default view
            }}
            const updateView = () => {{
                document.body.dataset.view = viewName;
                viewButtons.forEach(button => {{
                    const isActive = button.dataset.view === viewName;
                    button.classList.toggle("active", isActive);
                    button.setAttribute("aria-pressed", String(isActive));
                }});
                storeView(viewName);
            }};
            const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
            if (!animate || reducedMotion) {{
                updateView();
                return;
            }}
            // Fade only the grid; moving every card made view changes stutter.
            window.clearTimeout(viewSwitchTimer);
            grid.classList.add("view-switching");
            viewSwitchTimer = window.setTimeout(() => {{
                updateView();
                requestAnimationFrame(() => requestAnimationFrame(() => {{
                    grid.classList.remove("view-switching");
                }}));
            }}, 110);
        }}
        viewButtons.forEach(button => {{
            button.addEventListener("click", () => {{
                applyView(button.dataset.view);
            }});
        }});
        function hidePlaylist() {{
            playlistCard.classList.add("hidden");
            playlistCard.removeAttribute("href");
            playlistCover.removeAttribute("src");
            playlistCover.style.display = "none";
            playlistCta.textContent = "";
        }}
        function triggerSignalTransform() {{
            if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
            document.body.classList.remove("signal-transforming");
            void document.body.offsetWidth; // restart the short transformation on repeated filter changes
            document.body.classList.add("signal-transforming");
            window.setTimeout(() => document.body.classList.remove("signal-transforming"), 720);
        }}
        function clearFilter() {{ // return to default homepage state
            activeFilter = null; // forget active filter
            document.body.classList.remove("filter-active");
            document.body.removeAttribute("data-active-filter");
            document.documentElement.style.setProperty("--page-tint", "#ffffff"); // reset tint/glow

            buttons.forEach(button => {{ // remove active look from every button
                button.classList.remove("active");
                button.setAttribute("aria-pressed", "false");
            }});

            cards.forEach(card => {{ // show every song card
                card.style.display = "flex";
            }});

            box.classList.add("hidden"); // hide description panel
            title.textContent = ""; // clear title
            description.textContent = ""; // clear text
            box.removeAttribute("data-filter-label");
            box.removeAttribute("data-filter");
            box.classList.remove("filter-entering");
            filterRoomLabel.replaceChildren();
            filterDecor.replaceChildren();
            filterCount.textContent = "";
            filterStart.classList.add("hidden");
            filterStart.removeAttribute("href");
            filterFragments.replaceChildren();
            hidePlaylist();
        }}

        function setFilter(filterName) {{ // activate a filter
            if (activeFilter === filterName) {{ // clicking same filter again clears it
                clearFilter();
                return;
            }}

            activeFilter = filterName; // remember active filter
            triggerSignalTransform();
            document.body.classList.add("filter-active"); // we attach and remove a CSS class whose appearance is controlled by javascript
            document.body.dataset.activeFilter = filterName;
            const info = filterInfo[filterName]; // get label/description/color from config.json

            document.documentElement.style.setProperty("--page-tint", info.color); // update glow/tint
            title.textContent = info.label; // update panel title
            description.textContent = info.description; // update panel text
            description.hidden = !info.description;
            box.dataset.filterLabel = info.label;
            box.dataset.filter = filterName;
            box.classList.remove("hidden"); // reveal before restarting entrance animations
            box.classList.remove("filter-entering");
            void box.offsetWidth; // restart filter-specific entrance effects
            box.classList.add("filter-entering");
            window.setTimeout(() => box.classList.remove("filter-entering"), 1000);
            filterRoomLabel.replaceChildren(...info.room_label_lines.map(line => {{
                const span = document.createElement("span");
                span.textContent = line;
                return span;
            }}));
            filterDecor.replaceChildren();
            if (filterName === "pop") {{
                const popSignals = [
                    [12, 16, 26, -900, 3.7], [72, 12, 52, -2400, 5.1], [42, 36, 34, -600, 4.3],
                    [82, 58, 24, -3100, 5.7], [18, 70, 58, -1700, 4.9], [58, 78, 30, -3800, 6.2], [34, 8, 20, -1200, 3.4]
                ];
                popSignals.forEach(([x, y, size, delay, speed]) => {{
                    const pop = document.createElement("span");
                    pop.textContent = "POP";
                    pop.style.setProperty("--pop-x", `${{x}}%`);
                    pop.style.setProperty("--pop-y", `${{y}}%`);
                    pop.style.setProperty("--pop-size", `${{size}}px`);
                    pop.style.setProperty("--pop-delay", `${{delay}}ms`);
                    pop.style.setProperty("--pop-speed", `${{speed}}s`);
                    filterDecor.append(pop);
                }});
            }}
            filterCount.textContent = `${{String(info.count).padStart(2, "0")}} SIGNAL${{info.count === 1 ? "" : "S"}}`;
            if (info.start_url) {{
                filterStart.href = info.start_url;
                filterStartTitle.textContent = info.start_title;
                filterStartArtist.textContent = info.start_artist;
                filterStart.classList.remove("hidden");
            }} else {{
                filterStart.classList.add("hidden");
                filterStart.removeAttribute("href");
            }}
            filterFragments.replaceChildren(...info.preview_covers.map((src, index) => {{
                const image = document.createElement("img");
                image.src = src;
                image.alt = "";
                image.style.setProperty("--fragment-index", index);
                return image;
            }}));
            box.classList.remove("hidden"); // show description panel
            if (info.playlist_url || info.playlist_cover) {{
                playlistCard.href = info.playlist_url || info.start_url;
                if (info.playlist_url) {{
                    playlistCard.target = "_blank";
                }} else {{
                    playlistCard.removeAttribute("target");
                }}
                playlistCard.style.setProperty("--playlist-accent", info.playlist_color || info.color);
                playlistCta.textContent = info.playlist_url
                    ? `${{info.playlist_cta || "Want more of the same?"}} ↗`
                    : "CURRENT SIGNAL ↗";
                if (info.playlist_cover) {{
                    playlistCover.src = info.playlist_cover;
                    playlistCover.style.display = "block";
                }} else {{
                    playlistCover.removeAttribute("src");
                    playlistCover.style.display = "none";
                }}
                playlistCard.classList.remove("hidden");
            }} else {{
                hidePlaylist();
            }}
            buttons.forEach(button => {{ // update active button style
                const isActive = button.dataset.filter === filterName; // === checks exact equality
                button.classList.toggle("active", isActive);
                button.setAttribute("aria-pressed", String(isActive)); // converts boolean true/false into text
            }});

            cards.forEach(card => {{ // show/hide cards based on tags
                const tags = (card.dataset.tags || "").split(" "); // tags from tracks.csv
                const shouldShow = tags.includes(filterName); // overlap works here
                card.style.display = shouldShow ? "flex" : "none";
            }});
        }}

        buttons.forEach(button => {{ // attach click behavior to every filter button
            button.addEventListener("click", () => {{
                setFilter(button.dataset.filter);
            }});
        }});
        let savedView = "wall";
        try {{
            savedView = localStorage.getItem("gsi-view") || "wall";
        }} catch (error) {{
            savedView = "wall"; // fallback if localStorage is unavailable
        }}
        applyView(savedView, false); // set view to saved preference without animation
        clearFilter(); // initialize with all cards visible and description hidden
    }});
</script>
</body>
</html>
"""  # full HTML page as one string

    index_path = SITE_DIR / "index.html"
    index_path.write_text(index_html, encoding = "utf-8")
    print(f"\nBuilt visual index: {index_path}")

def build_404_page(tracks: list[dict]) -> None:
    config = load_config()
    copy = config.get("not_found", {}) # editable 404 wording lives in config.json
    site_url = (config.get("site_url") or "").rstrip("/")
    site_path = "/" + site_url.split("/", 3)[-1].split("/", 1)[-1].strip("/") + "/" if ".github.io/" in site_url else "/"
    recommendations = [
        {
            "track": item["track"],
            "artist": item["artist"],
            "album": item["album"],
            "cover": item.get("cover_file", ""),
            "url": f'entries/{item["html_file"]}',
            "accent": item["accent"],
            "spotify": item.get("spotify_url") or f'https://open.spotify.com/search/{quote(item["artist"] + " " + item["track"], safe="")}',
            "apple": item.get("apple_url") or f'https://music.apple.com/search?term={quote_plus(item["artist"] + " " + item["track"])}',
        }
        for item in tracks
    ]
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
        .protein-rain span {{ position:absolute; left:var(--x); top:-100px; width:var(--size); aspect-ratio:1; background:url("covers/P53_cover.png") center/420%; border-radius:62% 38% 67% 33% / 42% 58% 42% 58%; clip-path:polygon(46% 0,64% 11%,72% 30%,95% 41%,83% 58%,96% 78%,72% 92%,51% 78%,30% 100%,18% 73%,0 58%,17% 39%,8% 17%,32% 21%); filter:grayscale(.6) contrast(1.35) drop-shadow(7px 4px 0 rgba(255,79,163,.45)); animation:dissolve var(--speed) linear var(--delay) infinite; }}
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
            <p class="message">{html.escape(copy.get("message", "The page slipped out of the archive."))}</p>
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
                    <a class="read" id="signal-read" href="#">READ IN GSI</a>
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

def main() -> None:
    parser = argparse.ArgumentParser(description = "Build the GSI static website.")
    parser.add_argument(
        "--site-only",
        action = "store_true",
        help = "Generate site files without creating or updating entries and covers.",
    )
    args = parser.parse_args()
    tracks = build_entries(write_sources = not args.site_only)
    config = load_config()
    p53_history = prepare_p53_history(config, tracks, download_missing = True)
    copy_site_covers()
    remove_stale_entry_pages(tracks)
    for item in tracks:
        build_entry_page(item)
    p53_slug = (config.get("p53_current_slug") or "").strip()
    for item in p53_history:
        build_p53_page(item, f'{item["slug"]}.html')
    p53_item = next((item for item in p53_history if item["slug"] == p53_slug), None)
    if p53_item:
        build_p53_page(p53_item, "latest.html")
    if p53_history:
        build_p53_archive(p53_history, p53_slug)
    build_index_html(tracks)
    build_404_page(tracks)
    print("\nDone.")

if __name__ == "__main__":
    main()


