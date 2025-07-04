from core.modules.base_module import BaseModule
from core.managers.database_manager import DatabaseManager
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
            self.db_manager = app_manager.get_db_manager(role="read_write")
        else:
            self.db_manager = DatabaseManager(role="read_write")
            
        custom_log("TransactionsModule created with database manager")

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
        custom_log(f"TransactionsModule registered {len(self.registered_routes)} routes")

    def transactions_info(self):
        """Get transactions module information."""
        return jsonify({
            "module": "transactions",
            "status": "operational", 
            "message": "Transactions module is running with direct database operations"
        })

    def buy_credits(self):
        """Purchase credits directly in database."""
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
            
            # Create transaction record directly in database
            transaction_data = {
                'user_id': user_id,
                'amount': amount,
                'currency': currency,
                'purchase_date': datetime.utcnow().isoformat(),
                'status': 'completed',
                'transaction_id': transaction_id,
                'payment_method': payment_method
            }
            
            result = self.db_manager.insert_one("credit_purchases", transaction_data)
            
            if result:
                transaction_data['_id'] = str(result.inserted_id)
                
                return jsonify({
                    'success': True,
                    'message': 'Credit purchase completed successfully',
                    'transaction_id': str(result.inserted_id),
                    'user_id': user_id,
                    'amount': amount,
                    'currency': currency,
                    'status': 'completed'
                }), 201
            
            return jsonify({'error': 'Failed to process credit purchase'}), 500
            
        except Exception as e:
            custom_log(f"Error processing credit purchase: {e}")
            return jsonify({'error': 'Failed to process credit purchase'}), 500

    def health_check(self) -> Dict[str, Any]:
        """Perform health check for TransactionsModule."""
        health_status = super().health_check()
        health_status['dependencies'] = self.dependencies
        health_status['details'] = {'simplified_mode': True}
        return health_status 