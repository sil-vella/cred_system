# Local Development with k3d

This guide shows how to set up a local Kubernetes development environment using k3d that **exactly mirrors** your production VPS setup.

## 🎯 Why k3d?

- **Same K3s version** as production (`v1.31.5+k3s1`)
- **Identical deployment approach** - no registry, local images only
- **Same manifests** - use your existing Ansible playbooks unchanged
- **Fast and lightweight** - runs K3s in Docker containers

---

## 📋 Prerequisites

### 1. Install Docker
```bash
# Install Docker via Colima (lightweight) or Docker Desktop
brew install colima docker

# Start Colima
colima start

# Verify Docker is working
docker --version
# Should show: Docker version 28.3.0, build 38b7060a21
```

### 2. Install k3d and kubectl
```bash
# Install k3d
brew install k3d

# Install kubectl (if not already installed)
brew install kubectl

# Verify installations
k3d version
kubectl version --client
```

---

## 🚀 Quick Start

### 1. Create Local K3s Cluster
```bash
# Create cluster with port forwarding for web access
k3d cluster create local-dev --port "8080:80@loadbalancer"

# Verify cluster is running
kubectl get nodes
# Should show: k3d-local-dev-server-0   Ready    control-plane,master
```

### 2. Build and Import Flask Application
```bash
# Navigate to Flask app directory
cd python_base_03/

# Build Docker image (same name as production)
docker build -t flask-credit-system:latest .

# Import image into k3d cluster
k3d image import flask-credit-system:latest -c local-dev

# Verify image is available
docker images | grep flask-credit-system
```

### 3. Deploy Using Existing Playbooks
```bash
# Navigate to playbooks directory
cd ../playbooks/rop02/

# Deploy Flask app using existing playbook (unchanged!)
ansible-playbook -i inventory.ini 07_deploy_flask_docker.yml \
  -e vm_name=local \
  --connection=local
```

---

## 🔧 Development Workflow

### For Code Changes (Fast - No Rebuilds)
```bash
# 1. Edit your Flask code locally
vim python_base_03/core/managers/some_manager.py

# 2. Update the running container (if using volume mounts)
# Changes are automatically reflected since k3d can mount local directories

# 3. Or rebuild and update image
cd python_base_03/
docker build -t flask-credit-system:latest .
k3d image import flask-credit-system:latest -c local-dev

# 4. Restart deployment to pick up new image
kubectl rollout restart deployment/flask-app -n flask-app
```

### For Configuration Changes
```bash
# Redeploy with updated configuration
ansible-playbook -i inventory.ini 07_deploy_flask_docker.yml \
  -e vm_name=local \
  --connection=local
```

---

## 🌐 Accessing Your Application

### Port Forwarding (Recommended)
```bash
# Forward Flask app port for direct access
kubectl port-forward -n flask-app svc/flask-app 8080:80

# Access your app
curl http://localhost:8080/health
curl http://localhost:8080/

# Or open in browser
open http://localhost:8080
```

### Via k3d LoadBalancer
```bash
# Access via k3d's built-in load balancer (if configured)
curl http://localhost:8080/

# With host header (if using ingress)
curl -H 'Host: flask-app.local' http://localhost:8080/
```

---

## 🔍 Monitoring and Debugging

### Check Application Status
```bash
# Check all pods in flask-app namespace
kubectl get pods -n flask-app

# Check deployment status
kubectl get deployments -n flask-app

# Check services
kubectl get services -n flask-app
```

### View Logs
```bash
# View Flask app logs
kubectl logs -f -n flask-app deployment/flask-app

# View logs from specific pod
kubectl logs -f -n flask-app <pod-name>

# View recent logs
kubectl logs -n flask-app deployment/flask-app --tail=50
```

### Debug Pod Issues
```bash
# Describe pod for detailed information
kubectl describe pod -n flask-app <pod-name>

# Execute commands in running pod
kubectl exec -it -n flask-app deployment/flask-app -- /bin/bash

# Test connectivity from within pod
kubectl exec -n flask-app deployment/flask-app -- curl -s http://localhost:5001/health
```

---

## 🧪 Testing Your Setup

### 1. Health Check
```bash
# Test Flask app health endpoint
kubectl port-forward -n flask-app svc/flask-app 8080:80 &
curl -s http://localhost:8080/health
# Should return: {"status": "healthy"}
```

