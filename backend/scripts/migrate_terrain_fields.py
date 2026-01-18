#!/usr/bin/env python3
"""
Migration: Terrain-Felder für prefetch_neighbors() Enrichment
==============================================================

Fügt die neuen Terrain-Sampling Felder zu buildings_3d hinzu:
- terrain_z_min DOUBLE
- terrain_z_max DOUBLE
- terrain_slope_m DOUBLE
- terrain_sampled_at TIMESTAMP

Und erstellt den Index:
- idx_buildings_3d_enrichment ON buildings_3d(terrain_sampled_at, has_3d_layers)

Stand: 17.01.2026
"""

import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.config import get_building_3d_connection, USE_DUCKDB, BUILDING_3D_DUCKDB_PATH


def migrate():
    """Fuehrt die Migration aus."""
    if not USE_DUCKDB:
        print("[ERROR] Migration nur fuer DuckDB implementiert. USE_DUCKDB=false")
        return False

    print(f"[DB] DuckDB-Datei: {BUILDING_3D_DUCKDB_PATH}")

    # Neue Felder
    new_columns = [
        ("terrain_z_min", "DOUBLE"),
        ("terrain_z_max", "DOUBLE"),
        ("terrain_slope_m", "DOUBLE"),
        ("terrain_sampled_at", "TIMESTAMP"),
    ]

    with get_building_3d_connection() as conn:
        # Pruefe ob Felder bereits existieren
        result = conn.execute("DESCRIBE buildings_3d").fetchall()
        existing_columns = {row[0] for row in result}

        print(f"\n[SCHEMA] Bestehende Spalten: {len(existing_columns)}")

        # Felder hinzufuegen
        for col_name, col_type in new_columns:
            if col_name in existing_columns:
                print(f"  [OK] {col_name} existiert bereits")
            else:
                sql = f"ALTER TABLE buildings_3d ADD COLUMN {col_name} {col_type}"
                conn.execute(sql)
                print(f"  [ADD] {col_name} hinzugefuegt")

        # Index erstellen
        index_sql = """
        CREATE INDEX IF NOT EXISTS idx_buildings_3d_enrichment
        ON buildings_3d(terrain_sampled_at, has_3d_layers)
        """
        conn.execute(index_sql)
        print(f"\n[INDEX] idx_buildings_3d_enrichment erstellt")

        # Statistik
        count = conn.execute("SELECT COUNT(*) FROM buildings_3d").fetchone()[0]
        enriched = conn.execute(
            "SELECT COUNT(*) FROM buildings_3d WHERE terrain_sampled_at IS NOT NULL"
        ).fetchone()[0]

        print(f"\n[STATS] Statistik:")
        print(f"   Gebaeude gesamt: {count}")
        print(f"   Mit Terrain-Sampling: {enriched}")
        print(f"   Ohne Terrain-Sampling: {count - enriched}")

    print("\n[DONE] Migration abgeschlossen!")
    return True


if __name__ == "__main__":
    migrate()
