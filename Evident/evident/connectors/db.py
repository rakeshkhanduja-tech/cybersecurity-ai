import sqlite3
import json
import os
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


# Define database file path
# __file__ is evident/connectors/db.py
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "data", "connectors.db")


def get_connection():
    """Returns a connection to the SQLite database."""
    # Ensure directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db():
    """Initializes the database schema and performs migrations."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Connectors Config Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS connectors_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            connector_id TEXT UNIQUE NOT NULL,
            config_json TEXT NOT NULL,
            is_active BOOLEAN DEFAULT 0,
            last_run TEXT,
            records_generated INTEGER DEFAULT 0,
            scheduler_paused BOOLEAN DEFAULT 0,
            interval_minutes INTEGER DEFAULT 5
        )
    ''')

    # Migration: Add columns if they don't exist for older DBs
    cursor.execute("PRAGMA table_info(connectors_config)")
    columns = [row[1] for row in cursor.fetchall()]
    if "scheduler_paused" not in columns:
        cursor.execute("ALTER TABLE connectors_config ADD COLUMN scheduler_paused BOOLEAN DEFAULT 0")
    if "interval_minutes" not in columns:
        cursor.execute("ALTER TABLE connectors_config ADD COLUMN interval_minutes INTEGER DEFAULT 5")

    # 2. Global App Config Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS app_config (
            key TEXT PRIMARY KEY,
            value_json TEXT NOT NULL
        )
    ''')

    # Ensure is_paused Column exists (Migration)
    try:
        cursor.execute("SELECT is_paused FROM security_agents_config LIMIT 1")
    except sqlite3.OperationalError:
        # Check if table exists first before altering
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='security_agents_config'")
        if cursor.fetchone():
            logger.info("Migrating security_agents_config: adding is_paused column")
            cursor.execute("ALTER TABLE security_agents_config ADD COLUMN is_paused BOOLEAN DEFAULT 0")


    # 4. Agent Logs Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS agent_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id TEXT NOT NULL,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            level TEXT,
            message TEXT,
            trace_data TEXT
        )
    ''')
    
    # 5. Agent Activity Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS agent_activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id TEXT NOT NULL,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            summary TEXT,
            action_taken TEXT,
            details TEXT
        )
    ''')
    
    conn.commit()
    conn.close()




def save_config(connector_id: str, config: Dict[str, Any], is_active: bool = False, interval: int = 5):
    """Saves or updates a connector configuration."""
    conn = get_connection()
    cursor = conn.cursor()
    
    config_json = json.dumps(config)
    
    # Check if exists
    cursor.execute("SELECT id FROM connectors_config WHERE connector_id = ?", (connector_id,))
    row = cursor.fetchone()
    
    if row:
        cursor.execute('''
            UPDATE connectors_config
            SET config_json = ?, is_active = ?, interval_minutes = ?
            WHERE connector_id = ?
        ''', (config_json, is_active, interval, connector_id))
    else:
        cursor.execute('''
            INSERT INTO connectors_config (connector_id, config_json, is_active, interval_minutes)
            VALUES (?, ?, ?, ?)
        ''', (connector_id, config_json, is_active, interval))
        
    conn.commit()
    conn.close()


def get_all_configs() -> Dict[str, Dict[str, Any]]:
    """Retrieves all connector configurations and scheduler state."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT connector_id, config_json, is_active, last_run, records_generated, scheduler_paused, interval_minutes FROM connectors_config")
    except sqlite3.OperationalError:
        init_db()
        cursor.execute("SELECT connector_id, config_json, is_active, last_run, records_generated, scheduler_paused, interval_minutes FROM connectors_config")
        
    rows = cursor.fetchall()
    conn.close()
    
    configs = {}
    for row in rows:
        configs[row[0]] = {
            "config": json.loads(row[1]),
            "is_active": bool(row[2]),
            "last_run": row[3],
            "records_generated": row[4],
            "scheduler_paused": bool(row[5]),
            "interval_minutes": row[6]
        }
    return configs


def get_active_connectors() -> List[Dict[str, Any]]:
    """Retrieves currently active connectors for the scheduler."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT connector_id, config_json, scheduler_paused, interval_minutes FROM connectors_config WHERE is_active = 1")
    rows = cursor.fetchall()
    conn.close()
    
    active = []
    for row in rows:
        active.append({
            "connector_id": row[0],
            "parameters_json": row[1],
            "scheduler_paused": row[2],
            "interval_minutes": row[3]
        })
    return active


def update_scheduler_state(connector_id: str, paused: bool):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE connectors_config SET scheduler_paused = ? WHERE connector_id = ?", (1 if paused else 0, connector_id))
    conn.commit()
    conn.close()


def update_connector_stats(connector_id: str, records_count: int):
    from datetime import datetime
    conn = get_connection()
    cursor = conn.cursor()
    last_run = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''
        UPDATE connectors_config 
        SET last_run = ?, records_generated = records_generated + ? 
        WHERE connector_id = ?
    ''', (last_run, records_count, connector_id))
    conn.commit()
    conn.close()


def get_connector_config(connector_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT config_json FROM connectors_config WHERE connector_id = ?", (connector_id,))
    row = cursor.fetchone()
    conn.close()
    return json.loads(row[0]) if row else None


def set_app_config(key: str, value: Any):
    conn = get_connection()
    cursor = conn.cursor()
    val_json = json.dumps(value)
    cursor.execute("INSERT OR REPLACE INTO app_config (key, value_json) VALUES (?, ?)", (key, val_json))
    conn.commit()
    conn.close()


def get_app_config() -> Dict[str, Any]:
    """Retrieves the entire app config (schema, storage, etc.)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT key, value_json FROM app_config")
    rows = cursor.fetchall()
    conn.close()
    
    config = {}
    for row in rows:
        config[row[0]] = json.loads(row[1])
    return config


