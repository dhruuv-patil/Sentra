import hashlib
from datetime import datetime, timezone
from data.database import Database

class CacheEngine:
    @staticmethod
    def _compute_key(model: str, prompt: str) -> str:
        payload = f"{model.strip().lower()}:{prompt.strip()}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def get(model: str, prompt: str) -> dict | None:
        """
        Retrieves a cached completion if available.
        Returns dict with keys ('response', 'tokens', 'cost', 'created_at') or None.
        """
        cache_key = CacheEngine._compute_key(model, prompt)
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
    def set(model: str, prompt: str, response: str, tokens: int = 0, cost: float = 0.0):
        """Stores a verified completion in the cache."""
        cache_key = CacheEngine._compute_key(model, prompt)
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
