# Local Development Playbook Modifications

This guide shows how to adapt your production playbooks for local k3d development.

## 🎯 Playbook Compatibility Matrix

| Playbook | Local Compatible | Modifications Needed |
|----------|------------------|---------------------|
| `04_setup_flask_namespace.yml` | ✅ Yes | None - works as-is |
| `05_deploy_vault_proxy.yml` | ❌ No | Skip or mock |
| `06_setup_vault_approle_creds.yml` | ❌ No | Skip or mock |
| `07_deploy_flask_docker.yml` | ⚠️ Partial | Remove Vault dependencies |

---

## 🔧 Option 1: Skip Vault Components (Recommended)

### Modified Local Deployment Command
```bash
# Run only the compatible playbooks
ansible-playbook -i inventory.ini 04_setup_flask_namespace.yml \
  -e vm_name=local \
  --connection=local

# Skip 05 and 06 (Vault-related)

# Run modified version of 07
ansible-playbook -i inventory.ini 07_deploy_flask_docker_local.yml \
  -e vm_name=local \
  --connection=local
```

### Create `07_deploy_flask_docker_local.yml`
```yaml
---
- name: Deploy Flask Application (Local Development)
  hosts: localhost
  connection: local
  vars:
    flask_namespace: flask-app
    docker_image: "flask-credit-system:latest"
  tasks:
    - name: Import Docker image into k3d
      shell: |
        k3d image import {{ docker_image }} -c local-dev
      changed_when: true

    - name: Create Flask Application Deployment (No Vault)
      shell: |
        cat <<EOF | kubectl apply -f -
        apiVersion: apps/v1
        kind: Deployment
        metadata:
          name: flask-app
          namespace: {{ flask_namespace }}
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
                image: {{ docker_image }}
                imagePullPolicy: Never
                ports:
                - containerPort: 5001
                env:
                # Remove Vault-related env vars
                - name: FLASK_HOST
                  value: "0.0.0.0"
                - name: FLASK_PORT
                  value: "5001"
                - name: FLASK_ENV
                  value: "development"
                - name: FLASK_DEBUG
                  value: "True"
                - name: PYTHONPATH
                  value: "/app"
                # Local development secrets (not from Vault)
                - name: MONGODB_ROOT_PASSWORD
                  value: "local-dev-password"
                - name: JWT_SECRET_KEY
                  value: "local-dev-jwt-secret"
                - name: ENCRYPTION_KEY
                  value: "local-dev-encryption-key"
                # ... rest of config
        EOF
      changed_when: true
```

---

## 🔧 Option 2: Mock Vault Service

### Create Mock Vault Deployment
```yaml
# Add to your local deployment
- name: Create Mock Vault Service
  shell: |
    cat <<EOF | kubectl apply -f -
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: mock-vault
      namespace: {{ flask_namespace }}
    spec:
      replicas: 1
      selector:
        matchLabels:
          app: mock-vault
      template:
        metadata:
          labels:
            app: mock-vault
        spec:
          containers:
          - name: mock-vault
            image: nginx:alpine
            ports:
            - containerPort: 8200
            command:
            - /bin/sh
            - -c
            - |
              echo '{"status": "ok", "data": {"password": "local-dev-password"}}' > /usr/share/nginx/html/secret.json
              nginx -g 'daemon off;'
    ---
    apiVersion: v1
    kind: Service
    metadata:
      name: vault-proxy
      namespace: {{ flask_namespace }}
    spec:
      selector:
        app: mock-vault
      ports:
      - port: 8200
        targetPort: 8200
    EOF
  changed_when: true
```

---

## 🔧 Option 3: Local Vault Instance

### Run Vault in Development Mode
```bash
# Start Vault in dev mode (in a separate terminal)
docker run --cap-add=IPC_LOCK -d --name=local-vault \
  -p 8200:8200 \
  -e 'VAULT_DEV_ROOT_TOKEN_ID=local-dev-token' \
  vault:latest

# Configure local AppRole
export VAULT_ADDR='http://localhost:8200'
export VAULT_TOKEN='local-dev-token'

vault auth enable approle
vault policy write local-dev-policy - <<EOF
path "secret/data/flask-app/*" {
  capabilities = ["read"]
}
EOF

vault write auth/approle/role/local-dev-role \
  token_policies="local-dev-policy" \
  token_ttl=1h \
  token_max_ttl=4h

# Get credentials for local use
ROLE_ID=$(vault read -field=role_id auth/approle/role/local-dev-role/role-id)
SECRET_ID=$(vault write -field=secret_id -f auth/approle/role/local-dev-role/secret-id)

# Create local secrets
vault kv put secret/flask-app/config \
  mongodb_password="local-dev-password" \
  jwt_secret="local-dev-jwt-secret"
```

