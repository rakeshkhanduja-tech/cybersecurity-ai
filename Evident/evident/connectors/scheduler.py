"""
scheduler.py — Generic APScheduler-based job runner for Data Plugs.
Orchestrates periodic data pulls for all active connectors.
"""
from __future__ import annotations

import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from evident.connectors import db
from evident.connectors.http_connector import HttpConnector
from evident.connectors.aws_connector import AwsConnector
from evident.connectors.sql_connector import SqlConnector
from evident.connectors.storage import get_storage

logger = logging.getLogger(__name__)

class ConnectorScheduler:
    def __init__(self):
        self._scheduler = BackgroundScheduler()
        self._jobs = {}  # connector_id -> job_id

    def start(self):
        """Start the scheduler and load all active connectors from DB."""
        if not self._scheduler.running:
            self._scheduler.start()
            logger.info("Connector scheduler started.")
        self.refresh_from_db()

    def stop(self):
        self._scheduler.shutdown()

    def refresh_from_db(self):
        """Sync scheduler jobs with active connectors and agents in SQLite."""
        # 1. Connectors
        active_configs = db.get_active_connectors()
        active_ids = {f"connector_{cfg['connector_id']}" for cfg in active_configs}

        # 2. Agents
        active_agents = db.get_active_agents()
        agent_ids = {f"agent_{a['agent_id']}" for a in active_agents}
        
        all_active_ids = active_ids.union(agent_ids)

        # Remove jobs that are no longer active
        for jid in list(self._jobs.keys()):
            if jid not in all_active_ids:
                if jid.startswith("connector_"):
                     self.remove_connector(jid.replace("connector_", ""))
                else:
                     self.remove_agent(jid.replace("agent_", ""))

        # Add or update connector jobs
        for cfg in active_configs:
            self.upsert_connector(cfg)
            
        # Add or update agent jobs
        for agent_cfg in active_agents:
            self.upsert_agent(agent_cfg)

    def upsert_connector(self, cfg: dict):
        cid = cfg["connector_id"]
        interval = cfg.get("interval_minutes", 5) or 5
        paused = cfg.get("scheduler_paused", 0) == 1

        if f"connector_{cid}" in self._jobs:
            # Job exists
            job = self._scheduler.get_job(self._jobs[f"connector_{cid}"])
            if job:
                trigger = IntervalTrigger(minutes=interval)
                self._scheduler.reschedule_job(job.id, trigger=trigger)
                if paused:
                    self._scheduler.pause_job(job.id)
                else:
                    self._scheduler.resume_job(job.id)
                return

        # New job
        job = self._scheduler.add_job(
            func=run_connector_task,
            trigger="interval",
            minutes=interval,
            args=[cid],
            id=f"job_conn_{cid}"
        )
        self._jobs[f"connector_{cid}"] = job.id
        if paused:
            self._scheduler.pause_job(job.id)
        logger.info("Registered job for connector %s (interval: %s min)", cid, interval)

    def upsert_agent(self, cfg: dict):
        aid = cfg["agent_id"]
        interval = cfg.get("interval_minutes", 60) or 60
        is_autonomous = cfg.get("mode") == "autonomous"

        if not is_autonomous:
            # Only schedule autonomous agents
            if f"agent_{aid}" in self._jobs:
                self.remove_agent(aid)
            return

        if f"agent_{aid}" in self._jobs:
            job = self._scheduler.get_job(self._jobs[f"agent_{aid}"])
            if job:
                trigger = IntervalTrigger(minutes=interval)
                self._scheduler.reschedule_job(job.id, trigger=trigger)
                return

        job = self._scheduler.add_job(
            func=run_agent_task,
            trigger="interval",
            minutes=interval,
            args=[aid],
            id=f"job_agent_{aid}"
        )
        self._jobs[f"agent_{aid}"] = job.id
        logger.info("Registered job for autonomous agent %s (interval: %s min)", aid, interval)

    def remove_agent(self, aid: str):
        jid = f"agent_{aid}"
        if jid in self._jobs:
            try:
                self._scheduler.remove_job(self._jobs[jid])
            except:
                pass
            del self._jobs[jid]
            logger.info("Removed job for agent %s", aid)

    def remove_connector(self, cid: str):
        if cid in self._jobs:
            try:
                self._scheduler.remove_job(self._jobs[cid])
            except:
                pass
            del self._jobs[cid]
            logger.info("Removed job for connector %s", cid)

    def pause_connector(self, cid: str):
        jid = f"connector_{cid}"
        if jid in self._jobs:
            self._scheduler.pause_job(self._jobs[jid])
            db.update_scheduler_state(cid, paused=True)

    def resume_connector(self, cid: str):
        jid = f"connector_{cid}"
        if jid in self._jobs:
            self._scheduler.resume_job(self._jobs[jid])
            db.update_scheduler_state(cid, paused=False)

    def run_now(self, cid: str):
        """Immediate manual trigger."""
        self._scheduler.add_job(
            func=run_connector_task,
            trigger=None, # run now
            args=[cid]
        )

# Global singleton
scheduler = ConnectorScheduler()

