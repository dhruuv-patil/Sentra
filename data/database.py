import sqlite3
from core.config import config

class Database:
    @staticmethod
    def get_connection():
        return sqlite3.connect(config.DATABASE)

    @staticmethod
    def init_db():
        conn = Database.get_connection()
        c = conn.cursor()
        
        # Request Logs Table
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
        
        # Harmful Logs Table
        c.execute('''CREATE TABLE IF NOT EXISTS harmful_logs
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      request_id TEXT,
                      user_id TEXT,
                      prompt TEXT,
                      category TEXT,
                      risk_score INTEGER,
                      created_at TEXT)''')
        
        # Approval Queue Table
        c.execute('''CREATE TABLE IF NOT EXISTS approval_queue
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      request_id TEXT,
                      user_id TEXT,
                      model TEXT,
                      prompt TEXT,
                      status TEXT DEFAULT 'Pending',
                      created_at TEXT,
                      reviewed_at TEXT)''')
        
        conn.commit()
        conn.close()
