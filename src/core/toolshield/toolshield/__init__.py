"""ToolShield — Training-free defense for multi-turn safety risks in tool-using AI agents."""

__version__ = "0.1.0"

from toolshield.inspector import MCPSSEInspector, MCPStreamableHTTPInspector

# Backwards compatibility
MCPInspector = MCPSSEInspector

__all__ = ["MCPInspector", "MCPSSEInspector", "MCPStreamableHTTPInspector", "__version__"]
