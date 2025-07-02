"""
Example usage patterns for the QueueManager

This file demonstrates how to use the queue manager for different types of operations.
"""

from core.managers.queue_manager import QueueManager, QueuePriority
from core.managers.database_manager import DatabaseManager
from datetime import datetime

def example_basic_usage():
    """Example of basic queue usage for database operations."""
    
    # Get queue manager from app manager
    queue_manager = QueueManager()
    
    # Example 1: Insert a user registration
    user_data = {
        'operation': 'insert',
        'collection': 'users',
        'data': {
            'user_id': 'user123',
            'email': 'user@example.com',
            'username': 'testuser',
            'credit_balance': 0,
            'registration_date': datetime.utcnow(),
            'status': 'active'
        }
    }
    
    task_id = queue_manager.enqueue(
        queue_name='default',
        task_type='user_registration',
        task_data=user_data,
        priority=QueuePriority.NORMAL
    )
    print(f"User registration queued with task ID: {task_id}")
    
    # Example 2: Update credit balance (high priority)
    credit_update_data = {
        'operation': 'update',
        'collection': 'users',
        'query': {'user_id': 'user123'},
        'update_data': {'credit_balance': 100}
    }
    
    task_id = queue_manager.enqueue(
        queue_name='high_priority',
        task_type='credit_update',
        task_data=credit_update_data,
        priority=QueuePriority.HIGH
    )
    print(f"Credit update queued with task ID: {task_id}")
    
    # Example 3: Insert credit purchase
    purchase_data = {
        'operation': 'insert',
        'collection': 'credit_purchases',
        'data': {
            'user_id': 'user123',
            'amount': 50,
            'currency': 'USD',
            'purchase_date': datetime.utcnow(),
            'status': 'completed',
            'transaction_id': 'txn_456',
            'payment_method': 'credit_card'
        }
    }
    
    task_id = queue_manager.enqueue(
        queue_name='default',
        task_type='credit_purchase',
        task_data=purchase_data,
        priority=QueuePriority.NORMAL
    )
    print(f"Credit purchase queued with task ID: {task_id}")

def example_custom_handler():
    """Example of using custom handlers for complex operations."""
    
    queue_manager = QueueManager()
    
    # Define a custom handler for complex credit calculations
    def credit_calculation_handler(data, db_manager):
        """Custom handler for credit score calculations."""
        try:
            user_id = data['user_id']
            
            # Get user's credit history
            purchases = db_manager.find_many('credit_purchases', {'user_id': user_id})
            usage = db_manager.find_many('credit_usage', {'user_id': user_id})
            
            # Calculate credit score
            total_purchased = sum(p['amount'] for p in purchases)
            total_used = sum(u['amount'] for u in usage)
            available_credit = total_purchased - total_used
            
            # Calculate score (simplified algorithm)
            credit_score = min(850, int(total_purchased / 100))
            if total_purchased > 0:
                utilization_rate = total_used / total_purchased
                if utilization_rate > 0.7:
                    credit_score = int(credit_score * 0.6)
                elif utilization_rate > 0.3:
                    credit_score = int(credit_score * 0.8)
            
            # Store calculation result
            calculation_data = {
                'user_id': user_id,
                'total_purchased': total_purchased,
                'total_used': total_used,
                'available_credit': available_credit,
                'credit_score': credit_score,
                'calculated_at': datetime.utcnow()
            }
            
            result = db_manager.insert('credit_calculations', calculation_data)
            return result is not None
            
        except Exception as e:
            print(f"Error in credit calculation: {e}")
            return False
    
    # Register the custom handler
    queue_manager.register_handler('credit_calculation', credit_calculation_handler)
    
    # Queue a credit calculation task
    calculation_data = {
        'user_id': 'user123'
    }
    
    task_id = queue_manager.enqueue(
        queue_name='high_priority',
        task_type='credit_calculation',
        task_data=calculation_data,
        priority=QueuePriority.HIGH
    )
    print(f"Credit calculation queued with task ID: {task_id}")

def example_delayed_tasks():
    """Example of queuing tasks with delays."""
    
    queue_manager = QueueManager()
    
    # Queue a task that will be processed after 5 minutes
    delayed_data = {
        'operation': 'insert',
        'collection': 'notifications',
        'data': {
            'user_id': 'user123',
            'type': 'reminder',
            'message': 'Your credit balance is running low',
            'sent_at': datetime.utcnow(),
            'status': 'pending'
        }
    }
    
    task_id = queue_manager.enqueue(
        queue_name='low_priority',
        task_type='notification',
        task_data=delayed_data,
        priority=QueuePriority.LOW,
        delay=300  # 5 minutes delay
    )
    print(f"Delayed notification queued with task ID: {task_id}")

def example_check_task_status():
    """Example of checking task status and queue statistics."""
    
    queue_manager = QueueManager()
    
    # Queue a task
    task_data = {
        'operation': 'find',
        'collection': 'users',
        'query': {'user_id': 'user123'}
    }
    
    task_id = queue_manager.enqueue(
        queue_name='default',
        task_type='user_lookup',
        task_data=task_data,
        priority=QueuePriority.NORMAL
    )
    
    # Check task status
    status = queue_manager.get_task_status(task_id)
    if status:
        print(f"Task {task_id} status: {status['status']}")
        print(f"Created at: {status['created_at']}")
        print(f"Attempts: {status['attempts']}")
    
    # Get queue statistics
    stats = queue_manager.get_queue_stats()
    for queue_name, queue_stats in stats.items():
        print(f"\nQueue: {queue_name}")
        for status, count in queue_stats.items():
            print(f"  {status}: {count}")

if __name__ == "__main__":
    print("Queue Manager Examples")
    print("=" * 50)
    
    print("\n1. Basic Usage:")
    example_basic_usage()
    
    print("\n2. Custom Handler:")
    example_custom_handler()
    
    print("\n3. Delayed Tasks:")
    example_delayed_tasks()
    
    print("\n4. Check Task Status:")
    example_check_task_status() 