def run_connector_task(connector_id: str):
    """The actual task function executed by the scheduler threads."""
    from evident.connectors.logger_util import ConnectorLogger
    
    print(f"\n[SCHEDULER] Triggering task for connector: {connector_id}")
    run_logger = ConnectorLogger(connector_id)
    run_logger.info("Scheduler", f"Starting scheduled job for {connector_id}")

    try:
        # 1. Get config & creds
        cfg = db.get_connector_config(connector_id)
        if not cfg:
            run_logger.error("Scheduler", f"No configuration found for {connector_id}")
            return

        # 2. Get global app config (schema, storage)
        app_cfg = db.get_app_config() 
        schema = app_cfg.get("schema_preference", "evident")
        storage_cfg = app_cfg.get("storage_config", {}) 

        # 3. Instantiate right connector class
        plug_def = db.get_plug_metadata(connector_id)
        if not plug_def:
            run_logger.error("Scheduler", f"No plug metadata found for {connector_id}")
            return

        creds = cfg # cfg is already the parsed dictionary from get_connector_config

        conn = None
        if plug_def.get("base_url") == "boto3":
            conn = AwsConnector(plug_def, creds, run_logger=run_logger)
        elif plug_def.get("plug_file") == "snowflake_plug.json":
            conn = SqlConnector(plug_def, creds, run_logger=run_logger)
        else:
            conn = HttpConnector(plug_def, creds, run_logger=run_logger)

        # 4. Storage
        storage = get_storage(storage_cfg)

        # 5. Execute
        selected_signals = cfg.get("selected_signals", [])
        records_count = conn.run(schema, storage, selected_signals=selected_signals)

        # 6. Update stats
        db.update_connector_stats(connector_id, records_count)
        run_logger.info("Scheduler", f"Task completed successfully: {records_count} records generated")

    except Exception as e:
        run_logger.error("Scheduler", f"Failed to run task: {e}")
        logger.error("Failed to run task for %s: %s", connector_id, e, exc_info=True)


def run_agent_task(agent_id: str):
    """The actual task function executed by the scheduler for autonomous agents."""
    from evident.securityagents.agent_manager import agent_manager
    from evident.securityagents.notifications import notification_manager
    from evident.securityagents.agent_logger import AgentLogger
    from evident.agent import EvidentAgent
    from datetime import datetime
    
    alog = AgentLogger(agent_id)
    alog.info(f"Triggering autonomous run for agent: {agent_id}")
    
    try:
        agent_def = agent_manager.get_agent_by_id(agent_id)
        if not agent_def:
            alog.error(f"Agent {agent_id} not found in manager")
            return
            
        if agent_def.get("is_paused"):
            alog.info(f"Agent {agent_id} is paused. Skipping execution.")
            return

        # 1. Initialize Intelligence Engine
        alog.info("Initializing intelligence engine and loading context...")
        evident = EvidentAgent() 
        evident.ingest_data()
        evident.build_intelligence()
        
        # 2. Extract context from Graph and Vector Store
        alog.info("Scanning for active signals of interest...")
        signals = evident.smg_manager.get_signals_of_interest(limit=3)
        
        signal_context = ""
        if signals:
            signal_context = "Active Signals identified in Security Graph:\n" + \
                             "\n".join([f"- {s['label']}: {s['context']}" for s in signals])
        else:
            signal_context = "No immediate high-risk signals detected in graph. Checking general environment..."

        # 3. Perform Reasoning Task
        alog.info("Performing analysis over environment context...")
        system_instruction = agent_def['profile']['system_prompt']
        
        # We use a specialized prompt that asks for "Objective" and "Action Taken"
        reasoning_prompt = f"""
        Role: {agent_def['name']}
        System Instruction: {system_instruction}
        
        Current Context:
        {signal_context}
        
        Task: Perform a deep reasoning task over the current signals. 
        1. Identify the primary objective based on your instructions.
        2. Describe your analysis of the current state.
        3. Define the specific action taken or recommended.
        4. Provide a concise summary for the activity feed.
        
        Response format:
        SUMMARY: <summary>
        OBJECTIVE: <objective>
        ACTION: <action>
        ANALYSIS: <full analysis>
        """
        
        response = evident.query(reasoning_prompt, use_graph=True, use_rag=True)
        text = response.get("answer", "")
        
        # 4. Parse Response (Simple parsing for demo)
        import re
        summary = re.search(r"SUMMARY:\s*(.*)", text)
        objective = re.search(r"OBJECTIVE:\s*(.*)", text)
        action = re.search(r"ACTION:\s*(.*)", text)
        
        final_summary = summary.group(1).strip() if summary else "Autonomous investigation complete."
        final_objective = objective.group(1).strip() if objective else "General monitoring"
        final_action = action.group(1).strip() if action else "Continued surveillance"
        
        alog.info("Analysis complete. Logging activity.", {"summary": final_summary})

        # 5. Record Agent Action & Activity Feed
        agent_manager.record_activity(
            agent_id=agent_id,
            summary=final_summary,
            action_taken=final_action,
            details={
                "objective": final_objective,
                "analysis": text,
                "signals_processed": len(signals)
            }
        )
        
        # 6. Notify if necessary (e.g., if summary implies urgent threat)
        # For now, always notify as per previous requirements
        notification_manager.notify(
            method="email",
            recipient="admin@evident.ai",
            subject=f"Autonomous Security Update: {agent_def['name']}",
            message=f"Agent Activity Summary: {final_summary}\n\nObjective: {final_objective}\nAction Taken: {final_action}"
        )
        
        # 7. Update last run in DB
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE security_agents_config SET last_run = ? WHERE agent_id = ?", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), agent_id))
        conn.commit()
        conn.close()
        alog.info("Autonomous task iteration finalized.")

    except Exception as e:
        alog.error(f"Failed to run agent task: {str(e)}", {"exception": str(e)})
        logger.error(f"Failed to run agent task for {agent_id}: {e}", exc_info=True)


import json
