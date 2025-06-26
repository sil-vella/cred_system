# Flask Server Setup Playbooks

This directory contains Ansible playbooks to set up a Flask application server (rop02) that communicates with the Vault server (rop01) through a secure WireGuard VPN tunnel using **AppRole authentication**.

## Architecture Overview

```
┌─────────────────┐    WireGuard    ┌─────────────────┐
│   Flask Server  │◄──────────────►│  Vault Server   │
│   (rop02)       │  10.0.0.3      │   (rop01)       │
│   10.0.0.3      │◄──────────────►│   10.0.0.1      │
└─────────────────┘                └─────────────────┘
        │                                    │
        │                                    │
        ▼                                    ▼
┌─────────────────┐                ┌─────────────────┐
│   K3s Cluster   │                │   K3s Cluster   │
│  Flask App      │                │   Vault Server  │
│  Vault Proxy    │                │   AppRole Auth  │
│  AppRole Creds  │                │   Secrets       │
└─────────────────┘                └─────────────────┘
```

## Cross-Cluster Authentication Flow

```
Flask App (rop02) → vault-proxy → WireGuard tunnel → Vault Server (rop01)
     ↓                   ↓              ↓                    ↓
AppRole creds     Forwards to      Secure tunnel      Validates AppRole
from K8s secret   10.0.0.1:8200    encrypted          Returns secrets
```

## Prerequisites

1. **Vault Server Setup**: The Vault server (rop01) must be fully configured with AppRole authentication enabled
2. **AppRole Credentials**: Run `12_configure_flask_vault_access.yml` on rop01 first to generate AppRole credentials
3. **WireGuard Configuration**: WireGuard VPN must be configured and running on rop02
4. **SSH Access**: SSH key-based access to the rop02 server
5. **Network Connectivity**: Direct network access to the rop02 server

## Automated Setup

Use the automation script for easy deployment:

```bash
cd playbooks/rop02
python3 setup_server.py
```

**Menu Options:**
1. Start from the very beginning (all steps)
2. Run: 01_configure_security.yml
3. Run: 03_setup_k3s.yml
4. Run: 04_setup_flask_namespace.yml
5. Run: 05_deploy_vault_proxy.yml
6. Run: 06_setup_vault_approle_creds.yml
7. Run: 07_deploy_sample_flask_app.yml

## Manual Playbook Execution Order

Run the playbooks in the following order:

### 1. Security Configuration
```bash
ansible-playbook -i inventory.ini 01_configure_security.yml -e vm_name=rop02
```
- Creates dedicated user (`rop02_user`)
- Configures SSH security
- Installs essential packages

### 2. Kubernetes Setup
```bash
ansible-playbook -i inventory.ini 03_setup_k3s.yml -e vm_name=rop02
```
- Installs K3s lightweight Kubernetes
- Configures kubectl access
- Sets up cluster networking

### 3. Flask Namespace Setup
```bash
ansible-playbook -i inventory.ini 04_setup_flask_namespace.yml -e vm_name=rop02
```
- Creates `flask-app` namespace
- Sets up service account for Flask application
- Configures RBAC permissions

### 4. Vault Proxy Deployment
```bash
ansible-playbook -i inventory.ini 05_deploy_vault_proxy.yml -e vm_name=rop02
```
- Deploys Vault proxy service
- Bridges Flask app to Vault server through WireGuard
- Tests proxy connectivity

### 5. AppRole Credentials Setup
```bash
ansible-playbook -i inventory.ini 06_setup_vault_approle_creds.yml -e vm_name=rop02
```
- Reads AppRole credentials from rop01 setup
- Creates Kubernetes secret with role_id and secret_id
- Tests Vault connectivity through proxy

### 6. Flask Application Deployment
```bash
ansible-playbook -i inventory.ini 07_deploy_sample_flask_app.yml -e vm_name=rop02
```
- Deploys Flask application with AppRole authentication
- Demonstrates Vault integration with secret retrieval
- Creates service and ingress

## Configuration Details

### WireGuard Configuration (Pre-configured)
- **Interface**: `wg0`
- **Address**: `10.0.0.3/24`
- **Peer**: Vault server at `10.0.0.1:51820`
- **Status**: Active and providing encrypted tunnel

### Kubernetes Configuration
- **Cluster**: K3s single-node
- **Node IP**: `10.0.0.3`
- **Namespace**: `flask-app`
- **Service Account**: `flask-app-sa`

### Vault Integration
- **Authentication Method**: AppRole (cross-cluster compatible)
- **Proxy Service**: `vault-proxy.flask-app.svc.cluster.local:8200`
- **AppRole**: `flask-app-approle`
- **Credentials**: Stored in K8s secret `vault-approle-creds`
- **Secret Path**: `secret/data/flask-app/*`
- **Direct Access**: `http://10.0.0.1:8200` (through WireGuard)

## Testing the Setup

