"""Small dependency-free renderer for the checked-in GSI page templates.

Templates use explicit ``@@TOKEN@@`` markers. Values are prepared and escaped
by the page renderer before they reach this module; the renderer only performs
deterministic marker replacement and rejects a template with an unresolved
marker so a malformed page cannot silently ship.
"""

import re
from pathlib import Path


BASE = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = BASE / "templates"
# Markers are intentionally boring and explicit. A missing value is an error,
# because silently shipping @@TOKEN@@ would make a broken page hard to notice.
_MARKER_RE = re.compile(r"@@[A-Z0-9_]+@@")


def render_template(
    template_name: str,
    values: dict[str, object],
    *,
    template_dir: Path | None = None,
) -> str:
    """Render one source template with already-prepared values.

    ``template_dir`` exists for isolated renderer tests; production callers use
    the repository's ``templates/`` directory by default.
    """
    root = Path(template_dir) if template_dir is not None else TEMPLATE_DIR
    template_path = root / template_name
    # Read a checked-in template, replace only named values, then verify that no
    # marker escaped into the generated page.
    template = template_path.read_text(encoding="utf-8")
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace(f"@@{key.upper()}@@", str(value))
    unresolved = sorted(set(_MARKER_RE.findall(rendered)))
    if unresolved:
        raise ValueError(
            f"Unresolved template markers in {template_path}: {', '.join(unresolved)}"
        )
    return rendered
