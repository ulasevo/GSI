"""Generated error-page renderer for the GSI static site.

The 404 page intentionally keeps its playful signal-recovery composition, but
its renderer now has the same explicit config/output boundary as the other
page builders.  That makes it testable without touching the real ``site/``
directory during isolated checks.
"""

import html
import json
from pathlib import Path

from gsi_data import load_config
from gsi_links import resolve_provider_links
from builder.template_renderer import render_template


def build_404_page(
    tracks: list[dict],
    *,
    config_file: Path | None = None,
    output_path: Path | None = None,
) -> None:
    """Build the generated 404 page from prepared catalogue records."""
    base = Path(__file__).resolve().parents[1]
    config_file = config_file or base / "config.json"
    output_path = output_path or base / "site" / "404.html"
    config = load_config(config_file)
    copy = config.get("not_found", {})
    site_url = (config.get("site_url") or "").rstrip("/")
    site_path = (
        "/" + site_url.split("/", 3)[-1].split("/", 1)[-1].strip("/") + "/"
        if ".github.io/" in site_url
        else "/"
    )

    def recommendation_record(item: dict) -> dict:
        links = resolve_provider_links(item)
        return {
            "track": item["track"],
            "artist": item["artist"],
            "album": item["album"],
            "cover": item.get("cover_file", ""),
            "url": item.get("page_url") or f'entries/{item["html_file"]}',
            "accent": item["accent"],
            "spotify": links["spotify"]["url"],
            "apple": links["apple"]["url"],
        }

    recommendations = [recommendation_record(item) for item in tracks]
    not_found_title = html.escape(copy.get("title", "THIS FREQUENCY DOES NOT EXIST."))
    not_found_title = not_found_title.replace(" NOT ", ' <em>NOT</em> ')
    protein_drops = "".join(
        f'<span style="--x:{(index * 17) % 101}%;--delay:-{index * .73:.2f}s;--speed:{9 + index % 7}s;--size:{34 + index % 5 * 13}px"></span>'
        for index in range(18)
    )
    page = render_template(
        "404.html",
        {
            "error_page_data": json.dumps(
                {"tracks": recommendations, "deployedRoot": site_path},
                ensure_ascii=False,
            ).replace("</", "<\\/"),
            "site_path": html.escape(site_path, quote=True),
            "not_found_title": not_found_title,
            "protein_drops": protein_drops,
            "eyebrow": html.escape(copy.get("eyebrow", "SIGNAL LOST / 404")),
            "message": html.escape(copy.get("message", "The page slipped out of GSI.")),
            "recommendation_label": html.escape(copy.get("recommendation_label", "INTERCEPTED SIGNAL")),
        },
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(page, encoding="utf-8")
    print(f"Built playful 404 page: {output_path}")
