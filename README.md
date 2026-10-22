# mcp-notes

Serveur MCP **notes** : accès à un dossier de fichiers Markdown via un **agent Cursor**.

## Idée

L’agent Cursor passe par ce MCP pour lister / chercher / lire / écrire des notes sous `NOTES_ROOT`.

1. Cursor lit [`.cursor/mcp.json`](.cursor/mcp.json) (`type: stdio`)
2. Il lance directement `.venv/bin/python` + `src/notes_mcp/server.py`
3. Le serveur Python **reste allumé** et attend
4. L’agent appelle un tool (`read_note`, etc.)
5. Cursor envoie la demande sur **stdin** du process ; le serveur répond sur **stdout**
6. Le serveur joint `NOTES_ROOT` + le chemin relatif fourni

## Outils exposés

| Tool | Rôle |
|---|---|
| `list_notes` | Liste les `.md` |
| `search_notes` | Recherche dans le contenu |
| `read_note` | Lit un chemin relatif |
| `write_note` | Crée / écrase |
| `append_note` | Ajoute à la fin |
| `delete_note` | Supprime |
| `move_note` | Déplace / renomme |
| `mkdir` | Crée un dossier |