### Modified Playbook for Local Vault
```yaml
- name: Create local Vault credentials secret
  shell: |
    kubectl create secret generic vault-approle-creds \
      --from-literal=role_id="{{ local_role_id }}" \
      --from-literal=secret_id="{{ local_secret_id }}" \
      -n {{ flask_namespace }} \
      --dry-run=client -o yaml | kubectl apply -f -
  vars:
    local_role_id: "{{ lookup('env', 'LOCAL_VAULT_ROLE_ID') }}"
    local_secret_id: "{{ lookup('env', 'LOCAL_VAULT_SECRET_ID') }}"
```

---

## 🚀 Recommended Workflow

### For Pure Local Development (No Vault)
```bash
# 1. Create cluster
k3d cluster create local-dev --port "8080:80@loadbalancer"

# 2. Build and import image
cd python_base_03/
docker build -t flask-credit-system:latest .
k3d image import flask-credit-system:latest -c local-dev

# 3. Setup namespace
cd ../playbooks/rop02/
ansible-playbook -i inventory.ini 04_setup_flask_namespace.yml \
  -e vm_name=local --connection=local

# 4. Deploy Flask app (no Vault)
ansible-playbook -i inventory.ini 07_deploy_flask_docker_local.yml \
  -e vm_name=local --connection=local
```

### For Vault-Enabled Local Development
```bash
# 1. Start local Vault
docker run --cap-add=IPC_LOCK -d --name=local-vault \
  -p 8200:8200 -e 'VAULT_DEV_ROOT_TOKEN_ID=local-dev-token' vault:latest

# 2. Configure Vault (run setup script)
./setup-local-vault.sh

# 3. Deploy with Vault integration
export LOCAL_VAULT_ROLE_ID="hvs.CAESIxxxxx..."
export LOCAL_VAULT_SECRET_ID="hvs.AESBxxxxx..."
ansible-playbook -i inventory.ini 07_deploy_flask_docker_vault.yml \
  -e vm_name=local --connection=local
```

---

## 🔐 Security Best Practices

### ❌ Don't Do This:
```bash
# Using production AppRole locally (security risk)
kubectl create secret generic vault-approle-creds \
  --from-literal=role_id="PRODUCTION_ROLE_ID" \
  --from-literal=secret_id="PRODUCTION_SECRET_ID"
```

### ✅ Do This Instead:
```bash
# Separate credentials for each environment
# Production: hvs.CAESIprod... / hvs.AESBprod...
# Local:      hvs.CAESIlocal... / hvs.AESBlocal...
# Staging:    hvs.CAESIstage... / hvs.AESBstage...
```

---

## 📋 Environment-Specific Configuration

### Production
- **Vault**: Real Vault server at `10.0.0.1:8200`
- **AppRole**: Production credentials with limited access
- **Secrets**: Real production secrets
- **Network**: WireGuard VPN, network policies

### Local Development
- **Vault**: Mock service or local Vault in dev mode
- **AppRole**: Local-only credentials
- **Secrets**: Development/test values
- **Network**: Local k3d networking

### Benefits of Separation
- 🔒 **Security isolation** - Local compromise doesn't affect production
- 🧪 **Testing freedom** - Break things locally without consequences
- 📊 **Clear audit trails** - Distinguish local vs production access
- 🚀 **Faster development** - No network dependencies on production services

---

## 🎯 Summary

**Best Approach**: Use **Option 1 (Skip Vault)** for most local development, with hardcoded development secrets. Only use local Vault if you're specifically testing Vault integration features.

This gives you:
- ✅ Fast local development
- ✅ Production parity for core application logic
- ✅ Security isolation
- ✅ No production dependencies 