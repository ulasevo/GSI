"""Offline source and generated-site checks for GSI.

This module is the build's safety net. It checks editable inputs before a normal
build can change them, then checks generated routes and local assets afterward.
It never fetches remote services and never edits the site.
"""

import csv
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

from gsi_links import normalize_provider_url
from gsi_text import slugify


TRACK_COLUMNS = {
    "order",
    "tags",
    "artist",
    "track",
    "album",
    "accent",
    "cover_file",
    "cover_url",
    "spotify_url",
    "apple_url",
}
HEX_COLOR_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")


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


# The parser records only route-like attributes and IDs; it does not need to
# understand the visual markup or execute browser code.
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
        if tag.lower() == "base":
            return
        for name, value in attrs:
            if name in LOCAL_ROUTE_ATTRIBUTES and value is not None:
                self.references.append((name, value.strip(), element_id))


def _safe_source_path(root: Path, relative_path: str) -> Path | None:
    """Resolve a source asset path only when it remains inside its root."""
    normalized = (relative_path or "").replace("\\", "/").strip()
    if not normalized:
        return None
    candidate = (root / normalized).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    return candidate


def _append_slug_collision(
    errors: list[str],
    seen: dict[str, str],
    slug: str,
    identity: str,
    label: str,
) -> None:
    """Report a route collision while keeping the first identity for context."""
    previous = seen.get(slug)
    if previous is not None and previous != identity:
        errors.append(f"{label}: {slug!r} resolves both {previous!r} and {identity!r}")
    else:
        seen[slug] = identity


