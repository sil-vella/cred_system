from core.modules.base_module import BaseModule
from core.managers.queue_manager import QueueManager, QueuePriority
from tools.logger.custom_logging import custom_log
from flask import request, jsonify
from datetime import datetime
from typing import Dict, Any


class TransactionsModule(BaseModule):
    def __init__(self, app_manager=None):
        """Initialize the TransactionsModule."""
        super().__init__(app_manager)
        self.dependencies = ["connection_api", "user_management", "wallet"]
        
        # Use centralized managers from app_manager
        if app_manager:
            self.queue_manager = app_manager.get_queue_manager()
        else:
            self.queue_manager = QueueManager()
            
        custom_log("TransactionsModule created with queue manager")

    def initialize(self, app):
        """Initialize the TransactionsModule with Flask app."""
        self.app = app
        self.register_routes()
        self._initialized = True
        custom_log("TransactionsModule initialized")

    def register_routes(self):
        """Register transaction-related routes."""
        self._register_route_helper("/transactions/info", self.transactions_info, methods=["GET"])
        self._register_route_helper("/buy", self.buy_credits, methods=["POST"])
        self._register_route_helper("/transactions/status/<task_id>", self.get_transaction_status, methods=["GET"])
        custom_log(f"TransactionsModule registered {len(self.registered_routes)} routes")

    def transactions_info(self):
        """Get transactions module information."""
        return jsonify({
            "module": "transactions",
            "status": "operational", 
            "message": "Transactions module is running with queue system"
        })

    def buy_credits(self):
        """Purchase credits using queue system."""
        try:
            data = request.get_json()
            
            # Validate required fields
            required_fields = ['user_id', 'amount']
            for field in required_fields:
                if field not in data:
                    return jsonify({'error': f'Missing required field: {field}'}), 400
            
            user_id = data['user_id']
            amount = data['amount']
            currency = data.get('currency', 'USD')
            payment_method = data.get('payment_method', 'unknown')
            transaction_id = data.get('transaction_id')
            
            # Validate amount
            if amount <= 0:
                return jsonify({'error': 'Amount must be greater than 0'}), 400
            
            # Queue the credit purchase task
            task_data = {
                'operation': 'insert',
                'collection': 'credit_purchases',
                'data': {
                    'user_id': user_id,
                    'amount': amount,
                    'currency': currency,
                    'purchase_date': datetime.utcnow().isoformat(),
                    'status': 'pending',
                    'transaction_id': transaction_id,
                    'payment_method': payment_method
                }
            }
            
            task_id = self.queue_manager.enqueue(
                queue_name='high_priority',
                task_type='credit_purchase',
                task_data=task_data,
                priority=QueuePriority.HIGH
            )
            
            return jsonify({
                'success': True,
                'message': 'Credit purchase is being processed',
                'task_id': task_id,
                'user_id': user_id,
                'amount': amount,
                'currency': currency,
                'status': 'pending'
            }), 202  # 202 Accepted - request is being processed
            
        except Exception as e:
            custom_log(f"Error queuing credit purchase: {e}")
            return jsonify({'error': 'Failed to queue credit purchase'}), 500

    def get_transaction_status(self, task_id):
        """Get the status of a transaction task."""
        try:
            status = self.queue_manager.get_task_status(task_id)
            
            if not status:
                return jsonify({'error': 'Task not found'}), 404
            
            return jsonify({
                'success': True,
                'task_id': task_id,
                'status': status
            }), 200
            
        except Exception as e:
            custom_log(f"Error getting transaction status: {e}")
            return jsonify({'error': 'Failed to get transaction status'}), 500

    def health_check(self) -> Dict[str, Any]:
        """Perform health check for TransactionsModule."""
        health_status = super().health_check()
        health_status['dependencies'] = self.dependencies
        health_status['details'] = {'simplified_mode': True}
        return health_status 