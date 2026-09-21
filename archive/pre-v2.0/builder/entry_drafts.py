"""Link-first metadata and draft-entry helpers.

The draft workflow is deliberately separate from the page builder. It can
inspect a provider link, prepare a source record, and render an empty Markdown
entry without touching the catalogue until the caller explicitly asks to
write. Network access is limited to Apple's public lookup endpoint; Spotify
metadata remains an explicit later integration.
"""

import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request, urlopen

try:
    from builder.source_pipeline import make_markdown_template
except ModuleNotFoundError:
    # The published/main checkout predates the structural migration. Keep this
    # small authoring tool runnable there without copying the whole build stack.
    def _section_prompt(section: str) -> str:
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
        cover = f"![cover](../covers/{cover_file})\n\n" if cover_file else ""
        section_text = "\n\n".join(
            f"## {section}\n\n<!-- {_section_prompt(section)} -->\n"
            for section in sections
        )
        return (
            f"---\nartist: {json.dumps(artist, ensure_ascii=False)}\n"
            f"track: {json.dumps(track, ensure_ascii=False)}\n"
            f"album: {json.dumps(album, ensure_ascii=False)}\n"
            f"cover: {json.dumps(f'../covers/{cover_file}', ensure_ascii=False)}\n"
            f"accent: {json.dumps(accent, ensure_ascii=False)}\n---\n\n"
            f"# {track} — {artist}\n\n{cover}"
            f"**Album:** {album}\n**Accent:** `{accent}`\n\n{section_text}"
        )

try:
    from gsi_links import normalize_provider_url
except ModuleNotFoundError:
    from urllib.parse import urlunsplit

    def normalize_provider_url(value: str, provider: str) -> str:
        raw = (value or "").strip()
        allowed = {
            "apple": {"music.apple.com", "itunes.apple.com"},
            "spotify": {"open.spotify.com"},
        }.get(provider, set())
        try:
            parsed = urlsplit(raw)
            hostname = (parsed.hostname or "").lower()
        except ValueError:
            return ""
        if parsed.scheme.lower() != "https" or hostname not in allowed:
            return ""
        return urlunsplit(("https", hostname, parsed.path, parsed.query, parsed.fragment))

try:
    from gsi_text import slugify
