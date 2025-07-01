from core.modules.base_module import BaseModule
from tools.logger.custom_logging import custom_log
from flask import jsonify
from typing import Dict, Any


class TransactionsModule(BaseModule):
    def __init__(self, app_manager=None):
        """Initialize the TransactionsModule."""
        super().__init__(app_manager)
        self.dependencies = ["connection_api", "user_management", "wallet"]
        custom_log("TransactionsModule created")

    def initialize(self, app):
        """Initialize the TransactionsModule with Flask app."""
        self.app = app
        self.register_routes()
        self._initialized = True
        custom_log("TransactionsModule initialized")

    def register_routes(self):
        """Register transaction-related routes."""
        self._register_route_helper("/transactions/info", self.transactions_info, methods=["GET"])
        custom_log(f"TransactionsModule registered {len(self.registered_routes)} routes")

    def transactions_info(self):
        """Get transactions module information."""
        return jsonify({
            "module": "transactions",
            "status": "operational", 
            "message": "Transactions module is running in simplified mode"
        })

    def health_check(self) -> Dict[str, Any]:
        """Perform health check for TransactionsModule."""
        health_status = super().health_check()
        health_status['dependencies'] = self.dependencies
        health_status['details'] = {'simplified_mode': True}
        return health_status 