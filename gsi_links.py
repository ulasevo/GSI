"""Canonical external-media links and generated catalogue records.

The static site can only guarantee links that are explicit in source data.  When
an explicit provider URL is absent, these helpers create a clearly classified
search link rather than pretending that a fuzzy lookup is a canonical track.
"""

import html
from pathlib import Path
from urllib.parse import quote, quote_plus, urlsplit, urlunsplit


PROVIDER_HOSTS = {
    "spotify": {"open.spotify.com"},
    "apple": {"music.apple.com", "itunes.apple.com"},
}


def normalize_provider_url(value: str, provider: str) -> str:
    """Return a safe HTTPS provider URL, or an empty string when it is invalid."""
    raw = (value or "").strip()
    if not raw:
        return ""
    allowed_hosts = PROVIDER_HOSTS.get(provider, set())
    try:
        parsed = urlsplit(raw)
        hostname = (parsed.hostname or "").lower()
    except ValueError:
        return ""
    if (
        parsed.scheme.lower() != "https"
        or not hostname
        or hostname not in allowed_hosts
        or parsed.username
        or parsed.password
    ):
        return ""
    return urlunsplit(("https", hostname, parsed.path, parsed.query, parsed.fragment))


def provider_search_url(provider: str, artist: str, track: str, album: str) -> str:
    """Build a provider search URL with album context to reduce ambiguity."""
    search_text = " ".join(part.strip() for part in (artist, track, album) if part and part.strip())
    if provider == "spotify":
        return f"https://open.spotify.com/search/{quote(search_text, safe='')}"
    if provider == "apple":
        return f"https://music.apple.com/search?term={quote_plus(search_text)}"
    raise ValueError(f"Unsupported provider: {provider}")


def resolve_provider_links(item: dict) -> dict[str, dict[str, str]]:
    """Resolve canonical-or-search links for one song-like item."""
    links: dict[str, dict[str, str]] = {}
    for provider, source_key in (("spotify", "spotify_url"), ("apple", "apple_url")):
        explicit = normalize_provider_url(item.get(source_key, ""), provider)
        links[provider] = {
            "url": explicit or provider_search_url(
                provider, item.get("artist", ""), item.get("track", ""), item.get("album", "")
            ),
            "kind": "canonical" if explicit else "search",
        }
    return links


def streaming_link_markup(item: dict) -> str:
    """Render stable provider links while retaining a truthful fallback label."""
    links = resolve_provider_links(item)
    artist = html.escape(str(item.get("artist", "")), quote=True)
    track = html.escape(str(item.get("track", "")), quote=True)

    def link_markup(provider: str, label: str) -> str:
        link = links[provider]
        action = "Open" if link["kind"] == "canonical" else "Search"
        accessible_label = f"{action} {label} for {track} by {artist}"
        return (
            f'<a class="stream-link" data-link-kind="{link["kind"]}" '
            f'aria-label="{html.escape(accessible_label, quote=True)}" '
            f'href="{html.escape(link["url"], quote=True)}" target="_blank" '
            f'rel="noopener noreferrer">{label}</a>'
        )

    return f"""
                <div class="stream-block">
                    <div class= "stream-label">Have a listen on:</div>
                    <div class= "stream-links">
                        {link_markup("spotify", "Spotify")}
                        {link_markup("apple", "Apple Music")}
                    </div>
                </div>
"""


def _safe_cover_path(covers_dir: Path, cover_file: str) -> Path | None:
    """Resolve a cover path only when it stays inside the source cover directory."""
    normalized = (cover_file or "").replace("\\", "/").strip()
    if not normalized:
        return None
    candidate = (covers_dir / normalized).resolve()
    try:
        candidate.relative_to(covers_dir.resolve())
    except ValueError:
        return None
    return candidate


def catalogue_record(item: dict, covers_dir: Path, cover_metadata: dict) -> dict:
    """Return non-prose source metadata for the generated catalogue manifest."""
    cover_file = (item.get("cover_file") or "").replace("\\", "/")
    cover_path = _safe_cover_path(covers_dir, cover_file)
    metadata = cover_metadata if cover_path else {
        "exists": False,
        "valid": False,
        "width": None,
        "height": None,
        "bytes": None,
    }
    record = {
        "slug": item.get("slug", ""),
        "artist": item.get("artist", ""),
        "track": item.get("track", ""),
        "album": item.get("album", ""),
        "tags": [tag.strip() for tag in str(item.get("tags", "")).split(",") if tag.strip()],
        "page_url": item.get("page_url") or f'entries/{item.get("html_file", "")}',
        "links": resolve_provider_links(item),
        "cover": {
            "path": f"covers/{cover_file}" if cover_file else "",
            **metadata,
        },
    }
    if item.get("p53_order") is not None and item.get("p53_order") != 999:
        record["p53_order"] = item["p53_order"]
    return record
