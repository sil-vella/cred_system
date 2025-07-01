# Local Development with minikube

This guide shows how to set up a local Kubernetes development environment using **minikube** that **exactly mirrors** your production VPS setup.

## 🎯 Why minikube?

- **Production-identical structure** - same namespaces, secrets, and RBAC
- **Reliable networking** - stable DNS resolution and service discovery
- **Easy image management** - simple image loading with `minikube image load`
- **Mature ecosystem** - battle-tested with excellent Docker Desktop integration
- **113 secret files** - exact same filesystem structure as production

---

## 📋 Prerequisites

### 1. Install Docker Desktop
```bash
# Remove conflicting Docker CLI (if installed via brew)
brew uninstall docker

# Install Docker Desktop
brew install --cask docker

# Start Docker Desktop from Applications or:
open /Applications/Docker.app

# Verify Docker is working
docker --version
# Should show: Docker version 27.x.x
```

### 2. Install minikube and kubectl
```bash
# Install minikube
brew install minikube

# Install kubectl (if not already installed)
brew install kubectl

# Verify installations
minikube version
kubectl version --client
```

---

## 🚀 Quick Start

### 1. Create Local minikube Cluster
```bash
# Start minikube with Docker driver
minikube start --driver=docker

# Verify cluster is running
kubectl get nodes
# Should show: minikube   Ready    control-plane   2m   v1.31.0

# Check cluster status
minikube status
```

### 2. Deploy Complete Environment
```bash
# Navigate to local playbooks directory
cd playbooks/00_local/

# Run the orchestrator script
python3 setup_local_dev.py

# Choose option 1: Complete setup (build image + all components)
# This will:
# 1. Build Flask Docker image
# 2. Load image into minikube
# 3. Create namespace with 113 secrets
# 4. Deploy MongoDB
# 5. Deploy Redis  
# 6. Deploy Flask application
# 7. Test deployment
```

---

## 🏗️ Architecture Overview

### Production-Identical Components
- **Namespace**: `flask-app` with proper RBAC
- **Secrets**: 113 files mounted from `../../secrets/` (exact production match)
- **MongoDB**: Bitnami chart with persistent storage (10Gi)
- **Redis**: Bitnami chart with persistent storage (5Gi)
- **Flask App**: Production-identical deployment with health checks

### Key Features
- **Vault Fallback**: App detects no Vault and uses Kubernetes secrets (just like production)
- **Service Discovery**: Proper DNS resolution between services
- **Security**: Non-root containers, RBAC, network policies
- **Monitoring**: Health checks, readiness probes, metrics endpoints

---

## 🔧 Development Workflow

### For Code Changes
```bash
# 1. Edit your Flask code locally
vim python_base_04_k8s/core/managers/some_manager.py

# 2. Rebuild and update
cd playbooks/00_local/
python3 setup_local_dev.py
# Choose option 8: Update Flask application
# This rebuilds image and redeploys
```

### Individual Component Management
```bash
cd playbooks/00_local/
python3 setup_local_dev.py

# Available options:
# 1. 🏗️  Complete setup (build image + all components)
# 2. 💾 Setup local persistent storage
# 3. 🏠 Setup Flask namespace and RBAC  
# 4. 📊 Deploy MongoDB with persistent storage
# 5. 🚀 Deploy Redis with persistent storage
# 6. 🐳 Build Flask Docker image only
# 7. 🐍 Deploy Flask application
# 8. 🔄 Update Flask application
# 9. 📈 Deploy full infrastructure stack
# 10. 🧪 Test deployment
```

---

## 🌐 Accessing Your Application

### Port Forwarding (Recommended)
```bash
# Forward Flask app port for direct access
kubectl port-forward -n flask-app svc/flask-app 8080:80

# Access your app
curl http://localhost:8080/health
# Returns: {"status": "healthy"}

curl http://localhost:8080/
# Your Flask application

# Or open in browser
open http://localhost:8080
```

### Via minikube Service
```bash
# Open Flask app in browser via minikube
minikube service flask-app -n flask-app

# Get service URL
minikube service flask-app -n flask-app --url
```

---

## 🔍 Monitoring and Debugging

### Check Application Status
```bash
# Check all components
kubectl get all -n flask-app

# Check pods specifically
kubectl get pods -n flask-app
# Should show:
# flask-app-xxx         1/1     Running
# mongodb-xxx           1/1     Running  
# redis-master-xxx      1/1     Running
```

