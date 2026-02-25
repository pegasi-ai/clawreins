# Reproducing Experiments

This guide covers how to reproduce the ToolShield and MT-AgentRisk evaluation results.

## Prerequisites

- Python 3.10+
- Docker
- An [OpenRouter](https://openrouter.ai/) API key
- A [Notion](https://developers.notion.com/) API token (for Notion tasks)

## 1. Environment Setup

### 1.1 Install ToolShield

```bash
git clone https://github.com/CHATS-Lab/ToolShield.git
cd ToolShield
pip install -e ".[eval]"
```

### 1.2 Download the MT-AgentRisk Dataset

```bash
git clone https://huggingface.co/datasets/CHATS-Lab/MT-AgentRisk
cp -r MT-AgentRisk/workspaces/* workspaces/
```

### 1.3 Setup OpenHands

```bash
git clone --branch 0.54.0 --single-branch https://github.com/OpenHands/OpenHands.git
cp agentrisk/client.py OpenHands/openhands/mcp/client.py
pip install -e OpenHands/
```

### 1.4 Clone MCPMark

```bash
git clone https://github.com/eval-sys/mcpmark.git mcpmark-main
```

Follow [this guide](https://github.com/eval-sys/mcpmark/blob/main/docs/mcp/notion.md) to obtain your `NOTION_TOKEN`.

### 1.5 Set Environment Variables

```bash
export TOOLSHIELD_MODEL_NAME="anthropic/claude-sonnet-4.5"
export OPENROUTER_API_KEY="YOUR_OPENROUTER_KEY"
export NOTION_TOKEN="YOUR_EVAL_NOTION_KEY"
export SOURCE_NOTION_KEY="YOUR_SOURCE_NOTION_KEY"
export SERVER_HOST="localhost"
```

> Do **not** include the `openrouter/` prefix in `TOOLSHIELD_MODEL_NAME`.

### 1.6 Start MCP Servers

```bash
bash agentrisk/start_mcp_servers.sh
```

## 2. Running ToolShield Defense (Self-Exploration)

Full pipeline — inspect MCP, generate safety tree, generate tests, distill experiences, inject into agent:

```bash
toolshield \
  --mcp_name postgres \
  --mcp_server http://localhost:9091 \
  --output_path output/postgres \
  --agent codex
```

Generate only (no import):

```bash
toolshield generate \
  --mcp_name postgres \
  --mcp_server http://localhost:9091 \
  --output_path output/postgres
```

Import pre-generated experiences:

```bash
toolshield import \
  --exp-file toolshield/experiences/claude-sonnet-4.5/postgres-mcp.json \
  --agent codex
```

### Output

- Safety tree: `<output_path>/<mcp_name>_safety_tree.json`
- Test cases: `<output_path>/task.*` and `<output_path>/multi_turn_task.*`
- Experience list: `<output_path>/../{tool}-mcp.json`

## 3. Running Evaluation

### Agent Configuration

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

Remove `--use-experience` to run without defense.

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

## 4. Docker Quick Start

```bash
# Build and start all MCP servers + evaluation environment
docker compose -f docker/docker-compose.yml up -d

# Run ToolShield inside the container
docker compose -f docker/docker-compose.yml exec toolshield-eval \
  toolshield --mcp_name postgres --mcp_server http://mcp-postgres:9091 \
  --output_path /app/output/postgres --agent codex
```

## 5. Resetting Services Between Runs

```bash
python agentrisk/db_setup.py          # PostgreSQL
python agentrisk/reset_notion.py      # Notion
```

## 6. Playwright / Browser Tasks

Full Playwright setup (Reddit, Shopping, Shopping Admin) requires additional steps:

1. Follow the [SafeArena setup guide](https://github.com/McGill-NLP/safearena/blob/main/README.md)
2. See `agentrisk/playwright_note/README.md` for integration instructions
3. Replace prompt files with full-playwright variants
4. Run `correct_web_address.py`

## Common Issues

**Missing env vars**: Export `TOOLSHIELD_MODEL_NAME` and `OPENROUTER_API_KEY` before running.

**MCP connection timeout**: Verify the server is up:
```bash
curl -v http://localhost:9091/sse
```
