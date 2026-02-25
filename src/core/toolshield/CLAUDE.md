# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ToolShield is a research project for defending multi-turn safety risks in tool-using AI agents. It consists of:

- **ToolShield Defense** (`toolshield/`): A pip-installable, training-free pipeline where agents explore tool functionality in a sandbox, learn from executions, and distill safety experiences before deployment
- **MT-AgentRisk Benchmark** (`workspaces/`): 365 single-turn harmful tasks transformed into multi-turn attack sequences across 5 MCP tool categories (Filesystem, PostgreSQL, Terminal, Playwright/Browser, Notion)
- **AgentRisk Evaluation** (`agentrisk/`): Built on OpenHands, integrates with MCP servers for sandboxed task execution and LLM-as-judge post-evaluation

## Commands

```bash
# Install (uses Hatchling build backend)
pip install -e .

# Install with dev dependencies
pip install -e ".[dev]"

# Lint
ruff check toolshield/ agentrisk/

# Format
ruff format toolshield/ agentrisk/

# Start MCP servers (launches screen sessions for filesystem, postgres, playwright, notion)
bash agentrisk/start_mcp_servers.sh

# Generate safety experiences (end-to-end ToolShield pipeline)
toolshield \
  --mcp_name postgres \
  --mcp_server http://localhost:9091 \
  --output_path output/postgres \
  --agent codex

# Generate only (without importing experiences)
toolshield generate --mcp_name <name> --mcp_server <url> --output_path <dir>

# Import pre-generated experiences
toolshield import --exp-file <path> --agent <agent_name>

# Run single task evaluation
python agentrisk/run_eval.py \
  --task-path workspaces/terminal/multi_turn_tasks/multi-turn_root-remove \
  --agent-llm-config agent \
  --env-llm-config env \
  --outputs-path output/eval \
  --use-experience toolshield/experiences/claude-sonnet-4.5/terminal-mcp.json \
  --server-hostname localhost

# Batch evaluation
bash agentrisk/run_together.sh

# Post-evaluation (LLM-as-judge)
python agentrisk/post_eval.py --tasks-dir <task_dir> --output-dir <output_dir>

# Reset services between evaluation runs
python agentrisk/db_setup.py          # PostgreSQL
python agentrisk/reset_notion.py      # Notion
```

## Architecture

### ToolShield Defense Pipeline (`toolshield/`)

The pipeline has four stages, orchestrated by `cli.py`:

1. **MCP Inspection** (`inspector.py`) — Connect to running MCP server via SSE, fetch tool schemas
2. **Safety Tree Generation** (`tree_generation.py`) — LLM analyzes tools to produce hierarchical harm scenarios as JSON
3. **Test Case Generation** (`tree_generation.py`) — Creates single-turn (`task.X.md`) and multi-turn (`task-turn-*.md`) test tasks from harm scenarios
4. **Experience Distillation** (`exp_generate.py`, `iterative_exp_runner.py`) — Execute tasks, capture trajectories, extract safety guidelines into JSON experience files

Path configuration is centralized in `_paths.py` and can be overridden via environment variables (`TOOLSHIELD_REPO_ROOT`, etc.). Prompt templates live in `prompts.py` and `post_process_prompts.py`. Pre-generated experiences for multiple models are bundled in `toolshield/experiences/`.

### Evaluation Framework (`agentrisk/`)

- **`run_eval.py`**: Main orchestrator. `TurnManager` drives multi-turn execution; `SingleTurnUser` simulates adversarial human. Per-turn step limits (default 10 steps/turn, 30 total). Outcomes detected via regex patterns or LLM evaluation.
- **`client.py`**: `MCPClient` connects to MCP servers (SSE/Stdio/HTTP), wraps tools as `MCPClientTool` objects. Filters tool visibility and manages schema overrides.
- **`post_eval.py`**: LLM-as-judge classifying outcomes as COMPLETE, REJECT, or FAILED.
- **`browsing.py`**: Browser action abstraction layer for Playwright tasks.

Agent LLM config is in `agentrisk/agent_config/config.toml`. System prompt template at `agentrisk/agent_config/prompts/safety_prompt.j2`.

### MCP Server Ports (defaults, configurable via env vars)

| Server     | Port Env Var          | Default | SSE Endpoint                  |
|------------|-----------------------|---------|-------------------------------|
| Filesystem | `MCP_FILESYSTEM_PORT` | 9090    | `http://$SERVER_HOST:9090/sse`|
| PostgreSQL | `MCP_POSTGRES_PORT`   | 9091    | `http://$SERVER_HOST:9091/sse`|
| Playwright | `MCP_PLAYWRIGHT_PORT` | 9092    | `http://$SERVER_HOST:9092/sse`|
| Notion     | `MCP_NOTION_PORT`     | 9097    | `http://$SERVER_HOST:9097/sse`|

### External Dependencies

- **OpenHands** (modified multi-turn branch): Agent framework, installed separately
- **MCPMark** (`mcpmark-main/`): MCP tool server implementations
- **MT-AgentRisk dataset**: Hosted on HuggingFace (`CHATS-Lab/MT-AgentRisk`), tasks go in `workspaces/`

## Environment Variables

```bash
TOOLSHIELD_MODEL_NAME    # LLM model name without 'openrouter/' prefix (e.g., "anthropic/claude-sonnet-4.5")
TOOLSHIELD_REPO_ROOT     # Override repository root detection (default: auto-detected)
OPENROUTER_API_KEY       # API key for OpenRouter
NOTION_TOKEN             # Notion API token for evaluation
SOURCE_NOTION_KEY        # Source Notion key for workspace reset
SERVER_HOST              # Host for MCP servers (default: localhost)
MCP_FILESYSTEM_PORT      # Filesystem MCP port (default: 9090)
MCP_POSTGRES_PORT        # PostgreSQL MCP port (default: 9091)
MCP_PLAYWRIGHT_PORT      # Playwright MCP port (default: 9092)
MCP_NOTION_PORT          # Notion MCP port (default: 9097)
```

## Playwright/Browser Notes

Full Playwright setup (for Reddit, Shopping, Shopping Admin sites) requires additional steps documented in `agentrisk/playwright_note/README.md`: replacing prompt files with full-playwright variants and running `correct_web_address.py`. Requires SafeArena setup for hosting the 3 websites.
