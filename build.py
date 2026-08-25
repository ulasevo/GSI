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

TRACKS_FILE = BASE / "tracks.csv" #list of song inputs
CONFIG_FILE = BASE / "config.json" #settings file

ENTRIES_DIR.mkdir(exist_ok = True) #creates entry folder, but not on repeat
COVERS_DIR.mkdir(exist_ok = True)
SITE_DIR.mkdir(exist_ok = True)
SITE_ENTRIES_DIR.mkdir(exist_ok = True) #creates entries

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
    url = f"https://itunes.apple.com/search?term={query}&entity=song&limit=1"  # iTunes search

    response = requests.get(url, timeout = 15)
    response.raise_for_status() # yields error

    data = response.json()
    if data["resultCount"] == 0:
        return None
    artwork_url = data["results"][0].get("artworkUrl100") # gives 100"100 cover
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
        section_cards.append(f"""
        <section class="section-card">
            <h2>{html.escape(section["title"])}</h2>
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

        @media (max-width: 760px) {{
            .hero {{
                grid-template-columns: 1fr;
            }}

            .meta h1 {{
                font-size: 34px;
            }}
        }}
    </style>
</head>
<body>
    <main class="page">
        <a class="back" href="../index.html">← Back to GSI</a>

        <section class="hero">
            {cover_html}
            <div class="meta">
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
</body>
</html>
"""

    output_path = SITE_ENTRIES_DIR / item["html_file"] # final generated review page path
    output_path.write_text(html_page, encoding="utf-8") # save page)


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
    if homepage_url:
        safe_homepage_url = html.escape(homepage_url, quote = True)
        homepage_url_meta = f"""
    <link rel="canonical" href="{safe_homepage_url}">
    <meta property="og:url" content="{safe_homepage_url}">
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
        filter_buttons.append(
            f'<button class="filter-btn" data-filter="{safe_filter_key}" aria-pressed="false">{safe_label}</button>'
        )

        filter_data[filter_key] = {
            "label": label,
            "description": description,
            "color": color,
            "playlist_url": playlist_url,
            "playlist_cover": playlist_src,
            "playlist_color": playlist_color,
            "playlist_cta": playlist_cta
        }

    filters_html = f"""
    <section class="filter-panel">
        <div class="filter-row">
            {''.join(filter_buttons)}
        </div>
        <div class="filter-description hidden" id="filter-description-box">
            <div class="filter-copy">
                <h2 id="filter-title"></h2>
                <p id="filter-description"></p>
            </div>
            <a class="playlist-card hidden" id="playlist-card" href="#" target="_blank" rel="noopener noreferrer">
                <img id="playlist-cover" alt="Playlist cover">
                <div class="playlist-card-text" id="playlist-cta"></div>
            </a>
        </div>
    </section>
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
    <meta property="og:description" content="{safe_meta_description}">{homepage_url_meta}
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
            view-transition-name: archive-grid;
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
        :root {{
            view-transition-name: none;
        }}
        /* Animate one grid snapshot so changing views stays light on mobile. */
        ::view-transition-group(archive-grid) {{
            animation: none; /* prevent the browser from stretching the grid between sizes */
        }}
        /* Let the old wall settle downward instead of shrinking away. */
        ::view-transition-old(archive-grid) {{
            animation: archive-wall-out 700ms ease-in-out both;
            mix-blend-mode: normal;
        }}
        /* Bring the new layout in gently without zooming its cards. */
        ::view-transition-new(archive-grid) {{
            animation: archive-wall-in 700ms ease-out both;
            mix-blend-mode: normal;
        }}
        @keyframes archive-wall-out {{
            from {{
                opacity: 1;
                transform: translateY(0);
            }}
            to {{
                opacity: 0;
                transform: translateY(8px);
            }}
        }}
        @keyframes archive-wall-in {{
            from {{
                opacity: 0;
                transform: translateY(-8px);
                }}
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
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
    <header class = "site-hero">
        <div class = "wordmark">GSI</div>
        <div class = "subtitle">{safe_page_title}</div>
    </header>
    {intro_html}
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
        const box = document.querySelector("#filter-description-box"); // whole description box
        const title = document.querySelector("#filter-title"); // filter description title
        const description = document.querySelector("#filter-description"); // filter description text
        const playlistCard = document.querySelector("#playlist-card");
        const playlistCover = document.querySelector("#playlist-cover");
        const playlistCta = document.querySelector("#playlist-cta");

        let activeFilter = null; // no filter is active when page first loads
        function storeView(viewName) {{
            try {{
                localStorage.setItem("gsi-view", viewName);
            }} catch (error) {{
                // the view still works if storage is unavailable.
            }}
        }}
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
            if (animate && !reducedMotion && document.startViewTransition) {{
                document.documentElement.classList.add("view-changing");
                const transition = document.startViewTransition(updateView);
                transition.finished.finally(() => {{
                    document.documentElement.classList.remove("view-changing");
                }});
            }} else {{
                updateView();
            }}
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
        function clearFilter() {{ // return to default homepage state
            activeFilter = null; // forget active filter
            document.body.classList.remove("filter-active");
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
            hidePlaylist();
        }}

        function setFilter(filterName) {{ // activate a filter
            if (activeFilter === filterName) {{ // clicking same filter again clears it
                clearFilter();
                return;
            }}

            activeFilter = filterName; // remember active filter
            document.body.classList.add("filter-active"); // we attach and remove a CSS class whose appearance is controlled by javascript
            const info = filterInfo[filterName]; // get label/description/color from config.json

            document.documentElement.style.setProperty("--page-tint", info.color); // update glow/tint
            title.textContent = info.label; // update panel title
            description.textContent = info.description; // update panel text
            box.classList.remove("hidden"); // show description panel
            if (info.playlist_url) {{
                playlistCard.href = info.playlist_url;
                playlistCard.style.setProperty("--playlist-accent", info.playlist_color || info.color);
                playlistCta.textContent = `${{info.playlist_cta || "Want more of the same?"}} ↗`;
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

def main() -> None:
    parser = argparse.ArgumentParser(description = "Build the GSI static website.")
    parser.add_argument(
        "--site-only",
        action = "store_true",
        help = "Generate site files without creating or updating entries and covers.",
    )
    args = parser.parse_args()
    tracks = build_entries(write_sources = not args.site_only)
    copy_site_covers()
    remove_stale_entry_pages(tracks)
    for item in tracks:
        build_entry_page(item)
    build_index_html(tracks)
    print("\nDone.")

if __name__ == "__main__":
    main()


