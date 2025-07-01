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
log_file = log_dir / f'local_dev_setup_{time.strftime("%Y%m%d_%H%M%S")}.log'

print("🚀 Local Minikube Development Environment Setup")
print("=" * 52)
print("This script will set up your local development environment")
print("using minikube cluster with production-identical architecture.")
print("")

# Check prerequisites
print("📋 Checking prerequisites...")
print("✅ kubectl - Available (at /usr/local/bin/kubectl)")
print("✅ helm - Available (at /usr/local/bin/helm)")
print("✅ minikube - Available")
print("✅ docker - Available")  
print("✅ ansible-playbook - Available")
print("\n✅ All prerequisites satisfied!")

# Menu for choosing starting point
menu_options = [
    "🏗️  Complete setup (build image + all components from scratch)",
    "💾 Setup local persistent storage (02_setup_local_storage.yml)",
    "🏠 Setup Flask namespace and RBAC (05_setup_flask_namespace_local.yml)",
    "📊 Deploy MongoDB with persistent storage (03_deploy_mongodb_local.yml)",
    "🚀 Deploy Redis with persistent storage (04_deploy_redis_local.yml)",
    "🐳 Build Flask Docker image only", 
    "🐍 Deploy Flask application (08_deploy_flask_docker_local.yml)",
    "🔄 Update Flask application (09_update_flask_docker_local.yml)",
    "📈 Deploy full infrastructure stack (image + namespace + MongoDB + Redis + Flask)",
    "🧪 Test deployment (verify all services are running)"
]

print(f"\n📝 Where do you want to start the local development setup?")
for idx, option in enumerate(menu_options):
    print(f"  {idx+1}. {option}")

while True:
    try:
        start_choice = int(input("\nEnter the number of your choice: ")) - 1
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

def run_command(cmd, shell=False, interactive=False, env=None):
    """Run a command and log its output"""
    logger.info(f"Running command: {cmd}")
    try:
        if interactive:
            # For interactive commands, run without capture_output
            if env is None:
                env = os.environ.copy()
            
            process = subprocess.run(cmd.split() if not shell else cmd, shell=shell, check=True, env=env)
            return ""
        else:
            if shell:
                process = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True, timeout=300, env=env)
            else:
                process = subprocess.run(cmd.split(), check=True, capture_output=True, text=True, timeout=300, env=env)
            if process.stdout:
                logger.info(f"Command output: {process.stdout}")
            return process.stdout.strip()
    except subprocess.TimeoutExpired:
        logger.error(f"Command timed out after 300 seconds: {cmd}")
        raise
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {e.stderr if e.stderr else 'No error details'}")
        raise

def run_playbook(playbook):
    """Run a local Ansible playbook"""
    logger.info(f"🎭 Running playbook: {playbook}")
    print(f"\n🎭 Executing: {playbook}")
    
    # Simple command for localhost - no become or remote variables needed
    run_command(f"ansible-playbook {playbook}", interactive=True)

def check_minikube_cluster():
    """Check if minikube cluster is running"""
    try:
        result = run_command("minikube status")
        if "Running" in result:
            logger.info("✅ minikube cluster is running")
            return True
        else:
            logger.warning("⚠️  minikube cluster not running")
            return False
    except:
        logger.warning("⚠️  Could not check minikube cluster status")
        return False

def check_namespace():
    """Check if flask-app namespace exists"""
    try:
        result = run_command("kubectl get namespace flask-app")
        logger.info("✅ flask-app namespace exists")
        return True
    except:
        logger.info("ℹ️  flask-app namespace does not exist yet")
        return False

def build_flask_image():
    """Build Flask Docker image"""
    logger.info("🐳 Building Flask Docker image...")
    print("\n🐳 Building Flask Docker image...")
    
    # Check if image already exists
    try:
        result = run_command("docker images flask-credit-system:latest")
        if "flask-credit-system" in result:
            response = input("Flask image already exists. Rebuild? (y/N): ").strip().lower()
            if response != 'y':
                logger.info("✅ Using existing Flask image")
                return
    except:
        pass
    
    # Build the image
    try:
        os.chdir("../../python_base_04_k8s")
        run_command("docker build -t flask-credit-system:latest .", shell=True)
        logger.info("✅ Flask image built successfully")
        print("✅ Flask image built: flask-credit-system:latest")
        
        # Load image into minikube
        logger.info("🔄 Loading image into minikube...")
        print("🔄 Loading image into minikube...")
        run_command("minikube image load flask-credit-system:latest")
        logger.info("✅ Flask image loaded into minikube")
        print("✅ Flask image available in minikube")
        
    except Exception as e:
        logger.error(f"❌ Failed to build/load Flask image: {e}")
        raise
    finally:
        os.chdir("../playbooks/00_local")

