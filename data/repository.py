from datetime import datetime, timezone
from data.database import Database
from core.crypto import crypto

class Repository:
    @staticmethod
    def log_request(request_id, user_id, model, prompt, response, tokens, cost, risk_score, latency):
        conn = Database.get_connection()
        c = conn.cursor()
        encrypted_response = crypto.encrypt(response)
        c.execute("""INSERT INTO request_logs 
                     (request_id, user_id, model, prompt, response, tokens, cost, risk_score, latency, created_at)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                  (request_id, user_id, model, prompt, encrypted_response, tokens, cost, risk_score, latency, 
                   datetime.now(timezone.utc).isoformat()))
        conn.commit()
        conn.close()

    @staticmethod
    def log_harmful(request_id, user_id, prompt, category, risk_score):
        conn = Database.get_connection()
        c = conn.cursor()
        c.execute("""INSERT INTO harmful_logs 
                     (request_id, user_id, prompt, category, risk_score, created_at)
                     VALUES (?, ?, ?, ?, ?, ?)""",
                  (request_id, user_id, prompt, category, risk_score, 
                   datetime.now(timezone.utc).isoformat()))
        conn.commit()
        conn.close()

    @staticmethod
    def add_to_approval_queue(request_id, user_id, model, prompt):
        conn = Database.get_connection()
        c = conn.cursor()
        c.execute("""INSERT INTO approval_queue (request_id, user_id, model, prompt, created_at)
                     VALUES (?, ?, ?, ?, ?)""",
                  (request_id, user_id, model, prompt, datetime.now(timezone.utc).isoformat()))
        conn.commit()
        conn.close()

    @staticmethod
    def get_pending_approvals():
        conn = Database.get_connection()
        import pandas as pd
        df = pd.read_sql_query("SELECT * FROM approval_queue WHERE status='Pending' ORDER BY created_at DESC", conn)
        conn.close()
        return df

    @staticmethod
    def approve_request(request_id):
        conn = Database.get_connection()
        c = conn.cursor()
        c.execute("UPDATE approval_queue SET status=?, reviewed_at=? WHERE request_id=?",
                  ("Approved", datetime.now(timezone.utc).isoformat(), request_id))
        conn.commit()
        conn.close()

    @staticmethod
    def deny_request(request_id):
        conn = Database.get_connection()
        c = conn.cursor()
        c.execute("UPDATE approval_queue SET status=?, reviewed_at=? WHERE request_id=?",
                  ("Denied", datetime.now(timezone.utc).isoformat(), request_id))
        conn.commit()
        conn.close()
