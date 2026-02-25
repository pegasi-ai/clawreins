

<div align="center">
<h1>ToolShield: A Package to Guard Your Agent</h1>

[![PyPI](https://img.shields.io/pypi/v/toolshield?style=for-the-badge&logo=pypi&logoColor=white)](https://pypi.org/project/toolshield/) [![Paper](https://img.shields.io/badge/arXiv-2602.13379-b31b1b?style=for-the-badge&logo=arxiv&logoColor=white)](https://arxiv.org/abs/2602.13379) [![Homepage](https://img.shields.io/badge/Homepage-4d8cd8?style=for-the-badge&logo=google-chrome&logoColor=white)](https://unsafer-in-many-turns.github.io) [![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE) [![HuggingFace](https://img.shields.io/badge/%F0%9F%A4%97%20Dataset-FFD21E?style=for-the-badge)](https://huggingface.co/datasets/CHATS-Lab/MT-AgentRisk)

<strong>Supports:</strong>&nbsp;
<a href="#use-pre-generated-experiences"><img src="https://img.shields.io/badge/Claude_Code-D97757?style=flat-square&logo=anthropic&logoColor=white" alt="Claude Code"></a>
<a href="docs/agents/codex.md"><img src="https://img.shields.io/badge/Codex-000000?style=flat-square&logo=data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAIAAACQkWg2AAABm0lEQVR42rVSK6jCYBj9f7FoG75A0KRNWbDKQAQxGuRHYWCRgWYRLBo0DCwqBrUJLojY7C74aGPJMNGyMIQN8QEKv7pbLj7GhcsN97SP7xy+7xwO1HUd/AUm8EeYDfP9fud5fr/fRyIRm832ywWMMU3T6/UaABCNRlOpVCaTEUXxQ6G/odVqTSaTxWKBEOr3+8fjUVXVZDK5Wq2enJeAYRiSJGVZTiQSmqaVy+VYLMYwzGw2q1QqT9q3h+l06vP5XC4XhFBV1VwudzqdstlsIBCoVqt2u91oervdhkIhnufP57PX6+U47vF4hMNht9vNsmy9Xpdl2ePxvExTFMVxHE3TtVpNURSMMcaYIIhSqTQcDuPx+HK5/Ljg9/vNZnOxWGRZdrPZUBTldDoPh4PFYgEACIKAEDLGShBEoVDodrudTiedTrfbbavVquv6aDSCEAaDQWOskiQhhDRNu16vzWYTISRJ0mAwGI/H79HD9y6Jotjr9W63myAI+Xx+t9spitJoNEym1yPwx/JdLpf5fO5wOEiSNKzgv7f1C7WV+mn4U8OsAAAAAElFTkSuQmCC&logoColor=white" alt="Codex"></a>
<a href="#use-pre-generated-experiences"><img src="https://img.shields.io/badge/Cursor-00A3E0?style=flat-square&logo=cursor&logoColor=white" alt="Cursor"></a>
<a href="docs/agents/openhands.md"><img src="https://img.shields.io/badge/%F0%9F%99%8C_OpenHands-E5725E?style=flat-square" alt="OpenHands"></a>
<a href="docs/agents/openclaw.md"><img src="https://img.shields.io/badge/%F0%9F%A6%9E_OpenClaw-FF6B6B?style=flat-square" alt="OpenClaw"></a>
</div>

---

<p align="center">
  <a href="#quickstart">Quickstart</a> |
  <a href="#use-pre-generated-experiences">Pre-Generated Safety Experiences</a> |
  <a href="#generate-your-own-safety-experiences">Generate Your Own Safety Experiences</a> |
  <br>
  <a href="#extend-to-new-tools">Extend to New Tools</a> |
  <a href="#mt-agentrisk-benchmark">Safety Benchmark</a> |
  <a href="#citation">Citation</a>
</p>

**ToolShield** is a training-free, tool-agnostic defense for AI agents that use MCP tools. Just `pip install toolshield` and a single command guards your coding agent with safety experiences — no API keys, no sandbox setup, no fine-tuning. Reduces attack success rate by **30%** on average.

<p align="center">
  <img src="assets/overview.png" alt="Overview" width="75%">
</p>

## Quickstart

```bash
pip install toolshield
```

### Use Pre-generated Experiences

We ship safety experiences for 6 models across 5 tools, with plug-and-play support for **5 coding agents**:

<a href="#use-pre-generated-experiences">
  <img src="https://img.shields.io/badge/Claude_Code-D97757?style=flat-square&logo=anthropic&logoColor=white" alt="Claude Code" />
</a>
<a href="docs/agents/codex.md">
  <img src="https://img.shields.io/badge/Codex-000000?style=flat-square&logo=data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAIAAACQkWg2AAABm0lEQVR42rVSK6jCYBj9f7FoG75A0KRNWbDKQAQxGuRHYWCRgWYRLBo0DCwqBrUJLojY7C74aGPJMNGyMIQN8QEKv7pbLj7GhcsN97SP7xy+7xwO1HUd/AUm8EeYDfP9fud5fr/fRyIRm832ywWMMU3T6/UaABCNRlOpVCaTEUXxQ6G/odVqTSaTxWKBEOr3+8fjUVXVZDK5Wq2enJeAYRiSJGVZTiQSmqaVy+VYLMYwzGw2q1QqT9q3h+l06vP5XC4XhFBV1VwudzqdstlsIBCoVqt2u91oervdhkIhnufP57PX6+U47vF4hMNht9vNsmy9Xpdl2ePxvExTFMVxHE3TtVpNURSMMcaYIIhSqTQcDuPx+HK5/Ljg9/vNZnOxWGRZdrPZUBTldDoPh4PFYgEACIKAEDLGShBEoVDodrudTiedTrfbbavVquv6aDSCEAaDQWOskiQhhDRNu16vzWYTISRJ0mAwGI/H79HD9y6Jotjr9W63myAI+Xx+t9spitJoNEym1yPwx/JdLpf5fO5wOEiSNKzgv7f1C7WV+mn4U8OsAAAAAElFTkSuQmCC&logoColor=white" alt="Codex" />
</a>
<a href="#use-pre-generated-experiences">
  <img src="https://img.shields.io/badge/Cursor-00A3E0?style=flat-square&logo=cursor&logoColor=white" alt="Cursor" />
</a>
<a href="docs/agents/openhands.md">
  <img src="https://img.shields.io/badge/%F0%9F%99%8C_OpenHands-E5725E?style=flat-square" alt="OpenHands" />
</a>
<a href="docs/agents/openclaw.md">
  <img src="https://img.shields.io/badge/%F0%9F%A6%9E_OpenClaw-FF6B6B?style=flat-square" alt="OpenClaw" />
</a>

Inject them in one command — no need to know where files are installed:

```bash
# For Claude Code (filesystem example)
toolshield import --exp-file filesystem-mcp.json --agent claude_code

# For Codex (postgres example)
toolshield import --exp-file postgres-mcp.json --agent codex

# For OpenClaw (terminal example)
toolshield import --exp-file terminal-mcp.json --agent openclaw

# For Cursor (playwright example)
toolshield import --exp-file playwright-mcp.json --agent cursor

# For OpenHands (notion example)
toolshield import --exp-file notion-mcp.json --agent openhands
```

Use experiences from a different model with `--model`:

```bash
toolshield import --exp-file filesystem-mcp.json --model gpt-5.2 --agent claude_code
```

Or import **all** bundled experiences (all 5 tools) in one shot:

```bash
toolshield import --all --agent claude_code
```

You can also import multiple experience files individually:

```bash
toolshield import --exp-file filesystem-mcp.json --agent claude_code
toolshield import --exp-file terminal-mcp.json --agent claude_code
toolshield import --exp-file postgres-mcp.json --agent claude_code
```

See all available bundled experiences:

```bash
toolshield list
```

This appends safety guidelines to your agent's context file (`~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md`, `~/.openclaw/workspace/AGENTS.md`, Cursor's global user rules, or `~/.openhands/microagents/toolshield.md`). To remove them:

```bash
toolshield unload --agent claude_code
```

Available bundled experiences (run `toolshield list` to see all):

| Model | ![Filesystem](https://img.shields.io/badge/-Filesystem-black?style=flat-square&logo=files&logoColor=white) | ![PostgreSQL](https://img.shields.io/badge/-PostgreSQL-black?style=flat-square&logo=postgresql&logoColor=white) | ![Terminal](https://img.shields.io/badge/-Terminal-black?style=flat-square&logo=gnometerminal&logoColor=white) | ![Chrome](https://img.shields.io/badge/-Chrome-black?style=flat-square&logo=googlechrome&logoColor=white) | ![Notion](https://img.shields.io/badge/-Notion-black?style=flat-square&logo=notion&logoColor=white) |
|-------|:---:|:---:|:---:|:---:|:---:|
| `claude-sonnet-4.5` | ✅  | ✅ | ✅ | ✅ | ✅ |
| `gpt-5.2` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `deepseek-v3.2` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `gemini-3-flash-preview` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `qwen3-coder-plus` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `seed-1.6` | ✅ | ✅ | ✅ | ✅ | ✅ |

> More plug-and-play experiences for additional tools coming soon (including [Toolathlon](https://github.com/hkust-nlp/Toolathlon) support)! Have a tool you'd like covered? [Open an issue](https://github.com/CHATS-Lab/ToolShield/issues).

### Generate Your Own Safety Experiences

Point ToolShield at any running MCP server to generate custom safety experiences:

```bash
export TOOLSHIELD_MODEL_NAME="anthropic/claude-sonnet-4.5"
export OPENROUTER_API_KEY="your-key"

# Full pipeline: inspect → generate safety tree → test → distill → inject
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

### Auto-discover Local MCP Servers

Automatically scan localhost for running MCP servers, run the full pipeline for each, and inject the results:

```bash
toolshield auto --agent codex
```

This scans ports 8000-10000 by default (configurable with `--start-port` / `--end-port`).

### Extend to New Tools

ToolShield works with any MCP server that has an SSE endpoint:

```bash
toolshield generate \
  --mcp_name your_custom_tool \
  --mcp_server http://localhost:PORT \
  --output_path output/your_custom_tool
```

## MT-AgentRisk Benchmark

We also release **MT-AgentRisk**, a benchmark of 365 harmful tasks across 5 MCP tools, transformed into multi-turn attack sequences. See [`agentrisk/README.md`](agentrisk/README.md) for full evaluation setup.

**Quick evaluation:**

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

## Repository Layout

```
ToolShield/
├── toolshield/              # pip-installable defense package
│   └── experiences/         # bundled safety experiences (6 models × 5 tools)
├── agentrisk/               # evaluation framework (see agentrisk/README.md)
├── workspaces/              # MT-AgentRisk task data (from HuggingFace)
├── docker/                  # Dockerfiles and compose
└── scripts/                 # experiment reproduction guides
```

## Acknowledgments

We thank the authors of the following projects for their contributions:

- [OpenAgentSafety](https://github.com/sani903/OpenAgentSafety)
- [SafeArena](https://github.com/McGill-NLP/safearena)
- [MCPMark](https://github.com/eval-sys/mcpmark)

## Citation

```bibtex
@misc{li2026unsaferturnsbenchmarkingdefending,
      title={Unsafer in Many Turns: Benchmarking and Defending Multi-Turn Safety Risks in Tool-Using Agents},
      author={Xu Li and Simon Yu and Minzhou Pan and Yiyou Sun and Bo Li and Dawn Song and Xue Lin and Weiyan Shi},
      year={2026},
      eprint={2602.13379},
      archivePrefix={arXiv},
      primaryClass={cs.CR},
      url={https://arxiv.org/abs/2602.13379},
}
```

## License

MIT
