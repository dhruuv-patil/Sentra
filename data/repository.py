from datetime import datetime, timezone
import time
import hmac
from data.database import Database
from core.crypto import crypto
from core.config import config
from core.security.input_guards import InputGuards

class Repository:
    @staticmethod
    def validate_token(raw_token: str) -> dict | None:
        """
        Validates an API token or bearer secret using constant-time comparison.
        Returns token identity metadata or None if invalid.
        """
        if not raw_token or not isinstance(raw_token, str):
            return None

        # 1. Master admin secret validation (constant time)
        admin_secret = config.SECRET_KEY
        if admin_secret and hmac.compare_digest(raw_token, admin_secret):
            return {
                "id": 0,
                "name": "Admin Master",
                "provider": "All",
                "scope": "admin",
                "tenant_id": "admin"
            }

        # 2. Database active tokens check (constant time per token)
        conn = Database.get_connection()
        c = conn.cursor()
        rows = c.execute("SELECT id, token, name, provider, scope, active FROM api_tokens WHERE active = 1").fetchall()
        conn.close()

        matched_row = None
        for r in rows:
            token_val = r[1]
            if hmac.compare_digest(raw_token, token_val):
                matched_row = r
                break

        if matched_row:
            # Update last_used_at timestamp
            conn_up = Database.get_connection()
            c_up = conn_up.cursor()
            c_up.execute("UPDATE api_tokens SET last_used_at = ? WHERE id = ?",
                         (datetime.now(timezone.utc).isoformat(), matched_row[0]))
            conn_up.commit()
            conn_up.close()
            return {
                "id": matched_row[0],
                "name": matched_row[2],
                "provider": matched_row[3],
                "scope": matched_row[4],
                "tenant_id": f"tenant_{matched_row[0]}"
            }

        return None

    @staticmethod
    def is_model_allowed_for_tenant(identity: dict, model_spec: str) -> tuple[bool, str | None]:
        """
        Enforces tenant model restrictions and air-gapped sovereignty policies.
        Returns (is_allowed, denial_reason).
        """
        from core.llm.provider_dispatcher import ProviderDispatcher
        provider, model_name = ProviderDispatcher.parse_spec(model_spec)

        # 1. Global Air-gapped / Offline mode restriction
        if getattr(config, "AIRGAPPED_MODE", False):
            if provider != "ollama":
                return False, f"Cloud provider '{provider}' is disabled in air-gapped / offline deployment. Only local sovereign models (e.g. 'ollama/*') are permitted."

        # 2. Admin scope bypasses tenant model whitelist
        scope = identity.get("scope", "")
        if scope == "admin" or identity.get("tenant_id") == "admin":
            return True, None

        # 3. Tenant provider policy from token metadata
        allowed_policy = identity.get("provider", "All")
        if not allowed_policy or allowed_policy in ("All", "All Models", "*"):
            return True, None

        pol_lower = allowed_policy.lower()
        if "groq" in pol_lower and provider == "groq":
            return True, None
        if "ollama" in pol_lower and provider == "ollama":
            return True, None

        return False, f"Tenant is restricted to '{allowed_policy}', but requested provider '{provider}' ({model_spec})."

    @staticmethod
    def log_request(request_id, user_id, model, prompt, response, tokens, cost, risk_score, latency):
        """Logs a completed request. Ensures prompt is PII-sanitized and response is encrypted."""
        sanitized_prompt, _ = InputGuards.mask_pii(prompt or "")
        encrypted_response = crypto.encrypt(response or "")

        conn = Database.get_connection()
        c = conn.cursor()
        c.execute("""INSERT INTO request_logs 
                     (request_id, user_id, model, prompt, response, tokens, cost, risk_score, latency, created_at)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                  (request_id, user_id, model, sanitized_prompt, encrypted_response, tokens, cost, risk_score, latency, 
                   datetime.now(timezone.utc).isoformat()))
        conn.commit()
        conn.close()

    @staticmethod
    def log_harmful(request_id, user_id, prompt, category, risk_score):
        """Logs a harmful violation with sanitized prompt."""
        sanitized_prompt, _ = InputGuards.mask_pii(prompt or "")
        conn = Database.get_connection()
        c = conn.cursor()
        c.execute("""INSERT INTO harmful_logs 
                     (request_id, user_id, prompt, category, risk_score, created_at)
                     VALUES (?, ?, ?, ?, ?, ?)""",
                  (request_id, user_id, sanitized_prompt, category, risk_score, 
                   datetime.now(timezone.utc).isoformat()))
        conn.commit()
        conn.close()

    @staticmethod
    def add_to_approval_queue(request_id, user_id, model, prompt):
        """Places a high-risk interaction into the approval queue with sanitized prompt."""
        sanitized_prompt, _ = InputGuards.mask_pii(prompt or "")
        conn = Database.get_connection()
        c = conn.cursor()
        c.execute("""INSERT OR REPLACE INTO approval_queue (request_id, user_id, model, prompt, status, created_at)
                     VALUES (?, ?, ?, ?, 'Pending', ?)""",
                  (request_id, user_id, model, sanitized_prompt, datetime.now(timezone.utc).isoformat()))
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
            df['response'] = df['response'].apply(lambda x: crypto.decrypt(x) if isinstance(x, str) and x.startswith('gAAAAA') else x)
        return df

    @staticmethod
    def approve_request(request_id: str, reviewer: str = "admin") -> dict:
        """
        Approves a queued request, executes it through the model dispatcher,
        persists the response securely, and logs to request_logs.
        """
        from core.llm.provider_dispatcher import dispatcher

        conn = Database.get_connection()
        c = conn.cursor()
        c.execute("SELECT user_id, model, prompt FROM approval_queue WHERE request_id = ?", (request_id,))
        row = c.fetchone()
        if not row:
            conn.close()
            return {"error": "Request ID not found in approval queue"}

        user_id, model, stored_prompt = row
        sanitized_prompt, _ = InputGuards.mask_pii(stored_prompt)

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

        # Log into main request audit trail (stores sanitized prompt)
        Repository.log_request(request_id, user_id, model, sanitized_prompt, llm_response, tokens, cost, 50, latency)

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

    @staticmethod
    def get_dashboard_metrics(time_filter: str = "all") -> dict:
        """
        Aggregates dashboard metrics strictly from verified SQLite records.
        Zero fabricated numbers: every count, token sum, and rate is derived from database rows.
        """
        conn = Database.get_connection()
        c = conn.cursor()

        # Query live counts
        total_reqs = c.execute("SELECT COUNT(*) FROM request_logs").fetchone()[0] or 0
        total_tokens = c.execute("SELECT SUM(tokens) FROM request_logs").fetchone()[0] or 0
        total_cost = c.execute("SELECT SUM(cost) FROM request_logs").fetchone()[0] or 0.0
        harmful_count = c.execute("SELECT COUNT(*) FROM harmful_logs").fetchone()[0] or 0
        pending_count = c.execute("SELECT COUNT(*) FROM approval_queue WHERE status='Pending'").fetchone()[0] or 0
        high_risk_count = c.execute("SELECT COUNT(*) FROM request_logs WHERE risk_score > 50").fetchone()[0] or 0

        # Model usage stats
        model_counts = c.execute("SELECT model, COUNT(*) as cnt FROM request_logs GROUP BY model ORDER BY cnt DESC").fetchall()
        user_counts = c.execute("SELECT user_id, COUNT(*) as cnt FROM request_logs GROUP BY user_id ORDER BY cnt DESC LIMIT 5").fetchall()
        active_policies = c.execute("SELECT COUNT(*) FROM guardrail_policies WHERE enabled = 1").fetchone()[0] or 0

        conn.close()

        # True derived metrics
        blocked_prompts = harmful_count + high_risk_count
        prompts_sent = total_reqs + harmful_count
        blocked_pct = round((blocked_prompts / max(prompts_sent, 1)) * 100, 1) if prompts_sent > 0 else 0.0

        most_used_model = model_counts[0][0] if model_counts else "None"
        least_used_model = model_counts[-1][0] if len(model_counts) > 1 else most_used_model

        most_blocked_users = [
            {"rank": idx + 1, "user_id": r[0], "requests": r[1]}
            for idx, r in enumerate(user_counts)
        ]

        connections_usage = [
            {"model": r[0], "count": r[1]}
            for r in model_counts[:5]
        ]

        return {
            "summary": {
                "blocked_prompts": blocked_prompts,
                "prompts_sent": prompts_sent,
                "blocked_rate": blocked_pct,
                "blocked_responses": harmful_count,
                "most_used_model": most_used_model,
                "least_used_model": least_used_model,
                "total_tokens": total_tokens,
                "total_cost": round(total_cost, 4),
                "pending_approvals": pending_count,
            },
            "active_policies_count": active_policies,
            "most_active_users": most_blocked_users,
            "model_breakdown": connections_usage
        }

    @staticmethod
    def get_audit_logs(limit: int = 100, offset: int = 0, search: str = None, model: str = None, risk_filter: str = None) -> dict:
        conn = Database.get_connection()
        c = conn.cursor()

        query = "SELECT id, request_id, user_id, model, prompt, response, tokens, cost, risk_score, latency, created_at FROM request_logs WHERE 1=1"
        params = []

        if search:
            query += " AND (prompt LIKE ? OR request_id LIKE ? OR user_id LIKE ?)"
            term = f"%{search}%"
            params.extend([term, term, term])

        if model:
            query += " AND model = ?"
            params.append(model)

        if risk_filter == "high":
            query += " AND risk_score > 50"
        elif risk_filter == "low":
            query += " AND risk_score <= 50"

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = c.execute(query, params).fetchall()

        logs = []
        for r in rows:
            resp = r[5]
            if resp and isinstance(resp, str) and resp.startswith("gAAAAA"):
                try:
                    resp = crypto.decrypt(resp)
                except Exception:
                    pass
            logs.append({
                "id": r[0],
                "request_id": r[1],
                "user_id": r[2],
                "model": r[3],
                "prompt": r[4],
                "response": resp,
                "tokens": r[6],
                "cost": r[7],
                "risk_score": r[8],
                "latency": r[9],
                "created_at": r[10]
            })

        total = c.execute("SELECT COUNT(*) FROM request_logs").fetchone()[0]
        conn.close()
        return {"total": total, "logs": logs}

    @staticmethod
    def get_harmful_logs(limit: int = 100) -> list:
        conn = Database.get_connection()
        c = conn.cursor()
        rows = c.execute("""SELECT id, request_id, user_id, prompt, category, risk_score, created_at 
                            FROM harmful_logs ORDER BY created_at DESC LIMIT ?""", (limit,)).fetchall()
        conn.close()
        return [
            {
                "id": r[0],
                "request_id": r[1],
                "user_id": r[2],
                "prompt": r[3],
                "category": r[4],
                "risk_score": r[5],
                "created_at": r[6]
            }
            for r in rows
        ]

    @staticmethod
    def get_guardrail_policies() -> list:
        conn = Database.get_connection()
        c = conn.cursor()
        rows = c.execute("""SELECT id, key, name, description, category, enabled, action, sensitivity, triggers_count, updated_at 
                            FROM guardrail_policies ORDER BY id ASC""").fetchall()
        conn.close()
        return [
            {
                "id": r[0],
                "key": r[1],
                "name": r[2],
                "description": r[3],
                "category": r[4],
                "enabled": bool(r[5]),
                "action": r[6],
                "sensitivity": r[7],
                "triggers_count": r[8],
                "updated_at": r[9]
            }
            for r in rows
        ]

    @staticmethod
    def toggle_guardrail_policy(key: str, enabled: bool = None, action: str = None, sensitivity: float = None) -> dict:
        conn = Database.get_connection()
        c = conn.cursor()
        
        updates = []
        params = []
        if enabled is not None:
            updates.append("enabled = ?")
            params.append(1 if enabled else 0)
        if action is not None:
            updates.append("action = ?")
            params.append(action)
        if sensitivity is not None:
            updates.append("sensitivity = ?")
            params.append(sensitivity)

        updates.append("updated_at = datetime('now')")
        params.append(key)

        query = f"UPDATE guardrail_policies SET {', '.join(updates)} WHERE key = ?"
        c.execute(query, params)
        conn.commit()
        conn.close()
        return {"status": "success", "key": key}

    @staticmethod
    def get_api_tokens() -> list:
        conn = Database.get_connection()
        c = conn.cursor()
        rows = c.execute("""SELECT id, token, name, provider, scope, created_at, last_used_at, active 
                            FROM api_tokens ORDER BY id DESC""").fetchall()
        conn.close()
        return [
            {
                "id": r[0],
                "token": r[1],
                "name": r[2],
                "provider": r[3],
                "scope": r[4],
                "created_at": r[5],
                "last_used_at": r[6],
                "active": bool(r[7])
            }
            for r in rows
        ]

    @staticmethod
    def create_api_token(name: str, provider: str = "All Models", scope: str = "read:write") -> dict:
        import secrets
        raw_token = f"sg_live_{secrets.token_hex(16)}"
        conn = Database.get_connection()
        c = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()
        c.execute("""INSERT INTO api_tokens (token, name, provider, scope, created_at, last_used_at, active)
                     VALUES (?, ?, ?, ?, ?, ?, 1)""", (raw_token, name, provider, scope, now, now))
        token_id = c.lastrowid
        conn.commit()
        conn.close()
        return {
            "id": token_id,
            "token": raw_token,
            "name": name,
            "provider": provider,
            "scope": scope,
            "created_at": now
        }

    @staticmethod
    def delete_api_token(token_id: int) -> dict:
        conn = Database.get_connection()
        c = conn.cursor()
        c.execute("DELETE FROM api_tokens WHERE id = ?", (token_id,))
        conn.commit()
        conn.close()
        return {"status": "deleted", "id": token_id}
