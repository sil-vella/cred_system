import json
import time
import uuid
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum
import threading
import logging
from core.managers.redis_manager import RedisManager
from core.managers.database_manager import DatabaseManager
from tools.logger.custom_logging import custom_log
from utils.config.config import Config

class QueuePriority(Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4

class QueueStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY = "retry"

class QueueManager:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(QueueManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not QueueManager._initialized:
            self.redis_manager = RedisManager()
            self.db_manager = DatabaseManager(role="read_write")
            self.logger = logging.getLogger(__name__)
            
            # Queue configuration
            self.queues = {
                'default': {'priority': QueuePriority.NORMAL, 'workers': 2},
                'high_priority': {'priority': QueuePriority.HIGH, 'workers': 3},
                'low_priority': {'priority': QueuePriority.LOW, 'workers': 1}
            }
            
            # Worker pool
            self.running = False
            self.workers = {}
            self.task_handlers = {}  # Store custom task handlers
            
            QueueManager._initialized = True
            custom_log("QueueManager initialized")

    def register_handler(self, task_type: str, handler: Callable):
        """Register a custom handler for a specific task type."""
        self.task_handlers[task_type] = handler
        custom_log(f"Registered handler for task type: {task_type}")

    def enqueue(self, queue_name: str, task_type: str, task_data: Dict[str, Any], 
                priority: QueuePriority = QueuePriority.NORMAL,
                delay: int = 0) -> str:
        """
        Add a task to the specified queue.
        
        Args:
            queue_name: Name of the queue
            task_type: Type of task (used for routing to handlers)
            task_data: Data for the task
            priority: Task priority
            delay: Delay in seconds before processing
            
        Returns:
            Task ID
        """
        if queue_name not in self.queues:
            raise ValueError(f"Unknown queue: {queue_name}")

        task_id = str(uuid.uuid4())
        task = {
            'id': task_id,
            'queue': queue_name,
            'type': task_type,
            'data': task_data,
            'priority': priority.value,
            'status': QueueStatus.PENDING.value,
            'created_at': datetime.utcnow().isoformat(),
            'attempts': 0,
            'max_attempts': 3,
            'delay': delay,
            'process_after': (datetime.utcnow() + timedelta(seconds=delay)).isoformat() if delay > 0 else None
        }

        # Store task in Redis
        task_key = f"queue:task:{task_id}"
        self.redis_manager.set(task_key, json.dumps(task), expire=86400)  # 24 hours
        custom_log(f"[ENQUEUE] Task {task_id} stored in Redis with key {task_key}")

        # Add to priority queue
        queue_key = f"queue:{queue_name}:{priority.name.lower()}"
        score = time.time() + (delay if delay > 0 else 0)
        self.redis_manager.zadd(queue_key, {task_id: score})
        custom_log(f"[ENQUEUE] Task {task_id} added to queue {queue_key} with score {score}")

        custom_log(f"Task {task_id} enqueued in {queue_name} with priority {priority.name}")
        return task_id

    def dequeue(self, queue_name: str, priority: QueuePriority = None) -> Optional[Dict[str, Any]]:
        """
        Get the next task from the queue.
        
        Args:
            queue_name: Name of the queue
            priority: Specific priority to check (None for all priorities)
            
        Returns:
            Task data or None if no tasks available
        """
        if priority:
            priorities = [priority]
        else:
            priorities = [QueuePriority.CRITICAL, QueuePriority.HIGH, 
                         QueuePriority.NORMAL, QueuePriority.LOW]

        for p in priorities:
            queue_key = f"queue:{queue_name}:{p.name.lower()}"
            
            # Get tasks that are ready to process
            now = time.time()
            ready_tasks = self.redis_manager.zrangebyscore(queue_key, 0, now, start=0, num=1)
            custom_log(f"[DEQUEUE] Checking queue {queue_key} at {now}, found: {ready_tasks}")
            
            if ready_tasks:
                task_id = ready_tasks[0]
                
                # Remove from queue
                self.redis_manager.zrem(queue_key, task_id)
                custom_log(f"[DEQUEUE] Removed task {task_id} from queue {queue_key}")
                
                # Get task data
                task_key = f"queue:task:{task_id}"
                task_data = self.redis_manager.get(task_key)
                custom_log(f"[DEQUEUE] Fetched task data for {task_id}: {task_data}")
                
                if task_data:
                    task = json.loads(task_data)
                    
                    # Update status to processing
                    task['status'] = QueueStatus.PROCESSING.value
                    task['processing_started'] = datetime.utcnow().isoformat()
                    self.redis_manager.set(task_key, json.dumps(task), expire=86400)
                    custom_log(f"[DEQUEUE] Task {task_id} marked as processing and updated in Redis")
                    
                    return task

        return None

    def mark_completed(self, task_id: str, result: Any = None) -> bool:
        """Mark a task as completed."""
        task_key = f"queue:task:{task_id}"
        task_data = self.redis_manager.get(task_key)
        
        if task_data:
            # Handle both string and dict types
            if isinstance(task_data, (str, bytes, bytearray)):
                task = json.loads(task_data)
            else:
                task = task_data
                
            task['status'] = QueueStatus.COMPLETED.value
            task['completed_at'] = datetime.utcnow().isoformat()
            task['result'] = result
            
            self.redis_manager.set(task_key, json.dumps(task), expire=3600)  # Keep for 1 hour
            custom_log(f"Task {task_id} marked as completed")
            return True
        
        return False

    def mark_failed(self, task_id: str, error: str = None, retry: bool = True) -> bool:
        """Mark a task as failed and optionally retry."""
        task_key = f"queue:task:{task_id}"
        task_data = self.redis_manager.get(task_key)
        
        if task_data:
            # Handle both string and dict types
            if isinstance(task_data, (str, bytes, bytearray)):
                task = json.loads(task_data)
            else:
                task = task_data
                
            task['attempts'] += 1
            task['last_error'] = error
            task['last_failed_at'] = datetime.utcnow().isoformat()
            
            if retry and task['attempts'] < task['max_attempts']:
                # Retry with exponential backoff
                delay = min(60 * (2 ** task['attempts']), 3600)  # Max 1 hour
                task['status'] = QueueStatus.RETRY.value
                task['process_after'] = (datetime.utcnow() + timedelta(seconds=delay)).isoformat()
                
                # Re-add to queue
                queue_key = f"queue:{task['queue']}:{QueuePriority(task['priority']).name.lower()}"
                score = time.time() + delay
                self.redis_manager.zadd(queue_key, {task_id: score})
                
                custom_log(f"Task {task_id} scheduled for retry in {delay} seconds (attempt {task['attempts']})")
            else:
                task['status'] = QueueStatus.FAILED.value
                custom_log(f"Task {task_id} marked as failed after {task['attempts']} attempts")
            
            self.redis_manager.set(task_key, json.dumps(task), expire=86400)
            return True
        
        return False

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a specific task."""
        task_key = f"queue:task:{task_id}"
        task_data = self.redis_manager.get(task_key)
        if not task_data:
            custom_log(f"Task {task_id} not found in Redis", level="ERROR")
            return None
        # Fix: handle both string and dict
        if isinstance(task_data, (str, bytes, bytearray)):
            try:
                return json.loads(task_data)
            except Exception as e:
                custom_log(f"Error decoding task {task_id}: {e}", level="ERROR")
                return None
        elif isinstance(task_data, dict):
            return task_data
        else:
            custom_log(f"Task {task_id} has unexpected type: {type(task_data)}", level="ERROR")
            return None

    def get_queue_stats(self, queue_name: str = None) -> Dict[str, Any]:
        """Get statistics for queues."""
        stats = {}
        
        if queue_name:
            queues_to_check = [queue_name] if queue_name in self.queues else []
        else:
            queues_to_check = self.queues.keys()

        for q_name in queues_to_check:
            queue_stats = {
                'pending': 0,
                'processing': 0,
                'completed': 0,
                'failed': 0,
                'retry': 0
            }
            
            # Count tasks by status
            for priority in QueuePriority:
                queue_key = f"queue:{q_name}:{priority.name.lower()}"
                queue_stats['pending'] += self.redis_manager.zcard(queue_key)
            
            # Count by status in task storage
            pattern = f"queue:task:*"
            all_tasks = self.redis_manager.keys(pattern)
            
            for task_key in all_tasks:
                task_data = self.redis_manager.get(task_key)
                if task_data:
                    task = json.loads(task_data)
                    if task.get('queue') == q_name:
                        status = task.get('status', 'unknown')
                        if status in queue_stats:
                            queue_stats[status] += 1
            
            stats[q_name] = queue_stats

        return stats

    def start_workers(self):
        """Start background workers for all queues."""
        if self.running:
            custom_log("Queue workers already running.")
            return

        self.running = True
        custom_log("Starting queue workers...")

        for queue_name, config in self.queues.items():
            for i in range(config['workers']):
                worker_name = f"{queue_name}_worker_{i}"
                worker_thread = threading.Thread(
                    target=self._worker_loop,
                    args=(queue_name, worker_name),
                    daemon=True
                )
                worker_thread.start()
                self.workers[worker_name] = worker_thread
                custom_log(f"[WORKER] Started worker thread {worker_name} for queue {queue_name}")

        custom_log(f"Started {sum(config['workers'] for config in self.queues.values())} workers")

    def stop_workers(self):
        """Stop all background workers."""
        self.running = False
        custom_log("Stopping queue workers...")
        
        # Wait for workers to finish
        for worker_name, thread in self.workers.items():
            thread.join(timeout=5)
        
        self.workers.clear()
        custom_log("All workers stopped")

    def _worker_loop(self, queue_name: str, worker_name: str):
        """Main worker loop for processing tasks."""
        custom_log(f"Worker {worker_name} started for queue {queue_name}")
        
        while self.running:
            try:
                # Get next task
                task = self.dequeue(queue_name)
                
                if task:
                    custom_log(f"Worker {worker_name} processing task {task['id']}")
                    
                    # Process task using registered handler or default handler
                    success = self._process_task(task)
                    
                    if success:
                        self.mark_completed(task['id'])
                    else:
                        self.mark_failed(task['id'], "Task processing failed")
                else:
                    # No tasks available, sleep briefly
                    time.sleep(1)
                    
            except Exception as e:
                custom_log(f"Worker {worker_name} error: {str(e)}")
                time.sleep(5)  # Wait before retrying

    def _process_task(self, task: Dict[str, Any]) -> bool:
        """Process a task using registered handler or default database operation."""
        try:
            task_type = task.get('type')
            task_data = task.get('data', {})
            
            # Check if there's a custom handler for this task type
            if task_type in self.task_handlers:
                handler = self.task_handlers[task_type]
                return handler(task_data, self.db_manager)
            
            # Default handler: perform database operation
            return self._default_task_handler(task_type, task_data)
                
        except Exception as e:
            custom_log(f"Error processing task {task['id']}: {str(e)}", level="ERROR")
            return False

    def _default_task_handler(self, task_type: str, task_data: Dict[str, Any]) -> bool:
        """Default task handler that performs basic database operations."""
        try:
            operation = task_data.get('operation')
            collection = task_data.get('collection')
            data = task_data.get('data', {})
            
            if not operation or not collection:
                custom_log(f"Missing operation or collection in task data")
                return False
            
            # Add timestamp if not present
            if 'timestamp' not in data:
                data['timestamp'] = datetime.utcnow()
            
            # Perform database operation based on task type
            if operation == 'insert':
                result = self.db_manager.insert(collection, data)
                return result is not None
                
            elif operation == 'update':
                query = task_data.get('query', {})
                update_data = task_data.get('update_data', {})
                result = self.db_manager.update(collection, query, update_data)
                return result > 0
                
            elif operation == 'delete':
                query = task_data.get('query', {})
                result = self.db_manager.delete(collection, query)
                return result > 0
                
            elif operation == 'find':
                query = task_data.get('query', {})
                result = self.db_manager.find(collection, query)
                # Store result in task data for later retrieval
                task_data['result'] = result
                return True
                
            else:
                custom_log(f"Unknown operation: {operation}")
                return False
                
        except Exception as e:
            custom_log(f"Error in default task handler: {str(e)}")
            return False

    def get_db_manager(self):
        """Get the database manager instance."""
        return self.db_manager

    def get_redis_manager(self):
        """Get the Redis manager instance."""
        return self.redis_manager # Test comment for live reload
