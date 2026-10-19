from datetime import datetime, timezone
import time
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
        c.execute("""INSERT OR REPLACE INTO approval_queue (request_id, user_id, model, prompt, status, created_at)
                     VALUES (?, ?, ?, ?, 'Pending', ?)""",
                  (request_id, user_id, model, prompt, datetime.now(timezone.utc).isoformat()))
        conn.commit()
        conn.close()

    @staticmethod
    def get_request_status(request_id: str) -> dict | None:
        """Retrieves current status and response for a queued or logged request."""
        conn = Database.get_connection()
        c = conn.cursor()
        c.execute("""SELECT request_id, user_id, model, prompt, status, response, tokens, cost, latency, reviewed_by, created_at, reviewed_at
                     FROM approval_queue WHERE request_id = ?""", (request_id,))
        row = c.fetchone()
        conn.close()

        if not row:
            return None

        response_text = row[5]
        if response_text and row[4] == "Approved":
            response_text = crypto.decrypt(response_text)

        return {
            "request_id": row[0],
            "user_id": row[1],
            "model": row[2],
            "prompt": row[3],
            "status": row[4],
            "response": response_text,
            "tokens": row[6],
            "cost": row[7],
            "latency": row[8],
            "reviewed_by": row[9],
            "created_at": row[10],
            "reviewed_at": row[11]
        }

    @staticmethod
    def get_pending_approvals():
        conn = Database.get_connection()
        import pandas as pd
        df = pd.read_sql_query("SELECT * FROM approval_queue WHERE status='Pending' ORDER BY created_at DESC", conn)
        conn.close()
        return df

    @staticmethod
    def get_all_approvals():
        conn = Database.get_connection()
        import pandas as pd
        df = pd.read_sql_query("SELECT * FROM approval_queue ORDER BY created_at DESC", conn)
        conn.close()
        if not df.empty and 'response' in df.columns:
            df['response'] = df['response'].apply(lambda x: crypto.decrypt(x) if x and x.startswith('gAAAAA') else x)
        return df

    @staticmethod
    def approve_request(request_id: str, reviewer: str = "admin") -> dict:
        """
        Approves a queued request, executes it through the model dispatcher,
        persists the response securely, and logs to request_logs.
        """
        from core.llm.provider_dispatcher import dispatcher
        from core.security.input_guards import InputGuards

        conn = Database.get_connection()
        c = conn.cursor()
        c.execute("SELECT user_id, model, prompt FROM approval_queue WHERE request_id = ?", (request_id,))
        row = c.fetchone()
        if not row:
            conn.close()
            return {"error": "Request ID not found in approval queue"}

        user_id, model, raw_prompt = row
        sanitized_prompt, _ = InputGuards.mask_pii(raw_prompt)

        start_time = time.time()
        result = dispatcher.complete(model, [{"role": "user", "content": sanitized_prompt}])
        latency = round(time.time() - start_time, 2)

        if "error" in result:
            err_msg = result["error"].get("message", "Model execution failed")
            c.execute("UPDATE approval_queue SET status='Error', response=?, reviewed_by=?, reviewed_at=? WHERE request_id=?",
                      (err_msg, reviewer, datetime.now(timezone.utc).isoformat(), request_id))
            conn.commit()
            conn.close()
            return {"status": "Error", "error": err_msg}

        llm_response = result["choices"][0]["message"]["content"]
        tokens = result.get("usage", {}).get("total_tokens", 0)
        cost = (tokens / 1000) * 0.002

        encrypted_response = crypto.encrypt(llm_response)
        reviewed_at = datetime.now(timezone.utc).isoformat()

        # Update approval queue
        c.execute("""UPDATE approval_queue 
                     SET status='Approved', response=?, tokens=?, cost=?, latency=?, reviewed_by=?, reviewed_at=?
                     WHERE request_id=?""",
                  (encrypted_response, tokens, cost, latency, reviewer, reviewed_at, request_id))
        conn.commit()
        conn.close()

        # Log into main request audit trail
        Repository.log_request(request_id, user_id, model, raw_prompt, llm_response, tokens, cost, 50, latency)

        return {
            "status": "Approved",
            "request_id": request_id,
            "response": llm_response,
            "tokens": tokens,
            "cost": cost,
            "latency": latency
        }

    @staticmethod
    def deny_request(request_id: str, reviewer: str = "admin", reason: str = "Request denied by security administrator."):
        conn = Database.get_connection()
        c = conn.cursor()
        c.execute("""UPDATE approval_queue 
                     SET status='Denied', response=?, reviewed_by=?, reviewed_at=?
                     WHERE request_id=?""",
                  (reason, reviewer, datetime.now(timezone.utc).isoformat(), request_id))
        conn.commit()
        conn.close()
        return {"status": "Denied", "request_id": request_id, "reason": reason}
