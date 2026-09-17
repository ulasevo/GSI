"""Small, dependency-free text helpers shared by GSI page builders.

Keeping these pure formatting functions outside the build orchestrator makes
the source easier to audit without changing the generated page structure.
"""

import html
import re

from gsi_links import streaming_link_markup


def slugify(text: str) -> str:
    """Turn a display name into the stable, URL-safe slug used by GSI."""
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def simple_markdown_to_html(markdown_text: str) -> str:
    """Render the small Markdown subset used by entry prose."""
    text = html.escape(markdown_text.strip())
    text = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", text)
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    return "\n".join(
        [f"<p>{p.replace(chr(10), '<br>')}</p>" for p in paragraphs]
    )


def make_streaming_links(item: dict) -> str:
    """Return the Spotify/Apple Music links for one generated item."""
    return streaming_link_markup(item)
