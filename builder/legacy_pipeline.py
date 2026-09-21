"""Compatibility orchestration for the GSI build.

The page and source work now lives in named modules. This file intentionally
keeps only the build order, shared output paths, and old import names so the
existing command and tests continue to work while the migration settles.
"""

import argparse # command-line options such as the source-safe site build
from pathlib import Path # cross OS handling
from gsi_assets import copy_site_covers, copy_site_editor, copy_site_scripts, copy_site_styles
from gsi_artists import artist_catalogue_records, copy_site_artist_assets, write_artist_manifest
from gsi_data import artist_room_groups, build_generation_inventory, load_config, ordered_tracks, read_tracks
from gsi_links import print_provider_link_audit, provider_link_audit
from gsi_text import slugify
from gsi_validation import validate_generated_links, validate_source_contract

BASE = Path(__file__).resolve().parent.parent # repository root; this module lives under builder/
# These paths are the only places the orchestration writes during a build.
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
SITE_EDITOR_DIR = SITE_DIR / "tools"

TRACKS_FILE = BASE / "tracks.csv" #list of song inputs
CONFIG_FILE = BASE / "config.json" #settings file

# Create expected folders once when the command is imported or run.
ENTRIES_DIR.mkdir(exist_ok = True) #creates entry folder, but not on repeat
COVERS_DIR.mkdir(exist_ok = True)
SITE_DIR.mkdir(exist_ok = True)
SITE_ENTRIES_DIR.mkdir(exist_ok = True) #creates entries
SITE_P53_DIR.mkdir(exist_ok = True)
SITE_ARTISTS_DIR.mkdir(exist_ok = True)
ARTIST_ASSETS_DIR.mkdir(exist_ok = True)
SITE_ALBUMS_DIR.mkdir(exist_ok = True)
SITE_DATA_DIR.mkdir(exist_ok = True)

def main() -> None:
    """Run the build in a fixed order: check, prepare, render, then validate."""
    # Command-line flags decide whether source files may be updated or only read.
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
    parser.add_argument(
        "--audit-provider-links",
        action = "store_true",
        help = "Report canonical provider URLs and search fallbacks without generating the site.",
    )
    args = parser.parse_args()
    # Validate before any normal build can touch entries or download artwork.
    source_errors, source_warnings = validate_source_contract(
        TRACKS_FILE,
        CONFIG_FILE,
        ENTRIES_DIR,
        COVERS_DIR,
        ARTIST_ASSETS_DIR,
        require_entries=args.site_only,
    )
    if source_warnings:
        print("\nSource preflight warnings:")
        for warning in source_warnings:
            print(f" - {warning}")
    if source_errors:
        print("\nSource preflight failed:")
        for error in source_errors:
            print(f" - {error}")
        raise SystemExit(2)
    print("Source preflight passed.")
    if args.audit_provider_links:
        config = load_config(CONFIG_FILE)
        audit_items = read_tracks(TRACKS_FILE)
        audit_items.extend(config.get("p53_history", []))
        print_provider_link_audit(provider_link_audit(audit_items))
        return
    # Prepared records are shared by every page family so counts and links agree.
    tracks = build_entries(write_sources = not args.site_only)
    config = load_config(CONFIG_FILE)
    p53_history = prepare_p53_history(config, tracks, download_missing = not args.site_only)
    archive_tracks = merge_p53_into_archive(tracks, p53_history)
    artist_groups = artist_room_groups(tracks, p53_history)
    p53_slug = (config.get("p53_current_slug") or "").strip()
    inventory = build_generation_inventory(
        tracks,
        p53_history,
        archive_tracks,
        artist_groups,
        p53_slug,
    )
    artist_counts = {
        artist: len(items)
        for artist, items in artist_groups.items()
    }
    # Assets and manifests are copied before pages so every generated reference
    # points at a deterministic file in the output tree.
    copy_site_covers(COVERS_DIR, SITE_COVERS_DIR)
    copy_site_artist_assets(ARTIST_ASSETS_DIR, SITE_ARTIST_ASSETS_DIR)
    copy_site_scripts(WEB_DIR, SITE_SCRIPTS_DIR)
    copy_site_styles(WEB_DIR, SITE_STYLES_DIR)
    copy_site_editor(
        BASE / "tools" / "editor",
        SITE_EDITOR_DIR,
        config.get("sections", []),
        config.get("section_info", {}),
    )
    write_catalog_manifest(archive_tracks)
    write_generation_manifest(inventory)
    write_artist_manifest(
        artist_catalogue_records(artist_groups, config, ARTIST_ASSETS_DIR),
        SITE_DATA_DIR / "artists.json",
    )
    reconcile_generated_outputs(inventory)
    album_pages = {
        key: f'../{route}'
        for key, route in inventory["album_routes"].items()
    }
    # Render each page family from the same inventory, then remove only managed
    # stale outputs through reconcile_generated_outputs().
    for item in tracks:
        build_entry_page(item, artist_counts, album_pages)
    for item in p53_history:
        build_p53_page(item, f'{item["slug"]}.html', set(inventory["entry_routes"]), {slugify(artist) for artist in artist_groups})
    p53_item = next((item for item in p53_history if item["slug"] == p53_slug), None)
    if p53_item:
        build_p53_page(p53_item, "latest.html", set(inventory["entry_routes"]), {slugify(artist) for artist in artist_groups})
    if p53_history:
        build_p53_archive(
            p53_history,
            p53_slug,
            {key: settings.get("label", key) for key, settings in config.get("filters", {}).items()},
            {slugify(artist) for artist in artist_groups},
        )
    build_artist_pages(artist_groups, config)
    build_album_pages(archive_tracks, artist_groups, inventory["album_routes"])
    build_index_html(archive_tracks, inventory["album_routes"])
    build_404_page(archive_tracks)
    build_recommend_page()
    if args.validate_links:
        link_errors = validate_generated_links(SITE_DIR)
        if link_errors:
            print("\nGenerated link validation failed:")
            for error in link_errors:
                print(f" - {error}")
            raise SystemExit(1)
        print("\nValidated generated local links and assets.")
    print("\nDone.")

