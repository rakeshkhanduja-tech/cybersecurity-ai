import sqlite3
import json
import os
import logging
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

# --- Interfaces ---

class DBProvider(ABC):
    @abstractmethod
    def init_db(self):
        pass

    @abstractmethod
    def save_connector_config(self, connector_id: str, config: Dict[str, Any], is_active: bool, interval: int):
        pass

    @abstractmethod
    def get_all_connector_configs(self) -> Dict[str, Dict[str, Any]]:
        pass

    @abstractmethod
    def get_active_connectors(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def update_scheduler_state(self, connector_id: str, paused: bool):
        pass

    @abstractmethod
    def update_connector_stats(self, connector_id: str, records_count: int):
        pass

    @abstractmethod
    def get_connector_config(self, connector_id: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def set_app_config(self, key: str, value: Any):
        pass

    @abstractmethod
    def get_app_config(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def save_agent_config(self, agent_id: str, config: Dict[str, Any], is_active: bool, mode: str, interval: int, is_paused: bool):
        pass

    @abstractmethod
    def get_all_agent_configs(self) -> Dict[str, Dict[str, Any]]:
        pass

    @abstractmethod
    def set_agent_pause_state(self, agent_id: str, paused: bool):
        pass

    @abstractmethod
    def add_agent_log(self, agent_id: str, level: str, message: str, trace_data: Optional[Dict[str, Any]] = None):
        pass

    @abstractmethod
    def get_agent_logs(self, agent_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def add_agent_activity(self, agent_id: str, summary: str, action_taken: str, details: Optional[Dict[str, Any]] = None):
        pass

    @abstractmethod
    def get_agent_activity(self, agent_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def add_pending_action(self, agent_id: str, description: str, severity: str, command: str = None, action_type: str = "Manual"):
        pass

    @abstractmethod
    def get_pending_actions(self, agent_id: str, status: str = "Pending") -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def update_action_status(self, action_id: int, status: str):
        pass

    @abstractmethod
    def get_active_agents(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def update_agent_stats(self, agent_id: str):
        pass

    @abstractmethod
    def get_pending_action_by_id(self, action_id: int) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def test_connection(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_plug_metadata(self, connector_id: str) -> Optional[Dict[str, Any]]:
        pass


# --- SQLite Implementation ---

class SQLiteProvider(DBProvider):
    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def init_db(self):
        conn = self._get_connection()
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

        # 2. Global App Config Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS app_config (
                key TEXT PRIMARY KEY,
                value_json TEXT NOT NULL
            )
        ''')

        # 3. Security Agents Config Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS security_agents_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT UNIQUE NOT NULL,
                config_json TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 0,
                last_run TEXT,
                mode TEXT DEFAULT 'interactive',
                interval_minutes INTEGER DEFAULT 60,
                is_paused BOOLEAN DEFAULT 0
            )
        ''')

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

        # 6. Agent Pending Actions Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agent_pending_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                description TEXT NOT NULL,
                severity TEXT CHECK( severity IN ('Critical', 'High', 'Medium', 'Low') ) NOT NULL,
                command TEXT,
                action_type TEXT CHECK( action_type IN ('Run', 'Manual', 'No Action') ) DEFAULT 'Manual',
                status TEXT CHECK( status IN ('Pending', 'Executed', 'Manual Completion', 'Dismissed') ) DEFAULT 'Pending'
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info(f"SQLite database initialized at {self.db_path}")

    def save_connector_config(self, connector_id: str, config: Dict[str, Any], is_active: bool, interval: int):
        conn = self._get_connection()
        cursor = conn.cursor()
        config_json = json.dumps(config)
        cursor.execute("SELECT id FROM connectors_config WHERE connector_id = ?", (connector_id,))
        if cursor.fetchone():
            cursor.execute("UPDATE connectors_config SET config_json = ?, is_active = ?, interval_minutes = ? WHERE connector_id = ?", (config_json, is_active, interval, connector_id))
        else:
            cursor.execute("INSERT INTO connectors_config (connector_id, config_json, is_active, interval_minutes) VALUES (?, ?, ?, ?)", (connector_id, config_json, is_active, interval))
        conn.commit()
        conn.close()

    def get_all_connector_configs(self) -> Dict[str, Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
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

    def get_active_connectors(self) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT connector_id, config_json, scheduler_paused, interval_minutes FROM connectors_config WHERE is_active = 1")
        rows = cursor.fetchall()
        conn.close()
        active = []
        for row in rows:
            active.append({"connector_id": row[0], "parameters_json": row[1], "scheduler_paused": bool(row[2]), "interval_minutes": row[3]})
        return active

    def update_scheduler_state(self, connector_id: str, paused: bool):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE connectors_config SET scheduler_paused = ? WHERE connector_id = ?", (1 if paused else 0, connector_id))
        conn.commit()
        conn.close()

    def update_connector_stats(self, connector_id: str, records_count: int):
        from datetime import datetime
        last_run = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE connectors_config SET last_run = ?, records_generated = records_generated + ? WHERE connector_id = ?", (last_run, records_count, connector_id))
        conn.commit()
        conn.close()

    def get_connector_config(self, connector_id: str) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT config_json FROM connectors_config WHERE connector_id = ?", (connector_id,))
        row = cursor.fetchone()
        conn.close()
        return json.loads(row[0]) if row else None

    def set_app_config(self, key: str, value: Any):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO app_config (key, value_json) VALUES (?, ?)", (key, json.dumps(value)))
        conn.commit()
        conn.close()

    def get_app_config(self) -> Dict[str, Any]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT key, value_json FROM app_config")
        rows = cursor.fetchall()
        conn.close()
        return {row[0]: json.loads(row[1]) for row in rows}

    def save_agent_config(self, agent_id: str, config: Dict[str, Any], is_active: bool, mode: str, interval: int, is_paused: bool):
        conn = self._get_connection()
        cursor = conn.cursor()
        config_json = json.dumps(config)
        cursor.execute("SELECT id FROM security_agents_config WHERE agent_id = ?", (agent_id,))
        if cursor.fetchone():
            cursor.execute("UPDATE security_agents_config SET config_json = ?, is_active = ?, mode = ?, interval_minutes = ?, is_paused = ? WHERE agent_id = ?", (config_json, is_active, mode, interval, is_paused, agent_id))
        else:
            cursor.execute("INSERT INTO security_agents_config (agent_id, config_json, is_active, mode, interval_minutes, is_paused) VALUES (?, ?, ?, ?, ?, ?)", (agent_id, config_json, is_active, mode, interval, is_paused))
        conn.commit()
        conn.close()

    def get_all_agent_configs(self) -> Dict[str, Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT agent_id, config_json, is_active, last_run, mode, interval_minutes, is_paused FROM security_agents_config")
        rows = cursor.fetchall()
        conn.close()
        configs = {}
        for row in rows:
            configs[row[0]] = {
                "config": json.loads(row[1]), "is_active": bool(row[2]), "last_run": row[3], "mode": row[4], "interval_minutes": row[5], "is_paused": bool(row[6])
            }
        return configs

    def set_agent_pause_state(self, agent_id: str, paused: bool):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE security_agents_config SET is_paused = ? WHERE agent_id = ?", (1 if paused else 0, agent_id))
        conn.commit()
        conn.close()

    def add_agent_log(self, agent_id: str, level: str, message: str, trace_data: Optional[Dict[str, Any]] = None):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO agent_logs (agent_id, level, message, trace_data, timestamp) VALUES (?, ?, ?, ?, datetime('now'))", (agent_id, level, message, json.dumps(trace_data) if trace_data else None))
        conn.commit()
        conn.close()

    def get_agent_logs(self, agent_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT timestamp, level, message, trace_data FROM agent_logs WHERE agent_id = ? ORDER BY timestamp DESC LIMIT ?", (agent_id, limit))
        rows = cursor.fetchall()
        conn.close()
        return [{"timestamp": r[0], "level": r[1], "message": r[2], "trace_data": json.loads(r[3]) if r[3] else None} for r in rows]

    def add_agent_activity(self, agent_id: str, summary: str, action_taken: str, details: Optional[Dict[str, Any]] = None):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO agent_activity (agent_id, summary, action_taken, details, timestamp) VALUES (?, ?, ?, ?, datetime('now'))", (agent_id, summary, action_taken, json.dumps(details) if details else None))
        conn.commit()
        conn.close()

    def get_agent_activity(self, agent_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT timestamp, summary, action_taken, details FROM agent_activity WHERE agent_id = ? ORDER BY timestamp DESC LIMIT ?", (agent_id, limit))
        rows = cursor.fetchall()
        conn.close()
        return [{"timestamp": r[0], "summary": r[1], "action_taken": r[2], "details": json.loads(r[3]) if r[3] else None} for r in rows]

    def add_pending_action(self, agent_id: str, description: str, severity: str, command: str = None, action_type: str = "Manual"):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO agent_pending_actions (agent_id, description, severity, command, action_type) VALUES (?, ?, ?, ?, ?)", (agent_id, description, severity, command, action_type))
        conn.commit()
        conn.close()

    def get_pending_actions(self, agent_id: str, status: str = "Pending") -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, timestamp, description, severity, command, action_type, status FROM agent_pending_actions WHERE agent_id = ? AND status = ? ORDER BY timestamp DESC", (agent_id, status))
        rows = cursor.fetchall()
        conn.close()
        return [{"id": r[0], "timestamp": r[1], "description": r[2], "severity": r[3], "command": r[4], "action_type": r[5], "status": r[6]} for r in rows]

    def update_action_status(self, action_id: int, status: str):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE agent_pending_actions SET status = ? WHERE id = ?", (status, action_id))
        conn.commit()
        conn.close()

    def get_active_agents(self) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT agent_id, config_json, mode, interval_minutes, is_paused FROM security_agents_config WHERE is_active = 1")
        rows = cursor.fetchall()
        conn.close()
        return [{"agent_id": r[0], "config": json.loads(r[1]), "mode": r[2], "interval_minutes": r[3], "is_paused": bool(r[4])} for r in rows]

    def update_agent_stats(self, agent_id: str):
        from datetime import datetime
        last_run = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE security_agents_config SET last_run = ? WHERE agent_id = ?", (last_run, agent_id))
        conn.commit()
        conn.close()

    def get_pending_action_by_id(self, action_id: int) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, timestamp, agent_id, description, severity, command, action_type, status FROM agent_pending_actions WHERE id = ?", (action_id,))
        r = cursor.fetchone()
        conn.close()
        if not r: return None
        return {"id": r[0], "timestamp": r[1], "agent_id": r[2], "description": r[3], "severity": r[4], "command": r[5], "action_type": r[6], "status": r[7]}

    def test_connection(self) -> Dict[str, Any]:
        try:
            conn = self._get_connection()
            conn.execute("SELECT 1")
            conn.close()
            return {"success": True, "message": "SQLite connection successful"}
        except Exception as e:
            return {"success": False, "message": f"SQLite connection failed: {str(e)}"}

    def get_plug_metadata(self, connector_id: str) -> Optional[Dict[str, Any]]:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        plugs_index_path = os.path.join(base_dir, "dataplugs", "data_plugs.json")

        try:
            with open(plugs_index_path, 'r', encoding='utf-8') as f:
                plugs = json.load(f)

            plug_entry = next((p for p in plugs if p['id'] == connector_id), None)
            if not plug_entry:
                return None

            # Start with the index entry so 'plug_file', 'id', 'name' are always present
            result = dict(plug_entry)

            # Merge in the detailed plug JSON if it exists
            if plug_entry.get('plug_file'):
                detailed_plug_path = os.path.join(base_dir, "dataplugs", plug_entry['plug_file'])
                if os.path.exists(detailed_plug_path):
                    with open(detailed_plug_path, 'r', encoding='utf-8') as f:
                        detailed = json.load(f)
                    result.update(detailed)          # detailed overrides, but index keys remain if not overwritten
                    result['plug_file'] = plug_entry['plug_file']  # ensure plug_file is never lost
                    result['id']        = plug_entry['id']
                    result['name']      = plug_entry['name']

            return result
        except Exception as e:
            logger.error(f"Error loading plug metadata for {connector_id}: {e}")
            return None


# --- PostgreSQL Implementation ---

class PostgresProvider(DBProvider):
    def __init__(self, host, port, database, user, password):
        self.params = {
            "host": host,
            "port": port,
            "dbname": database,
            "user": user,
            "password": password
        }

    def _get_connection(self):
        import psycopg2
        return psycopg2.connect(**self.params)

    def init_db(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 1. Connectors Config Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS connectors_config (
                id SERIAL PRIMARY KEY,
                connector_id TEXT UNIQUE NOT NULL,
                config_json TEXT NOT NULL,
                is_active BOOLEAN DEFAULT false,
                last_run TEXT,
                records_generated INTEGER DEFAULT 0,
                scheduler_paused BOOLEAN DEFAULT false,
                interval_minutes INTEGER DEFAULT 5
            )
        ''')

        # 2. Global App Config Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS app_config (
                key TEXT PRIMARY KEY,
                value_json TEXT NOT NULL
            )
        ''')

        # 3. Security Agents Config Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS security_agents_config (
                id SERIAL PRIMARY KEY,
                agent_id TEXT UNIQUE NOT NULL,
                config_json TEXT NOT NULL,
                is_active BOOLEAN DEFAULT false,
                last_run TEXT,
                mode TEXT DEFAULT 'interactive',
                interval_minutes INTEGER DEFAULT 60,
                is_paused BOOLEAN DEFAULT false
            )
        ''')

        # 4. Agent Logs Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agent_logs (
                id SERIAL PRIMARY KEY,
                agent_id TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                level TEXT,
                message TEXT,
                trace_data TEXT
            )
        ''')
        
        # 5. Agent Activity Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agent_activity (
                id SERIAL PRIMARY KEY,
                agent_id TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                summary TEXT,
                action_taken TEXT,
                details TEXT
            )
        ''')

        # 6. Agent Pending Actions Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agent_pending_actions (
                id SERIAL PRIMARY KEY,
                agent_id TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                description TEXT NOT NULL,
                severity TEXT NOT NULL,
                command TEXT,
                action_type TEXT DEFAULT 'Manual',
                status TEXT DEFAULT 'Pending'
            )
        ''')
        
        conn.commit()
        cursor.close()
        conn.close()
        logger.info(f"PostgreSQL database initialized at {self.params['host']}")

    def save_connector_config(self, connector_id: str, config: Dict[str, Any], is_active: bool, interval: int):
        conn = self._get_connection()
        cursor = conn.cursor()
        config_json = json.dumps(config)
        cursor.execute("SELECT id FROM connectors_config WHERE connector_id = %s", (connector_id,))
        if cursor.fetchone():
            cursor.execute("UPDATE connectors_config SET config_json = %s, is_active = %s, interval_minutes = %s WHERE connector_id = %s", (config_json, is_active, interval, connector_id))
        else:
            cursor.execute("INSERT INTO connectors_config (connector_id, config_json, is_active, interval_minutes) VALUES (%s, %s, %s, %s)", (connector_id, config_json, is_active, interval))
        conn.commit()
        cursor.close()
        conn.close()

    def get_all_connector_configs(self) -> Dict[str, Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT connector_id, config_json, is_active, last_run, records_generated, scheduler_paused, interval_minutes FROM connectors_config")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        configs = {}
        for row in rows:
            configs[row[0]] = {
                "config": json.loads(row[1]), "is_active": bool(row[2]), "last_run": row[3], "records_generated": row[4], "scheduler_paused": bool(row[5]), "interval_minutes": row[6]
            }
        return configs

    def get_active_connectors(self) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT connector_id, config_json, scheduler_paused, interval_minutes FROM connectors_config WHERE is_active = true")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return [{"connector_id": r[0], "parameters_json": r[1], "scheduler_paused": bool(r[2]), "interval_minutes": r[3]} for r in rows]

    def update_scheduler_state(self, connector_id: str, paused: bool):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE connectors_config SET scheduler_paused = %s WHERE connector_id = %s", (paused, connector_id))
        conn.commit()
        cursor.close()
        conn.close()

    def update_connector_stats(self, connector_id: str, records_count: int):
        from datetime import datetime
        last_run = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE connectors_config SET last_run = %s, records_generated = records_generated + %s WHERE connector_id = %s", (last_run, records_count, connector_id))
        conn.commit()
        cursor.close()
        conn.close()

    def get_connector_config(self, connector_id: str) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT config_json FROM connectors_config WHERE connector_id = %s", (connector_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return json.loads(row[0]) if row else None

    def set_app_config(self, key: str, value: Any):
        conn = self._get_connection()
        cursor = conn.cursor()
        val_json = json.dumps(value)
        cursor.execute("INSERT INTO app_config (key, value_json) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value_json = EXCLUDED.value_json", (key, val_json))
        conn.commit()
        cursor.close()
        conn.close()

    def get_app_config(self) -> Dict[str, Any]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT key, value_json FROM app_config")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return {row[0]: json.loads(row[1]) for row in rows}

    def save_agent_config(self, agent_id: str, config: Dict[str, Any], is_active: bool, mode: str, interval: int, is_paused: bool):
        conn = self._get_connection()
        cursor = conn.cursor()
        config_json = json.dumps(config)
        cursor.execute("SELECT id FROM security_agents_config WHERE agent_id = %s", (agent_id,))
        if cursor.fetchone():
            cursor.execute("UPDATE security_agents_config SET config_json = %s, is_active = %s, mode = %s, interval_minutes = %s, is_paused = %s WHERE agent_id = %s", (config_json, is_active, mode, interval, is_paused, agent_id))
        else:
            cursor.execute("INSERT INTO security_agents_config (agent_id, config_json, is_active, mode, interval_minutes, is_paused) VALUES (%s, %s, %s, %s, %s, %s)", (agent_id, config_json, is_active, mode, interval, is_paused))
        conn.commit()
        cursor.close()
        conn.close()

    def get_all_agent_configs(self) -> Dict[str, Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT agent_id, config_json, is_active, last_run, mode, interval_minutes, is_paused FROM security_agents_config")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        configs = {}
        for row in rows:
            configs[row[0]] = {
                "config": json.loads(row[1]), "is_active": bool(row[2]), "last_run": row[3], "mode": row[4], "interval_minutes": row[5], "is_paused": bool(row[6])
            }
        return configs

    def set_agent_pause_state(self, agent_id: str, paused: bool):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE security_agents_config SET is_paused = %s WHERE agent_id = %s", (paused, agent_id))
        conn.commit()
        cursor.close()
        conn.close()

    def add_agent_log(self, agent_id: str, level: str, message: str, trace_data: Optional[Dict[str, Any]] = None):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO agent_logs (agent_id, level, message, trace_data) VALUES (%s, %s, %s, %s)", (agent_id, level, message, json.dumps(trace_data) if trace_data else None))
        conn.commit()
        cursor.close()
        conn.close()

    def get_agent_logs(self, agent_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT timestamp, level, message, trace_data FROM agent_logs WHERE agent_id = %s ORDER BY timestamp DESC LIMIT %s", (agent_id, limit))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return [{"timestamp": r[0].isoformat() if hasattr(r[0], 'isoformat') else r[0], "level": r[1], "message": r[2], "trace_data": json.loads(r[3]) if r[3] else None} for r in rows]

    def add_agent_activity(self, agent_id: str, summary: str, action_taken: str, details: Optional[Dict[str, Any]] = None):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO agent_activity (agent_id, summary, action_taken, details) VALUES (%s, %s, %s, %s)", (agent_id, summary, action_taken, json.dumps(details) if details else None))
        conn.commit()
        cursor.close()
        conn.close()

    def get_agent_activity(self, agent_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT timestamp, summary, action_taken, details FROM agent_activity WHERE agent_id = %s ORDER BY timestamp DESC LIMIT %s", (agent_id, limit))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return [{"timestamp": r[0].isoformat() if hasattr(r[0], 'isoformat') else r[0], "summary": r[1], "action_taken": r[2], "details": json.loads(r[3]) if r[3] else None} for r in rows]

    def add_pending_action(self, agent_id: str, description: str, severity: str, command: str = None, action_type: str = "Manual"):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO agent_pending_actions (agent_id, description, severity, command, action_type) VALUES (%s, %s, %s, %s, %s)", (agent_id, description, severity, command, action_type))
        conn.commit()
        cursor.close()
        conn.close()

    def get_pending_actions(self, agent_id: str, status: str = "Pending") -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, timestamp, description, severity, command, action_type, status FROM agent_pending_actions WHERE agent_id = %s AND status = %s ORDER BY timestamp DESC", (agent_id, status))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return [{"id": r[0], "timestamp": r[1].isoformat() if hasattr(r[1], 'isoformat') else r[1], "description": r[2], "severity": r[3], "command": r[4], "action_type": r[5], "status": r[6]} for r in rows]

    def update_action_status(self, action_id: int, status: str):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE agent_pending_actions SET status = %s WHERE id = %s", (status, action_id))
        conn.commit()
        cursor.close()
        conn.close()

    def get_active_agents(self) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT agent_id, config_json, mode, interval_minutes, is_paused FROM security_agents_config WHERE is_active = true")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return [{"agent_id": r[0], "config": json.loads(r[1]), "mode": r[2], "interval_minutes": r[3], "is_paused": bool(r[4])} for r in rows]

    def update_agent_stats(self, agent_id: str):
        from datetime import datetime
        last_run = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE security_agents_config SET last_run = %s WHERE agent_id = %s", (last_run, agent_id))
        conn.commit()
        cursor.close()
        conn.close()

    def get_pending_action_by_id(self, action_id: int) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, timestamp, agent_id, description, severity, command, action_type, status FROM agent_pending_actions WHERE id = %s", (action_id,))
        r = cursor.fetchone()
        cursor.close()
        conn.close()
        if not r: return None
        return {"id": r[0], "timestamp": r[1].isoformat() if hasattr(r[1], 'isoformat') else r[1], "agent_id": r[2], "description": r[3], "severity": r[4], "command": r[5], "action_type": r[6], "status": r[7]}

    def test_connection(self) -> Dict[str, Any]:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            conn.close()
            return {"success": True, "message": "PostgreSQL connection successful"}
        except ImportError:
            return {"success": False, "message": "PostgreSQL driver (psycopg2) not installed"}
        except Exception as e:
            return {"success": False, "message": f"PostgreSQL connection failed: {str(e)}"}

    def get_plug_metadata(self, connector_id: str) -> Optional[Dict[str, Any]]:
        # Same logic as SQLite — plugs are file-based
        base_dir = os.path.dirname(os.path.abspath(__file__))
        plugs_index_path = os.path.join(base_dir, "dataplugs", "data_plugs.json")

        try:
            with open(plugs_index_path, 'r', encoding='utf-8') as f:
                plugs = json.load(f)

            plug_entry = next((p for p in plugs if p['id'] == connector_id), None)
            if not plug_entry:
                return None

            # Start with the index entry so 'plug_file', 'id', 'name' are always present
            result = dict(plug_entry)

            # Merge in the detailed plug JSON if it exists
            if plug_entry.get('plug_file'):
                detailed_plug_path = os.path.join(base_dir, "dataplugs", plug_entry['plug_file'])
                if os.path.exists(detailed_plug_path):
                    with open(detailed_plug_path, 'r', encoding='utf-8') as f:
                        detailed = json.load(f)
                    result.update(detailed)
                    result['plug_file'] = plug_entry['plug_file']
                    result['id']        = plug_entry['id']
                    result['name']      = plug_entry['name']

            return result
        except Exception as e:
            logger.error(f"Error loading plug metadata for {connector_id}: {e}")
            return None


# --- Global Store Management ---

class DBManager:
    _provider: Optional[DBProvider] = None

    @classmethod
    def get_provider(cls) -> DBProvider:
        if cls._provider is None:
            from src.config import app_config
            store_cfg = app_config.config_store
            
            if store_cfg.type == "postgres":
                cls._provider = PostgresProvider(
                    store_cfg.postgres.host,
                    store_cfg.postgres.port,
                    store_cfg.postgres.database,
                    store_cfg.postgres.user,
                    store_cfg.postgres.password
                )
            else:
                # Default to SQLite
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                db_path = os.path.join(base_dir, store_cfg.sqlite.path)
                cls._provider = SQLiteProvider(db_path)
                
        return cls._provider

    @classmethod
    def reload_provider(cls):
        cls._provider = None

# --- Legacy Functional API Wrappers (for compatibility with existing code) ---

def init_db():
    return DBManager.get_provider().init_db()

def save_config(connector_id: str, config: Dict[str, Any], is_active: bool = False, interval: int = 5):
    return DBManager.get_provider().save_connector_config(connector_id, config, is_active, interval)

def get_all_configs():
    return DBManager.get_provider().get_all_connector_configs()

def get_active_connectors():
    return DBManager.get_provider().get_active_connectors()

def update_scheduler_state(connector_id: str, paused: bool):
    return DBManager.get_provider().update_scheduler_state(connector_id, paused)

def update_connector_stats(connector_id: str, records_count: int):
    return DBManager.get_provider().update_connector_stats(connector_id, records_count)

def get_connector_config(connector_id: str):
    return DBManager.get_provider().get_connector_config(connector_id)

def set_app_config(key: str, value: Any):
    return DBManager.get_provider().set_app_config(key, value)

def get_app_config():
    return DBManager.get_provider().get_app_config()

def save_agent_config(agent_id: str, config: Dict[str, Any], is_active: bool = False, mode: str = "interactive", interval: int = 60, is_paused: bool = False):
    return DBManager.get_provider().save_agent_config(agent_id, config, is_active, mode, interval, is_paused)

def get_all_agent_configs():
    return DBManager.get_provider().get_all_agent_configs()

def set_agent_pause_state(agent_id: str, paused: bool):
    return DBManager.get_provider().set_agent_pause_state(agent_id, paused)

def add_agent_log(agent_id: str, level: str, message: str, trace_data: Optional[Dict[str, Any]] = None):
    return DBManager.get_provider().add_agent_log(agent_id, level, message, trace_data)

def get_agent_logs(agent_id: str, limit: int = 100):
    return DBManager.get_provider().get_agent_logs(agent_id, limit)

def add_agent_activity(agent_id: str, summary: str, action_taken: str, details: Optional[Dict[str, Any]] = None):
    return DBManager.get_provider().add_agent_activity(agent_id, summary, action_taken, details)

def get_agent_activity(agent_id: str, limit: int = 50):
    return DBManager.get_provider().get_agent_activity(agent_id, limit)

def add_pending_action(agent_id: str, description: str, severity: str, command: str = None, action_type: str = "Manual"):
    return DBManager.get_provider().add_pending_action(agent_id, description, severity, command, action_type)

def get_pending_actions(agent_id: str, status: str = "Pending"):
    return DBManager.get_provider().get_pending_actions(agent_id, status)

def update_action_status(action_id: int, status: str):
    return DBManager.get_provider().update_action_status(action_id, status)

def get_active_agents():
    return DBManager.get_provider().get_active_agents()

def update_agent_stats(agent_id: str):
    return DBManager.get_provider().update_agent_stats(agent_id)

def get_pending_action_by_id(action_id: int):
    return DBManager.get_provider().get_pending_action_by_id(action_id)

def get_plug_metadata(connector_id: str):
    return DBManager.get_provider().get_plug_metadata(connector_id)

def reload_db():
    """Forces the DBManager to re-instantiate the provider on the next call."""
    DBManager.reload_provider()

# Initial auto-init for SQLite (keeping startup simple)
if __name__ == "__main__":
    init_db()
