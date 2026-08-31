import sqlite3
import os
import sys

if getattr(sys, 'frozen', False):
    _base_dir = os.path.dirname(sys.executable)
else:
    _base_dir = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(_base_dir, "scheduling_state.db")

def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 30000;")
    return conn

def init_sqlite_db():
    schema_path = os.path.join(os.path.dirname(__file__), "..", "schema.sql")
    if os.path.exists(schema_path):
        with open(schema_path, "r") as f:
            schema = f.read()
    else:
        # Fallback inline schema definitions (Identical to schema.sql for reliability)
        schema = """
        CREATE TABLE IF NOT EXISTS app_state (state_key TEXT PRIMARY KEY, state_value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS assignments (
            order_id TEXT PRIMARY KEY, sap_order_number TEXT, machine_name TEXT, queue_position INTEGER NOT NULL,
            status TEXT NOT NULL, original_qty INTEGER NOT NULL, completed_qty INTEGER DEFAULT 0,
            remaining_qty INTEGER NOT NULL, estimated_time REAL, tool_code TEXT NOT NULL,
            tool_desc TEXT, open_date TEXT, last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS status_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            event_type TEXT NOT NULL, order_id TEXT, machine_name TEXT, before_status TEXT,
            after_status TEXT, before_position INTEGER, after_position INTEGER, qty_change INTEGER, justification TEXT
        );
        CREATE TABLE IF NOT EXISTS machines_cache (machine_name TEXT PRIMARY KEY, last_updated DATETIME DEFAULT CURRENT_TIMESTAMP);
        INSERT OR IGNORE INTO app_state (state_key, state_value) VALUES ('mode', 'planning');
        """
    with get_connection() as conn:
        conn.executescript(schema)

def get_app_mode():
    with get_connection() as conn:
        row = conn.execute("SELECT state_value FROM app_state WHERE state_key = 'mode'").fetchone()
        return row['state_value'] if row else 'planning'

def set_app_mode(mode):
    with get_connection() as conn:
        conn.execute("INSERT OR REPLACE INTO app_state (state_key, state_value) VALUES ('mode', ?)", (mode,))
        conn.commit()

def log_status_event(event_type, order_id, machine_name, before_status, after_status, before_pos=None, after_pos=None, qty_change=None, justification=None, conn=None):
    if conn is not None:
        conn.execute(
            """INSERT INTO status_log 
               (event_type, order_id, machine_name, before_status, after_status, before_position, after_position, qty_change, justification) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (event_type, order_id, machine_name, before_status, after_status, before_pos, after_pos, qty_change, justification)
        )
    else:
        with get_connection() as conn:
            conn.execute(
                """INSERT INTO status_log 
                   (event_type, order_id, machine_name, before_status, after_status, before_position, after_position, qty_change, justification) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (event_type, order_id, machine_name, before_status, after_status, before_pos, after_pos, qty_change, justification)
            )
            conn.commit()

def save_machines_cache(machines):
    with get_connection() as conn:
        conn.execute("DELETE FROM machines_cache")
        for m in machines:
            conn.execute("INSERT INTO machines_cache (machine_name) VALUES (?)", (m['machine_name'],))
        conn.commit()

def get_cached_machines():
    with get_connection() as conn:
        rows = conn.execute("SELECT machine_name FROM machines_cache").fetchall()
        return [row['machine_name'] for row in rows]
