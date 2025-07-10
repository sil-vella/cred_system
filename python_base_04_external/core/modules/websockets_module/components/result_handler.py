from typing import Dict, Any, Optional
from tools.logger.custom_logging import custom_log

class ResultHandler:
    def __init__(self):
        self._results: Dict[str, Any] = {}

    def create_result(self, event: str, data: Any = None, error: str = None) -> Dict[str, Any]:
        """Create a standardized result object for WebSocket responses."""
        result = {
            "event": event,
            "timestamp": self._get_timestamp(),
            "success": error is None
        }
        
        if data is not None:
            result["data"] = data
            
        if error is not None:
            result["error"] = error
            
        return result

    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime
        return datetime.utcnow().isoformat()

    def log_result(self, result: Dict[str, Any]):
        """Log the result for debugging purposes."""
        if result.get("success"):
            custom_log(f"WebSocket result - Event: {result['event']}, Data: {result.get('data')}")
        else:
            custom_log(f"WebSocket error - Event: {result['event']}, Error: {result.get('error')}") 