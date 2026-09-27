"""Persistent, local-only snapshots for transactional GSI authoring publishes."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path


SNAPSHOT_SCHEMA = 1
SNAPSHOT_ID_PATTERN = re.compile(r"^[0-9]{8}T[0-9]{6}Z-[a-z0-9-]+$")


def _relative_path(root: Path, path: Path) -> str:
    """Return a normalized path only when it stays inside the source root."""
    resolved_root = root.resolve()
    resolved_path = path.resolve()
    resolved_path.relative_to(resolved_root)
    return resolved_path.relative_to(resolved_root).as_posix()


def _snapshot_root(root: Path) -> Path:
    return root / "submissions" / "snapshots"


def create_snapshot(root: Path, paths: list[Path], label: str) -> dict:
    """Copy the source boundary and write a manifest before a publish mutates it."""
    now = datetime.now(timezone.utc)
    clean_label = re.sub(r"[^a-z0-9-]+", "-", label.casefold()).strip("-") or "publish"
    snapshot_id = f"{now.strftime('%Y%m%dT%H%M%SZ')}-{clean_label}"
    destination = _snapshot_root(root) / snapshot_id
    destination.mkdir(parents=True, exist_ok=False)
    files = []
    try:
        for path in paths:
            relative = _relative_path(root, path)
            source = Path(path)
            existed = source.is_file()
            item = {"path": relative, "existed": existed}
            if existed:
                backup = destination / relative
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, backup)
                contents = source.read_bytes()
                item.update({"bytes": len(contents), "sha256": hashlib.sha256(contents).hexdigest()})
            files.append(item)
        manifest = {
            "schema": SNAPSHOT_SCHEMA,
            "id": snapshot_id,
            "created_at": now.isoformat(),
            "label": clean_label,
            "files": files,
        }
        (destination / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except Exception:
        shutil.rmtree(destination, ignore_errors=True)
        raise
    return {"id": snapshot_id, "path": f"submissions/snapshots/{snapshot_id}", "files": len(files)}


def restore_snapshot(root: Path, snapshot_id: str) -> dict:
    """Restore one explicitly named snapshot and return its manifest summary."""
    if not SNAPSHOT_ID_PATTERN.fullmatch(snapshot_id):
        raise ValueError("invalid snapshot ID")
    destination = _snapshot_root(root) / snapshot_id
    manifest_path = destination / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"snapshot not found: {snapshot_id}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != SNAPSHOT_SCHEMA:
        raise ValueError("unsupported snapshot schema")
    for item in manifest.get("files", []):
        relative = str(item.get("path") or "")
        target = (root / relative).resolve()
        target.relative_to(root.resolve())
        if item.get("existed"):
            backup = destination / relative
            if not backup.is_file():
                raise FileNotFoundError(f"snapshot member is missing: {relative}")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup, target)
        elif target.is_file():
            target.unlink()
    return {"id": snapshot_id, "files": len(manifest.get("files", [])), "label": manifest.get("label", "")}
