"""
GeodataService - Zentrale Verwaltung von Gebäude-Geodaten.

Cached Geodaten aus swissBUILDINGS3D in lokaler SQLite-DB.
Polygon wird original gespeichert, Vereinfachung erfolgt on-the-fly.

Features:
- EGID-Lookup (~1ms)
- Koordinaten-Lookup (~1-3ms)
- Nachbar-Suche für Gerüstbau (~5-15ms)
"""

import json
import math
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any
from dataclasses import dataclass, asdict, field

# Douglas-Peucker Default-Parameter
DEFAULT_SIMPLIFY_EPSILON = 0.3  # Meter
DEFAULT_COLLINEAR_ANGLE_TOLERANCE = 8.0  # Grad


@dataclass
class BuildingGeodata:
    """Gecachte Geodaten eines Gebäudes."""
    egid: str
    address: Optional[str] = None

    # Polygon (Original aus swissBUILDINGS3D)
    polygon: Optional[List[Tuple[float, float]]] = None

    # Höhen
    traufhoehe_m: Optional[float] = None
    firsthoehe_m: Optional[float] = None
    gebaeudehoehe_m: Optional[float] = None

    # Metadaten
    area_m2: Optional[float] = None
    perimeter_m: Optional[float] = None
    center_e: Optional[float] = None
    center_n: Optional[float] = None

    # Koordinaten für Lookup
    coord_e: Optional[float] = None
    coord_n: Optional[float] = None

    # Zeitstempel
    fetched_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class NeighborBuilding:
    """Ein Nachbargebäude mit Distanz-Informationen."""
    egid: str
    polygon: Optional[List[Tuple[float, float]]] = None

    # Distanz zum Zielgebäude
    distance_m: float = 0.0

    # Richtung relativ zum Zielgebäude (N, NE, E, SE, S, SW, W, NW)
    direction: Optional[str] = None

    # Zentrum des Nachbarn
    center_e: Optional[float] = None
    center_n: Optional[float] = None

    # Höhen (für 3D-View)
    traufhoehe_m: Optional[float] = None
    firsthoehe_m: Optional[float] = None
    gebaeudehoehe_m: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class NeighborsResult:
    """Ergebnis der Nachbar-Suche."""
    target_egid: str
    target_polygon: Optional[List[Tuple[float, float]]] = None
    target_center_e: Optional[float] = None
    target_center_n: Optional[float] = None

    neighbors: List[NeighborBuilding] = field(default_factory=list)

    # Meta
    radius_m: float = 10.0
    query_time_ms: float = 0.0
    source: str = "building_geodata.db"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = asdict(self)
        result["neighbors"] = [n.to_dict() if hasattr(n, 'to_dict') else n for n in self.neighbors]
        return result


