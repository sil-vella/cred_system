"""
Queue API Module

Provides API endpoints for queueing database operations and checking task status.
"""

from flask import Blueprint, request, jsonify
from core.managers.queue_manager import QueueManager, QueuePriority
from datetime import datetime
import logging

# Create blueprint
queue_api = Blueprint('queue_api', __name__, url_prefix='/api/queue')
logger = logging.getLogger(__name__)

@queue_api.route('/enqueue', methods=['POST'])
def enqueue_task():
    """Enqueue a database operation task."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Required fields
        required_fields = ['queue_name', 'task_type', 'task_data']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Optional fields with defaults
        queue_name = data['queue_name']
        task_type = data['task_type']
        task_data = data['task_data']
        priority = QueuePriority(data.get('priority', QueuePriority.NORMAL.value))
        delay = data.get('delay', 0)
        
        # Get queue manager
        queue_manager = QueueManager()
        
        # Enqueue the task
        task_id = queue_manager.enqueue(
            queue_name=queue_name,
            task_type=task_type,
            task_data=task_data,
            priority=priority,
            delay=delay
        )
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': f'Task queued successfully with ID: {task_id}'
        }), 200
        
    except Exception as e:
        logger.error(f"Error enqueueing task: {str(e)}")
        return jsonify({'error': f'Failed to enqueue task: {str(e)}'}), 500

@queue_api.route('/status/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """Get the status of a specific task."""
    try:
        queue_manager = QueueManager()
        status = queue_manager.get_task_status(task_id)
        
        if not status:
            return jsonify({'error': 'Task not found'}), 404
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'status': status
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting task status: {str(e)}")
        return jsonify({'error': f'Failed to get task status: {str(e)}'}), 500

@queue_api.route('/stats', methods=['GET'])
def get_queue_stats():
    """Get statistics for all queues."""
    try:
        queue_manager = QueueManager()
        stats = queue_manager.get_queue_stats()
        
        return jsonify({
            'success': True,
            'stats': stats
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting queue stats: {str(e)}")
        return jsonify({'error': f'Failed to get queue stats: {str(e)}'}), 500

@queue_api.route('/stats/<queue_name>', methods=['GET'])
def get_queue_stats_specific(queue_name):
    """Get statistics for a specific queue."""
    try:
        queue_manager = QueueManager()
        stats = queue_manager.get_queue_stats(queue_name)
        
        if queue_name not in stats:
            return jsonify({'error': 'Queue not found'}), 404
        
        return jsonify({
            'success': True,
            'queue_name': queue_name,
            'stats': stats[queue_name]
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting queue stats: {str(e)}")
        return jsonify({'error': f'Failed to get queue stats: {str(e)}'}), 500

@queue_api.route('/example/credit-purchase', methods=['POST'])
def example_credit_purchase():
    """Example endpoint for queuing a credit purchase."""
    try:
        data = request.get_json()
        
        if not data or 'user_id' not in data or 'amount' not in data:
            return jsonify({'error': 'Missing user_id or amount'}), 400
        
        # Create task data for credit purchase
        task_data = {
            'operation': 'insert',
            'collection': 'credit_purchases',
            'data': {
                'user_id': data['user_id'],
                'amount': data['amount'],
                'currency': data.get('currency', 'USD'),
                'purchase_date': datetime.utcnow().isoformat(),
                'status': 'completed',
                'transaction_id': data.get('transaction_id'),
                'payment_method': data.get('payment_method', 'unknown')
            }
        }
        
        # Get queue manager
        queue_manager = QueueManager()
        
        # Enqueue the task
        task_id = queue_manager.enqueue(
            queue_name='default',
            task_type='credit_purchase',
            task_data=task_data,
            priority=QueuePriority.NORMAL
        )
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': f'Credit purchase queued successfully with ID: {task_id}',
            'user_id': data['user_id'],
            'amount': data['amount']
        }), 200
        
    except Exception as e:
        logger.error(f"Error queuing credit purchase: {str(e)}")
        return jsonify({'error': f'Failed to queue credit purchase: {str(e)}'}), 500

@queue_api.route('/example/user-registration', methods=['POST'])
def example_user_registration():
    """Example endpoint for queuing a user registration."""
    try:
        data = request.get_json()
        
        if not data or 'user_id' not in data or 'email' not in data:
            return jsonify({'error': 'Missing user_id or email'}), 400
        
        # Create task data for user registration
        task_data = {
            'operation': 'insert',
            'collection': 'users',
            'data': {
                'user_id': data['user_id'],
                'email': data['email'],
                'username': data.get('username'),
                'credit_balance': 0,
                'registration_date': datetime.utcnow().isoformat(),
                'status': 'active'
            }
        }
        
        # Get queue manager
        queue_manager = QueueManager()
        
        # Enqueue the task
        task_id = queue_manager.enqueue(
            queue_name='default',
            task_type='user_registration',
            task_data=task_data,
            priority=QueuePriority.NORMAL
        )
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': f'User registration queued successfully with ID: {task_id}',
            'user_id': data['user_id'],
            'email': data['email']
        }), 200
        
    except Exception as e:
        logger.error(f"Error queuing user registration: {str(e)}")
        return jsonify({'error': f'Failed to queue user registration: {str(e)}'}), 500

@queue_api.route('/example/credit-update', methods=['POST'])
def example_credit_update():
    """Example endpoint for queuing a credit balance update."""
    try:
        data = request.get_json()
        
        if not data or 'user_id' not in data or 'new_balance' not in data:
            return jsonify({'error': 'Missing user_id or new_balance'}), 400
        
        # Create task data for credit update
        task_data = {
            'operation': 'update',
            'collection': 'users',
            'query': {'user_id': data['user_id']},
            'update_data': {'credit_balance': data['new_balance']}
        }
        
        # Get queue manager
        queue_manager = QueueManager()
        
        # Enqueue the task with high priority
        task_id = queue_manager.enqueue(
            queue_name='high_priority',
            task_type='credit_update',
            task_data=task_data,
            priority=QueuePriority.HIGH
        )
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': f'Credit update queued successfully with ID: {task_id}',
            'user_id': data['user_id'],
            'new_balance': data['new_balance']
        }), 200
        
    except Exception as e:
        logger.error(f"Error queuing credit update: {str(e)}")
        return jsonify({'error': f'Failed to queue credit update: {str(e)}'}), 500 