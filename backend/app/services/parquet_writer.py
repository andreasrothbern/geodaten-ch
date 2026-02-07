"""
Parquet-Writer für speichereffizientes GDB-Parsing.

NEU 15.01.2026: Ersetzt das Listen-basierte Parsing (OOM-Problem bei großen Tiles).

Architektur:
    Parser → Parquet (streaming, kein RAM-Overhead)
    → DuckDB Bulk-Load (ein Befehl, SIMD-optimiert)

Vorteile:
    - Kein OOM (streaming statt Liste)
    - Kein DB-Lock-Contention (Parquet-Dateien sind unabhängig)
    - Perfekte Parallelität (alle 3 Layer gleichzeitig)
    - DuckDB liest Parquet 10x schneller als Einzel-INSERTs
"""

import json
import logging
import time
from pathlib import Path
from typing import Iterator, Dict, Any, Optional, List
from dataclasses import dataclass, field

import pyarrow as pa
import pyarrow.parquet as pq
import fiona
from shapely.geometry import shape, Polygon, MultiPolygon
from shapely.ops import unary_union
from shapely import wkb

logger = logging.getLogger(__name__)

# NEU 15.01.2026: PARQUET_DIR aus config.py für Ephemeral Storage
from app.config import PARQUET_DIR


# =============================================================================
# SCHEMA-DEFINITIONEN
# =============================================================================

BUILDINGS_SCHEMA = pa.schema([
    ('egid', pa.int64()),
    ('geom_wkb', pa.binary()),          # NEU 31.01.2026: WKB statt JSON für DuckDB Spatial
    ('traufhoehe_m', pa.float64()),
    ('firsthoehe_m', pa.float64()),
    ('gebaeudehoehe_m', pa.float64()),
    ('area_m2', pa.float64()),
    ('perimeter_m', pa.float64()),
    ('center_e', pa.float64()),
    ('center_n', pa.float64()),
    ('tile_id', pa.string()),
    ('objektart', pa.string()),
    ('name_komplett', pa.string()),
    ('gebaeude_nutzung', pa.string()),
    ('gebaeudeeinheit', pa.string()),
    ('roof_form', pa.string()),
    ('roof_form_confidence', pa.float64()),
    ('roof_orientation', pa.string()),
    ('source', pa.string()),
])

ROOFS_SCHEMA = pa.schema([
    ('gebaeudeeinheit', pa.string()),
    ('egid', pa.string()),
    ('dach_min', pa.float64()),
    ('dach_max', pa.float64()),
    ('roof_form', pa.string()),
    ('roof_angle_deg', pa.float64()),
    ('roof_orientation', pa.string()),
    ('roof_form_confidence', pa.float64()),
    ('z_levels', pa.string()),          # JSON
    ('calculation_method', pa.string()),
    ('tile_id', pa.string()),
    ('geometry_wkb', pa.binary()),      # FIX 24.01.2026: 3D-Geometrie
])

WALLS_SCHEMA = pa.schema([
    ('gebaeudeeinheit', pa.string()),
    ('egid', pa.string()),
    ('z_min', pa.float64()),
    ('z_max', pa.float64()),
    ('geometry_wkb', pa.binary()),      # WKB als Bytes
    ('tile_id', pa.string()),
])


# =============================================================================
# STREAMING PARQUET WRITER
# =============================================================================

