# Flask Application Deployment Guide
## Docker + Kubernetes + Volume Mounts Development System

This document provides a comprehensive overview of the Flask application deployment system we built, featuring a custom Docker image with live volume mounts for optimal development experience.

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        LOCAL DEVELOPMENT                        │
├─────────────────────────────────────────────────────────────────┤
│  Local Machine: /Users/sil/.../python_base_03/                 │
│  ├── app.py                                                     │
│  ├── core/                                                      │
│  ├── plugins/                                                   │
│  ├── tools/                                                     │
│  ├── utils/                                                     │
│  └── static/                                                    │
└─────────────────────────────────────────────────────────────────┘
                                │ scp
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                         VPS HOST LAYER                          │
├─────────────────────────────────────────────────────────────────┤
│  VPS: /home/rop02_user/python_base_03/                         │
│  ├── app.py                                                     │
│  ├── core/                                                      │
│  ├── plugins/                                                   │
│  ├── tools/                                                     │
│  ├── utils/                                                     │
│  ├── static/                                                    │
│  └── Dockerfile                                                 │
└─────────────────────────────────────────────────────────────────┘
                                │ hostPath volumes
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    KUBERNETES CLUSTER LAYER                     │
├─────────────────────────────────────────────────────────────────┤
│  K3s Cluster (10.0.0.3)                                        │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ flask-app namespace                                     │    │
│  │ ├── flask-app pod (custom Docker image)                │    │
│  │ │   ├── /app/core → mounted from host                  │    │
│  │ │   ├── /app/plugins → mounted from host               │    │
│  │ │   ├── /app/tools → mounted from host                 │    │
│  │ │   ├── /app/utils → mounted from host                 │    │
│  │ │   ├── /app/static → mounted from host                │    │
│  │ │   └── /app/app.py → mounted from host                │    │
│  │ ├── redis-master pod                                   │    │
│  │ ├── mongodb pod                                        │    │
│  │ └── vault-proxy pod                                    │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📦 Docker Image Strategy

### Custom Docker Image: `flask-credit-system:latest`

**Base Image**: `python:3.9-slim`

**Key Features**:
- ⚡ **Pre-installed dependencies** (requirements.txt + hvac)
- 🔒 **Security hardened** (non-root user, minimal attack surface)
- 🏥 **Health checks** built-in
- 📦 **Optimized layers** for faster builds

**Dockerfile Location**: `/home/rop02_user/python_base_03/Dockerfile`

```dockerfile
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements file first (for better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install hvac

# Copy application code (excluding unnecessary directories)
COPY app.py .
COPY __init__.py .
COPY core/ ./core/
COPY utils/ ./utils/
COPY plugins/ ./plugins/
COPY tools/ ./tools/

# Set environment variables
ENV PYTHONPATH="/app:$PYTHONPATH"
ENV FLASK_HOST="0.0.0.0"
ENV FLASK_PORT="5001"

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 5001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5001/health || exit 1

# Start Flask application
CMD ["python", "app.py"]
```

---

## 🔧 Volume Mount Configuration

### Development Volume Mounts

The deployment uses **hostPath volumes** to mount live code from the VPS host into the container:

| Container Path | Host Path | Purpose |
|---------------|-----------|---------|
| `/app/core` | `/home/rop02_user/python_base_03/core` | Core application logic |
| `/app/plugins` | `/home/rop02_user/python_base_03/plugins` | Plugin system |
| `/app/tools` | `/home/rop02_user/python_base_03/tools` | Utility tools |
| `/app/utils` | `/home/rop02_user/python_base_03/utils` | Helper utilities |
| `/app/static` | `/home/rop02_user/python_base_03/static` | Static assets |
| `/app/app.py` | `/home/rop02_user/python_base_03/app.py` | Main Flask application |

### Benefits of Volume Mounts

- 🔄 **Live code updates** - Changes reflected immediately
- ⚡ **No container rebuilds** required for code changes
- 🚀 **Fast development cycle** - Edit → Copy → Test
- 🐳 **Production-ready base** - Uses optimized Docker image

---

## 🎯 Kubernetes Deployment

### Namespace: `flask-app`

**Components Deployed**:

1. **Flask Application**
   - **Deployment**: `flask-app`
   - **Service**: `flask-app` (ClusterIP, port 80 → 5001)
   - **Ingress**: `flask-app-ingress` (host: flask-app.local)

2. **Supporting Infrastructure**
   - **Redis**: `redis-master` (simple deployment, no persistence)
   - **MongoDB**: `mongodb` (simple deployment with auth)
   - **Vault Proxy**: `vault-proxy` (forwards to 10.0.0.1:8200)

### Flask Deployment Configuration

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: flask-app
  namespace: flask-app
