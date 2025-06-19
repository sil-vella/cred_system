#!/usr/bin/env python3

import os
import sys
import subprocess
import logging
import time
from pathlib import Path
import shutil
import json

# Configure logging
log_dir = Path(__file__).parent / 'logs'
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f'setup_{time.strftime("%Y%m%d_%H%M%S")}.log'

# Get VM name from user
vm_name = input("Please enter the VM name: ").strip()
if not vm_name:
    print("Error: VM name cannot be empty")
    sys.exit(1)

# Menu for choosing starting point
menu_options = [
    "Start from the very beginning (all steps)",
    "Multipass authentication",
    "SSH key check/generation",
    "Multipass instance setup",
    "Update values.json",
    "Run: 00_ssh_for_new_user.yml",
    "Run: 01_configure_security.yml",
    "Run: 02_setup_k3s.yml",
    "Run: 03_setup_and_config_wg.yml",
    "WireGuard setup",
    "VPN connection test",
    "Run: 05_setup_firewall.yml",
    "Run: 06_harden_firewall.yml",
    "Run: 07_vault_initial_setup.yml",
    "Run: 08_store_vault_keys.yml",
    "Run: 09_verify_prerequisites.yml",
    "Run: 10_setup_unseal_scripts.yml",
    "Run: 11_configure_vault_auth.yml",
    "Run: 12_configure_flask_vault_access.yml"
]

print("\nWhere do you want to start the setup?")
for idx, option in enumerate(menu_options):
    print(f"  {idx+1}. {option}")
while True:
    try:
        start_choice = int(input("Enter the number of your choice: ")) - 1
        if 0 <= start_choice < len(menu_options):
            break
        else:
            print("Invalid choice. Try again.")
    except ValueError:
        print("Please enter a valid number.")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def restart_multipass_daemon():
    """Restart the Multipass daemon on macOS"""
    logger.info("Restarting Multipass daemon...")
    try:
        subprocess.run([
            "sudo", "launchctl", "kickstart", "-k", "system/com.canonical.multipassd"
        ], check=True)
        logger.info("Multipass daemon restarted successfully.")
    except Exception as e:
        logger.error(f"Failed to restart Multipass daemon: {e}")
        raise

def check_multipass_auth():
    """Check and handle Multipass authentication, always recover and continue on error"""
    logger.info("Checking Multipass authentication...")
    try:
        subprocess.run(["multipass", "list"], check=True, capture_output=True, timeout=10)
        logger.info("Already authenticated with Multipass")
        return
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
        logger.warning(f"multipass list failed or timed out: {e}. Attempting to recover.")
        try:
            restart_multipass_daemon()
        except Exception as e2:
            logger.error(f"Failed to restart Multipass daemon: {e2}")
        # Always try to force kill and delete/purge the instance
        try:
            force_kill_vm(vm_name)
        except Exception as e3:
            logger.error(f"Failed to force kill VM: {e3}")
        try:
            run_command(f"multipass delete {vm_name} --purge")
        except Exception as e4:
            logger.warning(f"Failed to delete/purge instance (may not exist): {e4}")
        logger.info("Recovery steps complete. Continuing script.")
        return

def get_vm_ip():
    """Get the IP address of the VM"""
    ip_info = run_command(f"multipass info {vm_name} | grep IPv4", shell=True)
    return ip_info.split(':')[1].strip()

def get_sudo_password():
    """Get sudo password from user"""
    return input("Please enter your sudo password: ").strip()

