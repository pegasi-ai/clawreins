# ToolShield + OpenClaw

[OpenClaw](https://github.com/openclaw/openclaw) is an open-source AI coding agent. ToolShield injects safety guidelines into its workspace instruction file.

## How It Works

ToolShield appends guidelines to `~/.openclaw/workspace/AGENTS.md`, which OpenClaw loads as persistent agent instructions. Legacy directory names (`.clawdbot`, `.moltbot`, `.moldbot`) are also detected automatically.

## Import

```bash
toolshield import \
  --exp-file postgres-mcp.json \
  --agent openclaw
```

You can import multiple tools — each appends to the same file:

```bash
toolshield import --exp-file terminal-mcp.json --agent openclaw
toolshield import --exp-file filesystem-mcp.json --agent openclaw
```

## Unload

```bash
toolshield unload --agent openclaw
```

This removes all ToolShield-injected guidelines while preserving your existing `AGENTS.md` content.

## File Location

| Platform | Path |
|----------|------|
| All | `~/.openclaw/workspace/AGENTS.md` |

## Custom Location

If your `AGENTS.md` is in a non-default location:

```bash
toolshield import --exp-file <path> --agent openclaw --source_location /path/to/AGENTS.md
```