### View Logs
```bash
# View Flask app logs (most common)
kubectl logs -f -n flask-app deployment/flask-app

# View logs from specific pod
kubectl logs -f -n flask-app <pod-name>

# View recent logs with tail
kubectl logs -n flask-app deployment/flask-app --tail=50

# View MongoDB logs
kubectl logs -n flask-app deployment/mongodb

# View Redis logs  
kubectl logs -n flask-app deployment/redis-master
```

### Debug Pod Issues
```bash
# Describe pod for detailed information
kubectl describe pod -n flask-app <pod-name>

# Execute commands in running Flask pod
kubectl exec -it -n flask-app deployment/flask-app -- /bin/bash

# Test connectivity from within pod
kubectl exec -n flask-app deployment/flask-app -- curl -s http://localhost:5001/health

# Check mounted secrets
kubectl exec -n flask-app deployment/flask-app -- ls -la /app/secrets/
# Should show 113 secret files
```

---

## 🧪 Testing Your Setup

### 1. Health Check
```bash
# Quick health test via orchestrator
cd playbooks/00_local/
python3 setup_local_dev.py
# Choose option 10: Test deployment

# Manual health check
kubectl port-forward -n flask-app svc/flask-app 8080:80 &
curl -s http://localhost:8080/health
# Should return: {"status": "healthy"}
```

### 2. Database Connectivity
```bash
# Test MongoDB connection
kubectl exec -n flask-app deployment/flask-app -- python3 -c "
import socket
socket.create_connection(('mongodb.flask-app.svc.cluster.local', 27017), timeout=5)
print('MongoDB: Connected successfully')
"

# Test Redis connection
kubectl exec -n flask-app deployment/flask-app -- python3 -c "
import socket  
socket.create_connection(('redis-master-master.flask-app.svc.cluster.local', 6379), timeout=5)
print('Redis: Connected successfully')
"
```

### 3. Secrets Verification
```bash
# Check secret count
kubectl get secret external -n flask-app -o jsonpath='{.data}' | jq '. | length'
# Should return: 113

# Check Flask app can access secrets
kubectl exec -n flask-app deployment/flask-app -- ls /app/secrets/ | wc -l
# Should return: 113
```

---

## 🔄 Cluster Management

### Start/Stop Cluster
```bash
# Stop minikube (preserves state)
minikube stop

# Start minikube
minikube start

# Delete cluster completely
minikube delete

# Recreate cluster
minikube start --driver=docker
```

### Reset Development Environment
```bash
# Complete reset
minikube delete
minikube start --driver=docker

# Redeploy everything
cd playbooks/00_local/
python3 setup_local_dev.py
# Choose option 1: Complete setup
```

---

## ⚡ Performance Tips

### Image Management
```bash
# List images in minikube
minikube image ls | grep flask

# Load local image into minikube (done automatically by orchestrator)
minikube image load flask-credit-system:latest

# Check image is available
minikube ssh docker images | grep flask
```

### Resource Monitoring
```bash
# Check resource usage
kubectl top pods -n flask-app
kubectl top nodes

# Check persistent volumes
kubectl get pv,pvc -n flask-app

# Check storage usage
kubectl exec -n flask-app deployment/mongodb -- df -h
```

---

## 🔧 Troubleshooting

### Common Issues

**Flask Pod ErrImageNeverPull:**
```bash
# Solution: Load image into minikube
minikube image load flask-credit-system:latest

# Check image is available
minikube image ls | grep flask

# Or rebuild via orchestrator (automatic loading)
python3 setup_local_dev.py  # Choose option 6: Build Flask image
```

**MongoDB/Redis Pod Pending:**
```bash
# Check persistent volume claims
kubectl get pvc -n flask-app

# Check storage class
kubectl get storageclass

# Should use 'standard' storage class in minikube
```

**Secrets Not Found:**
```bash
# Check secret exists
kubectl get secret external -n flask-app

# Check secret files count
kubectl get secret external -n flask-app -o jsonpath='{.data}' | jq '. | length'

# Recreate secrets
cd playbooks/00_local/
python3 setup_local_dev.py  # Choose option 3: Setup namespace
```

**Can't Access Application:**
```bash
# Check service endpoints
kubectl get endpoints -n flask-app flask-app

# Check port forwarding
kubectl port-forward -n flask-app svc/flask-app 8080:80 &
netstat -an | grep 8080

# Use minikube service
minikube service flask-app -n flask-app
```

