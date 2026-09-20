"""Artwork color extraction and copying for the generated GSI site."""

import colorsys
import json
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


def _hex(rgb: tuple[int, int, int]) -> str:
    """Return one RGB tuple as a stable lowercase CSS color."""
    return "#%02x%02x%02x" % tuple(max(0, min(255, value)) for value in rgb)


def _mix(first: tuple[int, int, int], second: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
    """Blend two RGB colors without requiring a browser-side color function."""
    return tuple(round(a + (b - a) * amount) for a, b in zip(first, second))


def _relative_luminance(rgb: tuple[int, int, int]) -> float:
    """Return perceptual brightness for contrast decisions, not decoration."""
    channels = []
    for value in rgb:
        channel = value / 255
        channels.append(channel / 12.92 if channel <= .04045 else ((channel + .055) / 1.055) ** 2.4)
    return .2126 * channels[0] + .7152 * channels[1] + .0722 * channels[2]


def _contrast_ratio(first: tuple[int, int, int], second: tuple[int, int, int]) -> float:
    """Measure the contrast between two RGB colors using the WCAG formula."""
    light = max(_relative_luminance(first), _relative_luminance(second))
    dark = min(_relative_luminance(first), _relative_luminance(second))
    return (light + .05) / (dark + .05)


def _best_ink(background: tuple[int, int, int]) -> tuple[int, int, int]:
    """Choose dark or softened light copy against the *resulting* surface."""
    dark = (31, 20, 32)
    light = (248, 245, 239)
    return dark if _contrast_ratio(background, dark) >= _contrast_ratio(background, light) else light


def _cap_brightness(rgb: tuple[int, int, int], maximum: int = 198) -> tuple[int, int, int]:
    """Keep a light artwork field luminous without letting it become a flashbang."""
    perceived = (rgb[0] * 299 + rgb[1] * 587 + rgb[2] * 114) / 1000
    if perceived <= maximum:
        return rgb
    scale = maximum / perceived
    return tuple(round(channel * scale) for channel in rgb)


def _artwork_field_color(image_path: Path, fallback: tuple[int, int, int]) -> tuple[int, int, int]:
    """Sample the lower artwork edge that should continue into the room."""
    try:
        image = Image.open(image_path).convert("RGB")
        width, height = image.size
        band = image.crop((0, round(height * .72), width, height)).resize((64, 32))
        reduced = band.quantize(colors=12).convert("RGB")
        buckets = reduced.getcolors(64 * 32) or []
        if buckets:
            buckets.sort(reverse=True)
            return buckets[0][1]
    except (OSError, ValueError):
        pass
    return fallback


def _artwork_edge_colors(image_path: Path, fallback: tuple[int, int, int]) -> dict[str, tuple[int, int, int]]:
    """Read broad edge colours for a room-wide, non-blurred artwork field."""
    try:
        image = Image.open(image_path).convert("RGB")
        width, height = image.size
        x_band = max(1, round(width * .12))
        y_band = max(1, round(height * .12))
        samples = {
            "top": image.crop((0, 0, width, y_band)),
            "right": image.crop((width - x_band, 0, width, height)),
            "bottom": image.crop((0, height - y_band, width, height)),
            "left": image.crop((0, 0, x_band, height)),
        }
        edges = {}
        for name, sample in samples.items():
            reduced = sample.resize((32, 32)).quantize(colors=8).convert("RGB")
            buckets = reduced.getcolors(32 * 32) or []
            edges[name] = max(buckets, key=lambda entry: entry[0])[1] if buckets else fallback
        return edges
    except (OSError, ValueError):
        return {name: fallback for name in ("top", "right", "bottom", "left")}


def _artwork_rim_gradient(image_path: Path, fallback: tuple[int, int, int]) -> str:
    """Build a 32-point perimeter colour field for the page room.

    Each point reads a shallow band rather than one exact edge pixel.  That
    keeps a dark figure or hot accent just inside the cover from disappearing
    when the physical edge happens to be pale, while still letting the cover
    keep its own dark and bright character.
    """
    try:
        image = Image.open(image_path).convert("RGB").resize((96, 96))

        def band_color(coordinates: list[tuple[int, int]]) -> tuple[int, int, int]:
            """Blend outer, middle, and inner samples into one rim colour."""
            weights = (.48, .32, .20)
            return tuple(
                round(sum(image.getpixel(point)[channel] * weight for point, weight in zip(coordinates, weights)))
                for channel in range(3)
            )

        points: list[tuple[int, int, tuple[int, int, int]]] = []
        for index in range(8):
            position = 8 + index * 12
            top = band_color([(position, 2), (position, 8), (position, 16)])
            right = band_color([(93, position), (87, position), (79, position)])
            bottom = band_color([(position, 93), (position, 87), (position, 79)])
            left = band_color([(2, position), (8, position), (16, position)])
            points.append((position, 3, _mix(top, fallback, .10)))
            points.append((97, position, _mix(right, fallback, .10)))
            points.append((position, 97, _mix(bottom, fallback, .10)))
            points.append((3, position, _mix(left, fallback, .10)))
        layers = [
            "radial-gradient(ellipse at %d%% %d%%, color-mix(in srgb, %s, transparent 62%%), transparent 52%%)"
            % (x, y, _hex(color))
            for x, y, color in points
        ]
        return ",".join(layers)
    except (OSError, ValueError):
        color = _hex(fallback)
        return "radial-gradient(ellipse at 50%% 50%%, color-mix(in srgb, %s, transparent 70%%), transparent 58%%)" % color


def artwork_palette(image_path: Path, fallback: str = "#444444") -> dict[str, str]:
    """Extract a small, readable art palette for shared room backgrounds.

    The palette is deliberately limited to named roles instead of exposing a
    pile of arbitrary swatches.  That keeps templates and CSS predictable:
    ``primary`` carries the artwork's identity, ``secondary`` adds contrast,
    and the surface/copy/control roles are calculated for both light and dark
    room recipes.  Copy is chosen against the resulting surface rather than
    the raw swatch so a pale field never inherits blinding white text.
    """
    fallback_rgb = (68, 68, 68)
    try:
        raw = fallback.lstrip("#")
        if len(raw) == 6:
            fallback_rgb = tuple(int(raw[index:index + 2], 16) for index in (0, 2, 4))
    except ValueError:
        pass
    colors: list[tuple[int, int, int, int]] = []
    try:
        image = Image.open(image_path).convert("RGB").resize((96, 96))
        reduced = image.quantize(colors=18).convert("RGB")
        buckets = reduced.getcolors(96 * 96) or []
        for count, (r, g, b) in buckets:
            h, saturation, value = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            if value > 0.95 and saturation < 0.2:
                continue
            score = (saturation * 2.2 + value * .7) * (count ** .42)
            colors.append((round(score * 1000), r, g, b))
    except (OSError, ValueError):
        colors = []
    colors.sort(reverse=True)
    primary = (colors[0][1:]) if colors else fallback_rgb
    secondary = next(
        (entry[1:] for entry in colors[1:] if sum(abs(a - b) for a, b in zip(primary, entry[1:])) > 80),
        _mix(primary, (255, 255, 255), .28),
    )
    # A lower-edge average alone makes bright covers lose their authored hue.
    # Keep the field tied to the primary accent so the room still reads as the
    # same artwork when the lower edge is mostly white or beige.
    field = _mix(_artwork_field_color(image_path, primary), primary, .45)
    field_soft = _mix(field, secondary, .38)
    field_ink = _best_ink(field)
    edges = _artwork_edge_colors(image_path, field)
    rim_gradient = _artwork_rim_gradient(image_path, field)
    # These surfaces are the two recipes the future mode switch will choose
    # between.  Copy is selected against the recipe, not against the raw
    # artwork swatch; this prevents pale fields from inheriting blinding white
    # text and keeps dark artwork from collapsing into flat black UI.
    light_surface = _cap_brightness(_mix(primary, (255, 255, 255), .56))
    light_surface_2 = _cap_brightness(_mix(secondary, (255, 255, 255), .56))
    dark_surface = _mix(primary, (12, 12, 16), .62)
    control = _cap_brightness(_mix(primary, (255, 255, 255), .64), 212)
    control_hover = _cap_brightness(_mix(primary, (255, 255, 255), .50), 202)
    light_ink = _best_ink(light_surface)
    dark_ink = _best_ink(dark_surface)
    control_ink = _best_ink(control)
    focus = (31, 20, 32) if _contrast_ratio(primary, (31, 20, 32)) >= 3 else (248, 245, 239)
    return {
        "primary": _hex(primary),
        "secondary": _hex(secondary),
        "field": _hex(field),
        "field_soft": _hex(field_soft),
        "field_ink": _hex(field_ink),
        "edge_top": _hex(edges["top"]),
        "edge_right": _hex(edges["right"]),
        "edge_bottom": _hex(edges["bottom"]),
        "edge_left": _hex(edges["left"]),
        "rim_gradient": rim_gradient,
        "surface": _hex(_mix(primary, (10, 10, 14), .78)),
        "soft": _hex(_mix(primary, (255, 255, 255), .38)),
        "ink": _hex(dark_ink),
        "glow": _hex(_mix(primary, secondary, .35)),
        "light_surface": _hex(light_surface),
        "light_surface_2": _hex(light_surface_2),
        "dark_surface": _hex(dark_surface),
        "light_ink": _hex(light_ink),
        "dark_ink": _hex(dark_ink),
        "control": _hex(control),
        "control_hover": _hex(control_hover),
        "control_ink": _hex(control_ink),
        "edge": _hex(_mix(primary, (255, 255, 255), .28)),
        "focus": _hex(focus),
    }


def palette_style(palette: dict | None, image_src: str = "") -> str:
    """Serialize named palette roles as safe inline custom properties."""
    palette = palette or artwork_palette(Path("__missing_artwork__.jpg"))
    values = {
        "--art-primary": palette.get("primary", "#444444"),
        "--art-secondary": palette.get("secondary", "#888888"),
        "--art-field": palette.get("field", palette.get("surface", "#17151b")),
        "--art-field-soft": palette.get("field_soft", palette.get("secondary", "#888888")),
        "--art-field-ink": palette.get("field_ink", palette.get("ink", "#f8f5ef")),
        "--art-edge-top": palette.get("edge_top", palette.get("field", "#17151b")),
        "--art-edge-right": palette.get("edge_right", palette.get("field", "#17151b")),
        "--art-edge-bottom": palette.get("edge_bottom", palette.get("field", "#17151b")),
        "--art-edge-left": palette.get("edge_left", palette.get("field", "#17151b")),
        "--art-rim-gradient": palette.get("rim_gradient", ""),
        "--art-surface": palette.get("surface", "#17151b"),
        "--art-soft": palette.get("soft", "#aaaaaa"),
        "--art-ink": palette.get("ink", "#f8f5ef"),
        "--art-glow": palette.get("glow", "#666666"),
        "--art-light-surface": palette.get("light_surface", "#ded9df"),
        "--art-light-surface-2": palette.get("light_surface_2", "#ded9df"),
        "--art-dark-surface": palette.get("dark_surface", "#17151b"),
        "--art-light-ink": palette.get("light_ink", "#1f1420"),
        "--art-dark-ink": palette.get("dark_ink", "#f8f5ef"),
        "--art-control": palette.get("control", "#c7b0c6"),
        "--art-control-hover": palette.get("control_hover", "#b897b5"),
        "--art-control-ink": palette.get("control_ink", "#1f1420"),
        "--art-edge": palette.get("edge", "#c7b0c6"),
        "--art-focus": palette.get("focus", "#f8f5ef"),
    }
    if image_src:
        values["--art-image"] = f'url("{image_src.replace(chr(34), "")}")'
    return ";".join(f"{key}:{value}" for key, value in values.items()) + ";"


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


def copy_site_editor(
    editor_dir: Path,
    site_editor_dir: Path,
    sections: list[str],
) -> None:
    """Copy the browser Entry Loader into every generated site build."""
    site_editor_dir.mkdir(parents=True, exist_ok=True)
    for filename in ("new-entry.html", "new-entry.css", "new-entry.js"):
        source = editor_dir / filename
        if not source.is_file():
            raise FileNotFoundError(f"Missing browser editor asset: {source}")
        shutil.copy2(source, site_editor_dir / filename)
    (site_editor_dir / "editor-config.json").write_text(
        json.dumps({"sections": sections}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f" Copied browser Entry Loader into generated site: {site_editor_dir}")


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
