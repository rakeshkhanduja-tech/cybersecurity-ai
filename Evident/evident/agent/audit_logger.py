import json
import os
import time
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from evident.config import app_config

class AuditLogger:
    """Logs agent interactions for audit and explanation"""
    
    def __init__(self, log_path: str = "./data/audit_history.json"):
        self.log_path = log_path
        self._ensure_log_file()
        
    def _ensure_log_file(self):
        """Ensure the log file exists"""
        if not os.path.exists(self.log_path):
            os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
            with open(self.log_path, "w") as f:
                json.dump([], f)
    
    def load_history(self) -> List[Dict[str, Any]]:
        """Load audit history"""
        try:
            with open(self.log_path, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading audit history: {e}")
            return []
            
    def log_interaction(self, 
                       query: str, 
                       response: str, 
                       model: str, 
                       tokens: int, 
                       cost: float,
                       execution_steps: List[Dict[str, Any]],
                       context_summary: str = "") -> str:
        """
        Log an interaction
        
        Args:
            query: User's question
            response: Agent's response
            model: Model used
            tokens: Token count
            cost: Estimated cost
            execution_steps: List of steps taken (for 'Explain' feature)
            context_summary: Brief summary of context used
            
        Returns:
            Interaction ID
        """
        interaction_id = str(uuid.uuid4())
        
        entry = {
            "id": interaction_id,
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "response": response,
            "model": model,
            "tokens": tokens,
            "cost": cost,
            "execution_steps": execution_steps,
            "context_summary": context_summary
        }
        
        # Load existing history
        history = self.load_history()
        
        # Prepend new entry
        history.insert(0, entry)
        
        # Keep only last 100 entries
        if len(history) > 100:
            history = history[:100]
            
        # Save
        try:
            with open(self.log_path, "w") as f:
                json.dump(history, f, indent=2)
        except Exception as e:
            print(f"Error saving audit log: {e}")
            
        return interaction_id

# Global instance
audit_logger = AuditLogger()
