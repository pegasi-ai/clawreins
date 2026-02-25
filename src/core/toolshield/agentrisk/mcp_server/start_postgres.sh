#!/bin/bash
PORT=9091
# Connection to the standard 'postgres' db where we create our tables
DB_URL="postgresql://postgres:password@localhost:5432/postgres"
MCP_EXEC="/root/miniforge3/envs/mcp_mark/bin/postgres-mcp"

echo "----------------------------------------------------------------"
echo "🔌 Starting Postgres MCP Server on Port $PORT"
echo "----------------------------------------------------------------"
echo "   Target DB: $DB_URL"
echo "   Mode:      Stdio -> SSE (Supergateway)"

# Just run the server. 
# The data reset is now handled by Python (evaluation/db_setup.py)
npx -y supergateway --port $PORT --stdio "$MCP_EXEC $DB_URL"