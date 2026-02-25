#!/bin/bash

##############################################################################
# start_mcp_servers.sh
# Starts PostgreSQL container + 5 MCP servers in screen sessions
##############################################################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MCP_DIR="${SCRIPT_DIR}/mcp_server"
POSTGRES_CONTAINER="mcpmark-postgres"

# Check screen is installed
if ! command -v screen &> /dev/null; then
    echo "Error: screen not installed. Run: apt-get install screen"
    exit 1
fi

##############################################################################
# Start PostgreSQL if needed
##############################################################################

if ! docker ps | grep -q "$POSTGRES_CONTAINER"; then
    echo "Starting PostgreSQL container..."
    
    if docker ps -a | grep -q "$POSTGRES_CONTAINER"; then
        docker start "$POSTGRES_CONTAINER"
    else
        docker run --name "$POSTGRES_CONTAINER" \
            -e POSTGRES_PASSWORD=password \
            -e POSTGRES_HOST_AUTH_METHOD=trust \
            -p 5432:5432 \
            -d postgres
    fi
    
    echo "Waiting for PostgreSQL..."
    sleep 5
fi

##############################################################################
# Start MCP Servers in Screen
##############################################################################

start_mcp() {
    local name=$1
    local script=$2
    local screen_name="mcp_${name}"
    
    if screen -list | grep -q "$screen_name"; then
        echo "✓ $name already running"
        return
    fi
    
    screen -dmS "$screen_name" bash -c "cd $MCP_DIR && bash $script"
    sleep 2
    echo "✓ Started $name (screen -r $screen_name)"
}

echo "Starting MCP servers..."
start_mcp "filesystem" "start_filesystem.sh"
start_mcp "postgres" "start_postgres.sh"
start_mcp "playwright" "start_playwright.sh"
start_mcp "notion" "start_notion.sh"

echo ""
echo "All services started!"
echo ""
echo "Commands:"
echo "  screen -list              # List all sessions"
echo "  screen -r mcp_filesystem  # Attach to a server"
echo "  Ctrl+A, D                 # Detach from screen"