import csv
import os
from datetime import datetime
from pathlib import Path

class ConnectorLogger:
    """
    Handles CSV-based logging for a specific connector run.
    Logs are saved to Evident/evident/data/livedata/debug_logs/YYYYMMDD_HHMMSS_{plugname}.csv
    """
    def __init__(self, connector_id: str):
        self.connector_id = connector_id
        
        # Resolve absolute path for logs directory (Evident/evident)
        # __file__ is c:\PRODDEV\personal\cybersecurity-ai\Evident\evident\connectors\logger_util.py
        base_dir = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))) # Project root (c:\PRODDEV\personal\cybersecurity-ai)
        self.log_dir = base_dir / "Evident" / "evident" / "data" / "livedata" / "debug_logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.filename = self.log_dir / f"{timestamp}_{connector_id}.csv"
        
        print(f"[LOGGER] Initializing new log file: {self.filename}")
        
        # Initialize the CSV file with headers
        try:
            with open(self.filename, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Timestamp", "Level", "Component", "Message"])
        except Exception as e:
            print(f"[ERROR] Failed to initialize log file {self.filename}: {e}")

    def log(self, level: str, component: str, message: str):
        """Append a log entry to the CSV file and print to console."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Print to server console for immediate visibility
        print(f"[{timestamp}] [{level}] [{component}] {message}")
        
        try:
            with open(self.filename, mode='a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([timestamp, level, component, message])
        except Exception as e:
            # Fallback to standard logging if CSV write fails
            import logging
            logging.getLogger(__name__).error(f"Failed to write to CSV log {self.filename}: {e}")

    def info(self, component: str, message: str):
        self.log("INFO", component, message)

    def error(self, component: str, message: str):
        self.log("ERROR", component, message)

    def warning(self, component: str, message: str):
        self.log("WARNING", component, message)
