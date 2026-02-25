# ToolShield + Cursor

[Cursor](https://cursor.com) is an AI-powered code editor. ToolShield injects safety guidelines into Cursor's **global user rules** stored in its internal SQLite database.

## How It Works

Cursor stores user rules in a SQLite database (`state.vscdb`) under the key `aicontext.personalContext`. ToolShield reads the existing rules, appends safety guidelines, and writes them back. Your existing rules are fully preserved.

## Import

```bash
toolshield import \
  --exp-file postgres-mcp.json \
  --agent cursor
```

You can import multiple tools — each appends to the existing rules:

```bash
toolshield import --exp-file terminal-mcp.json --agent cursor
toolshield import --exp-file filesystem-mcp.json --agent cursor
```

## Unload

```bash
toolshield unload --agent cursor
```

This removes all ToolShield-injected guidelines while preserving your existing user rules.

## Database Location

| Platform | Path |
|----------|------|
| macOS | `~/Library/Application Support/Cursor/User/globalStorage/state.vscdb` |
| Linux | `~/.config/Cursor/User/globalStorage/state.vscdb` |
| Windows | `%APPDATA%\Cursor\User\globalStorage\state.vscdb` |

## Notes

- ToolShield writes to the **global** user rules (not project-level `.cursor/rules/`), so guidelines apply across all projects.
- Cursor must be restarted (or the rules reloaded) for changes to take effect.
- If Cursor is installed in a non-default location, use `--source_location` to point to a plain text file instead.