### Log Analysis
```bash
# Flask app startup logs
kubectl logs -n flask-app deployment/flask-app --tail=20

# Look for key indicators:
# ✅ "MainPlugin initialized successfully"
# ✅ "Running on http://0.0.0.0:5001"  
# ✅ "GET /health HTTP/1.1" 200
# ⚠️  "VaultManager initialization failed" (expected - uses K8s secrets)
```

---

## 🎉 Benefits of This Setup

### ✅ Production Parity
- **Exact same secrets** - 113 files from local filesystem
- **Same deployment structure** - namespace, RBAC, services
- **Same Vault fallback** - K8s secrets when Vault unavailable
- **Same service discovery** - proper DNS resolution

### ⚡ Development Speed
- **One-command deployment** - orchestrator handles everything
- **Fast image updates** - automatic building and loading
- **Quick feedback loop** - rebuild and test in minutes
- **Easy debugging** - full kubectl access and logs

### 🔒 Security
- **Isolated environment** - doesn't affect production
- **Same security model** - non-root containers, RBAC
- **Local secrets** - no external secret management needed
- **Network isolation** - Kubernetes network policies

### 🧹 Clean Management
- **Orchestrated deployment** - consistent, repeatable setup
- **Easy cleanup** - `minikube delete` removes everything
- **Version control** - all config in Git
- **Documentation** - step-by-step reproducible process

---

## 📁 File Structure

```
app_dev_new_playbooks/
├── playbooks/00_local/           # Local development playbooks
│   ├── setup_local_dev.py        # 🚀 Main orchestrator script
│   ├── 03_deploy_mongodb_local.yml
│   ├── 04_deploy_redis_local.yml
│   ├── 05_setup_flask_namespace_local.yml
│   ├── 08_deploy_flask_docker_local.yml
│   └── 09_update_flask_docker_local.yml
├── python_base_04_k8s/               # Flask application
│   ├── Dockerfile               # Flask image definition
│   ├── app.py                   # Main Flask app
│   └── core/                    # Application core
└── secrets/                     # 113 secret files (local copy)
    ├── auth_secret.txt
    ├── database_config.txt
    └── ... (111 more files)
```

---

## 📚 Common Commands Reference

### Quick Start
```bash
# Start fresh environment
minikube start --driver=docker
cd playbooks/00_local/
python3 setup_local_dev.py  # Choose option 1

# Access app
kubectl port-forward -n flask-app svc/flask-app 8080:80 &
curl http://localhost:8080/health
```

### Development Loop
```bash
# Edit code
vim python_base_04_k8s/core/managers/some_manager.py

# Update deployment
python3 setup_local_dev.py  # Choose option 8

# Check logs
kubectl logs -f -n flask-app deployment/flask-app
```

### Debugging
```bash
# Check all components
kubectl get all -n flask-app

# Debug specific pod
kubectl describe pod -n flask-app <pod-name>
kubectl logs -n flask-app <pod-name>

# Access pod shell
kubectl exec -it -n flask-app deployment/flask-app -- /bin/bash
```

---

## 🔗 Related Documentation

- [Flask Deployment Guide](../flask-app/FLASK_DEPLOYMENT_GUIDE.md)
- [Production Playbooks](../../playbooks/rop02/README.md)
- [minikube Documentation](https://minikube.sigs.k8s.io/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)

---

## 🎯 Production Comparison

| Component | Production (VPS) | Local (minikube) | Status |
|-----------|------------------|------------------|---------|
| **K8s** | k3s v1.31.5 | minikube v1.31.0 | ✅ Compatible |
| **Secrets** | 113 files via Vault | 113 files via K8s | ✅ Identical |
| **MongoDB** | Bitnami chart | Bitnami chart | ✅ Same |
| **Redis** | Bitnami chart | Bitnami chart | ✅ Same |
| **Flask** | Production image | Same image | ✅ Identical |
| **Networking** | k3s networking | minikube networking | ✅ Compatible |
| **Storage** | local-path | standard | ✅ Working |
| **RBAC** | Production RBAC | Same RBAC | ✅ Identical |

---

**Happy Coding!** 🚀 Your local development environment now perfectly mirrors production with minikube reliability and the convenience of the Python orchestrator. 