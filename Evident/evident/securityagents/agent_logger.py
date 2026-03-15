import logging
import json
from typing import Optional, Dict, Any
from evident.connectors import db

logger = logging.getLogger(__name__)

class AgentLogger:
    """Specialized logger for recording detailed agent execution traces."""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id

    def info(self, message: str, trace_data: Optional[Dict[str, Any]] = None):
        """Log an informational message with optional trace data."""
        self._log("INFO", message, trace_data)

    def warning(self, message: str, trace_data: Optional[Dict[str, Any]] = None):
        """Log a warning message."""
        self._log("WARNING", message, trace_data)

    def error(self, message: str, trace_data: Optional[Dict[str, Any]] = None):
        """Log an error message."""
        self._log("ERROR", message, trace_data)

    def _log(self, level: str, message: str, trace_data: Optional[Dict[str, Any]] = None):
        """Internal helper to write to the database."""
        try:
            db.add_agent_log(self.agent_id, level, message, trace_data)
            logger.debug(f"[AGENT {self.agent_id}] {level}: {message}")
        except Exception as e:
            logger.error(f"Failed to record agent log for {self.agent_id}: {e}")

    @staticmethod
    def get_logs(agent_id: str, limit: int = 100):
        """Static helper to retrieve logs for an agent."""
        return db.get_agent_logs(agent_id, limit)
