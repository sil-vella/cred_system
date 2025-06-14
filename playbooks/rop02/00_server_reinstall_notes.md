after reinstall server image process:

to cleanup wireguard on local...

brew uninstall wireguard-tools
brew uninstall wireguard-go
brew install wireguard-tools
brew install wireguard-go

then run the 00_cleanup_local_wg.yml:
```bash
cd playbooks/vault_vps
ansible-playbook -K playbooks/vault_vps/wireguard/cleanup/00_cleanup_local_wg.yml
```
- When prompted, enter your sudo password
- This will:
  - Stop all existing WireGuard interfaces
  - Remove old WireGuard configuration files and directories
  - Create a new WireGuard directory
  - Generate new WireGuard keys
  - Create a new WireGuard configuration file
  - Generate a new public key (save this for later use)

then 

1. Initial SSH Setup
   - Use the vault_initial inventory group which is configured for root access
   - Run the SSH setup playbook with both SSH and sudo password prompts:
   ```bash
   cd playbooks/vault_vps
   ansible-playbook -i inventory.ini 00_setup_ssh.yml -k -K
   ```
   - When prompted:
     - Enter the root SSH password (for initial connection)
     - Enter the root sudo password (for privilege escalation)
   - This will:
     - Automatically handle host key management (remove old key and accept new one)
     - Create hcvlt user
     - Set up .ssh directory
     - Add your rop01_key.pub to authorized_keys
     - Configure sudo access for hcvlt

2. Verify Setup
   - After completion, you should be able to SSH as hcvlt user:
   ```bash
   ssh -i ~/.ssh/rop01_key hcvlt@66.179.210.11
   ```
   - No password should be required for subsequent SSH connections

3. Security Configuration
   - Run the security configuration playbook using the vault_public group:
   ```bash
   ansible-playbook -i inventory.ini 01_configure_security.yml
   ```
   - This will:
     - Install and configure fail2ban for intrusion prevention
     - Set up AppArmor security profiles
     - Install essential security packages
     - Configure system updates and time synchronization
     - Set up audit logging
     - Configure password policies
     - Install and configure additional security tools

4. K3s Setup
   - Run the K3s setup playbook using the vault_public group:
   ```bash
   ansible-playbook -i inventory.ini 02_setup_k3s.yml
   ```
   - This will:
     - Install K3s (lightweight Kubernetes)
     - Configure K3s service to start on boot
     - Set up .kube directory and configuration
     - Configure kubectl access for hcvlt user
     - Set up KUBECONFIG environment variable
     - Create kubectl command-line tool symlink

5. WireGuard Setup
   - Run the WireGuard setup playbook using the vault_public group:
   ```bash
   ansible-playbook -i inventory.ini 03_setup_wireguard.yml -K
   ```
   - When prompted, enter your sudo password
   - This will:
     - Install WireGuard and required packages
     - Generate server keys
     - Create WireGuard configuration
     - Enable IP forwarding
     - Start and enable WireGuard service
     - Create local directories for WireGuard configuration
     - Copy server public key to local WireGuard directory
   - After completion, you should be able to connect to the server via WireGuard using IP 10.0.0.1
   - The server's public key will be displayed in the output (save this for later use)

6. Update Local WireGuard Configuration
   - Run the local WireGuard update playbook:
   ```bash
   ansible-playbook -i inventory.ini 04_update_local_wg.yml -K
   ```
   - When prompted, enter your sudo password
   - This will:
     - Stop the existing WireGuard interface
     - Update the local WireGuard configuration with the server's public key
     - Start the WireGuard interface
     - Display the current WireGuard status
     - Remove old SSH host keys
   - After completion, verify the connection by checking the WireGuard status output
   - The interface should show as connected with the correct endpoint and allowed IPs

7. Configure Firewall
   - Run the firewall configuration playbook:
   ```bash
   ansible-playbook -i inventory.ini 05_setup_firewall.yml
   ```
   - This will:
     - Allow SSH access from both public IP and WireGuard network
     - Configure WireGuard traffic rules
     - Set up forwarding rules for WireGuard
     - Set default policies (DROP for incoming, ACCEPT for outgoing)
     - Save rules to persist across reboots
   - After completion, verify you can still:
     - SSH to the server via public IP
     - SSH to the server via WireGuard (10.0.0.1)
     - Connect to the server via WireGuard


