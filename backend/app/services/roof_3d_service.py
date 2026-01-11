"""
Roof 3D Data Service
====================

Service für Dach-Daten aus swissBUILDINGS3D 3.0 Roof_solid Layer.

Zwei Modi:
1. **Pre-Import (Batch):** Nur berechnete Werte (Dachform, Neigung, Z-Levels)
2. **On-Demand:** Vollständige 3D-Geometrie für komplexe Gebäude

Schema:
    building_roofs (
        id INTEGER PRIMARY KEY,
        gebaeudeeinheit TEXT NOT NULL,  -- Verknüpfung zu buildings_3d
        egid TEXT,
        dach_min REAL,                  -- Traufhöhe (m ü.M.)
        dach_max REAL,                  -- Firsthöhe (m ü.M.)
        roof_form TEXT,                 -- 'flachdach', 'satteldach', etc.
        roof_angle_deg REAL,            -- Berechnete Neigung
        roof_orientation TEXT,          -- First-Verlauf
        z_levels TEXT,                  -- JSON: [546.9, 551.0, ...]
        geometry_wkb BLOB,              -- 3D-Geometrie (NULL bei Pre-Import)
        has_full_geometry INTEGER,
        calculated_at TIMESTAMP,
        calculation_method TEXT
    )

Version: 1.0 (11.01.2026)
"""

import sqlite3
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Pfad zur Datenbank (gleiche wie buildings_3d)
DATA_DIR = Path(__file__).parent.parent / "data"
BUILDING_3D_DB = DATA_DIR / "building_3d.db"


class Roof3DService:
    """
    Service für Dach-Daten aus Roof_solid Layer.

    Speichert:
    - Berechnete Dachform (Pre-Import)
    - Z-Level-Verteilung für Analyse
    - Optionale 3D-Geometrie (on-demand)
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

    @contextmanager
    def _get_connection(self):
        """Erstellt eine Datenbankverbindung."""
        conn = sqlite3.connect(BUILDING_3D_DB)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        try:
            yield conn
        finally:
            conn.close()

    def save(self, roof: Dict[str, Any]) -> bool:
        """
        Speichert Dach-Daten.

        Args:
            roof: Dict mit gebaeudeeinheit, dach_min, dach_max, roof_form, etc.

        Returns:
            True bei Erfolg
        """
        gebaeudeeinheit = roof.get('gebaeudeeinheit')
        if not gebaeudeeinheit:
            logger.warning("Cannot save roof without gebaeudeeinheit")
            return False

        # Z-Levels zu JSON serialisieren
        z_levels = roof.get('z_levels')
        if z_levels and not isinstance(z_levels, str):
            z_levels = json.dumps(z_levels)

        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO building_roofs
                (gebaeudeeinheit, egid, dach_min, dach_max,
                 roof_form, roof_angle_deg, roof_orientation, z_levels,
                 geometry_wkb, has_full_geometry, calculation_method)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                gebaeudeeinheit,
                roof.get('egid'),
                roof.get('dach_min'),
                roof.get('dach_max'),
                roof.get('roof_form'),
                roof.get('roof_angle_deg'),
                roof.get('roof_orientation'),
                z_levels,
                roof.get('geometry_wkb'),
                roof.get('has_full_geometry', 0),
                roof.get('calculation_method', 'z_level_analysis')
            ))

            conn.commit()
            return True

    def bulk_save(self, roofs: List[Dict[str, Any]]) -> int:
        """
        Speichert mehrere Dächer in einer Transaktion.

        Args:
            roofs: Liste von Dach-Dicts

        Returns:
            Anzahl gespeicherter Einträge
        """
        if not roofs:
            return 0

        # Daten vorbereiten
        prepared_data = []
        for roof in roofs:
            gebaeudeeinheit = roof.get('gebaeudeeinheit')
            if not gebaeudeeinheit:
                continue

            z_levels = roof.get('z_levels')
            if z_levels and not isinstance(z_levels, str):
                z_levels = json.dumps(z_levels)

            prepared_data.append((
                gebaeudeeinheit,
                roof.get('egid'),
                roof.get('dach_min'),
                roof.get('dach_max'),
                roof.get('roof_form'),
                roof.get('roof_angle_deg'),
                roof.get('roof_orientation'),
                z_levels,
                roof.get('geometry_wkb'),
                roof.get('has_full_geometry', 0),
                roof.get('calculation_method', 'z_level_analysis')
            ))

        if not prepared_data:
            return 0

        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.executemany("""
                INSERT OR REPLACE INTO building_roofs
                (gebaeudeeinheit, egid, dach_min, dach_max,
                 roof_form, roof_angle_deg, roof_orientation, z_levels,
                 geometry_wkb, has_full_geometry, calculation_method)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, prepared_data)

            conn.commit()

        logger.info(f"[ROOF] {len(prepared_data)} Dach-Einträge gespeichert")
        return len(prepared_data)

    def get_by_gebaeudeeinheit(self, gebaeudeeinheit: str) -> Optional[Dict[str, Any]]:
        """Holt Dach-Daten per Gebäudeeinheit."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM building_roofs WHERE gebaeudeeinheit = ?
            """, (gebaeudeeinheit,))

            row = cursor.fetchone()
            if not row:
                return None

            result = dict(row)

            # Z-Levels parsen
            if result.get('z_levels'):
                try:
                    result['z_levels'] = json.loads(result['z_levels'])
                except json.JSONDecodeError:
                    result['z_levels'] = None

            return result

    def get_by_egid(self, egid: str) -> Optional[Dict[str, Any]]:
        """Holt Dach-Daten per EGID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM building_roofs WHERE egid = ?
            """, (egid,))

            row = cursor.fetchone()
            if not row:
                return None

            result = dict(row)
            if result.get('z_levels'):
                try:
                    result['z_levels'] = json.loads(result['z_levels'])
                except json.JSONDecodeError:
                    result['z_levels'] = None

            return result

    def update_with_geometry(self, gebaeudeeinheit: str, geometry_wkb: bytes) -> bool:
        """
        Aktualisiert einen Eintrag mit vollständiger 3D-Geometrie.

        Wird aufgerufen beim On-Demand Fetch für komplexe Gebäude.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE building_roofs
                SET geometry_wkb = ?,
                    has_full_geometry = 1,
                    calculated_at = CURRENT_TIMESTAMP
                WHERE gebaeudeeinheit = ?
            """, (geometry_wkb, gebaeudeeinheit))

            conn.commit()
            return cursor.rowcount > 0

    def get_stats(self) -> Dict[str, Any]:
        """Gibt Statistiken zurück."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM building_roofs")
            total = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM building_roofs WHERE has_full_geometry = 1")
            with_geometry = cursor.fetchone()[0]

            cursor.execute("""
                SELECT roof_form, COUNT(*) as count
                FROM building_roofs
                WHERE roof_form IS NOT NULL
                GROUP BY roof_form
                ORDER BY count DESC
            """)
            forms = {row['roof_form']: row['count'] for row in cursor.fetchall()}

            return {
                "total_roofs": total,
                "with_full_geometry": with_geometry,
                "roof_forms": forms
            }


# Singleton-Accessor
_service_instance = None


def get_roof_3d_service() -> Roof3DService:
    """Gibt die Singleton-Instanz des Roof3DService zurück."""
    global _service_instance
    if _service_instance is None:
        _service_instance = Roof3DService()
    return _service_instance