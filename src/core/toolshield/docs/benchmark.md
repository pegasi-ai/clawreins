# MT-AgentRisk Benchmark

ToolShield includes **MT-AgentRisk**, a benchmark of 365 harmful tasks across 5 MCP tools, transformed into multi-turn attack sequences.

## Overview

MT-AgentRisk tests whether AI agents can be manipulated through multi-turn conversations into performing harmful actions via MCP tools. Each task is a multi-step attack sequence that an adversarial user might attempt.

**Tools covered:** Filesystem, PostgreSQL, Terminal, Playwright (Browser), Notion

## Quick Evaluation

```bash
# 1. Download benchmark tasks
git clone https://huggingface.co/datasets/CHATS-Lab/MT-AgentRisk
cp -r MT-AgentRisk/workspaces/* workspaces/

# 2. Run a single task (requires OpenHands setup — see agentrisk/README.md)
python agentrisk/run_eval.py \
  --task-path workspaces/terminal/multi_turn_tasks/multi-turn_root-remove \
  --agent-llm-config agent \
  --env-llm-config env \
  --outputs-path output/eval \
  --server-hostname localhost
```

Add `--use-experience <path>` to evaluate with ToolShield defense.

## Full Setup

See [`agentrisk/README.md`](https://github.com/CHATS-lab/ToolShield/blob/main/agentrisk/README.md) for complete evaluation setup including:

- MCP server configuration
- Agent LLM configuration
- Batch evaluation scripts
- Post-evaluation (LLM-as-judge)

## Dataset

The MT-AgentRisk dataset is hosted on HuggingFace: [CHATS-Lab/MT-AgentRisk](https://huggingface.co/datasets/CHATS-Lab/MT-AgentRisk)
