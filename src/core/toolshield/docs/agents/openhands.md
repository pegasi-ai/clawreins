# ToolShield + OpenHands

[OpenHands](https://github.com/OpenHands/OpenHands) is an open-source AI-driven development platform. ToolShield injects safety guidelines as a **microagent** that is always loaded into the agent's system prompt.

## How It Works

OpenHands supports [microagents](https://docs.openhands.dev/sdk) — specialized markdown files that enhance agents with domain-specific knowledge. ToolShield creates a user-level microagent at `~/.openhands/microagents/toolshield.md` with `type: repo`, which means it is **always active** (no keyword triggers needed).

## Import

```bash
toolshield import \
  --exp-file postgres-mcp.json \
  --agent openhands
```

You can import multiple tools — each appends to the same microagent file:

```bash
toolshield import --exp-file terminal-mcp.json --agent openhands
toolshield import --exp-file filesystem-mcp.json --agent openhands
```

## Unload

```bash
toolshield unload --agent openhands
```

This deletes the `toolshield.md` microagent file entirely.

## File Location

| Platform | Path |
|----------|------|
| All | `~/.openhands/microagents/toolshield.md` |

## Microagent Format

The generated file follows the OpenHands microagent spec:

```yaml
---
name: toolshield
type: repo
version: 1.0.0
agent: CodeActAgent
---

## Guidelines from Previous Experience
...
```

## Disabling Without Unloading

You can temporarily disable the microagent without deleting it by adding to your OpenHands `config.toml`:

```toml
[agent]
disabled_microagents = ["toolshield"]
```