spec:
  replicas: 1
  selector:
    matchLabels:
      app: flask-app
  template:
    metadata:
      labels:
        app: flask-app
    spec:
      serviceAccountName: flask-app-sa
      containers:
      - name: flask-app
        image: flask-credit-system:latest
        imagePullPolicy: Never  # Use local image
        ports:
        - containerPort: 5001
        env:
        - name: FLASK_ENV
          value: "development"
        - name: FLASK_DEBUG
          value: "True"
        - name: MONGODB_SERVICE_NAME
          value: "mongodb"
        - name: REDIS_HOST
          value: "redis-master.flask-app.svc.cluster.local"
        # ... more env vars
        volumeMounts:
        - name: core-volume
          mountPath: /app/core
        - name: plugins-volume
          mountPath: /app/plugins
        # ... more volume mounts
        livenessProbe:
          httpGet:
            path: /health
            port: 5001
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 5001
          initialDelaySeconds: 10
          periodSeconds: 5
      volumes:
      - name: core-volume
        hostPath:
          path: /home/rop02_user/python_base_03/core
          type: Directory
      # ... more volumes
```

---

## 🚀 Deployment Process

### Automated Deployment via Ansible

**Playbook**: `playbooks/rop02/07_deploy_flask_docker.yml`

**Process Flow**:

1. **Clean up old deployments**
   ```bash
   kubectl delete deployment sample-flask-app -n flask-app --ignore-not-found=true
   ```

2. **Import Docker image to K3s**
   ```bash
   sudo docker save flask-credit-system:latest -o /tmp/flask-app-image.tar
   sudo k3s ctr images import /tmp/flask-app-image.tar
   ```

3. **Create Kubernetes resources**
   - Flask deployment with volume mounts
   - Service (ClusterIP)
   - Ingress (Traefik)

4. **Wait for readiness**
   ```bash
   kubectl rollout status deployment/flask-app -n flask-app --timeout=300s
   kubectl wait --for=condition=ready pod -l app=flask-app -n flask-app --timeout=300s
   ```

5. **Health check validation**
   ```bash
   kubectl port-forward -n flask-app svc/flask-app 8080:80
   curl -s http://localhost:8080/health
   ```

### Quick Update Process

**Playbook**: `playbooks/rop02/08_update_flask_docker.yml`

- Rolling deployment with zero downtime
- Uses existing Docker image
- Updates only deployment configuration

---

## 🔄 Development Workflow

### For Code Changes (No K8s Redeployment)

```bash
# 1. Edit files locally
vim python_base_03/core/managers/some_manager.py

# 2. Copy to VPS
scp python_base_03/core/managers/some_manager.py rop02:/home/rop02_user/python_base_03/core/managers/

# 3. Changes are immediately live in the pod!
# No restart needed - Flask app reads from mounted volumes
```

### For Configuration Changes (Requires Redeployment)

```bash
# Edit environment variables, resources, etc. in playbook
vim playbooks/rop02/07_deploy_flask_docker.yml

# Redeploy
cd playbooks/rop02
ansible-playbook -i inventory.ini 07_deploy_flask_docker.yml -e vm_name=rop02
```

### For Docker Image Changes (Rare)

```bash
# 1. Update Dockerfile or requirements.txt
# 2. Copy to VPS
scp python_base_03/Dockerfile python_base_03/requirements.txt rop02:/home/rop02_user/python_base_03/

# 3. Rebuild image on VPS
ssh rop02 "cd /home/rop02_user/python_base_03 && sudo docker build -t flask-credit-system:latest ."

# 4. Import to K3s
ssh rop02 "sudo docker save flask-credit-system:latest -o /tmp/flask-app-image.tar && sudo k3s ctr images import /tmp/flask-app-image.tar"

# 5. Restart deployment
ssh rop02 "kubectl rollout restart deployment/flask-app -n flask-app"
```

---

## 🏥 Health Monitoring

### Health Check Endpoint

**URL**: `http://flask-app:5001/health`

**Response (Healthy)**:
```json
{
  "status": "healthy"
}
```

**Health Check Logic**:
1. ✅ App manager initialization
2. ✅ Database connection (MongoDB)
3. ✅ Redis connection

### Kubernetes Health Checks

**Liveness Probe**:
- Path: `/health`
- Initial delay: 30s
- Period: 10s
- Failure threshold: 3

**Readiness Probe**:
- Path: `/health`
- Initial delay: 10s
- Period: 5s
- Failure threshold: 3

---

## 🔌 Infrastructure Components

### MongoDB Configuration

**Connection Details**:
- Host: `mongodb.flask-app.svc.cluster.local:27017`
- Database: `credit_system`
- Auth: `credit_system_user` / `credit_system_password`
- Auth Source: `admin`

**Connection String**:
```
mongodb://credit_system_user:credit_system_password@mongodb:27017/credit_system?authSource=admin
```

### Redis Configuration

**Connection Details**:
- Host: `redis-master.flask-app.svc.cluster.local:6379`
- Database: `0`
- No authentication

