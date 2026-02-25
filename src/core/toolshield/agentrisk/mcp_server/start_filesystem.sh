#!/bin/bash
rm -f /workspace 2>/dev/null 
mkdir -p /mnt/shared_workspace
mkdir -p /workspace
mount --bind /mnt/shared_workspace /workspace

ls -ld /mnt/shared_workspace

npx -y supergateway --port 9090 --stdio "/root/.nvm/versions/node/v24.11.0/bin/node /mnt/data/OpenAgentSafety/node_modules/@modelcontextprotocol/server-filesystem/dist/index.js /root /mnt/shared_workspace /workspace /tmp /var /etc"