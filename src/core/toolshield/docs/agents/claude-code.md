# ToolShield + Claude Code

[Claude Code](https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/overview) is Anthropic's CLI-based coding agent. ToolShield injects safety guidelines into its global instruction file.

## How It Works

ToolShield appends guidelines to `~/.claude/CLAUDE.md`, which Claude Code loads as persistent instructions for every session.

## Import

```bash
toolshield import \
  --exp-file postgres-mcp.json \
  --agent claude_code
```

You can import multiple tools — each appends to the same file:

```bash
toolshield import --exp-file terminal-mcp.json --agent claude_code
toolshield import --exp-file filesystem-mcp.json --agent claude_code
```

## Unload

```bash
toolshield unload --agent claude_code
```

This removes all ToolShield-injected guidelines while preserving your existing `CLAUDE.md` content.

## File Location

| Platform | Path |
|----------|------|
| All | `~/.claude/CLAUDE.md` |

## Custom Location

If your `CLAUDE.md` is in a non-default location:

```bash
toolshield import --exp-file <path> --agent claude_code --source_location /path/to/CLAUDE.md
```
