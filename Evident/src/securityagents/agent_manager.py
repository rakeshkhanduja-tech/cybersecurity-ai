import os
import json
import logging
from typing import List, Dict, Any, Optional
from src.connectors import db

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
        
        # Start MCP Server
        try:
            from src.mcp.manager import mcp_manager
            mcp_manager.start_server(agent_id)
        except Exception as e:
            logger.error(f"Failed to start MCP server for {agent_id}: {e}")

        # Seed mock actions for autonomous mode demonstration
        if mode == "autonomous":
            self.seed_mock_actions(agent_id)

    def seed_mock_actions(self, agent_id: str):
        """Seeds representative security actions for the given agent."""
        # Clear existing pending actions first for a clean start
        existing = db.get_pending_actions(agent_id)
        if len(existing) > 0:
            return

        seeds = [
            {
                "description": "Isolate compromised host 10.0.1.45 due to C2 traffic detection",
                "severity": "Critical",
                "command": "network-isolate --host 10.0.1.45 --ticket-id INC-405",
                "action_type": "Run"
            },
            {
                "description": "Rotate IAM Access Key for user 'svc-cloud-sync' (Last used from unknown IP)",
                "severity": "High",
                "command": "aws iam rotate-access-key --user svc-cloud-sync",
                "action_type": "Run"
            },
            {
                "description": "Revoke excessive S3 permissions for 'PublicAccessRole'",
                "severity": "High",
                "command": "Manual: Update S3 Bucket Policy for 'prod-data-lake-01' via AWS Console",
                "action_type": "Manual"
            },
            {
                "description": "Enable Multi-Factor Authentication for 5 privileged accounts",
                "severity": "Medium",
                "command": "Manual: Send MFA enrollment link to: admin, root, dev-lead, ops-01, ops-02",
                "action_type": "Manual"
            },
            {
                "description": "Update vulnerable Nginx version (CVE-2025-1023) on edge-LB-01",
                "severity": "Medium",
                "command": "ansible-playbook patch_vulnerabilities.yml --limit edge-LB-01",
                "action_type": "Run"
            }
        ]
        
        for s in seeds:
            db.add_pending_action(agent_id, s["description"], s["severity"], s["command"], s["action_type"])
        
        logger.info(f"Seeded {len(seeds)} mock actions for {agent_id}")

    def disable_agent(self, agent_id: str):
        """Disables an agent."""
        config = db.get_all_agent_configs().get(agent_id, {}).get("config", {})
        db.save_agent_config(agent_id, config, is_active=False)
        logger.info(f"Agent {agent_id} disabled.")
        
        # Stop MCP Server
        try:
            from src.mcp.manager import mcp_manager
            mcp_manager.stop_server(agent_id)
        except Exception as e:
            logger.error(f"Failed to stop MCP server for {agent_id}: {e}")

    def pause_agent(self, agent_id: str):
        """Pauses an agent's scheduled execution."""
        db.set_agent_pause_state(agent_id, True)
        logger.info(f"Agent {agent_id} paused.")
        
        # Stop MCP Server on pause
        try:
            from src.mcp.manager import mcp_manager
            mcp_manager.stop_server(agent_id)
        except Exception as e:
            logger.error(f"Failed to stop MCP server for {agent_id} on pause: {e}")

    def resume_agent(self, agent_id: str):
        """Resumes an agent's scheduled execution."""
        db.set_agent_pause_state(agent_id, False)
        logger.info(f"Agent {agent_id} resumed.")
        
        # Resume MCP Server on resume
        try:
            from src.mcp.manager import mcp_manager
            mcp_manager.start_server(agent_id)
        except Exception as e:
            logger.error(f"Failed to resume MCP server for {agent_id}: {e}")

    def get_agent_logs(self, agent_id: str, limit: int = 50):
        """Retrieves execution logs for an agent."""
        return db.get_agent_logs(agent_id, limit)

    def record_activity(self, agent_id: str, summary: str, action_taken: str, details: Optional[Dict[str, Any]] = None):
        db.add_agent_activity(agent_id, summary, action_taken, details)

    def get_agent_activity(self, agent_id: str, limit: int = 50):
        return db.get_agent_activity(agent_id, limit)

    def get_pending_actions(self, agent_id: str):
        """Retrieves currently pending actions for an agent."""
        return db.get_pending_actions(agent_id)

    def execute_action(self, action_id: int):
        """Executes a remediation action."""
        # 1. Fetch action details
        action = db.get_pending_action_by_id(action_id)
        
        if not action:
            raise ValueError(f"Action {action_id} not found")
        
        agent_id = action["agent_id"]
        description = action["description"]
        command = action["command"]
        action_type = action["action_type"]
        
        logger.info(f"Executing action {action_id} for {agent_id}: {description}")
        
        # 2. Simulate execution (in a real app, this would use subprocess or an integration API)
        # We record the start in the logs
        self.record_activity(
            agent_id, 
            summary=f"Executing remediation: {description}",
            action_taken="Remediation Execution",
            details={"command": command, "result": "Execution initiated..."}
        )
        
        # 3. Update status based on type
        new_status = "Executed" if action_type == "Run" else "Manual Completion"
        db.update_action_status(action_id, new_status)
        
        # 4. Final log
        self.record_activity(
            agent_id,
            summary=f"Remediation Completed: {description}",
            action_taken="Success",
            details={"command": command, "result": "Action successfully processed."}
        )
        
        return {"status": "success", "executed_command": command}

# Global singleton
agent_manager = AgentManager()
