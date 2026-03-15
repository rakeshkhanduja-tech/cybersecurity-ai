import os
import json
import logging
from typing import List, Dict, Any, Optional
from evident.connectors import db

logger = logging.getLogger(__name__)

class AgentManager:
    def __init__(self):
        # Path to pre-built agents
        self.system_agents_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "system", "security_agents.json"
        )

    def get_all_agents(self) -> List[Dict[str, Any]]:
        """Loads system agents and merges with DB configurations."""
        system_agents = []
        try:
            if os.path.exists(self.system_agents_path):
                with open(self.system_agents_path, "r", encoding="utf-8") as f:
                    system_agents = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load system agents: {e}")
        
        db_configs = db.get_all_agent_configs()
        
        merged = []
        for agent in system_agents:
            aid = agent["id"]
            db_cfg = db_configs.get(aid, {})
            
            # Add dynamic status fields
            agent["is_active"] = db_cfg.get("is_active", False)
            agent["is_paused"] = db_cfg.get("is_paused", False)
            agent["last_run"] = db_cfg.get("last_run", None)
            agent["active_mode"] = db_cfg.get("mode", agent["profile"]["mode"])
            agent["active_interval"] = db_cfg.get("interval_minutes", agent["profile"]["frequency_minutes"])
            
            # Merge specific profile settings if they exist in DB (overrides)
            if "config" in db_cfg:
                agent["profile"].update(db_cfg["config"])
                
            merged.append(agent)
            
        return merged

    def get_agent_by_id(self, agent_id: str) -> Optional[Dict[str, Any]]:
        all_agents = self.get_all_agents()
        for a in all_agents:
            if a["id"] == agent_id:
                return a
        return None

    def enable_agent(self, agent_id: str, config: Dict[str, Any]):
        """Enables an agent with specific configuration."""
        agent = self.get_agent_by_id(agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")
        
        mode = config.get("mode", agent["profile"]["mode"])
        interval = config.get("frequency_minutes", agent["profile"]["frequency_minutes"])
        
        db.save_agent_config(agent_id, config, is_active=True, mode=mode, interval=interval)
        logger.info(f"Agent {agent_id} enabled in {mode} mode.")

    def disable_agent(self, agent_id: str):
        """Disables an agent."""
        config = db.get_all_agent_configs().get(agent_id, {}).get("config", {})
        db.save_agent_config(agent_id, config, is_active=False)
        logger.info(f"Agent {agent_id} disabled.")

    def pause_agent(self, agent_id: str):
        """Pauses an agent's scheduled execution."""
        db.set_agent_pause_state(agent_id, True)
        logger.info(f"Agent {agent_id} paused.")

    def resume_agent(self, agent_id: str):
        """Resumes an agent's scheduled execution."""
        db.set_agent_pause_state(agent_id, False)
        logger.info(f"Agent {agent_id} resumed.")

    def get_agent_logs(self, agent_id: str, limit: int = 50):
        """Retrieves execution logs for an agent."""
        return db.get_agent_logs(agent_id, limit)

    def record_activity(self, agent_id: str, summary: str, action_taken: str, details: Optional[Dict[str, Any]] = None):
        db.add_agent_activity(agent_id, summary, action_taken, details)

    def get_agent_activity(self, agent_id: str, limit: int = 50):
        return db.get_agent_activity(agent_id, limit)

# Global singleton
agent_manager = AgentManager()