### 2. Database Connectivity
```bash
# Test MongoDB connection (if deployed)
kubectl exec -n flask-app deployment/flask-app -- python3 -c "
import socket
socket.create_connection(('mongodb', 27017), timeout=5)
print('MongoDB: Connected successfully')
"

# Test Redis connection (if deployed)
kubectl exec -n flask-app deployment/flask-app -- python3 -c "
import socket
socket.create_connection(('redis-master', 6379), timeout=5)
print('Redis: Connected successfully')
"
```

### 3. Environment Variables
```bash
# Check Flask app environment
kubectl exec -n flask-app deployment/flask-app -- env | grep -E "(FLASK|MONGO|REDIS|VAULT)"
```

---

## 🔄 Cluster Management

### Start/Stop Cluster
```bash
# Stop cluster (preserves state)
k3d cluster stop local-dev

# Start cluster
k3d cluster start local-dev

# Delete cluster completely
k3d cluster delete local-dev
```

### Reset Development Environment
```bash
# Complete reset - delete and recreate cluster
k3d cluster delete local-dev
k3d cluster create local-dev --port "8080:80@loadbalancer"

# Rebuild and redeploy
cd python_base_03/
docker build -t flask-credit-system:latest .
k3d image import flask-credit-system:latest -c local-dev

cd ../playbooks/rop02/
ansible-playbook -i inventory.ini 07_deploy_flask_docker.yml \
  -e vm_name=local \
  --connection=local
```

---

## ⚡ Performance Tips

### Image Caching
```bash
# List imported images
k3d image list -c local-dev

# Import multiple images at once
k3d image import flask-credit-system:latest redis:latest mongodb:latest -c local-dev
```

### Resource Limits
```bash
# Check resource usage
kubectl top pods -n flask-app
kubectl top nodes

# Adjust cluster resources if needed
k3d cluster create local-dev \
  --agents 2 \
  --port "8080:80@loadbalancer" \
  --k3s-arg "--disable=traefik@server:*"
```

---

## 🔧 Troubleshooting

### Common Issues

**Cluster won't start:**
```bash
# Check Docker is running
docker ps

# Check k3d logs
k3d cluster list
docker logs k3d-local-dev-server-0
```

**Image not found:**
```bash
# Verify image was imported
k3d image list -c local-dev

# Re-import image
k3d image import flask-credit-system:latest -c local-dev
```

**Pod stuck in Pending:**
```bash
# Check pod events
kubectl describe pod -n flask-app <pod-name>

# Check node resources
kubectl describe nodes
```

**Can't access application:**
```bash
# Check service endpoints
kubectl get endpoints -n flask-app

# Check port forwarding
kubectl port-forward -n flask-app svc/flask-app 8080:80
netstat -an | grep 8080
```

### Useful Commands
```bash
# Get cluster info
kubectl cluster-info

# Get all resources in namespace
kubectl get all -n flask-app

# Check cluster events
kubectl get events -n flask-app --sort-by='.lastTimestamp'

# Export logs for debugging
kubectl logs -n flask-app deployment/flask-app > flask-app.log
```

---

## 🎉 Benefits of This Setup

### ✅ Production Parity
- **Same K3s version** as production
- **Same deployment process** - no registry required
- **Same manifests** - zero configuration changes
- **Same networking** - Kubernetes services and ingress

### ⚡ Development Speed
- **Fast cluster creation** - 30 seconds vs minutes
- **Quick image updates** - no registry push/pull
- **Instant feedback** - local development loop
- **Easy debugging** - full kubectl access

### 🔒 Security
- **Isolated environment** - doesn't affect production
- **Local-only** - no external dependencies
- **Same security policies** - network policies, RBAC, etc.

### 🧹 Clean Separation
- **No conflicts** with production
- **Easy cleanup** - delete cluster removes everything
- **Multiple environments** - run different versions simultaneously

---

## 📚 Next Steps

1. **Deploy supporting services** (MongoDB, Redis, Vault proxy)
2. **Set up monitoring** (Prometheus, Grafana)
3. **Configure CI/CD** pipeline for automated testing
4. **Add integration tests** that run against k3d cluster
5. **Set up development databases** with test data

## 🔗 Related Documentation

- [Flask Deployment Guide](../flask-app/FLASK_DEPLOYMENT_GUIDE.md)
- [Production Playbooks](../../playbooks/rop02/README.md)
- [k3d Documentation](https://k3d.io/)
- [K3s Documentation](https://k3s.io/)

---

**Happy Coding!** 🚀 Your local development environment now perfectly mirrors production. 