@dataclass
class StreamingParquetWriter:
    """
    Schreibt Features direkt in Parquet-Dateien (Streaming, kein RAM-Overhead).

    Usage:
        with StreamingParquetWriter(output_path, BUILDINGS_SCHEMA) as writer:
            for feature in parse_gdb():
                writer.write(feature_to_dict(feature))
    """

    output_path: Path
    schema: pa.Schema
    batch_size: int = 1000
    compression: str = "snappy"

    # Internal state
    _buffer: List[Dict] = field(default_factory=list, init=False)
    _writer: Optional[pq.ParquetWriter] = None
    _total_rows: int = field(default=0, init=False)

    def __enter__(self):
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self._writer = pq.ParquetWriter(
            str(self.output_path),
            self.schema,
            compression=self.compression
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Flush remaining buffer
        if self._buffer:
            self._flush()
        if self._writer:
            self._writer.close()
        return False

    def write(self, row: Dict[str, Any]):
        """Schreibt eine Zeile (buffered)."""
        self._buffer.append(row)
        if len(self._buffer) >= self.batch_size:
            self._flush()

    def _flush(self):
        """Schreibt Buffer in Parquet-Datei."""
        if not self._buffer:
            return

        table = pa.Table.from_pylist(self._buffer, schema=self.schema)
        self._writer.write_table(table)
        self._total_rows += len(self._buffer)
        self._buffer.clear()

    @property
    def rows_written(self) -> int:
        return self._total_rows + len(self._buffer)


# =============================================================================
# GDB → PARQUET STREAMING FUNCTIONS
# =============================================================================

def stream_buildings_to_parquet(
    gdb_path: Path,
    tile_id: str,
    output_dir: Optional[Path] = None
) -> tuple[Path, int]:
    """
    Streamt Building_solid Layer direkt in Parquet.

    Args:
        gdb_path: Pfad zur GDB-Datei
        tile_id: Tile-ID für Metadaten
        output_dir: Output-Verzeichnis (default: PARQUET_DIR/buildings/)

    Returns:
        (parquet_path, count) - Pfad und Anzahl geschriebener Gebäude
    """
    import math

    if output_dir is None:
        output_dir = PARQUET_DIR / "buildings"

    output_path = output_dir / f"{tile_id}.parquet"
    count = 0

    start_time = time.time()

    with StreamingParquetWriter(output_path, BUILDINGS_SCHEMA) as writer:
        try:
            with fiona.open(gdb_path, layer="Building_solid") as src:
                for feature in src:
                    props = feature.get("properties", {})
                    geom = feature.get("geometry")

                    if not geom:
                        continue

                    # EGID extrahieren (kann NaN sein!)
                    egid = props.get("EGID")
                    if egid is not None and isinstance(egid, float):
                        if math.isnan(egid):
                            egid = None
                        else:
                            egid = int(egid)
                    elif egid is not None:
                        egid = int(egid)

                    if egid is None:
                        continue  # Skip buildings without EGID

                    # Geometrie parsen
                    try:
                        geom_shape = shape(geom)
                        if isinstance(geom_shape, MultiPolygon):
                            geom_shape = unary_union(geom_shape)
                        if not isinstance(geom_shape, Polygon):
                            continue
                    except Exception:
                        continue

                    # FIX 07.02.2026: Prüfe auf leere/ungültige Geometrie
                    if geom_shape.is_empty or not geom_shape.is_valid:
                        logger.warning(f"[PARQUET] Skip EGID {egid}: empty or invalid geometry")
                        continue

                    # NEU 31.01.2026: Koordinaten extrahieren und WKB erstellen
                    coords = list(geom_shape.exterior.coords)
                    if len(coords) < 3:
                        logger.warning(f"[PARQUET] Skip EGID {egid}: polygon has < 3 coords")
                        continue

                    coords_2d = [(round(c[0], 2), round(c[1], 2)) for c in coords]
                    polygon_2d = Polygon(coords_2d)
                    geom_wkb = wkb.dumps(polygon_2d) if polygon_2d.is_valid else None

                    # Höhen berechnen
                    gelaendepunkt = props.get("GELAENDEPUNKT") or 0
                    dach_min = props.get("DACH_MIN") or 0
                    dach_max = props.get("DACH_MAX") or 0
                    gesamthoehe = props.get("GESAMTHOEHE") or 0

                    traufhoehe = (dach_min - gelaendepunkt) if dach_min and gelaendepunkt else None
                    firsthoehe = (dach_max - gelaendepunkt) if dach_max and gelaendepunkt else None

                    # Centroid - FIX 07.02.2026: Prüfe auf leeren Zentroid
                    centroid = geom_shape.centroid
                    if centroid.is_empty:
                        logger.warning(f"[PARQUET] Skip EGID {egid}: empty centroid")
                        continue

                    writer.write({
                        'egid': egid,
                        'geom_wkb': geom_wkb,  # NEU 31.01.2026: WKB statt JSON
                        'traufhoehe_m': traufhoehe,
                        'firsthoehe_m': firsthoehe,
                        'gebaeudehoehe_m': gesamthoehe,
                        'area_m2': round(geom_shape.area, 2),
                        'perimeter_m': round(geom_shape.length, 2),
                        'center_e': round(centroid.x, 2),
                        'center_n': round(centroid.y, 2),
                        'tile_id': tile_id,
                        'objektart': props.get("OBJEKTART"),
                        'name_komplett': props.get("NAME_KOMPLETT"),
                        'gebaeude_nutzung': props.get("GEBAEUDENUTZUNG"),
                        'gebaeudeeinheit': props.get("GEBAEUDEEINHEIT"),
                        'roof_form': None,  # Wird später berechnet
                        'roof_form_confidence': None,
                        'roof_orientation': None,
                        'source': 'swissBUILDINGS3D',
                    })
                    count += 1

        except Exception as e:
            logger.error(f"Error parsing Building_solid: {e}")
            raise

    elapsed_ms = (time.time() - start_time) * 1000
    logger.info(f"[PARQUET] Building_solid: {count} items → {output_path.name} ({elapsed_ms:.0f}ms)")

    return output_path, count


def stream_roofs_to_parquet(
    gdb_path: Path,
    tile_id: str,
    output_dir: Optional[Path] = None
) -> tuple[Path, int]:
    """
    Streamt Roof_solid Layer direkt in Parquet.
    """
    if output_dir is None:
        output_dir = PARQUET_DIR / "roofs"

    output_path = output_dir / f"{tile_id}.parquet"
    count = 0

    start_time = time.time()

    with StreamingParquetWriter(output_path, ROOFS_SCHEMA) as writer:
        try:
            with fiona.open(gdb_path, layer="Roof_solid") as src:
                for feature in src:
                    props = feature.get("properties", {})

                    gebaeudeeinheit = props.get("GEBAEUDEEINHEIT")
                    if not gebaeudeeinheit:
                        continue

                    egid = props.get("EGID")
                    if egid is not None:
                        egid = str(int(egid)) if not (isinstance(egid, float) and egid != egid) else None

                    # FIX 24.01.2026: geometry_wkb speichern!
                    geom = feature.get("geometry")
                    geometry_wkb = None
                    if geom:
                        try:
                            geom_shape = shape(geom)
                            geometry_wkb = geom_shape.wkb
                        except Exception:
                            pass

                    writer.write({
                        'gebaeudeeinheit': gebaeudeeinheit,
                        'egid': egid,
                        'dach_min': props.get("DACH_MIN"),
                        'dach_max': props.get("DACH_MAX"),
                        'roof_form': None,
                        'roof_angle_deg': None,
                        'roof_orientation': None,
                        'roof_form_confidence': None,
                        'z_levels': None,
                        'calculation_method': None,
                        'tile_id': tile_id,
                        'geometry_wkb': geometry_wkb,
                    })
                    count += 1

        except Exception as e:
            logger.error(f"Error parsing Roof_solid: {e}")
            raise

    elapsed_ms = (time.time() - start_time) * 1000
    logger.info(f"[PARQUET] Roof_solid: {count} items → {output_path.name} ({elapsed_ms:.0f}ms)")

    return output_path, count


def stream_walls_to_parquet(
    gdb_path: Path,
    tile_id: str,
    output_dir: Optional[Path] = None
) -> tuple[Path, int]:
    """
    Streamt Wall Layer direkt in Parquet (inkl. WKB-Geometrie).
    """
    import math

    if output_dir is None:
        output_dir = PARQUET_DIR / "walls"

    output_path = output_dir / f"{tile_id}.parquet"
    count = 0

    start_time = time.time()

    with StreamingParquetWriter(output_path, WALLS_SCHEMA) as writer:
        try:
            with fiona.open(gdb_path, layer="Wall") as src:
                for feature in src:
                    props = feature.get("properties", {})
                    geom = feature.get("geometry")

                    gebaeudeeinheit = props.get("GEBAEUDEEINHEIT")
                    if not gebaeudeeinheit:
                        continue

                    egid = props.get("EGID")
                    if egid is not None:
                        if isinstance(egid, float) and math.isnan(egid):
                            egid = None
                        else:
                            egid = str(int(egid))

                    # Z-Koordinaten aus Geometrie extrahieren
                    z_min = None
                    z_max = None
                    geometry_wkb = None

                    if geom:
                        try:
                            geom_shape = shape(geom)
                            geometry_wkb = geom_shape.wkb

                            # Z-Koordinaten aus 3D-Geometrie
                            gelaendepunkt = props.get("GELAENDEPUNKT") or 0
                            gesamthoehe = props.get("GESAMTHOEHE") or 0

                            if gelaendepunkt:
                                z_min = gelaendepunkt
                                z_max = gelaendepunkt + gesamthoehe if gesamthoehe else None
                        except Exception:
                            pass

                    writer.write({
                        'gebaeudeeinheit': gebaeudeeinheit,
                        'egid': egid,
                        'z_min': z_min,
                        'z_max': z_max,
                        'geometry_wkb': geometry_wkb,
                        'tile_id': tile_id,
                    })
                    count += 1

        except Exception as e:
            logger.error(f"Error parsing Wall: {e}")
            raise

    elapsed_ms = (time.time() - start_time) * 1000
    logger.info(f"[PARQUET] Wall: {count} items → {output_path.name} ({elapsed_ms:.0f}ms)")

    return output_path, count


# =============================================================================
# PARALLEL PARSING → PARQUET
# =============================================================================

async def parse_tile_to_parquet_parallel(
    gdb_path: Path,
    tile_id: str,
    output_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Parst alle 3 Layer PARALLEL und schreibt Parquet-Dateien.

    Diese Funktion löst das OOM-Problem:
    - Streaming statt Listen → kein RAM-Overhead
    - Unabhängige Parquet-Dateien → kein DB-Lock
    - asyncio.gather() funktioniert ohne OOM

    FIX 20.01.2026: Prüft ob GDB-Pfad existiert bevor er geparst wird.
    Bei 'cleaned' Tiles existiert das GDB nicht mehr.

    Args:
        gdb_path: Pfad zur GDB-Datei
        tile_id: Tile-ID
        output_dir: Output-Verzeichnis (default: PARQUET_DIR)

    Returns:
        Dict mit Pfaden und Counts pro Layer

    Raises:
        FileNotFoundError: Wenn GDB-Pfad nicht existiert
    """
    import asyncio

    # FIX 20.01.2026: Prüfen ob GDB-Pfad existiert BEVOR wir parsen
    if not gdb_path or not gdb_path.exists():
        raise FileNotFoundError(
            f"GDB-Pfad existiert nicht: {gdb_path}. "
            f"Tile wurde möglicherweise bereits gelöscht (CLEANUP_TILES_AFTER_IMPORT=true). "
            f"Prüfe ob Tile bereits importiert wurde (import_status='cleaned')."
        )

    if output_dir is None:
        output_dir = PARQUET_DIR

    start_time = time.time()

    # Wrapper für asyncio.to_thread()
    async def parse_buildings():
        return await asyncio.to_thread(
            stream_buildings_to_parquet, gdb_path, tile_id, output_dir / "buildings"
        )

    async def parse_roofs():
        return await asyncio.to_thread(
            stream_roofs_to_parquet, gdb_path, tile_id, output_dir / "roofs"
        )

    async def parse_walls():
        return await asyncio.to_thread(
            stream_walls_to_parquet, gdb_path, tile_id, output_dir / "walls"
        )

    # Alle 3 parallel ausführen
    results = await asyncio.gather(
        parse_buildings(),
        parse_roofs(),
        parse_walls()
    )

    buildings_path, buildings_count = results[0]
    roofs_path, roofs_count = results[1]
    walls_path, walls_count = results[2]

    elapsed_ms = (time.time() - start_time) * 1000

    logger.info(
        f"[PARQUET] Tile {tile_id} komplett: "
        f"{buildings_count} buildings, {roofs_count} roofs, {walls_count} walls "
        f"({elapsed_ms:.0f}ms parallel)"
    )

    return {
        'tile_id': tile_id,
        'buildings': {'path': buildings_path, 'count': buildings_count},
        'roofs': {'path': roofs_path, 'count': roofs_count},
        'walls': {'path': walls_path, 'count': walls_count},
        'elapsed_ms': elapsed_ms,
    }


# =============================================================================
# CLEANUP
# =============================================================================

def cleanup_parquet_dir(tile_id: Optional[str] = None):
    """
    Löscht Parquet-Dateien nach erfolgreichem DB-Load.

    Args:
        tile_id: Optional - nur dieses Tile löschen. None = alles löschen.
    """
    if tile_id:
        # Nur spezifisches Tile
        for subdir in ["buildings", "roofs", "walls"]:
            parquet_file = PARQUET_DIR / subdir / f"{tile_id}.parquet"
            if parquet_file.exists():
                parquet_file.unlink()
                logger.debug(f"[CLEANUP] Deleted {parquet_file}")
    else:
        # Alles löschen
        import shutil
        if PARQUET_DIR.exists():
            shutil.rmtree(PARQUET_DIR)
            logger.info(f"[CLEANUP] Deleted entire parquet directory")


def get_parquet_stats() -> Dict[str, Any]:
    """Gibt Statistiken über gecachte Parquet-Dateien zurück."""
    stats = {
        'buildings': 0,
        'roofs': 0,
        'walls': 0,
        'total_size_mb': 0.0,
    }

    if not PARQUET_DIR.exists():
        return stats

    for subdir in ["buildings", "roofs", "walls"]:
        subdir_path = PARQUET_DIR / subdir
        if subdir_path.exists():
            files = list(subdir_path.glob("*.parquet"))
            stats[subdir] = len(files)
            for f in files:
                stats['total_size_mb'] += f.stat().st_size / (1024 * 1024)

    stats['total_size_mb'] = round(stats['total_size_mb'], 2)
    return stats


# =============================================================================
# C.3: DUCKDB BULK-LOAD AUS PARQUET
# =============================================================================

def load_parquets_to_duckdb(
    parquet_dir: Optional[Path] = None,
    tile_id: Optional[str] = None
) -> Dict[str, int]:
    """
    Lädt alle Parquet-Dateien in DuckDB (ein Befehl pro Tabelle).

    Dies ist die schnellste Methode für Bulk-Imports:
    - DuckDB liest Parquet nativ (SIMD-optimiert)
    - Ein INSERT statt tausende einzelne
    - Multi-threaded innerhalb DuckDB

    Args:
        parquet_dir: Verzeichnis mit buildings/, roofs/, walls/ Unterordnern
        tile_id: Optional - nur dieses Tile laden (sonst alle *.parquet)

    Returns:
        Dict mit Anzahl geladener Zeilen pro Tabelle
    """
    from app.config import get_building_3d_connection

    if parquet_dir is None:
        parquet_dir = PARQUET_DIR

    results = {'buildings': 0, 'roofs': 0, 'walls': 0}
    start_time = time.time()

    # Glob-Pattern für Parquet-Dateien
    if tile_id:
        pattern = f"{tile_id}.parquet"
    else:
        pattern = "*.parquet"

    conn = get_building_3d_connection()

    try:
        # 1. BUILDINGS
        buildings_glob = str(parquet_dir / "buildings" / pattern)
        buildings_files = list((parquet_dir / "buildings").glob(pattern)) if (parquet_dir / "buildings").exists() else []

        if buildings_files:
            # Zähle Zeilen im Parquet vor dem Insert (DuckDB hat kein changes())
            count_result = conn.execute(f"SELECT COUNT(*) FROM read_parquet('{buildings_glob}')").fetchone()
            parquet_count = count_result[0] if count_result else 0

            # FIX 14.01.2026 v2: Echter UPSERT mit ON CONFLICT
            # - Neue Gebäude werden eingefügt
            # - Bestehende Gebäude werden NUR aktualisiert wenn has_3d_layers = 0
            # - Gebäude mit has_3d_layers = 1 behalten ihre detaillierten Daten
            # NEU 31.01.2026: geom GEOMETRY statt polygon JSON (DuckDB Spatial)
            conn.execute(f"""
                INSERT INTO buildings_3d (
                    egid, geom, traufhoehe_m, firsthoehe_m, gebaeudehoehe_m,
                    area_m2, perimeter_m, center_e, center_n, tile_id,
                    objektart, name_komplett, gebaeude_nutzung, gebaeudeeinheit,
                    roof_form, roof_form_confidence, roof_orientation,
                    has_3d_layers, imported_at, source
                )
                SELECT
                    egid, ST_GeomFromWKB(geom_wkb), traufhoehe_m, firsthoehe_m, gebaeudehoehe_m,
                    area_m2, perimeter_m, center_e, center_n, tile_id,
                    objektart, name_komplett, gebaeude_nutzung, gebaeudeeinheit,
                    roof_form, roof_form_confidence, roof_orientation,
                    1 as has_3d_layers,
                    current_timestamp as imported_at,
                    source
                FROM read_parquet('{buildings_glob}')
                ON CONFLICT (egid) DO UPDATE SET
                    geom = excluded.geom,
                    traufhoehe_m = excluded.traufhoehe_m,
                    firsthoehe_m = excluded.firsthoehe_m,
                    gebaeudehoehe_m = excluded.gebaeudehoehe_m,
                    area_m2 = excluded.area_m2,
                    perimeter_m = excluded.perimeter_m,
                    center_e = excluded.center_e,
                    center_n = excluded.center_n,
                    tile_id = excluded.tile_id,
                    objektart = excluded.objektart,
                    name_komplett = excluded.name_komplett,
                    gebaeude_nutzung = excluded.gebaeude_nutzung,
                    gebaeudeeinheit = excluded.gebaeudeeinheit,
                    roof_form = excluded.roof_form,
                    roof_form_confidence = excluded.roof_form_confidence,
                    roof_orientation = excluded.roof_orientation,
                    has_3d_layers = 1,
                    imported_at = now(),
                    source = excluded.source
                WHERE buildings_3d.has_3d_layers = 0 OR buildings_3d.has_3d_layers IS NULL
            """)

            results['buildings'] = parquet_count
            logger.info(f"[DUCKDB] buildings_3d: {parquet_count} rows (UPSERT, 3D-Layer geschützt)")

        # 2. ROOFS
        # Schema building_roofs: gebaeudeeinheit, egid(INT), dach_min, dach_max,
        # roof_form, roof_angle_deg, roof_orientation, z_levels, geometry_wkb,
        # has_full_geometry, calculated_at, calculation_method
        roofs_glob = str(parquet_dir / "roofs" / pattern)
        roofs_files = list((parquet_dir / "roofs").glob(pattern)) if (parquet_dir / "roofs").exists() else []

        if roofs_files:
            # Zähle Zeilen im Parquet vor dem Insert
            count_result = conn.execute(f"SELECT COUNT(*) FROM read_parquet('{roofs_glob}')").fetchone()
            parquet_count = count_result[0] if count_result else 0

            # FIX 24.01.2026: geometry_wkb und has_full_geometry hinzugefügt!
            conn.execute(f"""
                INSERT OR REPLACE INTO building_roofs (
                    gebaeudeeinheit, egid, dach_min, dach_max,
                    roof_form, roof_angle_deg, roof_orientation, z_levels, calculation_method,
                    geometry_wkb, has_full_geometry
                )
                SELECT
                    gebaeudeeinheit,
                    CAST(egid AS INTEGER),
                    dach_min,
                    dach_max,
                    roof_form,
                    roof_angle_deg,
                    roof_orientation,
                    z_levels,
                    calculation_method,
                    geometry_wkb,
                    CASE WHEN geometry_wkb IS NOT NULL THEN 1 ELSE 0 END
                FROM read_parquet('{roofs_glob}')
            """)
            results['roofs'] = parquet_count
            logger.info(f"[DUCKDB] building_roofs: {results['roofs']} rows loaded")

        # 3. WALLS
        # Schema building_walls: gebaeudeeinheit, egid(INT), z_min, z_max, geometry_wkb, created_at
        # Parquet hat: gebaeudeeinheit, egid(str), z_min, z_max, geometry_wkb, tile_id
        walls_glob = str(parquet_dir / "walls" / pattern)
        walls_files = list((parquet_dir / "walls").glob(pattern)) if (parquet_dir / "walls").exists() else []

        if walls_files:
            # Zähle Zeilen im Parquet vor dem Insert
            count_result = conn.execute(f"SELECT COUNT(*) FROM read_parquet('{walls_glob}')").fetchone()
            parquet_count = count_result[0] if count_result else 0

            # Explizite Spaltenangabe - nur die gemeinsamen Spalten
            conn.execute(f"""
                INSERT OR REPLACE INTO building_walls (
                    gebaeudeeinheit, egid, z_min, z_max, geometry_wkb
                )
                SELECT
                    gebaeudeeinheit,
                    CAST(egid AS INTEGER),
                    z_min,
                    z_max,
                    geometry_wkb
                FROM read_parquet('{walls_glob}')
            """)
            results['walls'] = parquet_count
            logger.info(f"[DUCKDB] building_walls: {results['walls']} rows loaded")

        # 4. has_3d_layers Flag - ENTFERNT (21.01.2026)
        # FIX: Das Flag wird jetzt direkt im INSERT gesetzt (1 as has_3d_layers)
        # Das vermeidet DuckDB write-write conflicts bei parallelen Imports
        # (INSERT + UPDATE auf gleiche Row = Konflikt)

    except Exception as e:
        logger.error(f"[DUCKDB] Bulk-Load Fehler: {e}")
        raise
    finally:
        conn.close()

    elapsed_ms = (time.time() - start_time) * 1000
    total = sum(results.values())
    logger.info(f"[DUCKDB] Bulk-Load komplett: {total} rows in {elapsed_ms:.0f}ms")

    return results


async def import_tile_with_parquet_pipeline(
    gdb_path: Path,
    tile_id: str,
    cleanup_after: bool = True
) -> Dict[str, Any]:
    """
    Kompletter Import eines Tiles mit der Parquet-Pipeline.

    Dies ist der neue Haupt-Einstiegspunkt für Tile-Imports:
    1. Parse GDB → Parquet (parallel, streaming)
    2. Load Parquet → DuckDB (bulk)
    3. Cleanup Parquet (optional)

    FIX 20.01.2026: Gibt leeres Ergebnis zurück wenn GDB nicht existiert.
    Der Aufrufer (prefetch_tile_buildings_async) prüft vorher den import_status.

    Args:
        gdb_path: Pfad zur GDB-Datei
        tile_id: Tile-ID
        cleanup_after: Parquet-Dateien nach Load löschen

    Returns:
        Dict mit Statistiken (oder leeres Dict wenn GDB nicht existiert)
    """
    import asyncio

    # FIX 20.01.2026: Früher Abbruch wenn GDB nicht existiert
    if not gdb_path or not gdb_path.exists():
        logger.warning(
            f"[PARQUET-PIPELINE] GDB-Pfad existiert nicht: {gdb_path}. "
            f"Tile {tile_id} wurde möglicherweise bereits gelöscht."
        )
        return {
            'tile_id': tile_id,
            'parse_ms': 0,
            'load_result': {'buildings': 0, 'roofs': 0, 'walls': 0},
            'total_ms': 0,
            'buildings_count': 0,
            'roofs_count': 0,
            'walls_count': 0,
            'skipped': True,
            'reason': 'gdb_not_found',
        }

    start_time = time.time()

    # Phase 1: Parse → Parquet (parallel)
    parse_result = await parse_tile_to_parquet_parallel(gdb_path, tile_id)

    # Phase 2: Parquet → DuckDB (bulk)
    load_result = await asyncio.to_thread(load_parquets_to_duckdb, PARQUET_DIR, tile_id)

    # Phase 3: Cleanup
    if cleanup_after:
        cleanup_parquet_dir(tile_id)

    elapsed_ms = (time.time() - start_time) * 1000

    return {
        'tile_id': tile_id,
        'parse_ms': parse_result['elapsed_ms'],
        'load_result': load_result,
        'total_ms': elapsed_ms,
        'buildings_count': parse_result['buildings']['count'],
        'roofs_count': parse_result['roofs']['count'],
        'walls_count': parse_result['walls']['count'],
    }


# =============================================================================
# NEU 31.01.2026: SINGLE-BUILDING IMPORT (für SSE-Pipeline Stufe 1)
# =============================================================================

def _stream_single_building_to_parquet(
    gdb_path: Path,
    egid: int,
    tile_id: str,
    output_dir: Path
) -> tuple[Path, bool]:
    """
    Streamt EIN Gebäude aus Building_solid in Parquet.

    Returns:
        (parquet_path, found) - Pfad und ob Gebäude gefunden wurde
    """
    import math

    output_path = output_dir / f"{tile_id}_{egid}.parquet"
    found = False

    with StreamingParquetWriter(output_path, BUILDINGS_SCHEMA, batch_size=1) as writer:
        try:
            with fiona.open(gdb_path, layer="Building_solid") as src:
                for feature in src:
                    props = feature.get("properties", {})
                    geom = feature.get("geometry")

                    # EGID extrahieren und vergleichen
                    feat_egid = props.get("EGID")
                    if feat_egid is not None and isinstance(feat_egid, float):
                        if math.isnan(feat_egid):
                            continue
                        feat_egid = int(feat_egid)
                    elif feat_egid is not None:
                        feat_egid = int(feat_egid)

                    if feat_egid != egid:
                        continue  # Nicht das gesuchte Gebäude

                    if not geom:
                        continue

                    # Gefunden! Geometrie parsen
                    try:
                        geom_shape = shape(geom)
                        if isinstance(geom_shape, MultiPolygon):
                            geom_shape = unary_union(geom_shape)
                        if not isinstance(geom_shape, Polygon):
                            continue
                    except Exception:
                        continue

                    # FIX 07.02.2026: Prüfe auf leere/ungültige Geometrie
                    if geom_shape.is_empty or not geom_shape.is_valid:
                        logger.warning(f"[PARQUET] Skip EGID {egid}: empty or invalid geometry")
                        continue

                    # WKB erstellen
                    coords = list(geom_shape.exterior.coords)
                    if len(coords) < 3:
                        logger.warning(f"[PARQUET] Skip EGID {egid}: polygon has < 3 coords")
                        continue

                    coords_2d = [(round(c[0], 2), round(c[1], 2)) for c in coords]
                    polygon_2d = Polygon(coords_2d)
                    geom_wkb = wkb.dumps(polygon_2d) if polygon_2d.is_valid else None

                    # Höhen
                    gelaendepunkt = props.get("GELAENDEPUNKT") or 0
                    dach_min = props.get("DACH_MIN") or 0
                    dach_max = props.get("DACH_MAX") or 0
                    gesamthoehe = props.get("GESAMTHOEHE") or 0

                    traufhoehe = (dach_min - gelaendepunkt) if dach_min and gelaendepunkt else None
                    firsthoehe = (dach_max - gelaendepunkt) if dach_max and gelaendepunkt else None

                    # FIX 07.02.2026: Prüfe auf leeren Zentroid
                    centroid = geom_shape.centroid
                    if centroid.is_empty:
                        logger.warning(f"[PARQUET] Skip EGID {egid}: empty centroid")
                        continue

                    writer.write({
                        'egid': egid,
                        'geom_wkb': geom_wkb,
                        'traufhoehe_m': traufhoehe,
                        'firsthoehe_m': firsthoehe,
                        'gebaeudehoehe_m': gesamthoehe,
                        'area_m2': round(geom_shape.area, 2),
                        'perimeter_m': round(geom_shape.length, 2),
                        'center_e': round(centroid.x, 2),
                        'center_n': round(centroid.y, 2),
                        'tile_id': tile_id,
                        'objektart': props.get("OBJEKTART"),
                        'name_komplett': props.get("NAME_KOMPLETT"),
                        'gebaeude_nutzung': props.get("GEBAEUDENUTZUNG"),
                        'gebaeudeeinheit': props.get("GEBAEUDEEINHEIT"),
                        'roof_form': None,
                        'roof_form_confidence': None,
                        'roof_orientation': None,
                        'source': 'swissBUILDINGS3D',
                    })
                    found = True
                    break  # Nur 1 Gebäude gesucht

        except Exception as e:
            logger.error(f"Error parsing Building_solid for EGID {egid}: {e}")

    return output_path, found


def _stream_single_roof_to_parquet(
    gdb_path: Path,
    egid: int,
    tile_id: str,
    output_dir: Path
) -> tuple[Path, int]:
    """
    Streamt Dächer für EIN Gebäude aus Roof_solid in Parquet.
    Ein Gebäude kann mehrere Dachflächen haben!

    Returns:
        (parquet_path, count) - Pfad und Anzahl gefundener Dächer
    """
    import math

    output_path = output_dir / f"{tile_id}_{egid}.parquet"
    count = 0
    egid_str = str(egid)

    with StreamingParquetWriter(output_path, ROOFS_SCHEMA, batch_size=10) as writer:
        try:
            with fiona.open(gdb_path, layer="Roof_solid") as src:
                for feature in src:
                    props = feature.get("properties", {})

                    # EGID prüfen (als String in Roof_solid)
                    feat_egid = props.get("EGID")
                    if feat_egid is not None:
                        if isinstance(feat_egid, float):
                            if math.isnan(feat_egid):
                                continue
                            feat_egid = str(int(feat_egid))
                        else:
                            feat_egid = str(int(feat_egid))

                    if feat_egid != egid_str:
                        continue

                    gebaeudeeinheit = props.get("GEBAEUDEEINHEIT")
                    if not gebaeudeeinheit:
                        continue

                    # Geometrie
                    geom = feature.get("geometry")
                    geometry_wkb = None
                    if geom:
                        try:
                            geom_shape = shape(geom)
                            geometry_wkb = geom_shape.wkb
                        except Exception:
                            pass

                    writer.write({
                        'gebaeudeeinheit': gebaeudeeinheit,
                        'egid': egid_str,
                        'dach_min': props.get("DACH_MIN"),
                        'dach_max': props.get("DACH_MAX"),
                        'roof_form': None,
                        'roof_angle_deg': None,
                        'roof_orientation': None,
                        'roof_form_confidence': None,
                        'z_levels': None,
                        'calculation_method': None,
                        'tile_id': tile_id,
                        'geometry_wkb': geometry_wkb,
                    })
                    count += 1

        except Exception as e:
            logger.error(f"Error parsing Roof_solid for EGID {egid}: {e}")

    return output_path, count


def _stream_single_wall_to_parquet(
    gdb_path: Path,
    egid: int,
    tile_id: str,
    output_dir: Path
) -> tuple[Path, int]:
    """
    Streamt Wände für EIN Gebäude aus Wall-Layer in Parquet.

    Returns:
        (parquet_path, count) - Pfad und Anzahl gefundener Wände
    """
    import math

    output_path = output_dir / f"{tile_id}_{egid}.parquet"
    count = 0
    egid_str = str(egid)

    with StreamingParquetWriter(output_path, WALLS_SCHEMA, batch_size=10) as writer:
        try:
            with fiona.open(gdb_path, layer="Wall") as src:
                for feature in src:
                    props = feature.get("properties", {})
                    geom = feature.get("geometry")

                    # EGID prüfen
                    feat_egid = props.get("EGID")
                    if feat_egid is not None:
                        if isinstance(feat_egid, float):
                            if math.isnan(feat_egid):
                                continue
                            feat_egid = str(int(feat_egid))
                        else:
                            feat_egid = str(int(feat_egid))

                    if feat_egid != egid_str:
                        continue

                    gebaeudeeinheit = props.get("GEBAEUDEEINHEIT")
                    if not gebaeudeeinheit:
                        continue

                    # Z-Koordinaten
                    z_min = None
                    z_max = None
                    geometry_wkb = None

                    if geom:
                        try:
                            geom_shape = shape(geom)
                            geometry_wkb = geom_shape.wkb

                            gelaendepunkt = props.get("GELAENDEPUNKT") or 0
                            gesamthoehe = props.get("GESAMTHOEHE") or 0

                            if gelaendepunkt:
                                z_min = gelaendepunkt
                                z_max = gelaendepunkt + gesamthoehe if gesamthoehe else None
                        except Exception:
                            pass

                    writer.write({
                        'gebaeudeeinheit': gebaeudeeinheit,
                        'egid': egid_str,
                        'z_min': z_min,
                        'z_max': z_max,
                        'geometry_wkb': geometry_wkb,
                        'tile_id': tile_id,
                    })
                    count += 1

        except Exception as e:
            logger.error(f"Error parsing Wall for EGID {egid}: {e}")

    return output_path, count


def _load_single_building_parquets_to_duckdb(
    parquet_dir: Path,
    tile_id: str,
    egid: int
) -> Dict[str, int]:
    """
    Lädt Parquet-Dateien für ein einzelnes Gebäude in DuckDB.
    Setzt has_3d_layers=1 für dieses Gebäude.
    """
    from app.config import get_building_3d_connection

    results = {'buildings': 0, 'roofs': 0, 'walls': 0}
    parquet_suffix = f"{tile_id}_{egid}.parquet"

    conn = get_building_3d_connection()

    try:
        # 1. BUILDING
        buildings_path = parquet_dir / "buildings" / parquet_suffix
        if buildings_path.exists():
            conn.execute(f"""
                INSERT INTO buildings_3d (
                    egid, geom, traufhoehe_m, firsthoehe_m, gebaeudehoehe_m,
                    area_m2, perimeter_m, center_e, center_n, tile_id,
                    objektart, name_komplett, gebaeude_nutzung, gebaeudeeinheit,
                    roof_form, roof_form_confidence, roof_orientation,
                    has_3d_layers, imported_at, source
                )
                SELECT
                    egid, ST_GeomFromWKB(geom_wkb), traufhoehe_m, firsthoehe_m, gebaeudehoehe_m,
                    area_m2, perimeter_m, center_e, center_n, tile_id,
                    objektart, name_komplett, gebaeude_nutzung, gebaeudeeinheit,
                    roof_form, roof_form_confidence, roof_orientation,
                    1 as has_3d_layers,
                    current_timestamp as imported_at,
                    source
                FROM read_parquet('{buildings_path}')
                ON CONFLICT (egid) DO UPDATE SET
                    geom = excluded.geom,
                    traufhoehe_m = excluded.traufhoehe_m,
                    firsthoehe_m = excluded.firsthoehe_m,
                    gebaeudehoehe_m = excluded.gebaeudehoehe_m,
                    area_m2 = excluded.area_m2,
                    perimeter_m = excluded.perimeter_m,
                    center_e = excluded.center_e,
                    center_n = excluded.center_n,
                    tile_id = excluded.tile_id,
                    objektart = excluded.objektart,
                    name_komplett = excluded.name_komplett,
                    gebaeude_nutzung = excluded.gebaeude_nutzung,
                    gebaeudeeinheit = excluded.gebaeudeeinheit,
                    has_3d_layers = 1,
                    imported_at = now(),
                    source = excluded.source
            """)
            results['buildings'] = 1

        # 2. ROOFS
        roofs_path = parquet_dir / "roofs" / parquet_suffix
        if roofs_path.exists():
            count_result = conn.execute(f"SELECT COUNT(*) FROM read_parquet('{roofs_path}')").fetchone()
            parquet_count = count_result[0] if count_result else 0

            if parquet_count > 0:
                conn.execute(f"""
                    INSERT OR REPLACE INTO building_roofs (
                        gebaeudeeinheit, egid, dach_min, dach_max,
                        roof_form, roof_angle_deg, roof_orientation, z_levels, calculation_method,
                        geometry_wkb, has_full_geometry
                    )
                    SELECT
                        gebaeudeeinheit,
                        CAST(egid AS INTEGER),
                        dach_min,
                        dach_max,
                        roof_form,
                        roof_angle_deg,
                        roof_orientation,
                        z_levels,
                        calculation_method,
                        geometry_wkb,
                        CASE WHEN geometry_wkb IS NOT NULL THEN 1 ELSE 0 END
                    FROM read_parquet('{roofs_path}')
                """)
                results['roofs'] = parquet_count

        # 3. WALLS
        walls_path = parquet_dir / "walls" / parquet_suffix
        if walls_path.exists():
            count_result = conn.execute(f"SELECT COUNT(*) FROM read_parquet('{walls_path}')").fetchone()
            parquet_count = count_result[0] if count_result else 0

            if parquet_count > 0:
                conn.execute(f"""
                    INSERT OR REPLACE INTO building_walls (
                        gebaeudeeinheit, egid, z_min, z_max, geometry_wkb
                    )
                    SELECT
                        gebaeudeeinheit,
                        CAST(egid AS INTEGER),
                        z_min,
                        z_max,
                        geometry_wkb
                    FROM read_parquet('{walls_path}')
                """)
                results['walls'] = parquet_count

    except Exception as e:
        logger.error(f"[DUCKDB] Single-Building Load Fehler für EGID {egid}: {e}")
        raise
    finally:
        conn.close()

    return results


async def import_single_building(
    gdb_path: Path,
    egid: int,
    tile_id: str,
    cleanup_after: bool = True
) -> Dict[str, Any]:
    """
    Importiert EIN Gebäude mit allen 3 Layern (Building, Roof, Wall).

    Für SSE-Pipeline Stufe 1: Das angefragte Objekt sofort speichern (~50ms Ziel).
    Setzt has_3d_layers=1 nach erfolgreichem Import.

    Args:
        gdb_path: Pfad zur GDB-Datei
        egid: Eidg. Gebäudeidentifikator
        tile_id: Tile-ID für Metadaten
        cleanup_after: Parquet-Dateien nach Load löschen

    Returns:
        Dict mit Import-Statistiken und Erfolgs-Flag
    """
    import asyncio

    if not gdb_path or not gdb_path.exists():
        logger.warning(f"[SINGLE-IMPORT] GDB nicht gefunden: {gdb_path}")
        return {
            'egid': egid,
            'tile_id': tile_id,
            'success': False,
            'reason': 'gdb_not_found',
            'buildings_count': 0,
            'roofs_count': 0,
            'walls_count': 0,
        }

    start_time = time.time()
    output_dir = PARQUET_DIR / "single"

    # Phase 1: Parse alle 3 Layer parallel (gefiltert nach EGID)
    async def parse_building():
        return await asyncio.to_thread(
            _stream_single_building_to_parquet, gdb_path, egid, tile_id, output_dir / "buildings"
        )

    async def parse_roofs():
        return await asyncio.to_thread(
            _stream_single_roof_to_parquet, gdb_path, egid, tile_id, output_dir / "roofs"
        )

    async def parse_walls():
        return await asyncio.to_thread(
            _stream_single_wall_to_parquet, gdb_path, egid, tile_id, output_dir / "walls"
        )

    results = await asyncio.gather(parse_building(), parse_roofs(), parse_walls())

    building_path, building_found = results[0]
    roofs_path, roofs_count = results[1]
    walls_path, walls_count = results[2]

    parse_ms = (time.time() - start_time) * 1000

    if not building_found:
        logger.warning(f"[SINGLE-IMPORT] EGID {egid} nicht in GDB gefunden")
        # Cleanup leere Parquet-Dateien
        for p in [building_path, roofs_path, walls_path]:
            if p.exists():
                p.unlink()
        return {
            'egid': egid,
            'tile_id': tile_id,
            'success': False,
            'reason': 'egid_not_found',
            'parse_ms': parse_ms,
            'buildings_count': 0,
            'roofs_count': 0,
            'walls_count': 0,
        }

    # Phase 2: Load in DuckDB
    load_result = await asyncio.to_thread(
        _load_single_building_parquets_to_duckdb, output_dir, tile_id, egid
    )

    # Phase 3: Cleanup
    if cleanup_after:
        parquet_suffix = f"{tile_id}_{egid}.parquet"
        for subdir in ["buildings", "roofs", "walls"]:
            parquet_file = output_dir / subdir / parquet_suffix
            if parquet_file.exists():
                parquet_file.unlink()

    elapsed_ms = (time.time() - start_time) * 1000

    logger.info(
        f"[SINGLE-IMPORT] EGID {egid}: "
        f"1 building, {roofs_count} roofs, {walls_count} walls "
        f"({elapsed_ms:.0f}ms) → has_3d_layers=1"
    )

    return {
        'egid': egid,
        'tile_id': tile_id,
        'success': True,
        'parse_ms': parse_ms,
        'total_ms': elapsed_ms,
        'buildings_count': 1,
        'roofs_count': roofs_count,
        'walls_count': walls_count,
        'load_result': load_result,
        'has_3d_layers': True,
    }


# =============================================================================
# NEU 31.01.2026: RADIUS-IMPORT (für SSE-Pipeline Stufe 2)
# =============================================================================

def _stream_buildings_in_radius_to_parquet(
    gdb_path: Path,
    center_e: float,
    center_n: float,
    radius_m: float,
    tile_id: str,
    output_dir: Path,
    exclude_egids: Optional[set] = None
) -> tuple[Path, List[int]]:
    """
    Streamt alle Gebäude im Radius aus Building_solid in Parquet.

    Args:
        center_e, center_n: Zentrums-Koordinaten (LV95)
        radius_m: Suchradius in Metern
        exclude_egids: EGIDs die übersprungen werden (z.B. bereits importiert)

    Returns:
        (parquet_path, found_egids) - Pfad und Liste gefundener EGIDs
    """
    import math

    output_path = output_dir / f"{tile_id}_radius.parquet"
    found_egids = []
    exclude_egids = exclude_egids or set()
    radius_sq = radius_m * radius_m

    with StreamingParquetWriter(output_path, BUILDINGS_SCHEMA, batch_size=100) as writer:
        try:
            with fiona.open(gdb_path, layer="Building_solid") as src:
                for feature in src:
                    props = feature.get("properties", {})
                    geom = feature.get("geometry")

                    # EGID extrahieren
                    egid = props.get("EGID")
                    if egid is not None and isinstance(egid, float):
                        if math.isnan(egid):
                            continue
                        egid = int(egid)
                    elif egid is not None:
                        egid = int(egid)

                    if egid is None or egid in exclude_egids:
                        continue

                    if not geom:
                        continue

                    # Geometrie parsen
                    try:
                        geom_shape = shape(geom)
                        if isinstance(geom_shape, MultiPolygon):
                            geom_shape = unary_union(geom_shape)
                        if not isinstance(geom_shape, Polygon):
                            continue
                    except Exception:
                        continue

                    # FIX 07.02.2026: Prüfe auf leere/ungültige Geometrie
                    if geom_shape.is_empty or not geom_shape.is_valid:
                        logger.warning(f"[PARQUET] Skip EGID {egid}: empty or invalid geometry (radius search)")
                        continue

                    # Distanz zum Zentrum prüfen
                    centroid = geom_shape.centroid
                    dx = centroid.x - center_e
                    dy = centroid.y - center_n
                    dist_sq = dx * dx + dy * dy

                    if dist_sq > radius_sq:
                        continue  # Ausserhalb Radius

                    # Im Radius! WKB erstellen
                    coords = list(geom_shape.exterior.coords)
                    coords_2d = [(round(c[0], 2), round(c[1], 2)) for c in coords]
                    polygon_2d = Polygon(coords_2d)
                    geom_wkb = wkb.dumps(polygon_2d) if polygon_2d.is_valid else None

                    # Höhen
                    gelaendepunkt = props.get("GELAENDEPUNKT") or 0
                    dach_min = props.get("DACH_MIN") or 0
                    dach_max = props.get("DACH_MAX") or 0
                    gesamthoehe = props.get("GESAMTHOEHE") or 0

                    traufhoehe = (dach_min - gelaendepunkt) if dach_min and gelaendepunkt else None
                    firsthoehe = (dach_max - gelaendepunkt) if dach_max and gelaendepunkt else None

                    writer.write({
                        'egid': egid,
                        'geom_wkb': geom_wkb,
                        'traufhoehe_m': traufhoehe,
                        'firsthoehe_m': firsthoehe,
                        'gebaeudehoehe_m': gesamthoehe,
                        'area_m2': round(geom_shape.area, 2),
                        'perimeter_m': round(geom_shape.length, 2),
                        'center_e': round(centroid.x, 2),
                        'center_n': round(centroid.y, 2),
                        'tile_id': tile_id,
                        'objektart': props.get("OBJEKTART"),
                        'name_komplett': props.get("NAME_KOMPLETT"),
                        'gebaeude_nutzung': props.get("GEBAEUDENUTZUNG"),
                        'gebaeudeeinheit': props.get("GEBAEUDEEINHEIT"),
                        'roof_form': None,
                        'roof_form_confidence': None,
                        'roof_orientation': None,
                        'source': 'swissBUILDINGS3D',
                    })
                    found_egids.append(egid)

        except Exception as e:
            logger.error(f"Error parsing Building_solid in radius: {e}")

    return output_path, found_egids


def _stream_roofs_by_egids_to_parquet(
    gdb_path: Path,
    egids: List[int],
    tile_id: str,
    output_dir: Path
) -> tuple[Path, int]:
    """
    Streamt Dächer für mehrere EGIDs in Parquet.

    Returns:
        (parquet_path, count)
    """
    import math

    output_path = output_dir / f"{tile_id}_radius.parquet"
    count = 0
    egid_strs = {str(e) for e in egids}

    with StreamingParquetWriter(output_path, ROOFS_SCHEMA, batch_size=100) as writer:
        try:
            with fiona.open(gdb_path, layer="Roof_solid") as src:
                for feature in src:
                    props = feature.get("properties", {})

                    feat_egid = props.get("EGID")
                    if feat_egid is not None:
                        if isinstance(feat_egid, float):
                            if math.isnan(feat_egid):
                                continue
                            feat_egid = str(int(feat_egid))
                        else:
                            feat_egid = str(int(feat_egid))

                    if feat_egid not in egid_strs:
                        continue

                    gebaeudeeinheit = props.get("GEBAEUDEEINHEIT")
                    if not gebaeudeeinheit:
                        continue

                    geom = feature.get("geometry")
                    geometry_wkb = None
                    if geom:
                        try:
                            geom_shape = shape(geom)
                            geometry_wkb = geom_shape.wkb
                        except Exception:
                            pass

                    writer.write({
                        'gebaeudeeinheit': gebaeudeeinheit,
                        'egid': feat_egid,
                        'dach_min': props.get("DACH_MIN"),
                        'dach_max': props.get("DACH_MAX"),
                        'roof_form': None,
                        'roof_angle_deg': None,
                        'roof_orientation': None,
                        'roof_form_confidence': None,
                        'z_levels': None,
                        'calculation_method': None,
                        'tile_id': tile_id,
                        'geometry_wkb': geometry_wkb,
                    })
                    count += 1

        except Exception as e:
            logger.error(f"Error parsing Roof_solid for EGIDs: {e}")

    return output_path, count


def _stream_walls_by_egids_to_parquet(
    gdb_path: Path,
    egids: List[int],
    tile_id: str,
    output_dir: Path
) -> tuple[Path, int]:
    """
    Streamt Wände für mehrere EGIDs in Parquet.

    Returns:
        (parquet_path, count)
    """
    import math

    output_path = output_dir / f"{tile_id}_radius.parquet"
    count = 0
    egid_strs = {str(e) for e in egids}

    with StreamingParquetWriter(output_path, WALLS_SCHEMA, batch_size=100) as writer:
        try:
            with fiona.open(gdb_path, layer="Wall") as src:
                for feature in src:
                    props = feature.get("properties", {})
                    geom = feature.get("geometry")

                    feat_egid = props.get("EGID")
                    if feat_egid is not None:
                        if isinstance(feat_egid, float):
                            if math.isnan(feat_egid):
                                continue
                            feat_egid = str(int(feat_egid))
                        else:
                            feat_egid = str(int(feat_egid))

                    if feat_egid not in egid_strs:
                        continue

                    gebaeudeeinheit = props.get("GEBAEUDEEINHEIT")
                    if not gebaeudeeinheit:
                        continue

                    z_min = None
                    z_max = None
                    geometry_wkb = None

                    if geom:
                        try:
                            geom_shape = shape(geom)
                            geometry_wkb = geom_shape.wkb

                            gelaendepunkt = props.get("GELAENDEPUNKT") or 0
                            gesamthoehe = props.get("GESAMTHOEHE") or 0

                            if gelaendepunkt:
                                z_min = gelaendepunkt
                                z_max = gelaendepunkt + gesamthoehe if gesamthoehe else None
                        except Exception:
                            pass

                    writer.write({
                        'gebaeudeeinheit': gebaeudeeinheit,
                        'egid': feat_egid,
                        'z_min': z_min,
                        'z_max': z_max,
                        'geometry_wkb': geometry_wkb,
                        'tile_id': tile_id,
                    })
                    count += 1

        except Exception as e:
            logger.error(f"Error parsing Wall for EGIDs: {e}")

    return output_path, count


def _load_radius_parquets_to_duckdb(
    parquet_dir: Path,
    tile_id: str
) -> Dict[str, int]:
    """
    Lädt Radius-Parquet-Dateien in DuckDB.
    Setzt has_3d_layers=1 für alle importierten Gebäude.
    """
    from app.config import get_building_3d_connection

    results = {'buildings': 0, 'roofs': 0, 'walls': 0}
    parquet_suffix = f"{tile_id}_radius.parquet"

    conn = get_building_3d_connection()

    try:
        # 1. BUILDINGS
        buildings_path = parquet_dir / "buildings" / parquet_suffix
        if buildings_path.exists():
            count_result = conn.execute(f"SELECT COUNT(*) FROM read_parquet('{buildings_path}')").fetchone()
            parquet_count = count_result[0] if count_result else 0

            if parquet_count > 0:
                conn.execute(f"""
                    INSERT INTO buildings_3d (
                        egid, geom, traufhoehe_m, firsthoehe_m, gebaeudehoehe_m,
                        area_m2, perimeter_m, center_e, center_n, tile_id,
                        objektart, name_komplett, gebaeude_nutzung, gebaeudeeinheit,
                        roof_form, roof_form_confidence, roof_orientation,
                        has_3d_layers, imported_at, source
                    )
                    SELECT
                        egid, ST_GeomFromWKB(geom_wkb), traufhoehe_m, firsthoehe_m, gebaeudehoehe_m,
                        area_m2, perimeter_m, center_e, center_n, tile_id,
                        objektart, name_komplett, gebaeude_nutzung, gebaeudeeinheit,
                        roof_form, roof_form_confidence, roof_orientation,
                        1 as has_3d_layers,
                        current_timestamp as imported_at,
                        source
                    FROM read_parquet('{buildings_path}')
                    ON CONFLICT (egid) DO UPDATE SET
                        geom = excluded.geom,
                        traufhoehe_m = excluded.traufhoehe_m,
                        firsthoehe_m = excluded.firsthoehe_m,
                        gebaeudehoehe_m = excluded.gebaeudehoehe_m,
                        area_m2 = excluded.area_m2,
                        perimeter_m = excluded.perimeter_m,
                        center_e = excluded.center_e,
                        center_n = excluded.center_n,
                        tile_id = excluded.tile_id,
                        objektart = excluded.objektart,
                        name_komplett = excluded.name_komplett,
                        gebaeude_nutzung = excluded.gebaeude_nutzung,
                        gebaeudeeinheit = excluded.gebaeudeeinheit,
                        has_3d_layers = 1,
                        imported_at = now(),
                        source = excluded.source
                """)
                results['buildings'] = parquet_count

        # 2. ROOFS
        roofs_path = parquet_dir / "roofs" / parquet_suffix
        if roofs_path.exists():
            count_result = conn.execute(f"SELECT COUNT(*) FROM read_parquet('{roofs_path}')").fetchone()
            parquet_count = count_result[0] if count_result else 0

            if parquet_count > 0:
                conn.execute(f"""
                    INSERT OR REPLACE INTO building_roofs (
                        gebaeudeeinheit, egid, dach_min, dach_max,
                        roof_form, roof_angle_deg, roof_orientation, z_levels, calculation_method,
                        geometry_wkb, has_full_geometry
                    )
                    SELECT
                        gebaeudeeinheit,
                        CAST(egid AS INTEGER),
                        dach_min,
                        dach_max,
                        roof_form,
                        roof_angle_deg,
                        roof_orientation,
                        z_levels,
                        calculation_method,
                        geometry_wkb,
                        CASE WHEN geometry_wkb IS NOT NULL THEN 1 ELSE 0 END
                    FROM read_parquet('{roofs_path}')
                """)
                results['roofs'] = parquet_count

        # 3. WALLS
        walls_path = parquet_dir / "walls" / parquet_suffix
        if walls_path.exists():
            count_result = conn.execute(f"SELECT COUNT(*) FROM read_parquet('{walls_path}')").fetchone()
            parquet_count = count_result[0] if count_result else 0

            if parquet_count > 0:
                conn.execute(f"""
                    INSERT OR REPLACE INTO building_walls (
                        gebaeudeeinheit, egid, z_min, z_max, geometry_wkb
                    )
                    SELECT
                        gebaeudeeinheit,
                        CAST(egid AS INTEGER),
                        z_min,
                        z_max,
                        geometry_wkb
                    FROM read_parquet('{walls_path}')
                """)
                results['walls'] = parquet_count

    except Exception as e:
        logger.error(f"[DUCKDB] Radius-Load Fehler: {e}")
        raise
    finally:
        conn.close()

    return results


async def import_buildings_in_radius(
    gdb_path: Path,
    center_e: float,
    center_n: float,
    radius_m: float,
    tile_id: str,
    exclude_egids: Optional[set] = None,
    cleanup_after: bool = True
) -> Dict[str, Any]:
    """
    Importiert alle Gebäude im Radius mit allen 3 Layern.

    Für SSE-Pipeline Stufe 2: Nachbarn im 100m Radius (~1.8s Ziel).
    Setzt has_3d_layers=1 für alle importierten Gebäude.

    Args:
        gdb_path: Pfad zur GDB-Datei
        center_e, center_n: Zentrums-Koordinaten (LV95)
        radius_m: Suchradius in Metern
        tile_id: Tile-ID
        exclude_egids: EGIDs die übersprungen werden
        cleanup_after: Parquet-Dateien nach Load löschen

    Returns:
        Dict mit Import-Statistiken
    """
    import asyncio

    if not gdb_path or not gdb_path.exists():
        logger.warning(f"[RADIUS-IMPORT] GDB nicht gefunden: {gdb_path}")
        return {
            'center': (center_e, center_n),
            'radius_m': radius_m,
            'tile_id': tile_id,
            'success': False,
            'reason': 'gdb_not_found',
            'buildings_count': 0,
            'roofs_count': 0,
            'walls_count': 0,
        }

    start_time = time.time()
    output_dir = PARQUET_DIR / "radius"

    # Phase 1: Parse Buildings im Radius (um EGIDs zu sammeln)
    buildings_path, found_egids = await asyncio.to_thread(
        _stream_buildings_in_radius_to_parquet,
        gdb_path, center_e, center_n, radius_m, tile_id,
        output_dir / "buildings", exclude_egids
    )

    if not found_egids:
        logger.info(f"[RADIUS-IMPORT] Keine Gebäude im {radius_m}m Radius gefunden")
        if buildings_path.exists():
            buildings_path.unlink()
        return {
            'center': (center_e, center_n),
            'radius_m': radius_m,
            'tile_id': tile_id,
            'success': True,
            'buildings_count': 0,
            'roofs_count': 0,
            'walls_count': 0,
            'egids': [],
        }

    # Phase 2: Parse Roofs und Walls für gefundene EGIDs (parallel)
    async def parse_roofs():
        return await asyncio.to_thread(
            _stream_roofs_by_egids_to_parquet,
            gdb_path, found_egids, tile_id, output_dir / "roofs"
        )

    async def parse_walls():
        return await asyncio.to_thread(
            _stream_walls_by_egids_to_parquet,
            gdb_path, found_egids, tile_id, output_dir / "walls"
        )

    results = await asyncio.gather(parse_roofs(), parse_walls())
    roofs_path, roofs_count = results[0]
    walls_path, walls_count = results[1]

    parse_ms = (time.time() - start_time) * 1000

    # Phase 3: Load in DuckDB
    load_result = await asyncio.to_thread(
        _load_radius_parquets_to_duckdb, output_dir, tile_id
    )

    # Phase 4: Cleanup
    if cleanup_after:
        parquet_suffix = f"{tile_id}_radius.parquet"
        for subdir in ["buildings", "roofs", "walls"]:
            parquet_file = output_dir / subdir / parquet_suffix
            if parquet_file.exists():
                parquet_file.unlink()

    elapsed_ms = (time.time() - start_time) * 1000

    logger.info(
        f"[RADIUS-IMPORT] {len(found_egids)} buildings, {roofs_count} roofs, {walls_count} walls "
        f"in {radius_m}m radius ({elapsed_ms:.0f}ms) → has_3d_layers=1"
    )

    return {
        'center': (center_e, center_n),
        'radius_m': radius_m,
        'tile_id': tile_id,
        'success': True,
        'parse_ms': parse_ms,
        'total_ms': elapsed_ms,
        'buildings_count': len(found_egids),
        'roofs_count': roofs_count,
        'walls_count': walls_count,
        'egids': found_egids,
        'load_result': load_result,
        'has_3d_layers': True,
    }