"""Restore a named local GSI source snapshot after an explicit confirmation."""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.source_snapshots import restore_snapshot


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot_id", help="Snapshot ID shown in a publish receipt")
    parser.add_argument("--confirm", action="store_true", help="Actually restore the source files")
    args = parser.parse_args()
    if not args.confirm:
        print("Refusing to restore without --confirm.")
        return 2
    try:
        result = restore_snapshot(ROOT, args.snapshot_id)
    except (OSError, ValueError) as error:
        print(f"Snapshot restore failed: {error}")
        return 2
    print(f"Restored {result['files']} source files from {result['id']}.")
    print("Regenerate the local site with: python build.py --site-only --validate-links")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
