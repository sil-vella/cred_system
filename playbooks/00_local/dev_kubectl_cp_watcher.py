import os
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time

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

class ChangeHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.is_directory:
            return
        rel_path = os.path.relpath(event.src_path, LOCAL_BASE)
        remote_path = os.path.join(REMOTE_BASE, rel_path)
        pod = get_pod_name()
        print(f"Detected change: {event.src_path} → {pod}:{remote_path}")
        subprocess.run([
            "kubectl", "cp", event.src_path, f"{NAMESPACE}/{pod}:{remote_path}"
        ])

    def on_created(self, event):
        self.on_modified(event)

if __name__ == "__main__":
    print(f"Watching for changes in {LOCAL_BASE} (namespace: {NAMESPACE})")
    event_handler = ChangeHandler()
    observer = Observer()
    observer.schedule(event_handler, path=LOCAL_BASE, recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join() 