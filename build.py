"""Stable GSI build entry point.

Run this file to build the site. The real work is organized under ``builder/``;
this small facade keeps the familiar command and older test imports working.
"""

from builder.legacy_pipeline import *  # noqa: F401,F403 - compatibility surface
from builder.legacy_pipeline import main


if __name__ == "__main__":
    main()
