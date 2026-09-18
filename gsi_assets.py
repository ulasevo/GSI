"""Artwork color extraction and copying for the generated GSI site."""

import colorsys
import shutil
from pathlib import Path

from PIL import Image


# Homepage CSS is authored in readable layers but shipped as one stylesheet so
# the browser keeps one stable public asset and the cascade order stays clear.
HOME_STYLE_PARTS = (
    "01-foundation.css",
    "02-hero-and-filter-room.css",
    "03-filter-and-controls.css",
    "04-cards-and-responsive.css",
)


# Artwork supplies accents, but a damaged or flat image must never stop a build.
def dominant_color(image_path: Path) -> str:
    """Extract a vivid accent color from an image, with a safe fallback."""
    try:
        image = Image.open(image_path).convert("RGB")
    except (OSError, ValueError) as error:
        print(f" Could not read image: {image_path}")
        print(f" Reason: {error}")
        return "#888888"
    image = image.resize((120, 120))

    reduced = image.quantize(colors=14).convert("RGB")
    colors = reduced.getcolors(120 * 120)
    if colors is None:
        return "#888888"
    best_color = None
    best_score = -1
    for count, (r, g, b) in colors:
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        if v < 0.18:
            continue
        if v > 0.94 and s < 0.25:
            continue
        if s < 0.18:
            continue
        score = (s * 2.4 + v * 0.8) * (count ** 0.45)
        if score > best_score:
            best_score = score
            best_color = (r, g, b)
    if best_color is None:
        colors.sort(reverse=True)
        best_color = colors[0][1]
    r, g, b = best_color
    return f"#{r:02x}{g:02x}{b:02x}"


def local_image_metadata(image_path: Path) -> dict:
    """Describe a local raster asset without changing it or making network calls."""
    metadata = {
        "exists": image_path.is_file(),
        "valid": False,
        "width": None,
        "height": None,
        "bytes": image_path.stat().st_size if image_path.is_file() else None,
    }
    if not metadata["exists"]:
        return metadata
    try:
        with Image.open(image_path) as image:
            image.verify()
        with Image.open(image_path) as image:
            metadata["width"], metadata["height"] = image.size
        metadata["valid"] = True
    except (OSError, ValueError):
        return metadata
    return metadata


# Generated output receives fresh copies so removed or renamed source assets do
# not linger in the published tree.
def copy_site_covers(covers_dir: Path, site_covers_dir: Path) -> None:
    """Refresh generated artwork from the editable cover directory."""
    if site_covers_dir.exists():
        shutil.rmtree(site_covers_dir)
    shutil.copytree(covers_dir, site_covers_dir)
    print(f" Copied covers into generated site: {site_covers_dir}")


def copy_site_scripts(web_dir: Path, site_scripts_dir: Path) -> None:
    """Copy source browser helpers into the generated GSI site."""
    site_scripts_dir.mkdir(parents=True, exist_ok=True)
    scripts_dir = web_dir / "scripts"
    for source in scripts_dir.glob("*.js"):
        shutil.copy2(source, site_scripts_dir / source.name)


def copy_site_styles(web_dir: Path, site_styles_dir: Path) -> None:
    """Copy stylesheets and assemble the layered homepage stylesheet."""
    site_styles_dir.mkdir(parents=True, exist_ok=True)
    styles_dir = web_dir / "styles"
    for source in styles_dir.glob("*.css"):
        shutil.copy2(source, site_styles_dir / source.name)
    home_parts_dir = styles_dir / "home"
    if home_parts_dir.is_dir():
        parts = []
        for part_name in HOME_STYLE_PARTS:
            part_path = home_parts_dir / part_name
            if not part_path.is_file():
                raise FileNotFoundError(f"Missing homepage style part: {part_path}")
            parts.append(part_path.read_text(encoding="utf-8").rstrip())
        (site_styles_dir / "gsi-home.css").write_text(
            "/* Generated from web/styles/home/*.css in HOME_STYLE_PARTS order. */\n"
            + "\n\n".join(parts)
            + "\n",
            encoding="utf-8",
        )


# Playlist art is a visual hint only; a missing optional cover falls back to the
# filter color and does not make that filter unusable.
def playlist_visuals(
    playlist_cover: str, fallback_color: str, base_dir: Path
) -> tuple[str, str]:
    """Return the browser path and accent color for an optional playlist cover."""
    playlist_cover = (playlist_cover or "").strip()
    if not playlist_cover:
        return "", fallback_color
    cover_path = base_dir / playlist_cover
    if not cover_path.exists():
        print(f" Playlist cover not found: {playlist_cover}")
        return "", fallback_color
    browser_src = playlist_cover.replace("\\", "/")
    return browser_src, dominant_color(cover_path)
