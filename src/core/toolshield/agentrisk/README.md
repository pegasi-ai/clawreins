# AgentRisk — MT-AgentRisk Evaluation Framework

This directory contains the evaluation framework for the **MT-AgentRisk** benchmark, built on [OpenHands](https://github.com/OpenHands/OpenHands).

## MT-AgentRisk Benchmark

365 single-turn harmful tasks across five MCP tool categories, transformed into multi-turn attack sequences using a principled taxonomy (Format, Method, Target). ASR increases by **16%** on average compared to single-turn.

| Tool Category | MCP Server | Port | Tasks |
|---------------|------------|------|-------|
| Filesystem    | `mcp-filesystem` | 9090 | File exfiltration, permission manipulation, data destruction |
| PostgreSQL    | `mcp-postgres`   | 9091 | Data theft, privilege escalation, schema destruction |
| Terminal      | —                | —    | Command injection, process manipulation, system compromise |
| Playwright    | `mcp-playwright` | 9092 | Credential theft, unauthorized purchases, data scraping |
| Notion        | `mcp-notion`     | 9097 | Document tampering, data exfiltration, access abuse |

### Dataset

Download from [HuggingFace](https://huggingface.co/datasets/CHATS-Lab/MT-AgentRisk):

```bash
git clone https://huggingface.co/datasets/CHATS-Lab/MT-AgentRisk
cp -r MT-AgentRisk/workspaces/* workspaces/
```

Each task directory contains:

| File | Description |
|------|-------------|
| `task.md` / `task-turn-*.md` | Instructions shown to the agent |
| `workspace/` | Pre-seeded sandbox filesystem contents |
| `utils/dependencies.yml` | MCP tools required by the task |
| `turns.yml` | Turn manifest for multi-turn tasks |
| `attack_chain.json` | Attack decomposition metadata |

## Setup

### 1. Install Dependencies

```bash
# From the repo root
pip install -e ".[eval]"

# Install OpenHands (pinned version)
git clone --branch 0.54.0 --single-branch https://github.com/OpenHands/OpenHands.git
cp agentrisk/client.py OpenHands/openhands/mcp/client.py
pip install -e OpenHands/

# Clone MCPMark (MCP server implementations)
git clone https://github.com/eval-sys/mcpmark.git mcpmark-main
```

### 2. Environment Variables

```bash
export TOOLSHIELD_MODEL_NAME="anthropic/claude-sonnet-4.5"
export OPENROUTER_API_KEY="YOUR_OPENROUTER_KEY"
export NOTION_TOKEN="YOUR_EVAL_NOTION_KEY"
export SOURCE_NOTION_KEY="YOUR_SOURCE_NOTION_KEY"
export SERVER_HOST="localhost"
```

> Do **not** include the `openrouter/` prefix in `TOOLSHIELD_MODEL_NAME`.

### 3. Start MCP Servers

```bash
bash agentrisk/start_mcp_servers.sh
```

### 4. Agent Configuration

Edit `agentrisk/agent_config/config.toml`:

```toml
[llm.agent]
model = "openrouter/anthropic/claude-sonnet-4.5"
base_url = "https://openrouter.ai/api/v1"
api_key = ""

[llm.env]
model = "openrouter/anthropic/claude-sonnet-4.5"
base_url = "https://openrouter.ai/api/v1"
api_key = ""
```

## Running Evaluation

### Single Task

```bash
python agentrisk/run_eval.py \
  --task-path workspaces/terminal/multi_turn_tasks/multi-turn_root-remove \
  --agent-llm-config agent \
  --env-llm-config env \
  --outputs-path output/eval \
  --use-experience toolshield/experiences/claude-sonnet-4.5/terminal-mcp.json \
  --server-hostname localhost
```

Remove `--use-experience` to run without ToolShield defense.

### Batch Evaluation

```bash
bash agentrisk/run_together.sh
```

### Post-Evaluation (LLM-as-Judge)

```bash
python agentrisk/post_eval.py \
  --tasks-dir <path-to-task-directory> \
  --output-dir <path-to-output-logs>
```

Classifies outcomes as **COMPLETE** (agent performed the harmful action), **REJECT** (agent refused), or **FAILED** (agent attempted but failed).

## Resetting Services Between Runs

```bash
python agentrisk/db_setup.py          # PostgreSQL
python agentrisk/reset_notion.py      # Notion
```

## Playwright / Full Browser Setup

Full Playwright setup (Reddit, Shopping, Shopping Admin) requires the [SafeArena](https://github.com/McGill-NLP/safearena) hosting setup. See `agentrisk/playwright_note/README.md` for integration instructions.

## Architecture

- **`run_eval.py`**: Main orchestrator. `TurnManager` drives multi-turn execution; `SingleTurnUser` simulates the adversarial human. Per-turn step limits (default 10 steps/turn, 30 total).
- **`client.py`**: `MCPClient` connects to MCP servers (SSE/Stdio/HTTP), wraps tools as `MCPClientTool` objects.
- **`post_eval.py`**: LLM-as-judge for three-way classification.
- **`browsing.py`**: Browser action abstraction layer for Playwright tasks.
