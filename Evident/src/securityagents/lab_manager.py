import os
import json
import logging
from typing import Dict, Any, List, Optional
from src.connectors import db

logger = logging.getLogger(__name__)

class LabManager:
    def __init__(self):
        self.content_path = os.path.join(os.path.dirname(__file__), "system", "lab_content.json")
        self._content = None
        self._state = {
            "current_step": 1,
            "completed_steps": [],
            "user_config": {}
        }

    def get_content(self) -> Dict[str, Any]:
        if self._content is None:
            try:
                with open(self.content_path, "r") as f:
                    self._content = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load lab content: {e}")
                return {"steps": []}
        return self._content

    def get_status(self) -> Dict[str, Any]:
        content = self.get_content()
        total_steps = len(content.get("steps", []))
        
        return {
            "current_step": self._state["current_step"],
            "total_steps": total_steps,
            "completed_steps": self._state["completed_steps"],
            "is_complete": self._state["current_step"] > total_steps
        }

    def next_step(self, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if data:
            self._state["user_config"].update(data)
            
        if self._state["current_step"] not in self._state["completed_steps"]:
            self._state["completed_steps"].append(self._state["current_step"])
            
        self._state["current_step"] += 1
        return self.get_status()

    def reset_lab(self):
        self._state = {
            "current_step": 1,
            "completed_steps": [],
            "user_config": {}
        }
        return self.get_status()

    def submit_exercise(self, step_id: int, result: str) -> Dict[str, Any]:
        content = self.get_content()
        step = next((s for s in content["steps"] if s["id"] == step_id), None)
        
        if not step or "exercises" not in step:
            return {"success": False, "message": "No exercise found for this step"}
        
        # Simple validation based on the first exercise for now
        exercise = step["exercises"][0]
        import re
        if re.search(exercise["validation_regex"], result):
            return {"success": True, "message": "Great job! The prompt is now much more secure."}
        else:
            return {"success": False, "message": "The prompt doesn't seem to include the necessary security guardrails. Try again!"}

lab_manager = LabManager()
