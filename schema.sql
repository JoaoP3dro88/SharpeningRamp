-- SQLite Schema (schema.sql)

CREATE TABLE IF NOT EXISTS app_state (
    state_key TEXT PRIMARY KEY,
    state_value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS assignments (
    order_id TEXT PRIMARY KEY,
    sap_order_number TEXT,
    machine_name TEXT,
    queue_position INTEGER NOT NULL,
    status TEXT NOT NULL,
    original_qty INTEGER NOT NULL,
    completed_qty INTEGER DEFAULT 0,
    remaining_qty INTEGER NOT NULL,
    estimated_time REAL,
    tool_code TEXT NOT NULL,
    tool_desc TEXT,
    open_date TEXT,
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS status_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    event_type TEXT NOT NULL,
    order_id TEXT,
    machine_name TEXT,
    before_status TEXT,
    after_status TEXT,
    before_position INTEGER,
    after_position INTEGER,
    qty_change INTEGER,
    justification TEXT
);

CREATE TABLE IF NOT EXISTS machines_cache (
    machine_name TEXT PRIMARY KEY,
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
);

INSERT OR IGNORE INTO app_state (state_key, state_value) VALUES ('mode', 'planning');
