"""Editable-source and P53 preparation stages for the GSI build.

This module owns network lookups, cover caching, Markdown metadata safety, and
the prepared signal records consumed by page renderers. It does not write HTML.
All filesystem locations are explicit arguments so the pipeline is testable and
cannot silently target a different checkout.
"""

import json
import re
from pathlib import Path
from urllib.parse import quote_plus

# Network lookups are optional. The bundled runtime may not include requests,
# so a tiny urllib fallback keeps site-only and offline checks available.
try:
    import requests
except ModuleNotFoundError:  # Keep site-only builds usable in the bundled runtime.
    from urllib.error import HTTPError, URLError
    from urllib.request import Request, urlopen

    class _CompatResponse:
        def __init__(self, payload: bytes):
            self.content = payload

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return json.loads(self.content.decode("utf-8"))

    class _CompatRequests:
        class RequestException(Exception):
            pass

        @staticmethod
        def get(url: str, *, timeout: int, headers: dict | None = None) -> _CompatResponse:
            request = Request(url, headers=headers or {})
            try:
                with urlopen(request, timeout=timeout) as response:
                    return _CompatResponse(response.read())
            except (HTTPError, URLError) as error:
                raise _CompatRequests.RequestException(str(error)) from error

    requests = _CompatRequests()

from gsi_assets import dominant_color
from gsi_data import load_config, ordered_tracks, read_tracks
from gsi_links import normalize_provider_url
from gsi_text import slugify