# Source preparation now lives behind explicit path-aware functions. Keep these
# names as compatibility exports so existing callers and the orchestration below
# do not need to know about the migration boundary.
from builder.source_pipeline import (
    append_missing_sections as _source_append_missing_sections,
    build_entries as _source_build_entries,
    make_frontmatter as _source_make_frontmatter,
    make_markdown_template as _source_make_markdown_template,
    make_section_prompt as _source_make_section_prompt,
    merge_p53_into_archive as _source_merge_p53_into_archive,
    prepare_p53_history as _source_prepare_p53_history,
    search_itunes_cover as _source_search_itunes_cover,
    sync_entry_metadata as _source_sync_entry_metadata,
)
from builder.p53_pages import build_p53_archive as _p53_build_archive, build_p53_page as _p53_build_page
from builder.catalog_pages import build_album_pages as _catalog_build_album_pages, build_artist_pages as _catalog_build_artist_pages
from builder.entry_pages import (
    build_entry_page as _build_entry_page,
    extract_sections_from_markdown as _extract_sections_from_markdown,
)
from builder.home_page import build_index_html as _build_index_html
from builder.error_pages import build_404_page as _build_404_page
from builder.recommend_page import build_recommend_page as _build_recommend_page
from builder.manifests import (
    reconcile_generated_outputs as _reconcile_generated_outputs,
    reconcile_generated_pages as _reconcile_generated_pages,
    write_catalog_manifest as _write_catalog_manifest,
    write_generation_manifest as _write_generation_manifest,
)
append_missing_sections = _source_append_missing_sections
build_entries = _source_build_entries
make_frontmatter = _source_make_frontmatter
make_markdown_template = _source_make_markdown_template
make_section_prompt = _source_make_section_prompt
merge_p53_into_archive = _source_merge_p53_into_archive
prepare_p53_history = _source_prepare_p53_history
search_itunes_cover = _source_search_itunes_cover
sync_entry_metadata = _source_sync_entry_metadata
build_p53_archive = _p53_build_archive
build_p53_page = _p53_build_page
build_artist_pages = _catalog_build_artist_pages
build_album_pages = _catalog_build_album_pages
build_entry_page = _build_entry_page
extract_sections_from_markdown = _extract_sections_from_markdown
build_index_html = _build_index_html
build_404_page = _build_404_page
build_recommend_page = _build_recommend_page
write_catalog_manifest = _write_catalog_manifest
write_generation_manifest = _write_generation_manifest
reconcile_generated_outputs = _reconcile_generated_outputs
reconcile_generated_pages = _reconcile_generated_pages


if __name__ == "__main__":
    main()


