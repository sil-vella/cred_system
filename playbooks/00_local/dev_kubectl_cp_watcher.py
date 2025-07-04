import os
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time
import shutil
import threading
import sys

# Set these to your environment
NAMESPACE = "flask-app"
LOCAL_BASE = os.path.abspath("../../python_base_04_k8s")
REMOTE_BASE = "/app"
LABEL_SELECTOR = "app=flask-app"


def get_pod_name():
    result = subprocess.run(
        [
            "kubectl",
            "get",
            "pods",
            "-n",
            NAMESPACE,
            "-l",
            LABEL_SELECTOR,
            "-o",
            "jsonpath={.items[0].metadata.name}"
        ],
        capture_output=True, text=True
    )
    return result.stdout.strip()

def clear_remote_directory(pod_name):
    """Clear the remote /app directory in the pod."""
    print(f"Clearing remote directory /app in pod {pod_name}...")
    try:
        # Execute command to remove all contents of /app directory
        result = subprocess.run([
            "kubectl", "exec", "-n", NAMESPACE, pod_name, "--", 
            "sh", "-c", "rm -rf /app/* /app/.[^.]* 2>/dev/null || true"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Remote directory cleared successfully")
        else:
            print(f"⚠️ Warning: {result.stderr}")
            
        # Also try to remove any remaining files that might be stuck
        subprocess.run([
            "kubectl", "exec", "-n", NAMESPACE, pod_name, "--", 
            "sh", "-c", "find /app -mindepth 1 -delete 2>/dev/null || true"
        ], capture_output=True, text=True)
        
    except Exception as e:
        print(f"❌ Error clearing remote directory: {e}")

def upload_entire_directory(pod_name):
    """Upload the entire LOCAL_BASE directory to the pod."""
    print(f"Uploading entire directory {LOCAL_BASE} to pod {pod_name}...")
    try:
        # Create a temporary tar file of the entire directory
        temp_tar = "/tmp/python_base_04_k8s.tar"
        
        # Create tar file with options to handle macOS extended attributes
        subprocess.run([
            "tar", "--exclude=*.DS_Store", "--exclude=__pycache__", "--exclude=*.pyc",
            "-cf", temp_tar, "-C", LOCAL_BASE, "."
        ], check=True)
        
        # Copy tar file to pod
        subprocess.run([
            "kubectl", "cp", temp_tar, f"{NAMESPACE}/{pod_name}:{temp_tar}"
        ], check=True)
        
        # Extract tar file in pod with force overwrite
        result = subprocess.run([
            "kubectl", "exec", "-n", NAMESPACE, pod_name, "--",
            "tar", "-xf", temp_tar, "-C", REMOTE_BASE, "--overwrite", "--ignore-command-error"
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"⚠️ Tar extraction warnings (continuing): {result.stderr}")
        
        # Clean up tar file in pod
        subprocess.run([
            "kubectl", "exec", "-n", NAMESPACE, pod_name, "--",
            "rm", "-f", temp_tar
        ], check=True)
        
        # Clean up local tar file
        os.remove(temp_tar)
        
        print("✅ Entire directory uploaded successfully")
        
    except Exception as e:
        print(f"❌ Error uploading directory with tar method: {e}")
        # Clean up temp file if it exists
        if os.path.exists(temp_tar):
            os.remove(temp_tar)
        
        # Fallback to individual file copying
        print("🔄 Trying fallback method with individual file copying...")
        upload_entire_directory_fallback(pod_name)

def upload_entire_directory_fallback(pod_name):
    """Fallback method: Upload directory using individual file copying."""
    print(f"Uploading directory using fallback method...")
    try:
        # Walk through the directory and copy files individually
        for root, dirs, files in os.walk(LOCAL_BASE):
            # Skip certain directories
            dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git', '.DS_Store']]
            
            for file in files:
                if file.endswith('.pyc') or file == '.DS_Store':
                    continue
                    
                local_file = os.path.join(root, file)
                rel_path = os.path.relpath(local_file, LOCAL_BASE)
                remote_path = os.path.join(REMOTE_BASE, rel_path)
                
                # Create remote directory if it doesn't exist
                remote_dir = os.path.dirname(remote_path)
                subprocess.run([
                    "kubectl", "exec", "-n", NAMESPACE, pod_name, "--",
                    "mkdir", "-p", remote_dir
                ], capture_output=True, text=True)
                
                # Copy the file
                try:
                    subprocess.run([
                        "kubectl", "cp", local_file, f"{NAMESPACE}/{pod_name}:{remote_path}"
                    ], check=True, capture_output=True, text=True)
                except subprocess.CalledProcessError as e:
                    print(f"⚠️ Warning: Could not copy {rel_path}: {e}")
                    continue
        
        print("✅ Directory uploaded successfully using fallback method")
        
    except Exception as e:
        print(f"❌ Error in fallback upload method: {e}")
        raise

def initialize_pod_sync():
    """Initialize pod synchronization by clearing and uploading entire directory."""
    print("🚀 Initializing pod synchronization...")
    
    # Get pod name
    pod_name = get_pod_name()
    if not pod_name:
        print("❌ No pod found matching the label selector")
        return False
    
    print(f"Found pod: {pod_name}")
    
    # Clear remote directory
    clear_remote_directory(pod_name)
    
    # Upload entire directory
    upload_entire_directory(pod_name)
    
    print("✅ Pod synchronization initialized successfully")
    return True

def wait_for_pod_ready(pod_name, max_wait=120):
    """Wait for pod to be ready and log status."""
    print(f"⏳ Waiting for pod {pod_name} to be ready (max {max_wait}s)...")
    
    start_time = time.time()
    while time.time() - start_time < max_wait:
        try:
            # Check pod status
            status_result = subprocess.run([
                "kubectl", "get", "pod", pod_name, "-n", NAMESPACE, "-o", "jsonpath={.status.phase}"
            ], capture_output=True, text=True)
            
            if status_result.returncode == 0:
                phase = status_result.stdout.strip()
                if phase == "Running":
                    # Check if pod is ready
                    ready_result = subprocess.run([
                        "kubectl", "get", "pod", pod_name, "-n", NAMESPACE, "-o", "jsonpath={.status.containerStatuses[0].ready}"
                    ], capture_output=True, text=True)
                    
                    if ready_result.returncode == 0 and ready_result.stdout.strip() == "true":
                        print(f"✅ Pod {pod_name} is ready and running!")
                        
                        # Log pod details
                        print("\n📊 Pod Status:")
                        subprocess.run([
                            "kubectl", "get", "pod", pod_name, "-n", NAMESPACE, "-o", "wide"
                        ])
                        
                        # Log recent pod logs
                        print("\n📋 Recent Pod Logs:")
                        subprocess.run([
                            "kubectl", "logs", pod_name, "-n", NAMESPACE, "--tail=10"
                        ])
                        
                        return True
                    else:
                        print(f"⏳ Pod {pod_name} is {phase} but not ready yet...")
                else:
                    print(f"⏳ Pod {pod_name} status: {phase}")
            else:
                print(f"⏳ Waiting for pod {pod_name} to appear...")
                
        except Exception as e:
            print(f"⚠️ Error checking pod status: {e}")
        
        time.sleep(2)
    
    print(f"❌ Timeout waiting for pod {pod_name} to be ready")
    return False

class ChangeHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.is_directory:
            return
        # Copy any file (Python or not) to pod, no restart
        rel_path = os.path.relpath(event.src_path, LOCAL_BASE)
        remote_path = os.path.join(REMOTE_BASE, rel_path)
        pod = get_pod_name()
        try:
            subprocess.run([
                "kubectl", "cp", event.src_path, f"{NAMESPACE}/{pod}:{remote_path}"
            ], check=True)
            print(f"✅ Copied {rel_path} to pod (no restart)")
        except subprocess.CalledProcessError as e:
            print(f"❌ Error copying file: {e}")

    def on_created(self, event):
        self.on_modified(event)

def restart_pod_and_wait():
    print("\n🔄 Restarting pod on user request...")
    restart_result = subprocess.run([
        "kubectl", "rollout", "restart", "deployment/flask-app", "-n", NAMESPACE
    ], capture_output=True, text=True)
    if restart_result.returncode == 0:
        print("✅ Pod restart initiated successfully")
        wait_result = subprocess.run([
            "kubectl", "rollout", "status", "deployment/flask-app", "-n", NAMESPACE
        ], capture_output=True, text=True)
        if wait_result.returncode == 0:
            print("✅ Deployment rollout completed")
            new_pod = get_pod_name()
            if new_pod:
                if wait_for_pod_ready(new_pod):
                    print("🎉 Pod is fully ready and running with updated code!")
                else:
                    print("⚠️ Pod restart completed but pod may not be fully ready")
            else:
                print("❌ Could not get new pod name")
        else:
            print("⚠️ Pod restart completed but status check failed")
    else:
        print(f"❌ Failed to restart pod: {restart_result.stderr}")

def input_thread():
    print("\nType 'restart' and press Enter to restart the pod and apply changes.")
    while True:
        try:
            user_input = input()
            if user_input.strip().lower() == 'restart':
                restart_pod_and_wait()
        except EOFError:
            break
        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    print(f"Watching for changes in {LOCAL_BASE} (namespace: {NAMESPACE})")
    if not initialize_pod_sync():
        print("❌ Failed to initialize pod synchronization. Exiting.")
        exit(1)
    event_handler = ChangeHandler()
    observer = Observer()
    observer.schedule(event_handler, path=LOCAL_BASE, recursive=True)
    observer.start()
    # Start input thread for restart command
    t = threading.Thread(target=input_thread, daemon=True)
    t.start()
    print("👀 File watcher started. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping file watcher...")
        observer.stop()
    observer.join()
    print("✅ File watcher stopped.") 