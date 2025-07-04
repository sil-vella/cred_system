#!/bin/bash

echo "🚀 Starting development environment..."

# Start port forwarding in background
echo "📡 Setting up port forwarding..."
./setup_port_forwarding.sh &
PF_PID=$!

# Wait a moment for port forwarding to establish
sleep 3

echo "🐳 Starting Flask app with Docker Compose..."
docker compose up --build

# Cleanup when done
echo "🧹 Cleaning up..."
kill $PF_PID 2>/dev/null || true
pkill -f "kubectl port-forward" 2>/dev/null || true 