#!/bin/bash
echo "🔌 Starting Notion MCP Server on Port 9097"
npx -y supergateway --port 9097 \
  --stdio "env NOTION_TOKEN=$NOTION_TOKEN npx -y @notionhq/notion-mcp-server"