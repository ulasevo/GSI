"""Build the public, non-destructive signal recommendation surface."""

from pathlib import Path

from builder.template_renderer import render_template


def build_recommend_page(*, output_path: Path | None = None) -> None:
    """Write the recommendation room without touching catalogue sources."""
    base = Path(__file__).resolve().parents[1]
    output_path = output_path or base / "site" / "recommend.html"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_template("recommend.html", {}), encoding="utf-8")
    print(f"Built recommendation room: {output_path}")
