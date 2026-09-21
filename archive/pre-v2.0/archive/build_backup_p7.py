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
        manual_cover_file = (row.get("cover_file") or "").strip()
        tags = (row.get("tags") or "").strip()

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
        needs_download = force_refresh_covers or manual_cover_url or not cover_path.exists()
        should_download_cover = (not has_local_cover) and needs_download

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
            if cover_path.exists():
                accent = dominant_color(cover_path) # use existing cover
                cover_file = cover_path.name
            else:
                accent = "#444444"
                cover_file = ""

        if not entry_path.exists():
            note = make_markdown_template(artist, track, album, cover_file, accent, sections)
            entry_path.write_text(note, encoding = "utf-8")
            print(f" Created entry: {entry_path}")
        else:
            append_missing_sections(entry_path, sections)
            print(" Entry already exists. Synced missing sections only.")

        built_tracks.append({  # save data needed for the index
            "tags": tags,
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
    filters = config.get("filters", {})
    cards = [] # stores HTML chunks for every song card

    for item in tracks:
        cover_html = ""
        if item["cover_file"]:
            cover_html = f'<img src="../covers/{item["cover_file"]}" alt="{item["album"]} cover">'  # image tag
        tags = item.get("tags", "")
        tags_for_attr = tags.lower().replace(","," ")
        card = f"""
        <a class="card" data-tags="{tags_for_attr}" href="../entries/{item["entry_file"]}" style="--accent: {item["accent"]};">
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
    filter_buttons = []

    filter_data = {}


    for filter_key, filter_settings in filters.items(): # build one button per config filter
        label = filter_settings.get("label", filter_key) # visible button text
        description = filter_settings.get("description", "") # panel text
        color = filter_settings.get("color", "#ffffff") # page tint color

        filter_buttons.append(
            f'<button class="filter-btn" data-filter="{filter_key}">{label}</button>'
        )

        filter_data[filter_key] = {
            "label": label,
            "description": description,
            "color": color
        }

    filters_html = f"""
    <section class="filter-panel">
        <div class="filter-row">
            {''.join(filter_buttons)}
        </div>
        <div class="filter-description hidden" id="filter-description-box">
            <h2 id="filter-title"></h2>
            <p id="filter-description"></p>
        </div>
    </section>
    """

    filter_data_json = json.dumps(filter_data) # turns Python dict into JavaScript object text
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{project_title}</title>
    <style>
        body {{
            transition: background 0.25s ease;
            margin: 0;
            padding: 40px;
            font-family: Arial, sans-serif;
            background: #111;
            color: #eee;
        }}

        h1 {{
            font-size: 42px;
            margin: 0 0 22px;
            letter-spacing: -0.03em;
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
                .filter-panel {{
            margin: 0 0 30px;
        }}

        .filter-row {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-bottom: 16px;
        }}

        .filter-btn {{
            border: 1px solid rgba(255,255,255,.14);
            border-radius: 999px;
            padding: 9px 14px;
            background: #191919;
            color: #eaeaea;
            cursor: pointer;
            transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
        }}

        .filter-btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 0 24px color-mix(in srgb, var(--page-tint, #ffffff), transparent 70%);
        }}

        .filter-btn.active {{
            border-color: color-mix(in srgb, var(--page-tint, #ffffff), white 35%);
            background: color-mix(in srgb, var(--page-tint, #ffffff), #111 70%);
            box-shadow: 0 0 22px color-mix(in srgb, var(--page-tint, #ffffff), transparent 65%);
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
            display: none;
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
    {filters_html}
    <div class="grid">
        {''.join(cards)}
    </div>
<script>
    document.addEventListener("DOMContentLoaded", () => {{ // wait until the page exists before selecting buttons/cards
        const filterInfo = {filter_data_json}; // filter data generated from config.json
        const buttons = document.querySelectorAll(".filter-btn"); // all clickable filter buttons
        const cards = document.querySelectorAll(".card"); // all song cards
        const box = document.querySelector("#filter-description-box"); // whole description box
        const title = document.querySelector("#filter-title"); // filter description title
        const description = document.querySelector("#filter-description"); // filter description text

        let activeFilter = null; // no filter is active when page first loads

        function clearFilter() {{ // return to default homepage state
            activeFilter = null; // forget active filter
            document.documentElement.style.setProperty("--page-tint", "#ffffff"); // reset tint/glow

            buttons.forEach(button => {{ // remove active look from every button
                button.classList.remove("active");
            }});

            cards.forEach(card => {{ // show every song card
                card.style.display = "block";
            }});

            box.classList.add("hidden"); // hide description panel
            title.textContent = ""; // clear title
            description.textContent = ""; // clear text
        }}

        function setFilter(filterName) {{ // activate a filter
            if (activeFilter === filterName) {{ // clicking same filter again clears it
                clearFilter();
                return;
            }}

            activeFilter = filterName; // remember active filter
            const info = filterInfo[filterName]; // get label/description/color from config.json

            document.documentElement.style.setProperty("--page-tint", info.color); // update glow/tint
            title.textContent = info.label; // update panel title
            description.textContent = info.description; // update panel text
            box.classList.remove("hidden"); // show description panel

            buttons.forEach(button => {{ // update active button style
                button.classList.toggle("active", button.dataset.filter === filterName);
            }});

            cards.forEach(card => {{ // show/hide cards based on tags
                const tags = card.dataset.tags || ""; // tags from tracks.csv
                const shouldShow = tags.includes(filterName); // overlap works here
                card.style.display = shouldShow ? "block" : "none";
            }});
        }}

        buttons.forEach(button => {{ // attach click behavior to every filter button
            button.addEventListener("click", () => {{
                setFilter(button.dataset.filter);
            }});
        }});

        clearFilter(); // initialize with all cards visible and description hidden
    }});
</script>
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