# Cover lookup is used only when a normal build needs missing artwork.
def search_itunes_cover(artist: str, track: str, album: str) -> str | None:
    """Find a high-confidence iTunes artwork URL using all three identities."""
    query = quote_plus(f"{artist} {track} {album}")
    response = requests.get(
        f"https://itunes.apple.com/search?term={query}&entity=song&limit=25",
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()
    if data.get("resultCount", 0) == 0:
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

    best_result = max(data["results"], key=result_score)
    if result_score(best_result) < 12:
        return None
    artwork_url = best_result.get("artworkUrl100")
    return artwork_url.replace("100x100bb", "600x600bb") if artwork_url else None


def download_cover(url: str, save_path: Path) -> bool:
    """Cache one cover without making a failed remote request fatal."""
    try:
        response = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        save_path.write_bytes(response.content)
        return True
    except requests.RequestException as error:
        print(f" Cover download failed: {url}")
        print(f" Reason: {error}")
        return False


# Metadata helpers change only the generated frontmatter and leave authored body
# lines alone.
def _frontmatter_value(value: str) -> str:
    """Encode one frontmatter value without allowing quotes to break the block."""
    return json.dumps(str(value), ensure_ascii=False)


def make_frontmatter(artist: str, track: str, album: str, cover_file: str, accent: str) -> str:
    return f"""---
artist: {_frontmatter_value(artist)}
track: {_frontmatter_value(track)}
album: {_frontmatter_value(album)}
cover: {_frontmatter_value(f"../covers/{cover_file}")}
accent: {_frontmatter_value(accent)}
---
"""


def make_section_prompt(section: str) -> str:
    prompts = {
        "Charge": "What state does this song trigger?",
        "Sonical Attraction": "What sound detail pulls you in? Rhythm, bass, vocal texture, distortion, switch, silence.",
        "Lyric/Vocal Detail": "Any line, delivery, breath, pronunciation, or vocal moment worth preserving?",
        "Version of ulaş": "What version of me does this song store? Time period, grind, breakup, desire, motion.",
        "Lore": "Any personal history, repeated use, place, habit, person attached to this track?",
        "Reading": "What do I think the song is doing or narrating?",
        "Comment": "Free field. Final take, vibe, joke, conclusion, or whatever does not fit elsewhere.",
    }
    return prompts.get(section, "Write whatever belongs here.")


def make_markdown_template(
    artist: str,
    track: str,
    album: str,
    cover_file: str,
    accent: str,
    sections: list[str],
) -> str:
    section_text = "\n\n".join(
        f"## {section}\n\n<!-- {make_section_prompt(section)} -->\n"
        for section in sections
    )
    cover_markdown = f"![cover](../covers/{cover_file})\n\n" if cover_file else ""
    return f"""{make_frontmatter(artist, track, album, cover_file, accent)}

# {track} — {artist}

{cover_markdown}**Album:** {album}
**Accent:** `{accent}`

{section_text}
"""


def sync_entry_metadata(
    entry_path: Path,
    artist: str,
    track: str,
    album: str,
    cover_file: str,
    accent: str,
) -> None:
    """Refresh generated metadata while preserving every authored body line."""
    text = entry_path.read_text(encoding="utf-8")
    new_frontmatter = make_frontmatter(artist, track, album, cover_file, accent).strip()
    if text.startswith("---"):
        parts = text.split("---", 2)
        body = parts[2].lstrip() if len(parts) == 3 else text
    else:
        body = text

    lines = body.splitlines()
    title_index = next((index for index, line in enumerate(lines) if line.startswith("# ")), None)
    title_line = f"# {track} — {artist}"
    if title_index is None:
        lines.insert(0, title_line)
        title_index = 0
    else:
        lines[title_index] = title_line

    cover_index = next(
        (index for index, line in enumerate(lines) if re.search(r"!\[cover\]\([^)]*\)", line)),
        None,
    )
    if cover_file and cover_index is None:
        lines[title_index + 1:title_index + 1] = ["", f"![cover](../covers/{cover_file})", ""]
        cover_index = title_index + 2

    preamble_start = cover_index + 1 if cover_index is not None else title_index + 1
    section_index = next(
        (index for index in range(preamble_start, len(lines)) if lines[index].startswith("## ")),
        len(lines),
    )
    if section_index >= preamble_start:
        preamble_range = range(preamble_start, section_index)
        album_index = next((index for index in preamble_range if re.match(r"^\*\*Album:\*\*", lines[index])), None)
        accent_index = next((index for index in preamble_range if re.match(r"^\*\*Accent:\*\*", lines[index])), None)
        if album_index is not None:
            lines[album_index] = f"**Album:** {album}"
        if accent_index is not None:
            lines[accent_index] = f"**Accent:** `{accent}`"
        missing_metadata = []
        if album_index is None:
            missing_metadata.append(f"**Album:** {album}")
        if accent_index is None:
            missing_metadata.append(f"**Accent:** `{accent}`")
        if missing_metadata:
            lines[section_index:section_index] = missing_metadata + [""]

    rebuilt_body = "\n".join(lines)
    if body.endswith(("\n", "\r")):
        rebuilt_body += "\n"
    entry_path.write_text(f"{new_frontmatter}\n\n{rebuilt_body.lstrip()}", encoding="utf-8")


def append_missing_sections(entry_path: Path, sections: list[str]) -> None:
    text = entry_path.read_text(encoding="utf-8")
    missing_sections = [section for section in sections if f"## {section}" not in text]
    if not missing_sections:
        return
    addition = "\n\n" + "\n\n".join(
        f"## {section}\n\n<!-- {make_section_prompt(section)} -->\n"
        for section in missing_sections
    )
    entry_path.write_text(text.rstrip() + addition + "\n", encoding="utf-8")


# Build ordinary song records and, when allowed, synchronize missing metadata.
def build_entries(
    *,
    tracks_file: Path | None = None,
    config_file: Path | None = None,
    entries_dir: Path | None = None,
    covers_dir: Path | None = None,
    write_sources: bool = True,
) -> list[dict]:
    """Prepare source entries and return renderer-ready signal records."""
    base = Path(__file__).resolve().parent.parent
    tracks_file = tracks_file or base / "tracks.csv"
    config_file = config_file or base / "config.json"
    entries_dir = entries_dir or base / "entries"
    covers_dir = covers_dir or base / "covers"
    config = load_config(config_file)
    sections = config["sections"]
    site_url = (config.get("site_url") or "").rstrip("/")
    force_refresh_covers = config.get("force_refresh_covers", False)
    built_tracks = []

    for row in ordered_tracks(read_tracks(tracks_file), config):
        artist, track, album = (row["artist"].strip(), row["track"].strip(), row["album"].strip())
        manual_cover_url = (row.get("cover_url") or "").strip()
        manual_cover_file = (row.get("cover_file") or "").strip()
        tags = (row.get("tags") or "").strip()
        manual_accent = (row.get("accent") or "").strip()
        spotify_url = (row.get("spotify_url") or "").strip()
        apple_url = (row.get("apple_url") or "").strip()
        normalized_spotify_url = normalize_provider_url(spotify_url, "spotify")
        normalized_apple_url = normalize_provider_url(apple_url, "apple")
        if spotify_url and not normalized_spotify_url:
            print(f" Invalid Spotify URL for {track}; using a search fallback.")
        if apple_url and not normalized_apple_url:
            print(f" Invalid Apple Music URL for {track}; using a search fallback.")

        slug = slugify(f"{artist}-{track}")
        entry_path = entries_dir / f"{slug}.md"
        cover_path = covers_dir / f"{slug}.jpg"
        if manual_cover_file:
            local_cover_path = covers_dir / manual_cover_file
            if local_cover_path.exists():
                cover_path = local_cover_path
            else:
                print(f" Local cover file not found for {track}: {manual_cover_file}")
                manual_cover_file = ""

        has_local_cover = bool(manual_cover_file)
        should_download_cover = write_sources and (not has_local_cover) and (
            force_refresh_covers or not cover_path.exists()
        )
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
                    accent, cover_file = dominant_color(cover_path), cover_path.name
                else:
                    accent, cover_file = "#444444", ""
            elif download_cover(cover_url, cover_path):
                accent, cover_file = dominant_color(cover_path), cover_path.name
            elif cover_path.exists():
                print(f" Using cached cover for {track}.")
                accent, cover_file = dominant_color(cover_path), cover_path.name
            else:
                accent, cover_file = "#444444", ""
        elif cover_path.exists():
            accent, cover_file = dominant_color(cover_path), cover_path.name
        else:
            accent, cover_file = "#444444", ""
        if manual_accent:
            accent = manual_accent

        if not entry_path.exists() and not write_sources:
            raise FileNotFoundError(f"Safe build stopped: missing source entry {entry_path.name}")
        if not entry_path.exists():
            entry_path.write_text(
                make_markdown_template(artist, track, album, cover_file, accent, sections),
                encoding="utf-8",
            )
            print(f" Created entry: {entry_path}")
        elif write_sources:
            sync_entry_metadata(entry_path, artist, track, album, cover_file, accent)
            append_missing_sections(entry_path, sections)
            print(f" Updated metadata and checked sections: {entry_path}")
        else:
            print(f" Read entry without modifying source: {entry_path}")

        built_tracks.append({
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
            "apple_url": normalized_apple_url,
        })
    return built_tracks


# P53 history can include transmission-only records; it must not create review
# files or alter Markdown during preparation.
def prepare_p53_history(
    config: dict,
    tracks: list[dict],
    covers_dir: Path | None = None,
    *,
    download_missing: bool = True,
) -> list[dict]:
    """Resolve P53 history without creating or changing Markdown sources."""
    covers_dir = covers_dir or Path(__file__).resolve().parent.parent / "covers"
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
        cover_path = covers_dir / cover_file
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


# Merge visible P53 records into the homepage catalogue without pretending they
# have ordinary entry prose.
def merge_p53_into_archive(tracks: list[dict], p53_history: list[dict]) -> list[dict]:
    """Expose opted-in P53 signals as cards without manufacturing review files."""
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