def run_command(cmd, shell=False, interactive=False):
    """Run a command and log its output"""
    logger.info(f"Running command: {cmd}")
    try:
        if interactive:
            # For interactive commands, run without capture_output
            # Add BatchMode=yes to SSH commands to prevent passphrase prompts
            if 'ansible-playbook' in cmd:
                env = os.environ.copy()
                env['ANSIBLE_SSH_ARGS'] = '-o BatchMode=yes'
                process = subprocess.run(cmd.split() if not shell else cmd, shell=shell, check=True, env=env)
            else:
                process = subprocess.run(cmd.split() if not shell else cmd, shell=shell, check=True)
            return ""
        else:
            if shell:
                process = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True, timeout=180)
            else:
                process = subprocess.run(cmd.split(), check=True, capture_output=True, text=True, timeout=180)
            logger.info(f"Command output: {process.stdout}")
            return process.stdout.strip()
    except subprocess.TimeoutExpired:
        logger.error(f"Command timed out after 180 seconds: {cmd}")
        raise
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {e.stderr}")
        raise

def generate_ssh_keys():
    """Generate SSH keys without passphrase"""
    logger.info("Generating SSH keys...")
    ssh_dir = Path.home() / '.ssh'
    key_path = ssh_dir / f'{vm_name}_key'
    
    # Generate new key without passphrase
    run_command(f"ssh-keygen -t ed25519 -f {key_path} -N ''", shell=True)
    logger.info("SSH keys generated successfully")

def check_ssh_keys():
    """Check if required SSH keys exist and generate if needed"""
    logger.info("Checking SSH keys...")
    ssh_dir = Path.home() / '.ssh'
    key_path = ssh_dir / f'{vm_name}_key'
    
    if not key_path.exists() or not key_path.with_suffix('.pub').exists():
        logger.info(f"SSH keys not found at {key_path}, generating new keys...")
        generate_ssh_keys()
    else:
        logger.info("SSH keys found and verified")

def force_kill_vm(vm_name):
    """Force kill the QEMU process for the given VM name"""
    logger.info(f"Force killing QEMU process for VM '{vm_name}' if running...")
    try:
        result = subprocess.run([
            "ps", "aux"
        ], capture_output=True, text=True, check=True)
        for line in result.stdout.splitlines():
            if "qemu-system-x86_64" in line and vm_name in line:
                pid = int(line.split()[1])
                logger.info(f"Killing QEMU process {pid} for VM '{vm_name}'")
                # Use sudo to kill if not running as root
                if os.geteuid() != 0:
                    subprocess.run(["sudo", "kill", "-9", str(pid)], check=True)
                else:
                    os.kill(pid, 9)
                logger.info(f"Successfully killed QEMU process {pid}")
                return True
        logger.info(f"No QEMU process found for VM '{vm_name}'")
        return False
    except Exception as e:
        logger.error(f"Error while force killing VM: {e}")
        return False

def setup_multipass():
    """Set up Multipass instance"""
    logger.info("Setting up Multipass instance...")
    
    # Check if instance exists and remove it
    try:
        force_kill_vm(vm_name)
        run_command(f"multipass -vvv delete {vm_name} --purge")
    except subprocess.CalledProcessError:
        pass
    
    # Launch new instance with HyperKit
    run_command(f"multipass -vvv launch --name {vm_name} --memory 4G --disk 20G --cpus 2")
    
    # Get instance IP
    ip_address = get_vm_ip()
    logger.info(f"Instance IP: {ip_address}")
    
    # Copy SSH key to instance
    run_command(f"multipass -vvv transfer {Path.home() / '.ssh' / f'{vm_name}_key.pub'} {vm_name}:")
    
    # Set up SSH in instance - combine commands to ensure atomic operation
    setup_ssh_cmd = f"""
    sudo mkdir -p /home/ubuntu/.ssh && \
    sudo cat /home/ubuntu/{vm_name}_key.pub > /home/ubuntu/.ssh/authorized_keys && \
    sudo chown -R ubuntu:ubuntu /home/ubuntu/.ssh && \
    sudo chmod 700 /home/ubuntu/.ssh && \
    sudo chmod 600 /home/ubuntu/.ssh/authorized_keys && \
    sudo sed -i "s/^#\?PubkeyAuthentication.*/PubkeyAuthentication yes/" /etc/ssh/sshd_config && \
    sudo sed -i "s/^#\?PasswordAuthentication.*/PasswordAuthentication no/" /etc/ssh/sshd_config && \
    sudo systemctl restart ssh && \
    echo "=== Debug Info ===" && \
    ls -la /home/ubuntu/.ssh && \
    cat /home/ubuntu/.ssh/authorized_keys && \
    grep -i "PubkeyAuthentication" /etc/ssh/sshd_config && \
    grep -i "PasswordAuthentication" /etc/ssh/sshd_config
    """
    run_command(f"multipass exec {vm_name} -- bash -c '{setup_ssh_cmd}'", shell=True)
    
    # Start ssh-agent and add the key
    logger.info("Setting up ssh-agent...")
    run_command("eval $(ssh-agent -s)", shell=True)
    run_command(f"ssh-add {Path.home() / '.ssh' / f'{vm_name}_key'}", shell=True)
    
    # Test SSH connection directly
    logger.info("Testing SSH connection...")
    test_ssh_cmd = f"ssh -v -o StrictHostKeyChecking=no ubuntu@{ip_address} 'echo SSH connection successful'"
    run_command(test_ssh_cmd, shell=True)

