import csv #so I can read csv files per rows of organized data
import json #so I can change the categories at ease via config.json
import re # so I can clean file names?
from pathlib import Path # cross OS handling
from urllib.parse import quote_plus # allows search text to be URL safe

import requests # web requests
from PIL import Image # read covers and extract colors

BASE = Path(".") # THIS folder
ENTRIES_DIR = BASE / "entries" # markdown file generation path
COVERS_DIR = BASE / "covers" # album cover saving path
SITE_DIR = BASE / "site" #HTML index creation path

TRACKS_FILE = BASE / "tracks.csv" #list of song inputs
CONFIG_FILE = BASE / "config.json" #settings file

ENTRIES_DIR.mkdir(exist_ok = True) #creates entry folder, but not on repeat
COVERS_DIR.mkdir(exist_ok = True)
SITE_DIR.mkdir(exist_ok = True)

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
    image = Image.open(image_path).convert("RGB")
    image = image.resize((80, 80)) # SHRINK FOR FASTER

    reduced = image.quantize(colors = 6).convert("RGB") #SIX MAIN COLORS!!
    colors = reduced.getcolors(80 * 80)  #for quantification check

    if colors is None:
        return "#444444" #GRAY
    colors.sort(reverse = True) # Most common comes first
    r, g, b = colors[0][1] # extract values
    return f"#{r:02x}{g:02x}{b:02x}" # hex color code

def make_frontmatter(artist: str, track: str, album: str, cover_file: str, accent: str) -> str: #markdown file metadata
    return f"""---
artist: "{artist}"
track: "{track}"
album: "{album}"
cover: "../covers/{cover_file}"
accent: "{accent}"
---
"""

def make_markdown_template(artist: str, track: str, album: str, cover_file: str, accent: str, sections: list[str]) -> str:  #ENTRY
    section_text = "\n\n".join([f"## {section}\n\n" for section in sections]) # headings from config.json

    cover_markdown = "" # default to empty cover line
    if cover_file: # IF it exists
        cover_markdown = f"![cover](../covers/{cover_file})\n\n"  # proper syntax

    return f"""{make_frontmatter(artist, track, album, cover_file, accent)}

# {track} — {artist}

{cover_markdown}**Album:** {album}
**Accent:** `{accent}`

{section_text}
"""

def append_missing_sections(entry_path: Path, sections: list[str]) -> None:  # add new settings
    text = entry_path.read_text(encoding = "utf-8")
    missing_sections = [] # sections that exist in config but not in this entry
    for section in sections: # check in line
        heading = f"## {section}" # markdown syntax for heading..
        if heading not in text:
            missing_sections.append(section) # recall if empty
    if not missing_sections: # if all is well
        return

    addition = "\n\n" + "\n\n".join([f"## {section}\n\n" for section in missing_sections]) # NEW ONES ONLY
    entry_path.write_text(text.rstrip() + addition + "\n", encoding = "utf-8") # append but don't overwrite

def build_entries() -> list[dict]: # Main Builder for markdown and covers
    config = load_config() #read settings
    sections = config["sections"]
    force_refresh_covers = config.get("force_refresh_covers", False)
    built_tracks = [] #store metadata for HTML gallery

    for row in ordered_tracks(read_tracks(), config): #loop songs in tracks.csv
        artist = row["artist"].strip()
        track = row["track"].strip()
        album = row["album"].strip() #cleanup
        manual_cover_url = (row.get("cover_url") or "").strip()

        slug = slugify(f"{artist}-{track}") # base filename
        entry_path = ENTRIES_DIR / f"{slug}.md"
        cover_path = COVERS_DIR / f"{slug}.jpg" #paths

        should_download_cover = force_refresh_covers or manual_cover_url or not cover_path.exists()
        if should_download_cover:
            if manual_cover_url:
                cover_url = manual_cover_url
            else:
                cover_url = search_itunes_cover(artist, track, album)
            if cover_url is None:
                print(f" No cover found for {track}.")
                accent = "#444444"
                cover_file = ""
            else:
                download_ok = download_cover(cover_url, cover_path) # try to download cover without crashing
                if download_ok: # if cover downloaded successfully
                    accent = dominant_color(cover_path)
                    cover_file = cover_path.name
                else: # if manual/auto cover failed
                    accent = "#444444"
                    cover_file = ""
        else:
            accent = dominant_color(cover_path) # use existing cover
            cover_file = cover_path.name

        if not entry_path.exists():
            note = make_markdown_template(artist, track, album, cover_file, accent, sections)
            entry_path.write_text(note, encoding = "utf-8")
            print(f" Created entry: {entry_path}")
        else:
            append_missing_sections(entry_path, sections)
            print(" Entry already exists. Synced missing sections only.")

        built_tracks.append({  # save data needed for the index
            "artist": artist,
            "track": track,
            "album": album,
            "slug": slug,
            "entry_file": entry_path.name,
            "cover_file": cover_file,
            "accent": accent
        })
    return built_tracks # HTML builder save