class GeodataService:
    """Service für Gebäude-Geodaten mit lokalem Cache."""

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            db_path = Path(__file__).parent.parent / "data" / "building_geodata.db"
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS buildings (
                egid TEXT PRIMARY KEY,
                address TEXT,

                -- Polygon (Original aus swissBUILDINGS3D)
                polygon TEXT,

                -- Höhen
                traufhoehe_m REAL,
                firsthoehe_m REAL,
                gebaeudehoehe_m REAL,

                -- Metadaten
                area_m2 REAL,
                perimeter_m REAL,
                center_e REAL,
                center_n REAL,

                -- Lookup ohne EGID
                coord_e REAL,
                coord_n REAL,

                fetched_at TEXT
            )
        ''')

        # Indices für schnellen Lookup
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_buildings_coords
            ON buildings(coord_e, coord_n)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_buildings_address
            ON buildings(address)
        ''')

        conn.commit()
        conn.close()

        print(f"[GeodataService] DB initialisiert: {self.db_path}")

    def get_by_egid(self, egid: str) -> Optional[BuildingGeodata]:
        """Get building geodata by EGID."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM buildings WHERE egid = ?', (egid,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return self._row_to_geodata(row)
        return None

    def get_by_coordinates(
        self,
        e: float,
        n: float,
        tolerance_m: float = 50.0
    ) -> Optional[BuildingGeodata]:
        """Get building geodata by coordinates with tolerance."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Suche nächstes Gebäude innerhalb Toleranz
        cursor.execute('''
            SELECT *,
                   ABS(coord_e - ?) + ABS(coord_n - ?) as distance
            FROM buildings
            WHERE coord_e BETWEEN ? AND ?
              AND coord_n BETWEEN ? AND ?
            ORDER BY distance
            LIMIT 1
        ''', (e, n, e - tolerance_m, e + tolerance_m, n - tolerance_m, n + tolerance_m))

        row = cursor.fetchone()
        conn.close()

        if row:
            return self._row_to_geodata(row)
        return None

    def get_by_address(self, address: str) -> Optional[BuildingGeodata]:
        """Get building geodata by address (exact match)."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM buildings WHERE address = ?', (address,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return self._row_to_geodata(row)
        return None

    def save(self, geodata: BuildingGeodata) -> None:
        """Save or update building geodata."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Polygon als JSON serialisieren
        polygon_json = json.dumps(geodata.polygon) if geodata.polygon else None

        cursor.execute('''
            INSERT OR REPLACE INTO buildings (
                egid, address, polygon,
                traufhoehe_m, firsthoehe_m, gebaeudehoehe_m,
                area_m2, perimeter_m, center_e, center_n,
                coord_e, coord_n, fetched_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            geodata.egid,
            geodata.address,
            polygon_json,
            geodata.traufhoehe_m,
            geodata.firsthoehe_m,
            geodata.gebaeudehoehe_m,
            geodata.area_m2,
            geodata.perimeter_m,
            geodata.center_e,
            geodata.center_n,
            geodata.coord_e,
            geodata.coord_n,
            geodata.fetched_at or datetime.utcnow().isoformat()
        ))

        conn.commit()
        conn.close()

    def delete(self, egid: str) -> bool:
        """Delete building geodata by EGID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('DELETE FROM buildings WHERE egid = ?', (egid,))
        deleted = cursor.rowcount > 0

        conn.commit()
        conn.close()

        return deleted

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) FROM buildings')
        count = cursor.fetchone()[0]

        cursor.execute('SELECT MIN(fetched_at), MAX(fetched_at) FROM buildings')
        min_date, max_date = cursor.fetchone()

        conn.close()

        return {
            "total_buildings": count,
            "oldest_entry": min_date,
            "newest_entry": max_date,
            "db_path": str(self.db_path)
        }

    def get_neighbors(
        self,
        egid: str,
        radius_m: float = 10.0,
        include_polygons: bool = True
    ) -> Optional[NeighborsResult]:
        """
        Findet alle Nachbargebäude im Umkreis.

        Für Gerüstbau: Erkennt angrenzende Gebäude die Fassaden blockieren.

        WICHTIG: Sucht zuerst in building_geodata.db, dann im egid_tile_index
        (tiles.db), da der Tile-Index ALLE Gebäude aus heruntergeladenen Tiles
        enthält, während building_geodata.db nur explizit abgefragte Gebäude hat.

        Args:
            egid: EGID des Zielgebäudes
            radius_m: Suchradius in Metern (0=nur angrenzend, 5=nah, 10=Kontext)
            include_polygons: Polygone mitliefern (für 3D-View)

        Returns:
            NeighborsResult mit Zielgebäude und Liste der Nachbarn
        """
        import time
        start_time = time.time()

        # Zielgebäude laden
        target = self.get_by_egid(egid)
        if not target:
            return None

        if not target.coord_e or not target.coord_n:
            return None

        # Koordinaten zu LV95 konvertieren (falls nötig)
        target_e_lv95 = target.coord_e
        target_n_lv95 = target.coord_n
        if target_e_lv95 < 2000000:
            target_e_lv95 += 2000000
        if target_n_lv95 < 1000000:
            target_n_lv95 += 1000000

        neighbors = []
        found_egids = set()

        # 1. Zuerst in building_geodata.db suchen (hat Polygone)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        search_radius = radius_m + 50
        cursor.execute('''
            SELECT egid, polygon, coord_e, coord_n, center_e, center_n,
                   traufhoehe_m, firsthoehe_m, gebaeudehoehe_m
            FROM buildings
            WHERE egid != ?
              AND coord_e BETWEEN ? AND ?
              AND coord_n BETWEEN ? AND ?
        ''', (
            egid,
            target.coord_e - search_radius, target.coord_e + search_radius,
            target.coord_n - search_radius, target.coord_n + search_radius
        ))

        for row in cursor.fetchall():
            neighbor_polygon = None
            if row['polygon']:
                neighbor_polygon = [tuple(p) for p in json.loads(row['polygon'])]

            if target.polygon and neighbor_polygon:
                distance = _polygon_distance(target.polygon, neighbor_polygon)
            else:
                dx = (row['coord_e'] or row['center_e'] or 0) - target.coord_e
                dy = (row['coord_n'] or row['center_n'] or 0) - target.coord_n
                distance = math.sqrt(dx*dx + dy*dy)

            if distance > radius_m:
                continue

            neighbor_center_e = row['center_e'] or row['coord_e']
            neighbor_center_n = row['center_n'] or row['coord_n']

            # Fassaden-basierte Richtungsberechnung wenn Polygone verfügbar
            if target.polygon and neighbor_polygon and distance < 1.0:
                # Bei angrenzenden Gebäuden (< 1m): Fassaden-Analyse
                direction = _calculate_facade_direction(target.polygon, neighbor_polygon)
            else:
                # Fallback: Schwerpunkt-basiert
                direction = _calculate_direction(
                    target.coord_e, target.coord_n,
                    neighbor_center_e, neighbor_center_n
                )

            neighbors.append(NeighborBuilding(
                egid=row['egid'],
                polygon=neighbor_polygon if include_polygons else None,
                distance_m=round(distance, 2),
                direction=direction,
                center_e=neighbor_center_e,
                center_n=neighbor_center_n,
                traufhoehe_m=row['traufhoehe_m'],
                firsthoehe_m=row['firsthoehe_m'],
                gebaeudehoehe_m=row['gebaeudehoehe_m']
            ))
            found_egids.add(row['egid'])

        conn.close()

        # 2. Dann im egid_tile_index suchen (hat alle Gebäude aus Tiles)
        # Dies findet Nachbarn die noch nicht in building_geodata.db sind
        tiles_db_path = Path(self.db_path).parent / "tiles.db"
        if tiles_db_path.exists():
            conn_tiles = sqlite3.connect(tiles_db_path)
            conn_tiles.row_factory = sqlite3.Row
            cursor_tiles = conn_tiles.cursor()

            cursor_tiles.execute('''
                SELECT egid, lv95_e, lv95_n
                FROM egid_tile_index
                WHERE egid != ?
                  AND lv95_e BETWEEN ? AND ?
                  AND lv95_n BETWEEN ? AND ?
            ''', (
                int(egid) if egid.isdigit() else egid,
                target_e_lv95 - search_radius, target_e_lv95 + search_radius,
                target_n_lv95 - search_radius, target_n_lv95 + search_radius
            ))

            # WICHTIG: Ergebnisse SOFORT speichern, bevor neuer Query läuft!
            neighbor_rows = cursor_tiles.fetchall()

            # Get tile_id for potential on-demand polygon loading
            cursor_tiles.execute(
                'SELECT tile_id FROM egid_tile_index WHERE egid = ?',
                (int(egid) if egid.isdigit() else egid,)
            )
            tile_row = cursor_tiles.fetchone()
            tile_id = tile_row['tile_id'] if tile_row else None

            for row in neighbor_rows:
                neighbor_egid = str(row['egid'])

                # Skip wenn schon gefunden
                if neighbor_egid in found_egids:
                    continue

                # Distanz berechnen (Zentrum-zu-Zentrum, LV95)
                dx = row['lv95_e'] - target_e_lv95
                dy = row['lv95_n'] - target_n_lv95
                center_distance = math.sqrt(dx*dx + dy*dy)

                if center_distance > radius_m:
                    continue

                # Versuchen Polygon aus building_geodata.db zu laden
                neighbor_polygon = None
                neighbor_heights = {}
                cached = self.get_by_egid(neighbor_egid)
                if cached:
                    neighbor_polygon = cached.polygon if include_polygons else None
                    neighbor_heights = {
                        'traufhoehe_m': cached.traufhoehe_m,
                        'firsthoehe_m': cached.firsthoehe_m,
                        'gebaeudehoehe_m': cached.gebaeudehoehe_m,
                    }

                # Calculate actual distance
                distance = center_distance

                # For close neighbors (< 20m center distance), try to get polygon
                # to calculate accurate polygon-to-polygon distance
                if center_distance < 20 and target.polygon:
                    if neighbor_polygon:
                        # Have polygon - calculate exact distance
                        distance = _polygon_distance(target.polygon, neighbor_polygon)
                    elif tile_id:
                        # No polygon cached - try to load from GDB on-demand
                        try:
                            from app.services.tile_cache import get_tile_cache
                            tile_cache = get_tile_cache()
                            gdb_path = tile_cache.get_tile_path(tile_id)
                            if gdb_path and gdb_path.exists():
                                # Load polygon from GDB
                                loaded_polygon = _load_polygon_from_gdb(
                                    gdb_path, int(neighbor_egid)
                                )
                                if loaded_polygon:
                                    neighbor_polygon = loaded_polygon
                                    distance = _polygon_distance(
                                        target.polygon, neighbor_polygon
                                    )
                                    # Cache for next time
                                    self.save(BuildingGeodata(
                                        egid=neighbor_egid,
                                        polygon=loaded_polygon,
                                        coord_e=row['lv95_e'] - 2000000 if row['lv95_e'] > 2000000 else row['lv95_e'],
                                        coord_n=row['lv95_n'] - 1000000 if row['lv95_n'] > 1000000 else row['lv95_n'],
                                        center_e=row['lv95_e'],
                                        center_n=row['lv95_n'],
                                    ))
                        except Exception as e:
                            # On-demand loading failed, use center distance
                            import logging
                            logging.getLogger(__name__).debug(
                                f"On-demand polygon load failed for {neighbor_egid}: {e}"
                            )

                # Fassaden-basierte Richtungsberechnung wenn Polygone verfügbar
                if target.polygon and neighbor_polygon and distance < 1.0:
                    # Bei angrenzenden Gebäuden (< 1m): Fassaden-Analyse
                    direction = _calculate_facade_direction(target.polygon, neighbor_polygon)
                else:
                    # Fallback: Schwerpunkt-basiert (mit LV95 Koordinaten)
                    direction = _calculate_direction(
                        target_e_lv95, target_n_lv95,
                        row['lv95_e'], row['lv95_n']
                    )

                neighbors.append(NeighborBuilding(
                    egid=neighbor_egid,
                    polygon=neighbor_polygon if include_polygons else None,
                    distance_m=round(distance, 2),
                    direction=direction,
                    center_e=row['lv95_e'],
                    center_n=row['lv95_n'],
                    traufhoehe_m=neighbor_heights.get('traufhoehe_m'),
                    firsthoehe_m=neighbor_heights.get('firsthoehe_m'),
                    gebaeudehoehe_m=neighbor_heights.get('gebaeudehoehe_m')
                ))
                found_egids.add(neighbor_egid)

            conn_tiles.close()

        # Nach Distanz sortieren
        neighbors.sort(key=lambda n: n.distance_m)

        query_time = (time.time() - start_time) * 1000

        return NeighborsResult(
            target_egid=egid,
            target_polygon=target.polygon if include_polygons else None,
            target_center_e=target.coord_e,
            target_center_n=target.coord_n,
            neighbors=neighbors,
            radius_m=radius_m,
            query_time_ms=round(query_time, 2),
            source="building_geodata.db+tiles.db"
        )

    def _row_to_geodata(self, row: sqlite3.Row) -> BuildingGeodata:
        """Convert database row to BuildingGeodata."""
        polygon = None
        if row['polygon']:
            polygon = [tuple(p) for p in json.loads(row['polygon'])]

        return BuildingGeodata(
            egid=row['egid'],
            address=row['address'],
            polygon=polygon,
            traufhoehe_m=row['traufhoehe_m'],
            firsthoehe_m=row['firsthoehe_m'],
            gebaeudehoehe_m=row['gebaeudehoehe_m'],
            area_m2=row['area_m2'],
            perimeter_m=row['perimeter_m'],
            center_e=row['center_e'],
            center_n=row['center_n'],
            coord_e=row['coord_e'],
            coord_n=row['coord_n'],
            fetched_at=row['fetched_at']
        )


def _polygon_distance(poly1: List[Tuple[float, float]], poly2: List[Tuple[float, float]]) -> float:
    """
    Berechnet minimale Distanz zwischen zwei Polygonen.

    Für angrenzende Gebäude (Reihenhäuser) ist die Distanz ~0.

    Args:
        poly1, poly2: Listen von (x, y) Koordinaten

    Returns:
        Minimale Distanz in Metern
    """
    min_dist = float('inf')

    # Jeden Punkt von poly1 gegen jede Kante von poly2 prüfen
    for p in poly1:
        for i in range(len(poly2) - 1):
            dist = _point_to_segment_distance(p, poly2[i], poly2[i + 1])
            min_dist = min(min_dist, dist)

    # Und umgekehrt
    for p in poly2:
        for i in range(len(poly1) - 1):
            dist = _point_to_segment_distance(p, poly1[i], poly1[i + 1])
            min_dist = min(min_dist, dist)

    return min_dist


def _load_polygon_from_gdb(gdb_path: Path, egid: int) -> Optional[List[Tuple[float, float]]]:
    """
    Lädt ein einzelnes Polygon aus einem GDB für einen bestimmten EGID.

    Args:
        gdb_path: Pfad zum GDB-Verzeichnis
        egid: EGID des Gebäudes

    Returns:
        Polygon als Liste von (x, y) Koordinaten oder None
    """
    try:
        import geopandas as gpd
        import fiona
    except ImportError:
        return None

    try:
        layers = fiona.listlayers(gdb_path)

        # Building-Layer finden
        target_layer = None
        for layer in layers:
            if 'building' in layer.lower() and 'solid' in layer.lower():
                target_layer = layer
                break
        if not target_layer:
            for layer in layers:
                if 'building' in layer.lower():
                    target_layer = layer
                    break
        if not target_layer and layers:
            target_layer = layers[0]

        if not target_layer:
            return None

        # GDB laden mit Filter für EGID
        gdf = gpd.read_file(gdb_path, layer=target_layer, engine='fiona')

        # EGID filtern
        matching = gdf[gdf['EGID'] == egid]
        if matching.empty:
            return None

        row = matching.iloc[0]
        geom = row.geometry

        if geom is None:
            return None

        # Polygon extrahieren (2D Footprint)
        polygon = None
        if hasattr(geom, 'geoms'):
            # MultiPolygon - take convex hull
            all_coords_2d = []
            for g in geom.geoms:
                if hasattr(g, 'exterior'):
                    coords = [(c[0], c[1]) for c in g.exterior.coords]
                    all_coords_2d.extend(coords)
            if all_coords_2d:
                from shapely.geometry import MultiPoint
                hull = MultiPoint(all_coords_2d).convex_hull
                if hasattr(hull, 'exterior'):
                    polygon = [(round(c[0], 2), round(c[1], 2))
                              for c in hull.exterior.coords]
        elif hasattr(geom, 'exterior'):
            # Single Polygon
            polygon = [(round(c[0], 2), round(c[1], 2))
                      for c in geom.exterior.coords]

        return polygon

    except Exception:
        return None


def _point_to_segment_distance(
    p: Tuple[float, float],
    a: Tuple[float, float],
    b: Tuple[float, float]
) -> float:
    """Berechnet Distanz von Punkt p zur Strecke ab."""
    px, py = p[0], p[1]
    ax, ay = a[0], a[1]
    bx, by = b[0], b[1]

    # Vektor ab
    abx = bx - ax
    aby = by - ay

    # Vektor ap
    apx = px - ax
    apy = py - ay

    # Projektion
    ab_sq = abx * abx + aby * aby
    if ab_sq == 0:
        # a und b sind gleich
        return math.sqrt(apx * apx + apy * apy)

    t = max(0, min(1, (apx * abx + apy * aby) / ab_sq))

    # Nächster Punkt auf der Strecke
    proj_x = ax + t * abx
    proj_y = ay + t * aby

    # Distanz
    dx = px - proj_x
    dy = py - proj_y
    return math.sqrt(dx * dx + dy * dy)


def _calculate_direction(
    from_e: float, from_n: float,
    to_e: float, to_n: float
) -> str:
    """
    Berechnet Himmelsrichtung von einem Punkt zum anderen.

    Returns:
        Richtung: N, NE, E, SE, S, SW, W, NW
    """
    dx = to_e - from_e
    dy = to_n - from_n

    # Winkel in Grad (0 = Ost, 90 = Nord)
    angle = math.degrees(math.atan2(dy, dx))

    # Normalisieren auf 0-360
    if angle < 0:
        angle += 360

    # Konvertieren zu Kompass (0 = Nord)
    compass = (90 - angle) % 360

    return _compass_to_direction(compass)


def _compass_to_direction(compass: float) -> str:
    """Konvertiert Kompass-Winkel (0=Nord) zu Himmelsrichtung."""
    # In 8 Richtungen einteilen
    if compass >= 337.5 or compass < 22.5:
        return "N"
    elif compass < 67.5:
        return "NE"
    elif compass < 112.5:
        return "E"
    elif compass < 157.5:
        return "SE"
    elif compass < 202.5:
        return "S"
    elif compass < 247.5:
        return "SW"
    elif compass < 292.5:
        return "W"
    else:
        return "NW"


def _calculate_facade_direction(
    target_polygon: List[Tuple[float, float]],
    neighbor_polygon: List[Tuple[float, float]]
) -> str:
    """
    Berechnet Himmelsrichtung basierend auf der blockierten Fassade.

    Findet die Kante des Ziel-Polygons, die am nächsten zum Nachbar-Schwerpunkt liegt,
    und berechnet deren Normalrichtung (nach aussen zeigend).

    Strategie: Bei überlappenden Polygonen (Reihenhäuser) haben viele Kanten
    Distanz 0. Deshalb verwenden wir die Kante, deren Mittelpunkt am nächsten
    zum Nachbar-Schwerpunkt liegt.

    Args:
        target_polygon: Polygon des Zielgebäudes
        neighbor_polygon: Polygon des Nachbargebäudes

    Returns:
        Himmelsrichtung der blockierten Fassade (N, NE, E, SE, S, SW, W, NW)
    """
    if not target_polygon or not neighbor_polygon:
        return "N"  # Fallback

    # Schwerpunkte berechnen
    target_center_e = sum(p[0] for p in target_polygon) / len(target_polygon)
    target_center_n = sum(p[1] for p in target_polygon) / len(target_polygon)

    neighbor_center_e = sum(p[0] for p in neighbor_polygon) / len(neighbor_polygon)
    neighbor_center_n = sum(p[1] for p in neighbor_polygon) / len(neighbor_polygon)

    # Distanz zwischen Schwerpunkten
    center_dist = math.sqrt(
        (neighbor_center_e - target_center_e)**2 +
        (neighbor_center_n - target_center_n)**2
    )

    # Bei sehr nahen/überlappenden Polygonen (<2m): Vereinfache auf 4 Hauptrichtungen
    # basierend auf der dominanten Achse (N/S oder E/W)
    if center_dist < 2.0:
        dx = neighbor_center_e - target_center_e
        dy = neighbor_center_n - target_center_n

        # Welche Achse dominiert?
        if abs(dy) >= abs(dx):
            # N-S dominiert
            return "N" if dy > 0 else "S"
        else:
            # E-W dominiert
            return "E" if dx > 0 else "W"

    # Finde die Kante, deren Mittelpunkt am nächsten zum Nachbar-Schwerpunkt liegt
    min_dist_to_neighbor = float('inf')
    best_edge_idx = 0

    for i in range(len(target_polygon) - 1):
        p1 = target_polygon[i]
        p2 = target_polygon[i + 1]

        # Kantenmittelpunkt
        mid_e = (p1[0] + p2[0]) / 2
        mid_n = (p1[1] + p2[1]) / 2

        # Distanz zum Nachbar-Schwerpunkt
        dist = math.sqrt((mid_e - neighbor_center_e)**2 + (mid_n - neighbor_center_n)**2)

        if dist < min_dist_to_neighbor:
            min_dist_to_neighbor = dist
            best_edge_idx = i

    # Die nächste Kante gefunden - berechne deren Normalrichtung
    p1 = target_polygon[best_edge_idx]
    p2 = target_polygon[best_edge_idx + 1]

    # Kantenvektor
    edge_dx = p2[0] - p1[0]
    edge_dy = p2[1] - p1[1]

    # Normalvektor (senkrecht zur Kante)
    # Es gibt zwei Möglichkeiten: (edge_dy, -edge_dx) oder (-edge_dy, edge_dx)
    # Wähle die, die zum Nachbarn zeigt (vom eigenen Schwerpunkt weg)

    # Mittelpunkt der Kante
    mid_e = (p1[0] + p2[0]) / 2
    mid_n = (p1[1] + p2[1]) / 2

    # Zwei mögliche Normalen
    normal1 = (edge_dy, -edge_dx)
    normal2 = (-edge_dy, edge_dx)

    # Richtungsvektor vom Kantenmittelpunkt zum Nachbar-Schwerpunkt
    to_neighbor_e = neighbor_center_e - mid_e
    to_neighbor_n = neighbor_center_n - mid_n

    # Dot-Product bestimmt welche Normale zum Nachbarn zeigt
    # Positive Dot-Product = Normale zeigt in gleiche Richtung wie "zum Nachbarn"
    dot1 = normal1[0] * to_neighbor_e + normal1[1] * to_neighbor_n

    if dot1 > 0:
        outward_normal = normal1
    else:
        outward_normal = normal2

    # Normalrichtung als Kompass-Winkel
    # atan2(dy, dx) gibt Winkel wo 0=Ost, 90=Nord
    angle = math.degrees(math.atan2(outward_normal[1], outward_normal[0]))
    if angle < 0:
        angle += 360

    # Konvertieren zu Kompass (0 = Nord)
    compass = (90 - angle) % 360

    return _compass_to_direction(compass)


# Singleton instance
_geodata_service: Optional[GeodataService] = None


def get_geodata_service() -> GeodataService:
    """Get singleton GeodataService instance."""
    global _geodata_service
    if _geodata_service is None:
        _geodata_service = GeodataService()
    return _geodata_service
