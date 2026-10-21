"""Notes MCP server — tools for list / search / read / write / append / delete."""

from __future__ import annotations

import logging
from pathlib import Path

from mcp.server import MCPServer

from notes_mcp.sandbox import SandboxError, get_roots, iter_markdown_files, resolve_note_path

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("notes-mcp")

mcp = MCPServer("notes", version="0.1.0")

MAX_READ_CHARS = 200_000
MAX_SEARCH_HITS = 50
MAX_SEARCH_SNIPPET = 200


def _err(exc: Exception) -> str:
    return f"Error: {exc}"


@mcp.tool()
def list_notes(subdir: str = "") -> str:
    """List markdown notes under NOTES_ROOT (optional relative subdir)."""
    try:
        roots = get_roots()
        items = iter_markdown_files()
        if subdir.strip():
            prefix = Path(subdir.strip()).as_posix().rstrip("/") + "/"
            if ".." in Path(subdir).parts:
                raise SandboxError("subdir must not contain '..'")
            items = [(p, rel) for p, rel in items if rel.startswith(prefix) or rel == subdir.strip()]
        if not items:
            roots_s = ", ".join(str(r) for r in roots)
            return f"No .md notes found under: {roots_s}"
        lines = [f"- {rel}" for _, rel in items]
        return f"{len(lines)} note(s):\n" + "\n".join(lines)
    except Exception as exc:
        return _err(exc)


@mcp.tool()
def search_notes(query: str, max_hits: int = 20) -> str:
    """Search note contents (case-insensitive substring). Returns path + snippet."""
    try:
        q = query.strip()
        if not q:
            raise SandboxError("query must be non-empty")
        limit = max(1, min(max_hits, MAX_SEARCH_HITS))
        hits: list[str] = []
        for path, rel in iter_markdown_files():
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            lower = text.lower()
            idx = lower.find(q.lower())
            if idx < 0:
                continue
            start = max(0, idx - 40)
            end = min(len(text), idx + len(q) + MAX_SEARCH_SNIPPET)
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
        note = resolve_note_path(path, must_exist=True)
        text = note.read_text(encoding="utf-8")
        if len(text) > MAX_READ_CHARS:
            return text[:MAX_READ_CHARS] + f"\n\n…[truncated at {MAX_READ_CHARS} chars]"
        return text
    except Exception as exc:
        return _err(exc)


@mcp.tool()
def write_note(path: str, content: str) -> str:
    """Create or overwrite a markdown note (relative path). Creates parent dirs if needed."""
    try:
        note = resolve_note_path(path, must_exist=False)
        note.parent.mkdir(parents=True, exist_ok=True)
        # Re-check after mkdir (parents must stay inside root)
        note = resolve_note_path(path, must_exist=False)
        note.write_text(content, encoding="utf-8")
        rel = path.strip()
        return f"Wrote {len(content)} chars to {rel}"
    except Exception as exc:
        return _err(exc)


@mcp.tool()
def append_note(path: str, content: str) -> str:
    """Append text to an existing note, or create it if missing."""
    try:
        note = resolve_note_path(path, must_exist=False)
        note.parent.mkdir(parents=True, exist_ok=True)
        note = resolve_note_path(path, must_exist=False)
        with note.open("a", encoding="utf-8") as f:
            f.write(content)
        return f"Appended {len(content)} chars to {path.strip()}"
    except Exception as exc:
        return _err(exc)


@mcp.tool()
def delete_note(path: str) -> str:
    """Delete a markdown note by relative path. Irreversible."""
    try:
        note = resolve_note_path(path, must_exist=True)
        note.unlink()
        return f"Deleted {path.strip()}"
    except Exception as exc:
        return _err(exc)


def main() -> None:
    # Log roots on stderr only (stdout is the MCP wire).
    try:
        roots = get_roots()
        log.info("notes MCP allowlist: %s", ", ".join(str(r) for r in roots))
    except SandboxError as exc:
        log.error("%s", exc)
    mcp.run()


if __name__ == "__main__":
    main()
