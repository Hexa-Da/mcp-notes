"""Path sandbox: only *.md under NOTES_ROOT (or allowlisted roots)."""

from __future__ import annotations

import os
from pathlib import Path


class SandboxError(ValueError):
    """Raised when a path escapes the allowlist or violates policy."""


def get_roots() -> list[Path]:
    """Resolve allowlisted roots from NOTES_ROOT (colon-separated on Unix)."""
    raw = os.environ.get("NOTES_ROOT", "").strip()
    if not raw:
        raise SandboxError(
            "NOTES_ROOT is not set. Export it to your notes directory, e.g. "
            "export NOTES_ROOT=/Users/you/Documents/notes"
        )
    roots: list[Path] = []
    for part in raw.split(os.pathsep):
        part = part.strip()
        if not part:
            continue
        root = Path(part).expanduser().resolve()
        if not root.is_dir():
            raise SandboxError(f"NOTES_ROOT is not a directory: {root}")
        roots.append(root)
    if not roots:
        raise SandboxError("NOTES_ROOT is empty after parsing")
    return roots


def _is_under(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def resolve_note_path(relative: str, *, must_exist: bool = False) -> Path:
    """
    Map a relative note path to an absolute path inside an allowlisted root.

    Rejects absolute paths, ``..`` traversal, non-``.md`` targets, and
    anything that resolves outside the allowlist (including via symlinks).
    """
    if not relative or not relative.strip():
        raise SandboxError("path must be a non-empty relative path")

    rel = Path(relative.strip())
    if rel.is_absolute():
        raise SandboxError("path must be relative to NOTES_ROOT, not absolute")
    if ".." in rel.parts:
        raise SandboxError("path must not contain '..'")
    if rel.suffix.lower() != ".md":
        raise SandboxError("only .md files are allowed")

    roots = get_roots()
    # Prefer the first root that already contains the file; else first root for create.
    candidates = [root / rel for root in roots]
    chosen: Path | None = None
    for candidate in candidates:
        if candidate.exists():
            chosen = candidate
            break
    if chosen is None:
        chosen = candidates[0]

    # Resolve parents for create; resolve fully when existing (follows symlinks).
    if chosen.exists() or chosen.is_symlink():
        resolved = chosen.resolve()
    else:
        parent = chosen.parent
        if parent.exists() or parent.is_symlink():
            resolved = parent.resolve() / chosen.name
        else:
            # Ensure we never create outside root: resolve root + relative under it.
            resolved = (roots[0] / rel).resolve()

    if not any(_is_under(resolved, root) or resolved == root for root in roots):
        raise SandboxError(f"path escapes allowlist: {relative!r}")

    if must_exist and not resolved.is_file():
        raise SandboxError(f"note not found: {relative}")

    return resolved


def iter_markdown_files() -> list[tuple[Path, str]]:
    """Return (absolute_path, relative_posix) for every .md under the roots."""
    roots = get_roots()
    out: list[tuple[Path, str]] = []
    seen: set[Path] = set()
    for root in roots:
        for path in sorted(root.rglob("*.md")):
            if not path.is_file():
                continue
            resolved = path.resolve()
            if not _is_under(resolved, root):
                continue  # symlink escaped
            if resolved in seen:
                continue
            seen.add(resolved)
            rel = resolved.relative_to(root).as_posix()
            out.append((resolved, rel))
    return out
