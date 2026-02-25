# CLI Reference

ToolShield provides a single `toolshield` command with several subcommands. This page covers every command, its flags, and when to use it.

## Quick Decision Guide

| I want to...                                  | Command |
|-----------------------------------------------|---------|
| Guard my agent with pre-built safety rules     | [`toolshield import`](#toolshield-import) |
| Guard my agent with all 5 tool experiences     | [`toolshield import --all`](#toolshield-import) |
| See what bundled experiences are available      | [`toolshield list`](#toolshield-list) |
| Generate custom experiences for my MCP server  | [`toolshield generate`](#toolshield-generate) |
| Generate + inject in one shot (end-to-end)     | [`toolshield` (no subcommand)](#end-to-end-mode) |
| Auto-discover local MCP servers and protect    | [`toolshield auto`](#toolshield-auto) |
| Remove all injected guidelines                 | [`toolshield unload`](#toolshield-unload) |

---

## `toolshield import`

Inject pre-generated safety experiences into your coding agent's instruction file. This is the most common command — no API keys or MCP servers required.

```bash
toolshield import --exp-file <name-or-path> --agent <agent> [--model <model>]
```

### Flags

| Flag | Required | Default | Description |
|------|----------|---------|-------------|
| `--exp-file` | Yes (unless `--all`) | — | Experience file name (e.g., `filesystem-mcp.json`) or full path. Bare names are resolved against bundled experiences. |
| `--agent` | No | `claude_code` | Target agent: `claude_code`, `codex`, `openclaw`, `cursor`, `openhands` |
| `--model` | No | `claude-sonnet-4.5` | Which model's bundled experiences to use (see `toolshield list`) |
| `--all` | No | — | Import all 5 tool experiences for the selected model |
| `--source_location` | No | — | Override the target file path (instead of auto-detected agent config) |

### Examples

```bash
# Import filesystem safety rules into Claude Code (uses bundled claude-sonnet-4.5 experiences)
toolshield import --exp-file filesystem-mcp.json --agent claude_code

# Same, but using GPT-5.2 experiences
toolshield import --exp-file filesystem-mcp.json --model gpt-5.2 --agent claude_code

# Import all 5 tools at once
toolshield import --all --agent codex

# Import from a custom experience file (full path)
toolshield import --exp-file /path/to/my-custom-experiences.json --agent cursor

# Import into a custom file location
toolshield import --exp-file terminal-mcp.json --agent claude_code --source_location ~/my-project/CLAUDE.md
```

### Where guidelines are injected

| Agent | File |
|-------|------|
| `claude_code` | `~/.claude/CLAUDE.md` |
| `codex` | `~/.codex/AGENTS.md` |
| `openclaw` | `~/.openclaw/workspace/AGENTS.md` |
| `cursor` | Cursor's global user rules (SQLite database) |
| `openhands` | `~/.openhands/microagents/toolshield.md` |

---

## `toolshield list`

Print all bundled models and their available experience files.

```bash
toolshield list
```

Example output:

```
Model                          Experience files
----------------------------------------------------------------------
claude-sonnet-4.5              filesystem-mcp.json, notion-mcp.json, playwright-mcp.json, postgres-mcp.json, terminal-mcp.json
deepseek-v3.2                  filesystem-mcp.json, notion-mcp.json, playwright-mcp.json, postgres-mcp.json, terminal-mcp.json
gpt-5.2                        filesystem-mcp.json, notion-mcp.json, playwright-mcp.json, postgres-mcp.json, terminal-mcp.json
...
```

---

## `toolshield generate`

Generate custom safety experiences for any MCP server. This runs the full ToolShield pipeline: inspect tools, generate a safety tree, create test cases, execute them, and distill experiences into a JSON file.

Requires `TOOLSHIELD_MODEL_NAME` and `OPENROUTER_API_KEY` environment variables.

```bash
toolshield generate --mcp_name <name> --mcp_server <url> --output_path <dir>
```

### Flags

| Flag | Required | Default | Description |
|------|----------|---------|-------------|
| `--mcp_name` | Yes | — | Name of the MCP tool (e.g., `PostgreSQL`, `Filesystem`) |
| `--mcp_server` | Yes | — | MCP server SSE URL (e.g., `http://localhost:9091`) |
| `--output_path` | Yes | — | Directory for generated test cases and intermediate files |
| `--exp_file` | No | `<output_path>/../<name>-mcp.json` | Custom path for the output experience JSON |
| `--context_guideline` | No | — | Additional context to guide safety tree generation |
| `--agent-config` | No | auto-detected | Path to agent config TOML |
| `--eval-dir` | No | auto-detected | Evaluation directory |
| `--server-hostname` | No | `localhost` | MCP server hostname |
| `--debug` | No | — | Show verbose logs |

### Example

```bash
export TOOLSHIELD_MODEL_NAME="anthropic/claude-sonnet-4.5"
export OPENROUTER_API_KEY="your-key"

toolshield generate \
  --mcp_name postgres \
  --mcp_server http://localhost:9091 \
  --output_path output/postgres
```

---

## End-to-End Mode

Running `toolshield` without a subcommand combines `generate` + `import` in one shot: it generates experiences from a live MCP server and immediately injects them into the target agent.

```bash
toolshield --mcp_name <name> --mcp_server <url> --output_path <dir> --agent <agent>
```

### Example

```bash
export TOOLSHIELD_MODEL_NAME="anthropic/claude-sonnet-4.5"
export OPENROUTER_API_KEY="your-key"

toolshield \
  --mcp_name postgres \
  --mcp_server http://localhost:9091 \
  --output_path output/postgres \
  --agent codex
```

---

## `toolshield auto`

Auto-discover MCP servers running on localhost, run the full pipeline for each, and inject the results. Scans a range of ports for SSE endpoints.

Requires `TOOLSHIELD_MODEL_NAME` and `OPENROUTER_API_KEY` environment variables.

```bash
toolshield auto --agent <agent> [--start-port <port>] [--end-port <port>]
```

### Flags

| Flag | Required | Default | Description |
|------|----------|---------|-------------|
| `--agent` | Yes | — | Target agent: `claude_code`, `codex`, `openclaw`, `cursor`, `openhands` |
| `--start-port` | No | `8000` | Start of port scan range |
| `--end-port` | No | `10000` | End of port scan range |
| `--source_location` | No | — | Override target file path |
| `--agent-config` | No | auto-detected | Path to agent config TOML |
| `--eval-dir` | No | auto-detected | Evaluation directory |
| `--server-hostname` | No | `localhost` | Server hostname |
| `--debug` | No | — | Show verbose logs |

### Example

```bash
export TOOLSHIELD_MODEL_NAME="anthropic/claude-sonnet-4.5"
export OPENROUTER_API_KEY="your-key"

# Scan ports 8000-10000 and protect Claude Code
toolshield auto --agent claude_code

# Custom port range
toolshield auto --agent codex --start-port 9000 --end-port 9100
```

---

## `toolshield unload`

Remove all ToolShield-injected safety guidelines from the agent's instruction file. Your original file content is preserved.

```bash
toolshield unload --agent <agent>
```

### Flags

| Flag | Required | Default | Description |
|------|----------|---------|-------------|
| `--agent` | No | `claude_code` | Target agent: `claude_code`, `codex`, `openclaw`, `cursor`, `openhands` |
| `--source_location` | No | — | Override target file path |

### Example

```bash
# Remove guidelines from Claude Code
toolshield unload --agent claude_code

# Remove guidelines from Codex
toolshield unload --agent codex
```

---

## Environment Variables

These are only required for `generate`, end-to-end mode, and `auto` commands. The `import`, `list`, and `unload` commands work without any environment variables.

| Variable | Description |
|----------|-------------|
| `TOOLSHIELD_MODEL_NAME` | LLM model name without `openrouter/` prefix (e.g., `anthropic/claude-sonnet-4.5`) |
| `OPENROUTER_API_KEY` | API key for OpenRouter |
| `TOOLSHIELD_REPO_ROOT` | Override repository root detection (advanced) |
| `SERVER_HOST` | Default hostname for MCP servers (default: `localhost`) |
