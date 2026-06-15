import sqlite3
import json
import time
import os

class AuditLogger:
    def __init__(self, db_path: str = "audit.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    event_type TEXT,
                    backend TEXT,
                    payload TEXT,
                    status_code INTEGER,
                    error TEXT
                )
            ''')
            
    def log_event(self, event_type: str, backend: str, payload: dict, status_code: int = None, error: str = None):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO audit_events (timestamp, event_type, backend, payload, status_code, error) VALUES (?, ?, ?, ?, ?, ?)",
                    (time.time(), event_type, backend, json.dumps(payload), status_code, error)
                )
        except Exception as e:
            print(f"Failed to write to audit log: {e}")

# Global audit logger instance
db_file = os.path.join(os.path.dirname(__file__), "..", "audit.db")
audit_logger = AuditLogger(db_file)
