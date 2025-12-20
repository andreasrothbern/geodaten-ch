"""
Cache Service
==============

SQLite-basierter Cache für API-Responses
"""

import sqlite3
import json
import os
from datetime import datetime, timedelta
from typing import Optional, Any
import threading


class CacheService:
    """SQLite-basierter Cache"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.getenv("CACHE_DB_PATH", "cache.db")
        self._local = threading.local()
    
    @property
    def _conn(self) -> sqlite3.Connection:
        """Thread-lokale Datenbankverbindung"""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn
    
    def initialize(self):
        """Cache-Tabelle erstellen"""
        cursor = self._conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_expires ON cache(expires_at)")
        self._conn.commit()
        
        # Alte Einträge löschen
        self._cleanup()
        print(f"✅ Cache initialisiert: {self.db_path}")
    
    def get(self, key: str) -> Optional[Any]:
        """Wert aus Cache holen"""
        cursor = self._conn.cursor()
        cursor.execute(
            "SELECT value FROM cache WHERE key = ? AND expires_at > ?",
            (key, datetime.now().isoformat())
        )
        row = cursor.fetchone()
        
        if row:
            try:
                return json.loads(row["value"])
            except json.JSONDecodeError:
                return row["value"]
        return None
    
    def set(self, key: str, value: Any, ttl_hours: int = 1) -> bool:
        """Wert in Cache speichern"""
        expires_at = datetime.now() + timedelta(hours=ttl_hours)
        
        try:
            value_json = json.dumps(value, default=str)
        except (TypeError, ValueError):
            value_json = str(value)
        
        cursor = self._conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO cache (key, value, expires_at)
            VALUES (?, ?, ?)
            """,
            (key, value_json, expires_at.isoformat())
        )
        self._conn.commit()
        return True
    
    def delete(self, key: str) -> bool:
        """Wert aus Cache löschen"""
        cursor = self._conn.cursor()
        cursor.execute("DELETE FROM cache WHERE key = ?", (key,))
        self._conn.commit()
        return cursor.rowcount > 0
    
    def clear(self) -> int:
        """Gesamten Cache leeren"""
        cursor = self._conn.cursor()
        cursor.execute("DELETE FROM cache")
        count = cursor.rowcount
        self._conn.commit()
        return count
    
    def _cleanup(self) -> int:
        """Abgelaufene Einträge löschen"""
        cursor = self._conn.cursor()
        cursor.execute(
            "DELETE FROM cache WHERE expires_at < ?",
            (datetime.now().isoformat(),)
        )
        count = cursor.rowcount
        self._conn.commit()
        if count > 0:
            print(f"🧹 {count} abgelaufene Cache-Einträge gelöscht")
        return count
    
    def stats(self) -> dict:
        """Cache-Statistiken"""
        cursor = self._conn.cursor()
        
        cursor.execute("SELECT COUNT(*) as total FROM cache")
        total = cursor.fetchone()["total"]
        
        cursor.execute(
            "SELECT COUNT(*) as valid FROM cache WHERE expires_at > ?",
            (datetime.now().isoformat(),)
        )
        valid = cursor.fetchone()["valid"]
        
        # Datenbankgrösse
        db_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
        
        return {
            "total_entries": total,
            "valid_entries": valid,
            "expired_entries": total - valid,
            "db_size_kb": round(db_size / 1024, 2),
        }
    
    def close(self):
        """Verbindung schliessen"""
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None