### 1. Test WireGuard Connectivity
```bash
# On rop02 server
ping 10.0.0.1
curl http://10.0.0.1:8200/v1/sys/health
```

### 2. Test AppRole Authentication
```bash
# On rop02 server - get credentials and test
ROLE_ID=$(kubectl get secret vault-approle-creds -n flask-app -o jsonpath='{.data.role_id}' | base64 -d)
SECRET_ID=$(kubectl get secret vault-approle-creds -n flask-app -o jsonpath='{.data.secret_id}' | base64 -d)

# Authenticate and read secret
TOKEN=$(curl -s -X POST -d '{"role_id":"'$ROLE_ID'","secret_id":"'$SECRET_ID'"}' \
  http://10.0.0.1:8200/v1/auth/approle/login | \
  sed 's/.*"client_token":"\([^"]*\)".*/\1/')

curl -H "X-Vault-Token: $TOKEN" http://10.0.0.1:8200/v1/secret/data/flask-app/config
```

### 3. Test Flask Application
```bash
# Test directly from within the cluster
kubectl exec -n flask-app deployment/sample-flask-app -- curl -s http://localhost:5000/vault-status

# Expected response:
{
  "auth_method": "AppRole",
  "secret": {
    "api_key": "test123",
    "app_name": "flask-credit-system",
    "database_url": "postgresql://user:pass@db:5432/app"
  },
  "status": "connected"
}
```

### 4. Test via Port Forward (Optional)
```bash
# Port forward to Flask app
kubectl port-forward -n flask-app svc/sample-flask-app 8081:80

# Test endpoints
curl http://localhost:8081/health
curl http://localhost:8081/vault-status
curl http://localhost:8081/
```

## AppRole Credentials Management

### Generated on rop01:
```bash
# File location: playbooks/rop01/vault_creds/flask-approle-creds.txt
VAULT_ROLE_ID=hvs.CAESIxxxxx...
VAULT_SECRET_ID=hvs.AESBxxxxx...
```

### Used on rop02:
```bash
# Kubernetes secret: vault-approle-creds
kubectl get secret vault-approle-creds -n flask-app -o yaml
```

### Security Features:
- **Cross-cluster compatible** - No K8s API dependencies
- **Rotatable** - Secret IDs can be regenerated
- **Scoped access** - Limited to `secret/data/flask-app/*` paths
- **Encrypted transit** - All communication through WireGuard

## Troubleshooting

### WireGuard Issues
- Check interface: `wg show`
- Test connectivity: `ping 10.0.0.1`
- Verify config: `cat /etc/wireguard/wg0.conf`

### Vault Authentication Issues
```bash
# Check AppRole credentials
kubectl get secret vault-approle-creds -n flask-app -o yaml

# Test authentication manually
ROLE_ID=$(kubectl get secret vault-approle-creds -n flask-app -o jsonpath='{.data.role_id}' | base64 -d)
curl -X POST -d '{"role_id":"'$ROLE_ID'"}' http://10.0.0.1:8200/v1/auth/approle/role/flask-app-approle/role-id
```

### Flask Application Issues
```bash
# Check pod status
kubectl get pods -n flask-app

# Check Flask app logs
kubectl logs -n flask-app deployment/sample-flask-app

# Check vault-proxy logs  
kubectl logs -n flask-app deployment/vault-proxy
```

### Common Error Solutions

**"invalid role or secret ID"**
- Re-run `06_setup_vault_approle_creds.yml` to refresh credentials
- Verify AppRole exists on rop01: `vault read auth/approle/role/flask-app-approle`

**"permission denied"**
- Check secret path in Flask app code
- Verify policy allows access: `vault policy read flask-app-policy`

**Connection timeout**
- Verify WireGuard tunnel: `ping 10.0.0.1`
- Check vault-proxy service: `kubectl get svc -n flask-app`

## Security Notes

- **End-to-end encryption**: WireGuard tunnel secures all Vault communication
- **AppRole authentication**: Cluster-agnostic, rotatable credentials
- **Least privilege**: Policy restricts access to specific secret paths
- **Network isolation**: Network policies control internal cluster access
- **No persistent tokens**: Flask app re-authenticates as needed

## Production Considerations

1. **Secret Rotation**: Implement automated AppRole secret_id rotation
2. **High Availability**: Deploy multiple vault-proxy replicas
3. **Monitoring**: Add metrics for Vault authentication success/failure
4. **Backup**: Backup AppRole credentials securely
5. **Audit**: Enable Vault audit logging for compliance

## Next Steps

1. **Custom Flask Application**: Replace sample app with your production Flask app
2. **Database Integration**: Add PostgreSQL/MongoDB with Vault-managed credentials
3. **Monitoring**: Deploy Prometheus/Grafana for observability
4. **CI/CD Pipeline**: Automate deployments with secret rotation
5. **Load Balancing**: Add Traefik/nginx-ingress for external access
6. **Secret Management**: Implement automated credential rotation 