# Quickstart

## Install

```bash
pip install toolshield
```

## Use Pre-generated Experiences

ToolShield ships with safety experiences for **6 models** across **5 MCP tools**, ready to inject into any supported agent.

### Import a single tool

```bash
toolshield import --exp-file filesystem-mcp.json --agent claude_code
```

### Import all 5 tools at once

```bash
toolshield import --all --agent claude_code
```

### Use a different model's experiences

```bash
toolshield import --exp-file filesystem-mcp.json --model gpt-5.2 --agent claude_code
```

### See what's available

```bash
toolshield list
```

### Available experiences

| Model | Filesystem | PostgreSQL | Terminal | Playwright | Notion |
|-------|:---:|:---:|:---:|:---:|:---:|
| `claude-sonnet-4.5` | :white_check_mark: | :white_check_mark: | :white_check_mark: | :white_check_mark: | :white_check_mark: |
| `gpt-5.2` | :white_check_mark: | :white_check_mark: | :white_check_mark: | :white_check_mark: | :white_check_mark: |
| `deepseek-v3.2` | :white_check_mark: | :white_check_mark: | :white_check_mark: | :white_check_mark: | :white_check_mark: |
| `gemini-3-flash-preview` | :white_check_mark: | :white_check_mark: | :white_check_mark: | :white_check_mark: | :white_check_mark: |
| `qwen3-coder-plus` | :white_check_mark: | :white_check_mark: | :white_check_mark: | :white_check_mark: | :white_check_mark: |
| `seed-1.6` | :white_check_mark: | :white_check_mark: | :white_check_mark: | :white_check_mark: | :white_check_mark: |

## Unload

Remove all injected guidelines:

```bash
toolshield unload --agent claude_code
```

## Generate Your Own

Point ToolShield at any running MCP server to generate custom safety experiences:

```bash
export TOOLSHIELD_MODEL_NAME="anthropic/claude-sonnet-4.5"
export OPENROUTER_API_KEY="your-key"

# Full pipeline: inspect -> generate safety tree -> test -> distill -> inject
toolshield \
  --mcp_name postgres \
  --mcp_server http://localhost:9091 \
  --output_path output/postgres \
  --agent codex
```

Or generate without injecting (useful for review):

```bash
toolshield generate \
  --mcp_name postgres \
  --mcp_server http://localhost:9091 \
  --output_path output/postgres
```

## Auto-discover Local MCP Servers

Automatically scan localhost for running MCP servers, run the full pipeline for each, and inject the results:

```bash
toolshield auto --agent codex
```

This scans ports 8000-10000 by default (configurable with `--start-port` / `--end-port`).

## Next Steps

- [CLI Reference](cli.md) — every command and flag
- [Agent Guides](agents/claude-code.md) — per-agent setup details
