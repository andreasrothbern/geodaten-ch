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

logger = logging.getLogger(__name__)

# Parquet-Output-Verzeichnis
PARQUET_DIR = Path(__file__).parent.parent / "data" / "parquet"


# =============================================================================
# SCHEMA-DEFINITIONEN
# =============================================================================

BUILDINGS_SCHEMA = pa.schema([
    ('egid', pa.int64()),
    ('polygon', pa.string()),           # JSON: [[e,n], ...]
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

                    # Koordinaten extrahieren (nur 2D)
                    coords = list(geom_shape.exterior.coords)
                    coords_2d = [[round(c[0], 2), round(c[1], 2)] for c in coords]

                    # Höhen berechnen
                    gelaendepunkt = props.get("GELAENDEPUNKT") or 0
                    dach_min = props.get("DACH_MIN") or 0
                    dach_max = props.get("DACH_MAX") or 0
                    gesamthoehe = props.get("GESAMTHOEHE") or 0

                    traufhoehe = (dach_min - gelaendepunkt) if dach_min and gelaendepunkt else None
                    firsthoehe = (dach_max - gelaendepunkt) if dach_max and gelaendepunkt else None

                    # Centroid
                    centroid = geom_shape.centroid

                    writer.write({
                        'egid': egid,
                        'polygon': json.dumps(coords_2d),
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

    Args:
        gdb_path: Pfad zur GDB-Datei
        tile_id: Tile-ID
        output_dir: Output-Verzeichnis (default: PARQUET_DIR)

    Returns:
        Dict mit Pfaden und Counts pro Layer
    """
    import asyncio

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
            conn.execute(f"""
                INSERT INTO buildings_3d (
                    egid, polygon, traufhoehe_m, firsthoehe_m, gebaeudehoehe_m,
                    area_m2, perimeter_m, center_e, center_n, tile_id,
                    objektart, name_komplett, gebaeude_nutzung, gebaeudeeinheit,
                    roof_form, roof_form_confidence, roof_orientation,
                    has_3d_layers, imported_at, source
                )
                SELECT
                    egid, polygon, traufhoehe_m, firsthoehe_m, gebaeudehoehe_m,
                    area_m2, perimeter_m, center_e, center_n, tile_id,
                    objektart, name_komplett, gebaeude_nutzung, gebaeudeeinheit,
                    roof_form, roof_form_confidence, roof_orientation,
                    0 as has_3d_layers,
                    current_timestamp as imported_at,
                    source
                FROM read_parquet('{buildings_glob}')
                ON CONFLICT (egid) DO UPDATE SET
                    polygon = excluded.polygon,
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
                    imported_at = current_timestamp,
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

            # Explizite Spaltenangabe - nur die gemeinsamen Spalten
            conn.execute(f"""
                INSERT OR REPLACE INTO building_roofs (
                    gebaeudeeinheit, egid, dach_min, dach_max,
                    roof_form, roof_angle_deg, roof_orientation, z_levels, calculation_method
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
                    calculation_method
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

        # 4. has_3d_layers Flag setzen für alle Gebäude mit Walls
        if results['walls'] > 0:
            conn.execute("""
                UPDATE buildings_3d SET has_3d_layers = 1
                WHERE egid IN (SELECT DISTINCT CAST(egid AS INTEGER) FROM building_walls WHERE egid IS NOT NULL)
            """)

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

    Args:
        gdb_path: Pfad zur GDB-Datei
        tile_id: Tile-ID
        cleanup_after: Parquet-Dateien nach Load löschen

    Returns:
        Dict mit Statistiken
    """
    import asyncio

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