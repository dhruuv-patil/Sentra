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

        # 5. API Tokens Table
        c.execute('''CREATE TABLE IF NOT EXISTS api_tokens
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      token TEXT UNIQUE,
                      name TEXT,
                      provider TEXT DEFAULT 'All',
                      scope TEXT DEFAULT 'read:write',
                      created_at TEXT,
                      last_used_at TEXT,
                      active INTEGER DEFAULT 1)''')

        # 6. Guardrail Policies Table
        c.execute('''CREATE TABLE IF NOT EXISTS guardrail_policies
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      key TEXT UNIQUE,
                      name TEXT,
                      description TEXT,
                      category TEXT,
                      enabled INTEGER DEFAULT 1,
                      action TEXT DEFAULT 'BLOCK',
                      sensitivity REAL DEFAULT 0.75,
                      triggers_count INTEGER DEFAULT 0,
                      updated_at TEXT)''')

        # Seed default guardrails if empty
        existing_guards = c.execute("SELECT COUNT(*) FROM guardrail_policies").fetchone()[0]
        if existing_guards == 0:
            default_guards = [
                ("prompt_injection", "Prompt Injection Shield", "Heuristic adversarial jailbreak & DAN defense with Base64 recursion", "INPUT", 1, "BLOCK", 0.85, 0),
                ("pii_masker", "SSN & PII Anonymizer", "Masks SSN, credit cards, emails, phone numbers, and API tokens before upstream dispatch", "INPUT", 1, "REDACT", 0.90, 0),
                ("context_scanner_v3", "Context Scanner v3", "Deep context semantic scanner analyzing prompt intent and policy alignment", "INPUT", 1, "BLOCK", 0.80, 0),
                ("output_harm_guard", "Harmful Output & System Leakage", "Detects system prompt leakage, toxic output, and instructions disclosure", "OUTPUT", 1, "BLOCK", 0.75, 0),
                ("high_risk_hitl", "High-Risk HITL Gate", "Queues prompts exceeding risk threshold (Score > 50) for human authorization", "POLICY", 1, "QUEUE", 0.50, 0),
                ("regex_firewall", "Regex Behavioral Firewall", "Custom regex rule matcher for proprietary tokens and sensitive keywords", "FILTER", 1, "BLOCK", 0.95, 0),
            ]
            for g in default_guards:
                c.execute("""INSERT OR IGNORE INTO guardrail_policies 
                             (key, name, description, category, enabled, action, sensitivity, triggers_count, updated_at)
                             VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))""", g)

        # Seed initial tokens if empty
        existing_tokens = c.execute("SELECT COUNT(*) FROM api_tokens").fetchone()[0]
        if existing_tokens == 0:
            sample_tokens = [
                ("sg_live_948f98c8e19b489d82a17f", "Production Service Token", "All Models", "read:write", "2026-03-10T08:00:00Z", "2026-04-07T12:44:00Z", 1),
                ("sg_live_732a10e44b918f0a99c3de", "Staging Client Token", "Groq Models", "read:write", "2026-03-15T09:30:00Z", "2026-04-06T19:20:00Z", 1),
                ("sg_test_11a84f3cd789e023ba78cc", "Developer Sandbox", "Ollama Local", "read", "2026-04-01T14:15:00Z", "2026-04-07T11:05:00Z", 1),
            ]
            for t in sample_tokens:
                c.execute("""INSERT OR IGNORE INTO api_tokens 
                             (token, name, provider, scope, created_at, last_used_at, active)
                             VALUES (?, ?, ?, ?, ?, ?, ?)""", t)

        conn.commit()
        conn.close()
