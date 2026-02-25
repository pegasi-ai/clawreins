# ToolShield

**Training-Free Defense for Tool-Using AI Agents**

ToolShield is a training-free, tool-agnostic defense for AI agents that use MCP tools. Just `pip install toolshield` and a single command guards your coding agent with safety experiences — no API keys, no sandbox setup, no fine-tuning.

Reduces attack success rate by **30%** on average.

![Overview](assets/overview.png)

## Supported Agents

- [Claude Code](agents/claude-code.md)
- [Codex](agents/codex.md)
- [Cursor](agents/cursor.md)
- [OpenHands](agents/openhands.md)
- [OpenClaw](agents/openclaw.md)

## Get Started

```bash
pip install toolshield

# Guard your agent with one command
toolshield import --all --agent claude_code

# Or pick a specific tool
toolshield import --exp-file filesystem-mcp.json --agent claude_code
```

See the [Quickstart](quickstart.md) for more examples, or the full [CLI Reference](cli.md) for every command and flag.

## Links

- [PyPI](https://pypi.org/project/toolshield/)
- [GitHub](https://github.com/CHATS-lab/ToolShield)
- [Homepage](https://unsafer-in-many-turns.github.io)
- [Dataset (HuggingFace)](https://huggingface.co/datasets/CHATS-Lab/MT-AgentRisk)
