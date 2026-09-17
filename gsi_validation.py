"""Small, offline checks for the generated GSI site."""

from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit

from gsi_links import normalize_provider_url


LOCAL_ROUTE_ATTRIBUTES = {
    "href",
    "src",
    "data-base-href",
    "data-entry-base-href",
    "data-artist-base-href",
    "data-context-base-href",
}

# These links receive a destination from page JavaScript after a visitor arrives.
INTENTIONAL_PLACEHOLDERS = {
    ("404.html", "signal-spotify"),
    ("404.html", "signal-apple"),
    ("404.html", "signal-read"),
    ("index.html", "playlist-card"),
}


class _LocalRouteCollector(HTMLParser):
    """Collect local-looking URL attributes and page fragment IDs."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.references: list[tuple[str, str, str | None]] = []
        self.ids: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        element_id = attributes.get("id")
        if element_id:
            self.ids.add(element_id)
        for name, value in attrs:
            if name in LOCAL_ROUTE_ATTRIBUTES and value is not None:
                self.references.append((name, value.strip(), element_id))


def _resolve_local_target(site_dir: Path, page: Path, url_path: str) -> Path:
    """Resolve a local URL path without treating query state as a filesystem name."""
    decoded_path = unquote(url_path)
    if decoded_path.startswith("/"):
        return (site_dir / decoded_path.lstrip("/")).resolve()
    return (page.parent / decoded_path).resolve()


def validate_generated_links(site_dir: Path) -> list[str]:
    """Return actionable errors for local generated-page routes and assets only.

    External streaming, canonical, and protocol links are deliberately ignored. The
    validator checks the static base routes that GSI's context script later enriches
    with query state, rather than trying to simulate browser navigation.
    """
    site_root = site_dir.resolve()
    pages = sorted(site_root.rglob("*.html"))
    page_data: dict[Path, _LocalRouteCollector] = {}

    for page in pages:
        collector = _LocalRouteCollector()
        collector.feed(page.read_text(encoding="utf-8"))
        page_data[page.resolve()] = collector

    errors: list[str] = []
    for page, collector in page_data.items():
        page_name = page.relative_to(site_root).as_posix()
        for attribute, value, element_id in collector.references:
            if not value:
                errors.append(f"{page_name}: empty {attribute} attribute")
                continue
            parsed = urlsplit(value)
            if parsed.scheme or value.startswith("//"):
                continue
            if not parsed.path and not parsed.fragment:
                if attribute == "href" and (page_name, element_id) in INTENTIONAL_PLACEHOLDERS:
                    continue
                errors.append(f"{page_name}: unresolved {attribute}={value!r}")
                continue

            # A fragment-only route stays on the current document; resolving an
            # empty path as a directory would incorrectly point at index.html.
            target = page if not parsed.path else _resolve_local_target(site_root, page, parsed.path)
            try:
                target.relative_to(site_root)
            except ValueError:
                errors.append(f"{page_name}: {attribute} escapes generated site: {value!r}")
                continue

            if target.is_dir():
                target = target / "index.html"
            if not target.is_file():
                errors.append(
                    f"{page_name}: missing target for {attribute}={value!r} "
                    f"({target.relative_to(site_root).as_posix()})"
                )
                continue

            if parsed.fragment and target.suffix == ".html":
                target_ids = page_data.get(target, _LocalRouteCollector()).ids
                if parsed.fragment not in target_ids:
                    errors.append(
                        f"{page_name}: missing #{parsed.fragment} in "
                        f"{target.relative_to(site_root).as_posix()}"
                    )

    manifest_path = site_root / "data" / "catalog.json"
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            errors.append(f"data/catalog.json: invalid manifest ({error})")
        else:
            signals = manifest.get("signals") if isinstance(manifest, dict) else None
            if not isinstance(signals, list):
                errors.append("data/catalog.json: signals must be a list")
            else:
                for index, signal in enumerate(signals):
                    prefix = f"data/catalog.json: signals[{index}]"
                    if not isinstance(signal, dict):
                        errors.append(f"{prefix} must be an object")
                        continue
                    for provider in ("spotify", "apple"):
                        link = (signal.get("links") or {}).get(provider)
                        if not isinstance(link, dict) or not link.get("url"):
                            errors.append(f"{prefix} missing {provider} link")
                            continue
                        if normalize_provider_url(link["url"], provider) == "":
                            errors.append(f"{prefix} has invalid {provider} URL")
                    cover = signal.get("cover") or {}
                    cover_path = str(cover.get("path") or "")
                    if cover.get("exists") and not cover_path:
                        errors.append(f"{prefix} marks a cover as present without a path")
                    if cover_path:
                        target = (site_root / cover_path).resolve()
                        try:
                            target.relative_to(site_root)
                        except ValueError:
                            errors.append(f"{prefix} cover escapes generated site")
                        else:
                            if cover.get("exists") and not target.is_file():
                                errors.append(f"{prefix} cover is missing from generated site")

    artist_manifest_path = site_root / "data" / "artists.json"
    if artist_manifest_path.is_file():
        try:
            artist_manifest = json.loads(artist_manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            errors.append(f"data/artists.json: invalid manifest ({error})")
        else:
            artists = artist_manifest.get("artists") if isinstance(artist_manifest, dict) else None
            if not isinstance(artists, list):
                errors.append("data/artists.json: artists must be a list")
            else:
                for index, artist in enumerate(artists):
                    prefix = f"data/artists.json: artists[{index}]"
                    if not isinstance(artist, dict):
                        errors.append(f"{prefix} must be an object")
                        continue
                    page_url = str(artist.get("page_url") or "")
                    if page_url:
                        target = (site_root / page_url).resolve()
                        try:
                            target.relative_to(site_root)
                        except ValueError:
                            errors.append(f"{prefix} page escapes generated site")
                        else:
                            if not target.is_file():
                                errors.append(f"{prefix} page is missing: {page_url!r}")
                    image = artist.get("image") or {}
                    image_file = str(image.get("file") or "")
                    if image_file:
                        target = (site_root / "artist-assets" / image_file).resolve()
                        try:
                            target.relative_to(site_root / "artist-assets")
                        except ValueError:
                            errors.append(f"{prefix} image escapes artist-assets")
                        else:
                            if not target.is_file():
                                errors.append(f"{prefix} image is missing: {image_file!r}")

    return errors