except ModuleNotFoundError:
    import re

    def slugify(text: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", text.lower().strip()).strip("-")


class DraftMetadataError(ValueError):
    """Raised when a link cannot safely produce complete draft metadata."""


def provider_for_url(url: str) -> str:
    """Return the supported provider name for an HTTPS media URL."""
    normalized = normalize_provider_url(url, "apple")
    if normalized:
        return "apple"
    normalized = normalize_provider_url(url, "spotify")
    if normalized:
        return "spotify"
    raise DraftMetadataError(
        "The link must be an HTTPS Apple Music or Spotify URL."
    )


def apple_track_id(url: str) -> str:
    """Extract Apple's track id from a song URL."""
    query = parse_qs(urlsplit(url).query)
    track_id = (query.get("i") or [""])[0].strip()
    if not track_id.isdigit():
        raise DraftMetadataError(
            "This Apple Music link does not contain a track id (the `i=` value)."
        )
    return track_id


def _apple_lookup_payload(url: str, timeout: int = 15, opener=None) -> dict:
    """Fetch one Apple track record using the public iTunes lookup endpoint."""
    track_id = apple_track_id(url)
    lookup_url = f"https://itunes.apple.com/lookup?id={track_id}"
    request = Request(lookup_url, headers={"User-Agent": "GSI entry drafter"})
    opener = opener or urlopen
    try:
        with opener(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, OSError, json.JSONDecodeError) as error:
        raise DraftMetadataError(f"Apple Music lookup failed: {error}") from error
    results = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(results, list):
        raise DraftMetadataError("Apple Music returned an unreadable lookup response.")
    song = next((item for item in results if item.get("kind") == "song"), None)
    if not isinstance(song, dict):
        raise DraftMetadataError("Apple Music returned no song for this link.")
    return song


def metadata_from_apple_link(url: str, *, timeout: int = 15, opener=None) -> dict:
    """Resolve the safe, user-facing metadata needed for a new entry."""
    normalized_url = normalize_provider_url(url, "apple")
    if not normalized_url:
        raise DraftMetadataError("This is not a valid HTTPS Apple Music URL.")
    song = _apple_lookup_payload(normalized_url, timeout=timeout, opener=opener)
    artist = str(song.get("artistName") or "").strip()
    track = str(song.get("trackName") or "").strip()
    album = str(song.get("collectionName") or "").strip()
    if not artist or not track or not album:
        raise DraftMetadataError("Apple Music did not return artist, track, and album names.")
    artwork_url = str(song.get("artworkUrl100") or "").strip()
    if artwork_url:
        artwork_url = artwork_url.replace("100x100bb", "600x600bb")
    return {
        "provider": "apple",
        "artist": artist,
        "track": track,
        "album": album,
        "apple_url": normalized_url,
        "spotify_url": "",
        "cover_url": artwork_url,
    }


def metadata_from_link(
    url: str,
    *,
    artist: str = "",
    track: str = "",
    album: str = "",
    timeout: int = 15,
    opener=None,
) -> dict:
    """Resolve a link, allowing explicit overrides for uncertain metadata."""
    provider = provider_for_url(url)
    # A fully specified manual record is a safe offline path. The provider URL
    # remains canonical; artwork can still be discovered by the normal build.
    if provider == "apple" and not all(value.strip() for value in (artist, track, album)):
        metadata = metadata_from_apple_link(url, timeout=timeout, opener=opener)
    elif provider == "apple":
        metadata = {
            "provider": "apple",
            "artist": "",
            "track": "",
            "album": "",
            "apple_url": normalize_provider_url(url, "apple"),
            "spotify_url": "",
            "cover_url": "",
        }
    else:
        normalized_url = normalize_provider_url(url, "spotify")
        metadata = {
            "provider": "spotify",
            "artist": "",
            "track": "",
            "album": "",
            "apple_url": "",
            "spotify_url": normalized_url,
            "cover_url": "",
        }
    for key, override in (("artist", artist), ("track", track), ("album", album)):
        if override.strip():
            metadata[key] = override.strip()
    missing = [key for key in ("artist", "track", "album") if not metadata[key]]
    if missing:
        names = ", ".join(missing)
        raise DraftMetadataError(
            f"Spotify metadata is not looked up yet; provide --artist, --track, and --album ({names} missing)."
        )
    return metadata


def draft_record(metadata: dict, *, tags: str = "", accent: str = "") -> dict:
    """Convert resolved metadata into the exact fields expected by tracks.csv."""
    slug = slugify(f"{metadata['artist']}-{metadata['track']}")
    if not slug:
        raise DraftMetadataError("Artist and track do not produce a usable route slug.")
    return {
        "order": "",
        "tags": tags.strip(),
        "artist": metadata["artist"].strip(),
        "track": metadata["track"].strip(),
        "album": metadata["album"].strip(),
        "accent": accent.strip(),
        "cover_file": f"{slug}.jpg",
        "cover_url": metadata.get("cover_url", "").strip(),
        "spotify_url": metadata.get("spotify_url", "").strip(),
        "apple_url": metadata.get("apple_url", "").strip(),
        "slug": slug,
    }


def render_empty_entry(record: dict, sections: list[str]) -> str:
    """Render all configured headings so the author can keep or fill any of them."""
    accent = record.get("accent") or "#444444"
    return make_markdown_template(
        record["artist"],
        record["track"],
        record["album"],
        record["cover_file"],
        accent,
        sections,
    )


def p53_record_from_draft(record: dict) -> dict:
    """Prepare an explicit P53 history record without inventing status labels."""
    return {
        "artist": record["artist"],
        "track": record["track"],
        "album": record["album"],
        "slug": record["slug"],
        "cover_file": record["cover_file"],
        **({"apple_url": record["apple_url"]} if record.get("apple_url") else {}),
        **({"spotify_url": record["spotify_url"]} if record.get("spotify_url") else {}),
        "show_in_archive": True,
    }
