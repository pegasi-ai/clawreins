# ToolShield + Codex

[Codex](https://github.com/openai/codex) is OpenAI's CLI coding agent. ToolShield injects safety guidelines into its global instruction file.

## How It Works

ToolShield appends guidelines to `~/.codex/AGENTS.md`, which Codex loads as persistent agent instructions.

## Import

```bash
toolshield import \
  --exp-file postgres-mcp.json \
  --agent codex
```

You can import multiple tools — each appends to the same file:

```bash
toolshield import --exp-file terminal-mcp.json --agent codex
toolshield import --exp-file filesystem-mcp.json --agent codex
```

## Unload

```bash
toolshield unload --agent codex
```

This removes all ToolShield-injected guidelines while preserving your existing `AGENTS.md` content.

## File Location

| Platform | Path |
|----------|------|
| All | `~/.codex/AGENTS.md` |

## Custom Location

If your `AGENTS.md` is in a non-default location:

```bash
toolshield import --exp-file <path> --agent codex --source_location /path/to/AGENTS.md
```
