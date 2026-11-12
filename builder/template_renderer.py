"""Small dependency-free renderer for the checked-in GSI page templates.

Templates use explicit ``@@TOKEN@@`` markers. Values are prepared and escaped
by the page renderer before they reach this module; the renderer only performs
deterministic marker replacement and rejects a template with an unresolved
marker so a malformed page cannot silently ship.
"""

import hashlib
import re
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from gsi_assets import HOME_STYLE_PARTS


BASE = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = BASE / "templates"
WEB_DIR = BASE / "web"
# Markers are intentionally boring and explicit. A missing value is an error,
# because silently shipping @@TOKEN@@ would make a broken page hard to notice.
_MARKER_RE = re.compile(r"@@[A-Z0-9_]+@@")
_LOCAL_ASSET_ATTR_RE = re.compile(
    r"""(?P<prefix>\b(?:href|src)\s*=\s*)(?P<quote>["'])(?P<url>(?:\.\./)*(?:styles/[^"'?#]+\.css|scripts/[^"'?#]+\.js)(?:\?[^"'#]*)?(?:#[^"']*)?)(?P=quote)"""
)


def _asset_payload(asset_rel_path: str, web_root: Path) -> bytes | None:
    """Return exact source bytes for a local ``styles/*.css`` or ``scripts/*.js`` asset."""
    normalized = asset_rel_path.strip()
    if not normalized or "\\" in normalized or normalized.startswith("/"):
        return None
    parts = Path(normalized).parts
    if not parts or parts[0] not in {"styles", "scripts"} or ".." in parts:
        return None
    resolved_root = web_root.resolve()
    candidate = (resolved_root / normalized).resolve()
    try:
        candidate.relative_to(resolved_root)
    except ValueError:
        return None
    if candidate.is_file():
        return candidate.read_bytes()
    if normalized == "styles/gsi-home.css":
        home_dir = resolved_root / "styles" / "home"
        if home_dir.is_dir():
            home_parts = []
            for part_name in HOME_STYLE_PARTS:
                part_path = home_dir / part_name
                if not part_path.is_file():
                    return None
                home_parts.append(part_path.read_text(encoding="utf-8").rstrip())
            assembled = (
                "/* Generated from web/styles/home/*.css in HOME_STYLE_PARTS order. */\n"
                + "\n\n".join(home_parts)
                + "\n"
            )
            return assembled.encode("utf-8")
    return None


def asset_version(
    asset_rel_path: str,
    *,
    web_dir: Path | None = None,
) -> str | None:
    """Return a short deterministic SHA-256 digest for a local asset under ``web/``."""
    web_root = Path(web_dir) if web_dir is not None else WEB_DIR
    payload = _asset_payload(asset_rel_path, web_root)
    if payload is None:
        return None
    return hashlib.sha256(payload).hexdigest()[:10]


def versioned_asset_url(
    url: str,
    *,
    web_dir: Path | None = None,
    versions: dict[str, str | None] | None = None,
) -> str:
    """Attach or replace ``?v=<hash>`` for local ``styles/*.css`` and ``scripts/*.js`` URLs."""
    split = urlsplit(url)
    if split.scheme or split.netloc or split.path.startswith("/"):
        return url
    normalized = split.path
    while normalized.startswith("../"):
        normalized = normalized[3:]
    if not (
        (normalized.startswith("styles/") and normalized.endswith(".css"))
        or (normalized.startswith("scripts/") and normalized.endswith(".js"))
    ):
        return url
    if versions is not None and normalized in versions:
        digest = versions[normalized]
    else:
        digest = asset_version(normalized, web_dir=web_dir)
        if versions is not None:
            versions[normalized] = digest
    if not digest:
        return url
    filtered_query = [
        (key, value)
        for key, value in parse_qsl(split.query, keep_blank_values=True)
        if key != "v"
    ]
    filtered_query.append(("v", digest))
    return urlunsplit((split.scheme, split.netloc, split.path, urlencode(filtered_query), split.fragment))


def bust_template_asset_urls(
    template_text: str,
    *,
    web_dir: Path | None = None,
) -> str:
    """Rewrite local stylesheet/script URLs in template markup using content hashes."""
    versions: dict[str, str | None] = {}

    def _replace(match: re.Match[str]) -> str:
        updated = versioned_asset_url(match.group("url"), web_dir=web_dir, versions=versions)
        return f'{match.group("prefix")}{match.group("quote")}{updated}{match.group("quote")}'

    return _LOCAL_ASSET_ATTR_RE.sub(_replace, template_text)


def render_template(
    template_name: str,
    values: dict[str, object],
    *,
    template_dir: Path | None = None,
    web_dir: Path | None = None,
) -> str:
    """Render one source template with already-prepared values.

    ``template_dir`` and ``web_dir`` exist for isolated renderer tests; production
    callers use the repository's ``templates/`` and ``web/`` directories by default.
    """
    root = Path(template_dir) if template_dir is not None else TEMPLATE_DIR
    template_path = root / template_name
    # Read a checked-in template, version its local CSS/JS references from web/,
    # replace only named values, then verify that no marker escaped into the generated page.
    template = bust_template_asset_urls(
        template_path.read_text(encoding="utf-8"),
        web_dir=web_dir,
    )
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace(f"@@{key.upper()}@@", str(value))
    unresolved = sorted(set(_MARKER_RE.findall(rendered)))
    if unresolved:
        raise ValueError(
            f"Unresolved template markers in {template_path}: {', '.join(unresolved)}"
        )
    return rendered