### Vault Integration

**Proxy Service**: `vault-proxy.flask-app.svc.cluster.local:8200`
- Forwards to Vault server at `10.0.0.1:8200` via WireGuard tunnel
- Uses AppRole authentication
- Credentials stored in K8s secret: `vault-approle-creds`

---

## 🧪 Testing & Validation

### Basic Connectivity Tests

```bash
# Test Flask app health
kubectl exec -n flask-app deployment/flask-app -- curl -s http://localhost:5001/health

# Test main endpoint
kubectl exec -n flask-app deployment/flask-app -- curl -s http://localhost:5001/

# Test external access
curl -H 'Host: flask-app.local' http://10.0.0.3/
```

### Infrastructure Tests

```bash
# Test Redis connectivity
kubectl exec -n flask-app deployment/flask-app -- python3 -c "
import socket
socket.create_connection(('redis-master', 6379), timeout=5)
print('Redis: Connected successfully')
"

# Test MongoDB connectivity
kubectl exec -n flask-app deployment/flask-app -- python3 -c "
import socket
socket.create_connection(('mongodb', 27017), timeout=5)
print('MongoDB: Connected successfully')
"

# Test Vault proxy
kubectl exec -n flask-app deployment/vault-proxy -- wget -qO- http://10.0.0.1:8200/v1/sys/health
```

### Performance Validation

**Startup Time**: ~30 seconds (vs 5-10 minutes with ConfigMap approach)

**Metrics**:
- Image size: ~451MB
- Memory usage: 256Mi request, 512Mi limit
- CPU usage: 250m request, 500m limit

---

## 🛠️ Troubleshooting

### Common Issues

**Pod stuck in `CreateContainerConfigError`**:
- Check volume mount paths exist on host
- Verify file permissions
- Check hostPath type (File vs Directory)

**Health checks failing (503 errors)**:
- Check AppManager initialization
- Verify database connections
- Check Redis connectivity

**Volume mounts not working**:
- Verify files exist on VPS host
- Check mount paths in deployment
- Restart deployment: `kubectl rollout restart deployment/flask-app -n flask-app`

### Debug Commands

```bash
# Check pod status
kubectl get pods -n flask-app

# Check deployment logs
kubectl logs -n flask-app deployment/flask-app

# Check volume mounts
kubectl exec -n flask-app deployment/flask-app -- ls -la /app/

# Check environment variables
kubectl exec -n flask-app deployment/flask-app -- env | grep -E "(MONGO|REDIS|VAULT)"

# Check Docker image
sudo docker images | grep flask-credit-system
sudo k3s ctr images list | grep flask-credit-system
```

---

## 📈 Performance Benefits

### Before (ConfigMap Approach)
- ❌ **Startup time**: 5-10 minutes
- ❌ **Code changes**: Required ConfigMap updates + pod restarts
- ❌ **Dependencies**: Installed on every startup
- ❌ **Resource usage**: High CPU during dependency installation

### After (Docker + Volume Mounts)
- ✅ **Startup time**: ~30 seconds
- ✅ **Code changes**: Immediate (no restarts needed)
- ✅ **Dependencies**: Pre-installed in image
- ✅ **Resource usage**: Minimal - just Flask app startup

---

## 🚀 Future Enhancements

### Production Readiness
1. **Persistent storage** for MongoDB and Redis
2. **Horizontal Pod Autoscaling** based on CPU/memory
3. **Resource quotas** and limits per namespace
4. **Network policies** for security isolation
5. **Monitoring** with Prometheus/Grafana

### Development Improvements
1. **Hot reloading** for Flask development server
2. **Debugger integration** with IDE
3. **Automated testing** pipeline
4. **Code quality** checks (linting, formatting)

### Security Enhancements
1. **Pod Security Standards** enforcement
2. **Image vulnerability scanning**
3. **Secret rotation** automation
4. **RBAC** fine-tuning

---

## 📝 Key Files Reference

### Local Development
- `python_base_03/app.py` - Main Flask application
- `python_base_03/Dockerfile` - Docker image definition
- `python_base_03/requirements.txt` - Python dependencies

### Deployment Automation
- `playbooks/rop02/07_deploy_flask_docker.yml` - Main deployment playbook
- `playbooks/rop02/08_update_flask_docker.yml` - Quick update playbook
- `playbooks/rop02/setup_server.py` - Interactive deployment menu

### Infrastructure Setup
- `playbooks/rop02/04_setup_flask_namespace.yml` - Namespace and RBAC
- `playbooks/rop02/05_deploy_vault_proxy.yml` - Vault proxy setup
- `playbooks/rop02/06_setup_vault_approle_creds.yml` - Vault authentication

---

**This deployment system provides an optimal balance between development speed and production readiness, enabling rapid iteration while maintaining container-based deployment practices.** 🎉