def update_values_json():
    """Update values.json with new SSH key and IP"""
    logger.info("Updating values.json...")
    values_path = Path(__file__).parent.parent / '00utils' / 'values.json'
    
    # Get public key
    pub_key = run_command(f"cat {Path.home() / '.ssh/rop01_key.pub'}")
    
    # Get IP address
    ip_address = get_vm_ip()
    
    # Read and parse current values.json
    with open(values_path, 'r') as f:
        values = json.load(f)
    
    # Update SSH key and IP
    values['nodes']['rop01']['ssh_public_key'] = pub_key
    values['nodes']['rop01']['ip'] = ip_address
    
    # Write updated content
    with open(values_path, 'w') as f:
        json.dump(values, f, indent=4)

def run_playbook(playbook):
    sudo_password = get_sudo_password()
    logger.info(f"Running playbook: {playbook}")
    run_command(f"ansible-playbook -i inventory.ini {playbook} --ask-become-pass", interactive=True)

def setup_wireguard():
    """Set up WireGuard configuration"""
    logger.info("Setting up WireGuard...")
    
    # Get client public key
    client_pub_key = run_command("sudo cat /etc/wireguard/client_public.key")
    
    # Get VM IP
    vm_ip = get_vm_ip()
    
    # SSH into server and update WireGuard config
    wg_config = f"""[Interface]
Address = 10.0.0.1/24
ListenPort = 51820
PrivateKey = {run_command(f"ssh rop01_user@{vm_ip} -i {Path.home() / '.ssh' / f'{vm_name}_key'} 'sudo cat /etc/wireguard/server_private.key'", shell=True)}

[Peer]
PublicKey = {client_pub_key}
AllowedIPs = 10.0.0.2/32
"""
    ssh_cmd = f"ssh rop01_user@{vm_ip} -i {Path.home() / '.ssh' / f'{vm_name}_key'}"
    
    # First, ensure the config file exists and has proper format
    run_command(f"{ssh_cmd} 'sudo touch /etc/wireguard/wg0.conf'", shell=True)
    run_command(f"{ssh_cmd} 'sudo chmod 600 /etc/wireguard/wg0.conf'", shell=True)
    
    # Add the complete configuration
    run_command(f"{ssh_cmd} 'echo \"{wg_config}\" | sudo tee /etc/wireguard/wg0.conf'", shell=True)
    
    # Restart WireGuard
    run_command(f"{ssh_cmd} 'sudo wg-quick down wg0 || true'", shell=True)
    run_command(f"{ssh_cmd} 'sudo wg-quick up wg0'", shell=True)
    
    # Update local WireGuard config
    server_pub_key = run_command(f"{ssh_cmd} 'sudo cat /etc/wireguard/server_public.key'", shell=True)
    local_config = f"""[Interface]
PrivateKey = {run_command("sudo cat /etc/wireguard/client_private.key")}
Address = 10.0.0.2/24
DNS = 1.1.1.1

[Peer]
PublicKey = {server_pub_key}
Endpoint = {vm_ip}:51820
AllowedIPs = 10.0.0.0/24
PersistentKeepalive = 25
"""
    # Ensure local config file exists and has proper permissions
    run_command("sudo touch /etc/wireguard/wg0.conf", shell=True)
    run_command("sudo chmod 600 /etc/wireguard/wg0.conf", shell=True)
    
    # Update local config
    run_command(f"echo '{local_config}' | sudo tee /etc/wireguard/wg0.conf", shell=True)
    
    # Restart local WireGuard
    run_command("sudo wg-quick down wg0 || true", shell=True)
    run_command("sudo wg-quick up wg0", shell=True)

