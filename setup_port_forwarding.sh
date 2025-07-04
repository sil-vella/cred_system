#!/bin/bash

echo "Setting up port forwarding for MongoDB and Redis..."

# Kill any existing port forwarding
pkill -f "kubectl port-forward" || true

# Set up MongoDB port forwarding
echo "Setting up MongoDB port forwarding (27017)..."
kubectl port-forward -n flask-app svc/mongodb 27017:27017 &
MONGO_PID=$!

# Set up Redis port forwarding
echo "Setting up Redis port forwarding (6379)..."
kubectl port-forward -n flask-app svc/redis-master-master 6379:6379 &
REDIS_PID=$!

echo "Port forwarding started:"
echo "MongoDB: localhost:27017"
echo "Redis: localhost:6379"
echo ""
echo "PIDs: MongoDB=$MONGO_PID, Redis=$REDIS_PID"
echo "To stop port forwarding, run: kill $MONGO_PID $REDIS_PID"

# Wait for user to stop
echo "Press Ctrl+C to stop port forwarding..."
wait 