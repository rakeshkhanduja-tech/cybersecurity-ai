"""MCP Process Manager for controlling per-agent MCP servers"""

import os
import sys
import subprocess
import logging
import signal
import json
from typing import Dict, Optional, List, Any

logger = logging.getLogger("evident-mcp-manager")

class MCPProcessManager:
    """Manages separate background processes for each security agent's MCP server"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MCPProcessManager, cls).__new__(cls)
            cls._instance.processes: Dict[str, subprocess.Popen] = {}
            cls._instance.base_port = 6101
        return cls._instance

    def get_port_for_agent(self, agent_id: str) -> int:
        """Determines the fixed port for an agent based on its position in security_agents.json"""
        # Load agents directly from file to avoid circular dependency with agent_manager.get_all_agents()
        agents_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "securityagents", "system", "security_agents.json")
        try:
            with open(agents_path, "r", encoding="utf-8") as f:
                all_agents = json.load(f)
            
            for i, agent in enumerate(all_agents):
                if agent["id"] == agent_id:
                    return self.base_port + i
        except Exception as e:
            logger.error(f"Error loading agents for port mapping: {e}")
            
        return self.base_port + 999 # Fallback

    def get_endpoint_for_agent(self, agent_id: str) -> str:
        """Returns the full SSE endpoint URL for an agent's MCP server"""
        port = self.get_port_for_agent(agent_id)
        return f"http://localhost:{port}/sse"

    def start_server(self, agent_id: str):
        """Starts the MCP server process for a specific agent if not already running"""
        if agent_id in self.processes and self.processes[agent_id].poll() is None:
            logger.info(f"MCP Server for {agent_id} is already running.")
            return

        port = self.get_port_for_agent(agent_id)
        
        # Command to run the generic_server module
        cmd = [
            sys.executable, "-m", "src.mcp.generic_server",
            "--agent-id", agent_id,
            "--port", str(port)
        ]
        
        logger.info(f"Starting MCP Server for {agent_id} on port {port}...")
        
        try:
            # Run in a process group/separate session if needed, but for now simple popen
            # We redirect output to devnull or a log file to prevent blocking
            kwargs = {}
            if sys.platform == "win32":
                kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")),
                **kwargs
            )
            
            self.processes[agent_id] = proc
            logger.info(f"[OK] MCP Server {agent_id} started with PID {proc.pid}")
            
            # Non-blocking log monitor (optional, for debugging)
            # In a real app we'd pipe this to a per-agent log file
            
        except Exception as e:
            logger.error(f"Failed to start MCP Server for {agent_id}: {e}")

    def stop_server(self, agent_id: str):
        """Terminates the MCP server process for a specific agent"""
        if agent_id not in self.processes:
            return

        proc = self.processes[agent_id]
        if proc.poll() is None:
            logger.info(f"Stopping MCP Server for {agent_id} (PID {proc.pid})...")
            try:
                if sys.platform == "win32":
                    # On Windows, taskkill is more reliable for killing process groups
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], check=False, capture_output=True)
                else:
                    proc.terminate()
                    proc.wait(timeout=5)
            except Exception as e:
                logger.error(f"Error stopping MCP Server {agent_id}: {e}")
                proc.kill()
        
        del self.processes[agent_id]
        logger.info(f"[OK] MCP Server {agent_id} stopped.")

    def stop_all(self):
        """Stop all running MCP servers"""
        for agent_id in list(self.processes.keys()):
            self.stop_server(agent_id)

# Singleton export
mcp_manager = MCPProcessManager()
