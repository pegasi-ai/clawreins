#!/bin/bash
PORT=9092
NODE_EXEC="/root/.nvm/versions/node/v24.11.0/bin/node"
SERVER_SCRIPT="/mnt/data/OpenAgentSafety/node_modules/@playwright/mcp/cli.js"

echo "----------------------------------------------------------------"
echo "🔌 Starting Playwright MCP (Ephemeral Session)"
echo "----------------------------------------------------------------"

# 1. Create a unique temp directory for THIS session (locks & profile) and clean it up on exit
TEMP_HOME=$(mktemp -d -t playwright_session_XXXXXX)
trap 'rm -rf "$TEMP_HOME"' EXIT
mkdir -p "$TEMP_HOME/.cache"

# 2. Export Variables
# CRITICAL: Point to the REAL location where you installed browsers
export PLAYWRIGHT_BROWSERS_PATH="/root/.cache/ms-playwright"

# Point HOME to the TEMP location to avoid "SingletonLock" errors
export HOME="$TEMP_HOME"
export XDG_CACHE_HOME="$TEMP_HOME/.cache"

echo "📂 User Data (Locks): $TEMP_HOME"
echo "📂 Browser Binaries:  $PLAYWRIGHT_BROWSERS_PATH"

# 3. Run Supergateway with isolated, no-sandbox browser contexts to avoid Playwright lock errors
npx -y supergateway --port $PORT --stdio \
    "env HOME=$TEMP_HOME XDG_CACHE_HOME=$XDG_CACHE_HOME PLAYWRIGHT_BROWSERS_PATH=$PLAYWRIGHT_BROWSERS_PATH PLAYWRIGHT_MCP_ISOLATED=1 PLAYWRIGHT_MCP_SANDBOX=0 $NODE_EXEC $SERVER_SCRIPT --isolated --no-sandbox"
