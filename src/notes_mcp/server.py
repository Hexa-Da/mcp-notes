"""Notes MCP server — tools for list / search / read / write / append / delete / move / mkdir."""

import logging
import os
from pathlib import Path

from mcp.server import MCPServer

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("notes-mcp")

mcp = MCPServer("notes", version="0.1.0")


def _notes_root() -> Path:
    raw = os.environ.get("NOTES_ROOT", "").strip()
    if not raw:
        raise ValueError(
            "NOTES_ROOT is not set. Set it in mcp.json."
        )
    root = Path(raw).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"NOTES_ROOT is not a directory: {root}")
    return root


def _note_path(root: Path, relative: str) -> Path:
    """Join relative path under NOTES_ROOT."""
    rel = relative.strip()
    if not rel:
        raise ValueError("path must be non-empty")
    return root / rel


def _iter_markdown_files(root: Path) -> list[tuple[Path, str]]:
    out: list[tuple[Path, str]] = []
    for path in sorted(root.rglob("*.md")):
        if path.is_file():
            out.append((path, path.relative_to(root).as_posix()))
    return out


def _err(exc: Exception) -> str:
    return f"Error: {exc}"


@mcp.tool()
def list_notes(subdir: str = "") -> str:
    """List markdown notes under NOTES_ROOT (optional relative subdir)."""
    try:
        root = _notes_root()
        items = _iter_markdown_files(root)
        if subdir.strip():
            prefix = Path(subdir.strip()).as_posix().rstrip("/") + "/"
            items = [
                (p, rel)
                for p, rel in items
                if rel.startswith(prefix) or rel == subdir.strip()
            ]
        if not items:
            return f"No .md notes found under: {root}"
        lines = [f"- {rel}" for _, rel in items]
        return f"{len(lines)} note(s):\n" + "\n".join(lines)
    except Exception as exc:
        return _err(exc)


@mcp.tool()
def search_notes(query: str, max_hits: int = 20) -> str:
    """Search note contents (case-insensitive substring). Returns path + snippet."""
    try:
        root = _notes_root()
        q = query.strip()
        if not q:
            raise ValueError("query must be non-empty")
        limit = max(1, max_hits)
        hits: list[str] = []
        for path, rel in _iter_markdown_files(root):
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            lower = text.lower()
            idx = lower.find(q.lower())
            if idx < 0:
                continue
            start = max(0, idx - 40)
            nl = text.find("\n", idx)
            end = nl if nl != -1 else len(text)
            snippet = text[start:end].replace("\n", " ").strip()
            hits.append(f"- {rel}: …{snippet}…")
            if len(hits) >= limit:
                break
        if not hits:
            return f"No matches for {q!r}"
        return f"{len(hits)} hit(s) for {q!r}:\n" + "\n".join(hits)
    except Exception as exc:
        return _err(exc)


@mcp.tool()
def read_note(path: str) -> str:
    """Read a markdown note by relative path (e.g. inbox/ideas.md)."""
    try:
        root = _notes_root()
        note = _note_path(root, path)
        return note.read_text(encoding="utf-8")
    except Exception as exc:
        return _err(exc)


@mcp.tool()
def write_note(path: str, content: str) -> str:
    """Create or overwrite a markdown note (relative path). Creates parent dirs if needed."""
    try:
        root = _notes_root()
        note = _note_path(root, path)
        note.parent.mkdir(parents=True, exist_ok=True)
        note.write_text(content, encoding="utf-8")
        return f"Wrote {len(content)} chars to {path.strip()}"
    except Exception as exc:
        return _err(exc)


@mcp.tool()
def append_note(path: str, content: str) -> str:
    """Append text to an existing note, or create it if missing."""
    try:
        root = _notes_root()
        note = _note_path(root, path)
        note.parent.mkdir(parents=True, exist_ok=True)
        with note.open("a", encoding="utf-8") as f:
            f.write(content)
        return f"Appended {len(content)} chars to {path.strip()}"
    except Exception as exc:
        return _err(exc)


@mcp.tool()
def delete_note(path: str) -> str:
    """Delete a markdown note by relative path. Irreversible."""
    try:
        root = _notes_root()
        note = _note_path(root, path)
        note.unlink()
        return f"Deleted {path.strip()}"
    except Exception as exc:
        return _err(exc)

@mcp.tool()
def move_note(from_path: str, to_path: str) -> str:
    """Move/rename a note. Parent dir must exist (or use mkdir). Never overwrites — pick another to_path if dest exists."""
    try:
        root = _notes_root()
        src_rel = from_path.strip()
        dst_rel = to_path.strip()
        src = _note_path(root, src_rel)
        dst = _note_path(root, dst_rel)
        if not src.is_file():
            raise ValueError(f"source not found: {src_rel}")
        if src.resolve() == dst.resolve():
            return f"Already at {src_rel}"
        parent = dst.parent
        if not parent.is_dir():
            parent_rel = parent.relative_to(root).as_posix() or "."
            raise ValueError(f"destination parent missing: {parent_rel} (use mkdir)")
        if dst.exists():
            raise ValueError(f"destination already exists: {dst_rel} (choose another name)")
        src.rename(dst)
        return f"Moved {src_rel} → {dst_rel}"
    except Exception as exc:
        return _err(exc)


@mcp.tool()
def mkdir(path: str) -> str:
    """Create a directory under NOTES_ROOT (relative path). Creates parents. Idempotent."""
    try:
        root = _notes_root()
        rel = path.strip()
        target = _note_path(root, rel)
        if target.is_dir():
            return f"Already exists: {rel}"
        target.mkdir(parents=True, exist_ok=True)
        return f"Created {rel}"
    except Exception as exc:
        return _err(exc)


def main() -> None:
    # Log root on stderr only (stdout is the MCP wire).
    try:
        log.info("notes MCP root: %s", _notes_root())
    except ValueError as exc:
        log.error("%s", exc)
    mcp.run()


if __name__ == "__main__":
    main()