def test_vpn_connection():
    """Test VPN connection"""
    logger.info("Testing VPN connection...")
    
    # Remove old host key
    run_command("ssh-keygen -R 10.0.0.1")
    
    # Test SSH connection
    try:
        run_command(f"ssh {vm_name}_user@10.0.0.1 -i {Path.home() / '.ssh' / f'{vm_name}_key'} 'echo \"VPN connection successful\"'", shell=True)
        logger.info("VPN connection test successful!")
    except subprocess.CalledProcessError as e:
        logger.error("VPN connection test failed!")
        raise

def is_fatal_error(e):
    """Return True if the error is fatal, False if it is a known non-fatal error."""
    non_fatal_patterns = [
        "Vault is already initialized",
        "Could not find the requested service vault: host",
        "command terminated with exit code 2",
        # Add more patterns as needed
    ]
    msg = str(e)
    for pat in non_fatal_patterns:
        if pat in msg:
            return False
    return True

def main():
    try:
        logger.info("Starting server setup process...")
        os.chdir(Path(__file__).parent)
        # Step index mapping
        steps = [
            ("multipass_auth", check_multipass_auth),
            ("ssh_keys", check_ssh_keys),
            ("multipass_setup", setup_multipass),
            ("update_values_json", update_values_json),
            ("playbook_00", lambda: run_playbook("00_ssh_for_new_user.yml")),
            ("playbook_01", lambda: run_playbook("01_configure_security.yml")),
            ("playbook_02", lambda: run_playbook("02_setup_k3s.yml")),
            ("playbook_03", lambda: run_playbook("03_setup_and_config_wg.yml")),
            ("wireguard_setup", setup_wireguard),
            ("vpn_test", test_vpn_connection),
            ("playbook_05", lambda: run_playbook("05_setup_firewall.yml")),
            ("playbook_06", lambda: run_playbook("06_harden_firewall.yml")),
            ("playbook_07", lambda: run_playbook("07_vault_initial_setup.yml")),
            ("playbook_08", lambda: run_playbook("08_store_vault_keys.yml")),
            ("playbook_09", lambda: run_playbook("09_verify_prerequisites.yml")),
            ("playbook_10", lambda: run_playbook("10_setup_unseal_scripts.yml")),
            ("playbook_11", lambda: run_playbook("11_configure_vault_auth.yml")),
            ("playbook_12", lambda: run_playbook("12_configure_flask_vault_access.yml")),
        ]
        # Map menu choice to step index
        step_start_map = list(range(len(menu_options)))
        start_idx = step_start_map[start_choice]

        # If "Start from the very beginning", run all steps
        if start_idx == 0:
            run_range = range(len(steps))
        else:
            run_range = range(start_idx - 1, len(steps))

        # Run steps from the selected point
        for i in run_range:
            logger.info(f"Running step: {steps[i][0]}")
            try:
                steps[i][1]()
            except Exception as e:
                logger.error(f"Step failed: {str(e)}")
                if is_fatal_error(e):
                    logger.error("Fatal error encountered. Exiting.")
                    sys.exit(1)
                else:
                    logger.warning("Non-fatal error. Continuing to next step.")

        logger.info("Server setup completed successfully!")

    except Exception as e:
        logger.error(f"Setup failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 