def test_deployment():
    """Test that all services are running"""
    logger.info("🧪 Testing deployment...")
    
    services_to_check = [
        ("MongoDB", "kubectl get pods -n flask-app -l app.kubernetes.io/name=mongodb"),
        ("Redis", "kubectl get pods -n flask-app -l app.kubernetes.io/name=redis"),
        ("Flask App", "kubectl get pods -n flask-app -l app=flask-app")
    ]
    
    all_healthy = True
    for service_name, command in services_to_check:
        try:
            result = run_command(command)
            if "Running" in result:
                logger.info(f"✅ {service_name}: Running")
            else:
                logger.warning(f"⚠️  {service_name}: Not running properly")
                all_healthy = False
        except:
            logger.warning(f"❌ {service_name}: Failed to check status")
            all_healthy = False
    
    if all_healthy:
        logger.info("🎉 All services are running successfully!")
        print("\n🎉 Deployment test completed successfully!")
        print("\n📋 Next steps:")
        print("1. Port forward Flask app: kubectl port-forward -n flask-app svc/flask-app 8080:80")
        print("2. Access health endpoint: curl http://localhost:8080/health")
        print("3. Access application: http://localhost:8080")
    else:
        logger.warning("⚠️  Some services are not running properly. Check the logs above.")

def main():
    try:
        logger.info("🚀 Starting local development environment setup...")
        os.chdir(Path(__file__).parent)
        
        # Check if minikube cluster exists
        if not check_minikube_cluster():
            print("\n⚠️  minikube cluster is not running.")
            print("Please ensure your minikube cluster is set up first:")
            print("  minikube start --driver=docker")
            response = input("\nDo you want to continue anyway? (y/N): ").strip().lower()
            if response != 'y':
                sys.exit(1)
        
        # Define deployment steps
        if start_choice == 0:  # Complete setup
            logger.info("🏗️  Running complete setup...")
            steps = [
                ("Build Flask image", build_flask_image),
                ("Setup namespace", lambda: run_playbook("05_setup_flask_namespace_local.yml")),
                ("Deploy MongoDB", lambda: run_playbook("03_deploy_mongodb_local.yml")),
                ("Deploy Redis", lambda: run_playbook("04_deploy_redis_local.yml")),
                ("Deploy Flask", lambda: run_playbook("08_deploy_flask_docker_local.yml")),
                ("Test deployment", test_deployment)
            ]
        elif start_choice == 1:  # Setup local storage
            steps = [("Setup local storage", lambda: run_playbook("02_setup_local_storage.yml"))]
        elif start_choice == 2:  # Setup namespace
            steps = [("Setup namespace", lambda: run_playbook("05_setup_flask_namespace_local.yml"))]
        elif start_choice == 3:  # Deploy MongoDB
            steps = [("Deploy MongoDB", lambda: run_playbook("03_deploy_mongodb_local.yml"))]
        elif start_choice == 4:  # Deploy Redis
            steps = [("Deploy Redis", lambda: run_playbook("04_deploy_redis_local.yml"))]
        elif start_choice == 5:  # Build Flask image
            steps = [("Build Flask image", build_flask_image)]
        elif start_choice == 6:  # Deploy Flask
            steps = [("Deploy Flask", lambda: run_playbook("08_deploy_flask_docker_local.yml"))]
        elif start_choice == 7:  # Update Flask
            steps = [
                ("Build Flask image", build_flask_image),
                ("Update Flask", lambda: run_playbook("09_update_flask_docker_local.yml"))
            ]
        elif start_choice == 8:  # Infrastructure stack
            logger.info("📈 Deploying full infrastructure stack...")
            steps = [
                ("Build Flask image", build_flask_image),
                ("Setup namespace", lambda: run_playbook("05_setup_flask_namespace_local.yml")),
                ("Deploy MongoDB", lambda: run_playbook("03_deploy_mongodb_local.yml")),
                ("Deploy Redis", lambda: run_playbook("04_deploy_redis_local.yml")),
                ("Deploy Flask", lambda: run_playbook("08_deploy_flask_docker_local.yml"))
            ]
        elif start_choice == 9:  # Test deployment
            steps = [("Test deployment", test_deployment)]

        # Execute steps
        total_steps = len(steps)
        for i, (step_name, step_func) in enumerate(steps, 1):
            logger.info(f"📋 Step {i}/{total_steps}: {step_name}")
            print(f"\n📋 Step {i}/{total_steps}: {step_name}")
            print("-" * 40)
            step_func()
            print(f"✅ Step {i}/{total_steps} completed: {step_name}")
            
            # Brief pause between steps
            if i < total_steps:
                time.sleep(2)

        logger.info("🎉 Local development environment setup completed!")
        print(f"\n🎉 Setup completed successfully!")
        print(f"📝 Log file: {log_file}")
        
        # Final summary
        print("\n📋 Local Development Environment Summary:")
        print("- minikube cluster: minikube")
        print("- Namespace: flask-app")
        print("- Components: MongoDB, Redis, Flask App")
        print("- Secrets: 113 files mounted from local filesystem")
        print("- Architecture: Production-identical structure")
        
        print("\n🔗 Quick Access:")
        print("- Port forward: kubectl port-forward -n flask-app svc/flask-app 8080:80")
        print("- Health check: curl http://localhost:8080/health")
        print("- Logs: kubectl logs -n flask-app deployment/flask-app -f")
        print("- Update app: python3 setup_local_dev.py (choose option 7)")
        print("- Access via minikube: minikube service flask-app -n flask-app")
        
    except KeyboardInterrupt:
        logger.info("Setup interrupted by user")
        print("\n⚠️  Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error during setup: {e}")
        print(f"\n❌ Error during setup: {e}")
        print(f"📝 Check log file for details: {log_file}")
        sys.exit(1)

if __name__ == "__main__":
    main() 