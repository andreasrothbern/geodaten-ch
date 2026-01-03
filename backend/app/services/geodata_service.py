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

        # Nachbarn im Umkreis suchen
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Rechteck-Suche (schnell mit Index)
        search_radius = radius_m + 50  # Etwas grösser für Polygon-Distanz
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

        rows = cursor.fetchall()
        conn.close()

        neighbors = []

        for row in rows:
            neighbor_polygon = None
            if row['polygon']:
                neighbor_polygon = [tuple(p) for p in json.loads(row['polygon'])]

            # Distanz berechnen (Polygon-zu-Polygon wenn vorhanden)
            if target.polygon and neighbor_polygon:
                distance = _polygon_distance(target.polygon, neighbor_polygon)
            else:
                # Fallback: Zentrum-zu-Zentrum
                dx = (row['coord_e'] or row['center_e'] or 0) - target.coord_e
                dy = (row['coord_n'] or row['center_n'] or 0) - target.coord_n
                distance = math.sqrt(dx*dx + dy*dy)

            # Filter nach tatsächlichem Radius
            if distance > radius_m:
                continue

            # Richtung berechnen
            neighbor_center_e = row['center_e'] or row['coord_e']
            neighbor_center_n = row['center_n'] or row['coord_n']
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
            source="building_geodata.db"
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


# Singleton instance
_geodata_service: Optional[GeodataService] = None


def get_geodata_service() -> GeodataService:
    """Get singleton GeodataService instance."""
    global _geodata_service
    if _geodata_service is None:
        _geodata_service = GeodataService()
    return _geodata_service