def save_agent_config(agent_id: str, config: Dict[str, Any], is_active: bool = False, mode: str = "interactive", interval: int = 60, is_paused: bool = False):
    """Saves or updates a security agent configuration."""
    conn = get_connection()
    cursor = conn.cursor()
    config_json = json.dumps(config)
    
    cursor.execute("SELECT id FROM security_agents_config WHERE agent_id = ?", (agent_id,))
    row = cursor.fetchone()
    
    if row:
        cursor.execute('''
            UPDATE security_agents_config
            SET config_json = ?, is_active = ?, mode = ?, interval_minutes = ?, is_paused = ?
            WHERE agent_id = ?
        ''', (config_json, is_active, mode, interval, is_paused, agent_id))
    else:
        cursor.execute('''
            INSERT INTO security_agents_config (agent_id, config_json, is_active, mode, interval_minutes, is_paused)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (agent_id, config_json, is_active, mode, interval, is_paused))
        
    conn.commit()
    conn.close()


def get_all_agent_configs() -> Dict[str, Dict[str, Any]]:
    """Retrieves all agent configurations."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT agent_id, config_json, is_active, last_run, mode, interval_minutes, is_paused FROM security_agents_config")
    rows = cursor.fetchall()
    conn.close()
    
    configs = {}
    for row in rows:
        configs[row[0]] = {
            "config": json.loads(row[1]),
            "is_active": bool(row[2]),
            "last_run": row[3],
            "mode": row[4],
            "interval_minutes": row[5],
            "is_paused": bool(row[6])
        }
    return configs


def set_agent_pause_state(agent_id: str, paused: bool):
    """Pauses or resumes an agent."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE security_agents_config SET is_paused = ? WHERE agent_id = ?", (1 if paused else 0, agent_id))
    conn.commit()
    conn.close()


def add_agent_log(agent_id: str, level: str, message: str, trace_data: Optional[Dict[str, Any]] = None):
    """Adds a log entry for an agent."""
    conn = get_connection()
    cursor = conn.cursor()
    trace_json = json.dumps(trace_data) if trace_data else None
    cursor.execute('''
        INSERT INTO agent_logs (agent_id, level, message, trace_data, timestamp)
        VALUES (?, ?, ?, ?, datetime('now'))
    ''', (agent_id, level, message, trace_json))
    conn.commit()
    conn.close()



def get_agent_logs(agent_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Retrieves recent logs for an agent."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT timestamp, level, message, trace_data 
        FROM agent_logs 
        WHERE agent_id = ? 
        ORDER BY timestamp DESC LIMIT ?
    ''', (agent_id, limit))
    rows = cursor.fetchall()
    conn.close()
    
    logs = []
    for row in rows:
        logs.append({
            "timestamp": row[0],
            "level": row[1],
            "message": row[2],
            "trace_data": json.loads(row[3]) if row[3] else None
        })
    return logs


def add_agent_activity(agent_id: str, summary: str, action_taken: str, details: Optional[Dict[str, Any]] = None):
    """Adds an entry to the agent activity feed."""
    conn = get_connection()
    cursor = conn.cursor()
    details_json = json.dumps(details) if details else None
    cursor.execute('''
        INSERT INTO agent_activity (agent_id, summary, action_taken, details, timestamp)
        VALUES (?, ?, ?, ?, datetime('now'))
    ''', (agent_id, summary, action_taken, details_json))
    conn.commit()
    conn.close()


def get_agent_activity(agent_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieves recent activity entries for an agent."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT timestamp, summary, action_taken, details 
        FROM agent_activity 
        WHERE agent_id = ? 
        ORDER BY timestamp DESC LIMIT ?
    ''', (agent_id, limit))
    rows = cursor.fetchall()
    conn.close()
    
    activities = []
    for row in rows:
        activities.append({
            "timestamp": row[0],
            "summary": row[1],
            "action_taken": row[2],
            "details": json.loads(row[3]) if row[3] else None
        })
    return activities



def get_active_agents() -> List[Dict[str, Any]]:
    """Retrieves currently active agents (autonomous ones usually)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT agent_id, config_json, mode, interval_minutes, is_paused FROM security_agents_config WHERE is_active = 1")
    rows = cursor.fetchall()
    conn.close()
    
    active = []
    for row in rows:
        active.append({
            "agent_id": row[0],
            "config": json.loads(row[1]),
            "mode": row[2],
            "interval_minutes": row[3],
            "is_paused": bool(row[4])
        })
    return active


def get_plug_metadata(connector_id: str) -> Optional[Dict[str, Any]]:
    """Load plug metadata from data_plugs.json."""
    try:
        # Use absolute path resolution
        current_dir = os.path.dirname(os.path.abspath(__file__))
        plug_path = os.path.join(current_dir, "dataplugs", "data_plugs.json")
        
        if not os.path.exists(plug_path):
             print(f"[DB ERROR] data_plugs.json not found at: {plug_path}")
             return None
             
        with open(plug_path, "r", encoding="utf-8") as f:
            plugs = json.load(f)
            for p in plugs:
                if p["id"] == connector_id:
                    return p
        print(f"[DB ERROR] Connector ID '{connector_id}' not found in data_plugs.json")
    except Exception as e:
        print(f"[DB ERROR] Failed to read plug metadata: {e}")
    return None

# Initialize database on import to ensure migrations/tables are up to date
try:
    init_db()
except Exception as e:
    # Fallback if logger still fails or similar
    print(f"[DB FATAL] Failed to initialize database: {e}")


