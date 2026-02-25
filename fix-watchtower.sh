#!/bin/bash
# Fix Watchtower API version error
# Run this script on Proxmox LXC (docker-server)

echo "🔧 Fixing Watchtower API version error..."
echo ""

# Stop and remove old watchtower container
echo "1️⃣ Stopping old Watchtower container..."
docker stop 3d-farm-watchtower 2>/dev/null || echo "   Container already stopped"

echo "2️⃣ Removing old container..."
docker rm 3d-farm-watchtower 2>/dev/null || echo "   Container already removed"

# Pull latest watchtower image
echo "3️⃣ Pulling latest Watchtower image (API 1.44+)..."
docker pull containrrr/watchtower:latest

# Recreate watchtower from stack
echo "4️⃣ Recreating Watchtower from stack..."
docker run -d \
  --name 3d-farm-watchtower \
  --restart unless-stopped \
  -v /var/run/docker.sock:/var/run/docker.sock \
  --network 3d-print-farm_printfarm-network \
  containrrr/watchtower:latest \
  --interval 300 --cleanup

echo ""
echo "✅ Watchtower fixed! Checking status..."
docker ps | grep watchtower

echo ""
echo "📋 Container logs (should be no more API errors):"
docker logs --tail 10 3d-farm-watchtower