# Check the editable files before source synchronization or downloads begin.
def validate_source_contract(
    tracks_file: Path,
    config_file: Path,
    entries_dir: Path,
    covers_dir: Path,
    artist_assets_dir: Path,
    *,
    require_entries: bool = False,
) -> tuple[list[str], list[str]]:
    """Validate editable source data before the builder mutates anything.

    The returned tuple is ``(errors, warnings)``. Errors are structural blockers;
    warnings describe recoverable absences such as an optional cover or provider
    URL that will receive a search fallback during generation.
    """
    errors: list[str] = []
    warnings: list[str] = []

    try:
        config = json.loads(config_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return [f"config.json: unable to parse ({error})"], warnings
    if not isinstance(config, dict):
        return ["config.json: top-level value must be an object"], warnings

    try:
        with tracks_file.open("r", encoding="utf-8", newline="") as file:
            reader = csv.DictReader(file)
            fieldnames = set(reader.fieldnames or [])
            rows = list(reader)
    except (OSError, csv.Error) as error:
        return [f"tracks.csv: unable to parse ({error})"], warnings

    missing_columns = sorted(TRACK_COLUMNS - fieldnames)
    unexpected_columns = sorted(fieldnames - TRACK_COLUMNS)
    if missing_columns:
        errors.append(f"tracks.csv: missing columns {', '.join(missing_columns)}")
    if unexpected_columns:
        warnings.append(f"tracks.csv: unrecognized columns {', '.join(unexpected_columns)}")
    if None in fieldnames:
        errors.append("tracks.csv: one or more rows contain extra unnamed columns")

    filters = config.get("filters")
    if not isinstance(filters, dict) or not filters:
        errors.append("config.json: filters must be a non-empty object")
        filters = {}
    known_tags = {str(key).strip().casefold() for key in filters}

    sections = config.get("sections")
    if not isinstance(sections, list) or not sections:
        errors.append("config.json: sections must be a non-empty list")
        sections = []
    section_names: set[str] = set()
    for index, section in enumerate(sections):
        section_name = str(section).strip()
        if not section_name:
            errors.append(f"config.json: sections[{index}] is blank")
            continue
        section_key = section_name.casefold()
        if section_key in section_names:
            errors.append(f"config.json: duplicate section {section_name!r}")
        section_names.add(section_key)

    track_by_slug: dict[str, dict] = {}
    track_route_seen: dict[str, str] = {}
    artist_slugs: dict[str, str] = {}
    album_slugs: dict[str, str] = {}
    for row_number, row in enumerate(rows, start=2):
        if None in row:
            errors.append(f"tracks.csv:{row_number}: extra unnamed values")
        artist = (row.get("artist") or "").strip()
        track = (row.get("track") or "").strip()
        album = (row.get("album") or "").strip()
        identity = f"{artist} / {track} / {album}"
        for field, value in (("artist", artist), ("track", track), ("album", album)):
            if not value:
                errors.append(f"tracks.csv:{row_number}: {field} is blank")

        tags = [tag.strip() for tag in (row.get("tags") or "").split(",") if tag.strip()]
        unknown_tags = sorted({tag for tag in tags if tag.casefold() not in known_tags})
        if unknown_tags:
            errors.append(f"tracks.csv:{row_number}: unknown tag(s) {', '.join(unknown_tags)}")

        accent = (row.get("accent") or "").strip()
        if accent and not HEX_COLOR_PATTERN.fullmatch(accent):
            errors.append(f"tracks.csv:{row_number}: accent must be a six-digit hex color")

        slug = slugify(f"{artist}-{track}")
        if not slug:
            errors.append(f"tracks.csv:{row_number}: artist/track produce an empty route slug")
        else:
            _append_slug_collision(errors, track_route_seen, slug, identity, "tracks.csv route")
            track_by_slug.setdefault(slug, row)

        cover_file = (row.get("cover_file") or "").strip()
        if cover_file:
            cover_path = _safe_source_path(covers_dir, cover_file)
            if cover_path is None:
                errors.append(f"tracks.csv:{row_number}: cover_file escapes covers/: {cover_file!r}")
            elif not cover_path.is_file():
                warnings.append(f"tracks.csv:{row_number}: cover file is not present yet: {cover_file!r}")

        for provider, field in (("spotify", "spotify_url"), ("apple", "apple_url")):
            raw_url = (row.get(field) or "").strip()
            if raw_url and not normalize_provider_url(raw_url, provider):
                warnings.append(
                    f"tracks.csv:{row_number}: invalid {provider.title()} URL; build will use a search fallback"
                )

        if require_entries and slug and not (entries_dir / f"{slug}.md").is_file():
            errors.append(f"tracks.csv:{row_number}: missing source entry {slug}.md for site-only build")

        artist_slug = slugify(artist)
        if artist_slug:
            _append_slug_collision(errors, artist_slugs, artist_slug, artist, "artist route")
        album_slug = slugify(f"{artist}-{album}")
        if album_slug:
            _append_slug_collision(errors, album_slugs, album_slug, f"{artist} / {album}", "album route")

    # P53 records use the same slug and asset rules as ordinary tracks.
    p53_history = config.get("p53_history", [])
    if not isinstance(p53_history, list):
        errors.append("config.json: p53_history must be a list")
        p53_history = []
    p53_slugs: dict[str, str] = {}
    for index, record in enumerate(p53_history):
        if not isinstance(record, dict):
            errors.append(f"config.json: p53_history[{index}] must be an object")
            continue
        artist = str(record.get("artist") or "").strip()
        track = str(record.get("track") or "").strip()
        album = str(record.get("album") or "").strip()
        slug = str(record.get("slug") or slugify(f"{artist}-{track}")).strip()
        identity = f"{artist} / {track} / {album}"
        for field, value in (("artist", artist), ("track", track), ("album", album), ("slug", slug)):
            if not value:
                errors.append(f"config.json: p53_history[{index}] {field} is blank")
        if slug:
            _append_slug_collision(errors, p53_slugs, slug, identity, "P53 route")
            track_match = track_by_slug.get(slug)
            if track_match:
                track_identity = " / ".join([
                    (track_match.get("artist") or "").strip(),
                    (track_match.get("track") or "").strip(),
                    (track_match.get("album") or "").strip(),
                ])
                if track_identity != identity:
                    errors.append(
                        f"config.json: p53_history[{index}] slug {slug!r} disagrees with tracks.csv metadata"
                    )
        cover_file = str(record.get("cover_file") or "").strip()
        if cover_file:
            cover_path = _safe_source_path(covers_dir, cover_file)
            if cover_path is None:
                errors.append(f"config.json: p53_history[{index}] cover_file escapes covers/: {cover_file!r}")
            elif not cover_path.is_file():
                warnings.append(f"config.json: p53_history[{index}] cover file is not present yet: {cover_file!r}")
        accent = str(record.get("accent") or "").strip()
        if accent and not HEX_COLOR_PATTERN.fullmatch(accent):
            errors.append(f"config.json: p53_history[{index}] accent must be a six-digit hex color")
        for provider, field in (("spotify", "spotify_url"), ("apple", "apple_url")):
            raw_url = str(record.get(field) or "").strip()
            if raw_url and not normalize_provider_url(raw_url, provider):
                warnings.append(
                    f"config.json: p53_history[{index}] invalid {provider.title()} URL; build will use a search fallback"
                )
        if artist:
            artist_slug = slugify(artist)
            if artist_slug:
                _append_slug_collision(errors, artist_slugs, artist_slug, artist, "artist route")
        if artist and album:
            album_slug = slugify(f"{artist}-{album}")
            if album_slug:
                _append_slug_collision(errors, album_slugs, album_slug, f"{artist} / {album}", "album route")

    current_slug = str(config.get("p53_current_slug") or "").strip()
    if current_slug and current_slug not in p53_slugs:
        errors.append(f"config.json: p53_current_slug {current_slug!r} is not present in p53_history")

    artist_assets = config.get("artist_assets", {})
    if artist_assets is not None and not isinstance(artist_assets, dict):
        errors.append("config.json: artist_assets must be an object when provided")
        artist_assets = {}
    for artist, settings in artist_assets.items():
        if not isinstance(settings, dict):
            errors.append(f"config.json: artist_assets[{artist!r}] must be an object")
            continue
        image_file = str(settings.get("image_file") or "").strip()
        if image_file:
            image_path = _safe_source_path(artist_assets_dir, image_file)
            if image_path is None:
                errors.append(f"config.json: artist image escapes artist-assets/: {image_file!r}")
            elif not image_path.is_file():
                warnings.append(f"config.json: artist image is not present yet: {image_file!r}")

    return errors, warnings


def _resolve_local_target(site_dir: Path, page: Path, url_path: str) -> Path:
    """Resolve a local URL path without treating query state as a filesystem name."""
    decoded_path = unquote(url_path)
    if decoded_path.startswith("/"):
        return (site_dir / decoded_path.lstrip("/")).resolve()
    return (page.parent / decoded_path).resolve()


# Validate the generated relationship inventory independently from HTML links.
def validate_generation_manifest(site_dir: Path) -> list[str]:
    """Validate the generated relationship/expected-output manifest when present."""
    site_root = site_dir.resolve()
    manifest_path = site_root / "data" / "generation.json"
    if not manifest_path.is_file():
        return []

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return [f"data/generation.json: invalid manifest ({error})"]
    if not isinstance(manifest, dict):
        return ["data/generation.json: top-level value must be an object"]

    errors: list[str] = []
    relationships = manifest.get("relationships")
    expected_pages = manifest.get("expected_pages")
    families = {
        "entries": "entries",
        "p53": "p53",
        "artists": "artists",
        "albums": "albums",
    }
    if not isinstance(relationships, dict):
        errors.append("data/generation.json: relationships must be an object")
        relationships = {}
    if not isinstance(expected_pages, dict):
        errors.append("data/generation.json: expected_pages must be an object")
        expected_pages = {}

    def safe_target(href: str, prefix: str, family_dir: str) -> Path | None:
        parsed = urlsplit(href)
        if parsed.scheme or href.startswith("//") or not parsed.path:
            errors.append(f"{prefix} has an invalid local href: {href!r}")
            return None
        relative_path = unquote(parsed.path.lstrip("/"))
        if not relative_path.startswith(f"{family_dir}/"):
            errors.append(f"{prefix} href leaves its {family_dir} route family: {href!r}")
            return None
        target = (site_root / relative_path).resolve()
        try:
            target.relative_to(site_root)
        except ValueError:
            errors.append(f"{prefix} href escapes generated site: {href!r}")
            return None
        return target

    for family, directory in families.items():
        names = expected_pages.get(family)
        if not isinstance(names, list) or not all(isinstance(name, str) for name in names):
            errors.append(f"data/generation.json: expected_pages[{family!r}] must be a list of names")
            continue
        expected = set(names)
        actual = {path.name for path in (site_root / directory).glob("*.html")}
        missing = sorted(expected - actual)
        if missing:
            errors.append(f"data/generation.json: missing expected {family} page(s): {', '.join(missing)}")
        # P53 slugs are permanent links and may intentionally outlive the source
        # record; the other families are fully managed by the builder.
        if family != "p53":
            unexpected = sorted(actual - expected)
            if unexpected:
                errors.append(f"data/generation.json: unexpected generated {family} page(s): {', '.join(unexpected)}")

        records = relationships.get(family)
        if not isinstance(records, list):
            errors.append(f"data/generation.json: relationships[{family!r}] must be a list")
            continue
        seen_hrefs: set[str] = set()
        for index, record in enumerate(records):
            prefix = f"data/generation.json: relationships[{family}][{index}]"
            if not isinstance(record, dict):
                errors.append(f"{prefix} must be an object")
                continue
            href = str(record.get("href") or "")
            if href in seen_hrefs:
                errors.append(f"{prefix} duplicates href {href!r}")
            seen_hrefs.add(href)
            target = safe_target(href, prefix, directory)
            if target is not None and not target.is_file():
                errors.append(f"{prefix} points to missing page: {href!r}")
            if family in {"entries", "p53"} and not str(record.get("slug") or "").strip():
                errors.append(f"{prefix} is missing slug")
            if family == "artists" and not str(record.get("artist") or "").strip():
                errors.append(f"{prefix} is missing artist")
            if family == "albums" and not all(str(record.get(field) or "").strip() for field in ("artist", "album")):
                errors.append(f"{prefix} is missing artist or album")
    return errors


def validate_generated_links(site_dir: Path) -> list[str]:
    """Return actionable errors for local generated-page routes and assets only.

    External streaming, canonical, and protocol links are deliberately ignored. The
    validator checks the static base routes that GSI's context script later enriches
    with query state, rather than trying to simulate browser navigation.
    """
    # Resolve every local route from the page that contains it, while ignoring
    # external providers and URLs intentionally filled by browser scripts.
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

    errors.extend(validate_generation_manifest(site_root))

    return errors
