import hashlib
import json
from datetime import datetime, timezone
from data.database import Database

class CacheEngine:
    @staticmethod
    def _normalize_params(parameters: dict | None) -> str:
        if not parameters:
            return ""
        # Deterministic canonical representation with sorted keys and rounded floats
        filtered = {}
        for k, v in sorted(parameters.items()):
            if v is not None:
                if isinstance(v, float):
                    filtered[k] = round(v, 4)
                else:
                    filtered[k] = v
        return json.dumps(filtered, sort_keys=True)

    @staticmethod
    def _compute_key(
        model: str,
        prompt: str,
        tenant_id: str = "default",
        parameters: dict | None = None
    ) -> str:
        """
        Builds a cryptographically scoped cache key by:
        (tenant_id, model, normalized_parameters, prompt_hash)
        """
        norm_tenant = (tenant_id or "default").strip()
        norm_model = (model or "").strip().lower()
        norm_prompt = (prompt or "").strip()
        prompt_hash = hashlib.sha256(norm_prompt.encode("utf-8")).hexdigest()
        norm_params = CacheEngine._normalize_params(parameters)
        payload = f"{norm_tenant}:{norm_model}:{norm_params}:{prompt_hash}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def get(
        model: str,
        prompt: str,
        tenant_id: str = "default",
        parameters: dict | None = None
    ) -> dict | None:
        """
        Retrieves a cached completion if available for the specific tenant and configuration.
        Returns dict with keys ('response', 'tokens', 'cost', 'created_at') or None.
        """
        cache_key = CacheEngine._compute_key(model, prompt, tenant_id=tenant_id, parameters=parameters)
        conn = Database.get_connection()
        c = conn.cursor()
        c.execute("SELECT response, tokens, cost, created_at FROM cache_entries WHERE cache_key = ?", (cache_key,))
        row = c.fetchone()
        conn.close()

        if row:
            return {
                "response": row[0],
                "tokens": row[1],
                "cost": row[2],
                "created_at": row[3],
                "cache_hit": True
            }
        return None

    @staticmethod
    def set(
        model: str,
        prompt: str,
        response: str,
        tokens: int = 0,
        cost: float = 0.0,
        tenant_id: str = "default",
        parameters: dict | None = None
    ):
        """Stores a verified completion in the cache scoped by tenant and parameters."""
        cache_key = CacheEngine._compute_key(model, prompt, tenant_id=tenant_id, parameters=parameters)
        conn = Database.get_connection()
        c = conn.cursor()
        c.execute("""
            INSERT OR REPLACE INTO cache_entries (cache_key, model, prompt, response, tokens, cost, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (cache_key, model, prompt, response, tokens, cost, datetime.now(timezone.utc).isoformat()))
        conn.commit()
        conn.close()

    @staticmethod
    def clear():
        """Clears all cached responses."""
        conn = Database.get_connection()
        c = conn.cursor()
        c.execute("DELETE FROM cache_entries")
        conn.commit()
        conn.close()

    @staticmethod
    def count() -> int:
        """Returns the total number of cached entries."""
        conn = Database.get_connection()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM cache_entries")
        count = c.fetchone()[0]
        conn.close()
        return count

cache = CacheEngine()
