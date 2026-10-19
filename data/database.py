import sqlite3
from core.config import config

class Database:
    @staticmethod
    def get_connection():
        conn = sqlite3.connect(config.DATABASE, timeout=20.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=20000;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    @staticmethod
    def init_db():
        conn = Database.get_connection()
        c = conn.cursor()
        
        # 1. Request Logs Table
        c.execute('''CREATE TABLE IF NOT EXISTS request_logs
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      request_id TEXT,
                      user_id TEXT,
                      model TEXT,
                      prompt TEXT,
                      response TEXT,
                      tokens INTEGER,
                      cost REAL,
                      risk_score INTEGER,
                      latency REAL,
                      created_at TEXT)''')
        
        # 2. Harmful Logs Table
        c.execute('''CREATE TABLE IF NOT EXISTS harmful_logs
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      request_id TEXT,
                      user_id TEXT,
                      prompt TEXT,
                      category TEXT,
                      risk_score INTEGER,
                      created_at TEXT)''')
        
        # 3. Approval Queue Table
        c.execute('''CREATE TABLE IF NOT EXISTS approval_queue
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      request_id TEXT UNIQUE,
                      user_id TEXT,
                      model TEXT,
                      prompt TEXT,
                      status TEXT DEFAULT 'Pending',
                      response TEXT,
                      tokens INTEGER,
                      cost REAL,
                      latency REAL,
                      reviewed_by TEXT,
                      created_at TEXT,
                      reviewed_at TEXT)''')

        # Run safe column migrations for approval_queue if table previously existed
        existing_cols = [row[1] for row in c.execute("PRAGMA table_info(approval_queue)").fetchall()]
        for col_name, col_type in [
            ("response", "TEXT"),
            ("tokens", "INTEGER"),
            ("cost", "REAL"),
            ("latency", "REAL"),
            ("reviewed_by", "TEXT"),
        ]:
            if col_name not in existing_cols:
                c.execute(f"ALTER TABLE approval_queue ADD COLUMN {col_name} {col_type}")
        
        # 4. Cache Entries Table
        c.execute('''CREATE TABLE IF NOT EXISTS cache_entries
                     (cache_key TEXT PRIMARY KEY,
                      model TEXT,
                      prompt TEXT,
                      response TEXT,
                      tokens INTEGER,
                      cost REAL,
                      created_at TEXT)''')

        conn.commit()
        conn.close()