def build_index_html(tracks: list[dict]) -> None:  #sample homepage
    config = load_config()
    project_title = config.get("project_title", "GSI")
    page_title = config.get("page_title", project_title)
    intro = config.get("intro", "")
    cards = [] # stores HTML chunks for every song card

    for item in tracks:
        cover_html = ""
        if item["cover_file"]:
            cover_html = f'<img src="../covers/{item["cover_file"]}" alt="{item["album"]} cover">'  # image tag
        card = f"""
        <a class="card" href="../entries/{item["entry_file"]}" style="--accent: {item["accent"]};">
            {cover_html}
            <div class="info">
                <h2>{item["track"]}</h2>
                <p>{item["artist"]}</p>
                <span>{item["album"]}</span>
            </div>
        </a>
        """  # one visual card, colored by album accent

        cards.append(card)  # add this card to the gallery
    intro_html = ""
    if intro.strip():
        intro_html = f"""
        <section class = "intro">
            <p>{intro}</p>
        </section>
        """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{project_title}</title>
    <style>
        body {{
            margin: 0;
            padding: 40px;
            font-family: Arial, sans-serif;
            background: #111;
            color: #eee;
        }}

        h1 {{
            font-size: 42px;
            margin: 0 0 22px;
            letter spacing: -0.03em;
        }}
        .intro {{
            max-width: 850px;
            margin: 0 0 30px;
            padding: 20px 22px;
            border-radius: 24px;
            background: rgba(28, 28, 28, .86);
            border: 1px solid rgba(255, 255, 255, .09);
            box-shadow: 0 0 35px rgba(0,0,0,.22);
        }}

        .intro p {{
            margin: 0;
            line-height: 1.6;
            color: #d8d8d8;
            font-size: 16px;
        }}

        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
            gap: 20px;
        }}

        .card {{
            display: block;
            text-decoration: none;
            color: #eee;
            background: #1b1b1b;
            border: 2px solid var(--accent);
            border-radius: 18px;
            overflow: hidden;
            box-shadow: 0 0 30px color-mix(in srgb, var(--accent), transparent 80%);
            transition: transform 0.15s ease;
        }}

        .card:hover {{
            transform: translateY(-4px);
        }}

        img {{
            width: 100%;
            display: block;
        }}

        .info {{
            padding: 18px;
        }}

        .info h2 {{
            margin: 0 0 8px;
            font-size: 22px;
        }}

        .info p {{
            margin: 0 0 6px;
            color: #ccc;
        }}

        .info span {{
            font-size: 14px;
            color: var(--accent);
        }}
    </style>
</head>
<body>
    <h1>{page_title}</h1>
    {intro_html}
    <div class="grid">
        {''.join(cards)}
    </div>
</body>
</html>
"""  # full HTML page as one string

    index_path = SITE_DIR / "index.html"
    index_path.write_text(html, encoding = "utf-8")
    print(f"\nBuilt visual index: {index_path}")

def main() -> None:
    tracks = build_entries()
    build_index_html(tracks)
    print("\nDone.")

if __name__ == "__main__":
    main()


