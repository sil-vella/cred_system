from core.modules.base_module import BaseModule
from tools.logger.custom_logging import custom_log
from flask import jsonify
from typing import Dict, Any


class WalletModule(BaseModule):
    def __init__(self, app_manager=None):
        """Initialize the WalletModule."""
        super().__init__(app_manager)
        self.dependencies = ["connection_api", "user_management"]
        custom_log("WalletModule created")

    def initialize(self, app_manager):
        """Initialize the WalletModule with AppManager."""
        self.app_manager = app_manager
        self.app = app_manager.flask_app
        self.register_routes()
        self._initialized = True
        custom_log("WalletModule initialized")

    def register_routes(self):
        """Register wallet-related routes."""
        self._register_route_helper("/wallet/info", self.wallet_info, methods=["GET"])
        custom_log(f"WalletModule registered {len(self.registered_routes)} routes")

    def wallet_info(self):
        """Get wallet module information."""
        return jsonify({
            "module": "wallet",
            "status": "operational",
            "message": "Wallet module is running in simplified mode"
        })

    def health_check(self) -> Dict[str, Any]:
        """Perform health check for WalletModule."""
        health_status = super().health_check()
        health_status['dependencies'] = self.dependencies
        health_status['details'] = {'simplified_mode': True}
        return health_status 