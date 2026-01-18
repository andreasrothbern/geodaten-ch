"""
NeighborsService - Nachbar-Suche für Gerüstbau.

Findet Nachbargebäude basierend auf:
1. building_3d.db (primär - alle pre-processed Gebäude)
2. smart_building_cache (Fallback für Bundle-Daten)

WICHTIG: building_3d.db enthält ALLE Gebäude aus heruntergeladenen Tiles
(via tile_prefetch). Dies ist viel schneller als GDB-Parsing!

NEU 13.01.2026 17:00: DuckDB-kompatibel via get_building_3d_connection()

FIX 17.01.2026: traufhoehe_m/firsthoehe_m wiederhergestellt!
Nachbar-Höhen werden aus buildings_3d gelesen (Schätzung aus GELAENDEPUNKT).
Bei Hanglagen ~1-2m ungenau, aber für 3D-Visualisierung ausreichend.
Für das Hauptgebäude erfolgt exakte Berechnung via Terrain-Sampling.

FIX 18.01.2026 21:45: Multi-EGID Support für Projekte mit mehreren Gebäuden.
EGID-Strings wie "1243787+1243789+1243791" werden korrekt in Liste geparst.
"""

def parse_egid_list(egid_input):
    """
    FIX 18.01.2026 21:45: Fail-safe EGID-Parsing für alle Formate.

    Unterstützt:
    - Integer: 1243787
    - String: "1243787"
    - Multi-EGID String: "1243787+1243789+1243791"
    - Liste: [1243787, 1243789]

    Returns:
        Liste von Integer-EGIDs (leere Liste bei Fehler)
    """
    if egid_input is None:
        return []

    # Bereits eine Liste
    if isinstance(egid_input, list):
        result = []
        for e in egid_input:
            try:
                result.append(int(e))
            except (ValueError, TypeError):
                pass
        return result

    # Integer direkt
    if isinstance(egid_input, int):
        return [egid_input]

    # String: prüfen ob Multi-EGID (mit +)
    if isinstance(egid_input, str):
        if '+' in egid_input:
            result = []
            for part in egid_input.split('+'):
                try:
                    result.append(int(part.strip()))
                except (ValueError, TypeError):
                    pass
            return result
        else:
            try:
                return [int(egid_input)]
            except (ValueError, TypeError):
                return []

    return []

import json
import math
import time
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

# NEU 13.01.2026 17:00: DuckDB-kompatible Connection
# FIX 14.01.2026 13:50: DATA_DIR aus config.py für Railway Volume
# NEU 18.01.2026 23:15: NEIGHBOR_SEARCH_RADIUS_M für SQL-Suchradius
from app.config import get_building_3d_connection, BUILDING_3D_DB_PATH, DATA_DIR, NEIGHBOR_SEARCH_RADIUS_M


@dataclass
class NeighborBuilding:
    """Ein Nachbargebäude mit Distanz-Informationen."""
    egid: str
    polygon: Optional[List[Tuple[float, float]]] = None
    distance_m: float = 0.0
    direction: Optional[str] = None
    center_e: Optional[float] = None
    center_n: Optional[float] = None
    # FIX 17.01.2026: Höhen aus buildings_3d (Schätzung aus GELAENDEPUNKT)
    traufhoehe_m: Optional[float] = None
    firsthoehe_m: Optional[float] = None
    gebaeudehoehe_m: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class NeighborsResult:
    """Ergebnis der Nachbar-Suche."""
    target_egid: str
    target_polygon: Optional[List[Tuple[float, float]]] = None
    target_center_e: Optional[float] = None
    target_center_n: Optional[float] = None
    neighbors: List[NeighborBuilding] = field(default_factory=list)
    radius_m: float = 10.0
    query_time_ms: float = 0.0
    source: str = "building_3d.db"

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result["neighbors"] = [n.to_dict() if hasattr(n, 'to_dict') else n for n in self.neighbors]
        return result


class NeighborsService:
    """
    Service für Nachbar-Suche.

    Alle Nachbarn werden aus building_3d.db geholt (O(1), ~1ms).
    Diese DB enthält ALLE Gebäude aus heruntergeladenen Tiles (via tile_prefetch).

    Für das Zielgebäude wird zusätzlich smart_building_cache als Fallback
    genutzt (in _get_building_from_cache), falls das Bundle noch nicht
    in building_3d.db ist (z.B. bei erstem Aufruf).

    FIX 17.01.2026: traufhoehe_m/firsthoehe_m wiederhergestellt!
    Höhen werden aus buildings_3d gelesen (Schätzung aus GELAENDEPUNKT).
    Für Nachbarn reicht diese Schätzung für 3D-Visualisierung.
    """

    def __init__(self):
        # FIX 14.01.2026 13:50: Nutze zentrale DATA_DIR aus config.py
        self.data_path = DATA_DIR
        # NEU 13.01.2026 17:00: Nutzt BUILDING_3D_DB_PATH (DuckDB oder SQLite)
        self.building_3d_db_path = BUILDING_3D_DB_PATH
        self._smart_service = None
        self._building_3d_service = None

    def _get_smart_service(self):
        """Lazy-Loading des SmartBuildingService."""
        if self._smart_service is None:
            from .smart_building import get_smart_building_service
            self._smart_service = get_smart_building_service()
        return self._smart_service

    def _get_building_3d_service(self):
        """Lazy-Loading des Building3DService."""
        if self._building_3d_service is None:
            from .building_3d_service import get_building_3d_service
            self._building_3d_service = get_building_3d_service()
        return self._building_3d_service

    def _get_building_from_cache(self, egid: str) -> Optional[Dict]:
        """
        Lädt Gebäude mit 2-Stufen Lookup.

        1. building_3d.db (primär) - Enthält alle pre-processed Gebäude
        2. smart_building_cache (Fallback) - Vollständige Bundle-Daten
        """
        # STUFE 1: building_3d.db prüfen (schnell!)
        try:
            conn = get_building_3d_connection()
            cursor = conn.cursor()

            # FIX 18.01.2026 21:50: parse_egid_list für fail-safe Parsing
            egid_list = parse_egid_list(egid)
            if not egid_list:
                return None
            egid_int = egid_list[0]  # Erstes EGID verwenden

            cursor.execute("""
                SELECT egid, polygon, center_e, center_n, gebaeudehoehe_m
                FROM buildings_3d
                WHERE egid = ?
            """, (egid_int,))

            row = cursor.fetchone()
            conn.close()

            if row:
                # Polygon aus JSON parsen falls String
                polygon_data = row[1] if isinstance(row, tuple) else row['polygon']
                polygon = None
                if polygon_data:
                    try:
                        polygon = json.loads(polygon_data) if isinstance(polygon_data, str) else polygon_data
                    except (json.JSONDecodeError, TypeError):
                        pass

                return {
                    'egid': str(row[0] if isinstance(row, tuple) else row['egid']),
                    'polygon': polygon,
                    'lv95_e': row[2] if isinstance(row, tuple) else row['center_e'],
                    'lv95_n': row[3] if isinstance(row, tuple) else row['center_n'],
                    # gebaeudehoehe_m ist GESAMTHOEHE, nicht traufhoehe!
                    'gebaeudehoehe_m': row[4] if isinstance(row, tuple) else row['gebaeudehoehe_m'],
                }
        except Exception:
            pass  # Fallback auf smart_building_cache

        # STUFE 2: smart_building_cache (Fallback)
        try:
            smart_service = self._get_smart_service()
            bundle = smart_service.get_bundle_by_egid(egid)

            if bundle is None:
                return None

            # Bundle zu Dict konvertieren (für Kompatibilität)
            return {
                'egid': bundle.egid,
                'polygon': bundle.polygon,
                'lv95_e': bundle.lv95_e,
                'lv95_n': bundle.lv95_n,
                'traufhoehe_m': bundle.traufhoehe_m,
                'firsthoehe_m': bundle.firsthoehe_m,
                'gebaeudehoehe_m': bundle.gebaeudehoehe_m,
            }
        except Exception:
            return None

    def get_neighbors(
        self,
        egid: str,
        radius_m: float = 10.0,
        include_polygons: bool = True
    ) -> Optional[NeighborsResult]:
        """
        Findet alle Nachbargebäude im Umkreis eines Objekts.

        FIX 18.01.2026 22:50: Einheitliche Behandlung - alles ist ein OBJEKT!
        Ein Objekt hat 1..n Gebäude. Die Nachbarsuche basiert immer auf dem
        Objektzentrum (BoundingBox aller Gebäude) und der Distanz zu den
        Objekt-Polygonen.

        Args:
            egid: EGID(s) des Objekts - unterstützt:
                  - "1243787" (einzelnes Gebäude)
                  - "1243787+1243789+1243791" (Multi-Building)
            radius_m: Suchradius in Metern (ab Objekt-Rand, nicht Zentrum!)
            include_polygons: Polygone mitliefern

        Returns:
            NeighborsResult mit Objektzentrum und Nachbarn
        """
        start_time = time.time()

        # EGID-Liste parsen (1..n Gebäude pro Objekt)
        object_egids = parse_egid_list(egid)
        if not object_egids:
            return None

        # Alle Gebäude des Objekts laden und BoundingBox berechnen
        object_polygons = []
        min_e, max_e = float('inf'), float('-inf')
        min_n, max_n = float('inf'), float('-inf')

        for obj_egid in object_egids:
            building = self._get_building_from_cache(str(obj_egid))
            if not building:
                continue

            poly = building.get('polygon')
            if poly:
                object_polygons.append(poly)
                # BoundingBox aus Polygon-Punkten (präziser als Zentrum)
                for point in poly:
                    px, py = point[0], point[1]
                    # LV95 normalisieren
                    if px < 2000000:
                        px += 2000000
                    if py < 1000000:
                        py += 1000000
                    min_e, max_e = min(min_e, px), max(max_e, px)
                    min_n, max_n = min(min_n, py), max(max_n, py)
            else:
                # Fallback: Zentrum verwenden
                e = building.get('lv95_e', 0)
                n = building.get('lv95_n', 0)
                if e < 2000000:
                    e += 2000000
                if n < 1000000:
                    n += 1000000
                min_e, max_e = min(min_e, e), max(max_e, e)
                min_n, max_n = min(min_n, n), max(max_n, n)

        if not object_polygons and min_e == float('inf'):
            return None

        # Objektzentrum = BoundingBox-Mitte
        object_center_e = (min_e + max_e) / 2
        object_center_n = (min_n + max_n) / 2

        # Für Response: Erstes Polygon als Referenz
        target_polygon = object_polygons[0] if object_polygons else None

        neighbors = []
        # Objekt-EGIDs ausschließen (als Strings für Vergleich)
        object_egid_set = {str(e) for e in object_egids}

        # Nachbarn aus building_3d DB suchen (DuckDB mit R-Tree Index)
        if self.building_3d_db_path.exists():
            conn = get_building_3d_connection()
            cursor = conn.cursor()

            # SQL-Suchradius aus Config (Default: 100m)
            # Ein Call, R-Tree indexiert - Performance kein Problem
            # Exakte Filterung erfolgt danach via Polygon-Distanz mit radius_m
            sql_search_radius = NEIGHBOR_SEARCH_RADIUS_M

            # SQL mit dynamischer NOT IN Klausel für Objekt-EGIDs
            placeholders = ','.join(['?' for _ in object_egids])
            cursor.execute(f"""
                SELECT egid, polygon, center_e, center_n,
                       traufhoehe_m, firsthoehe_m, gebaeudehoehe_m
                FROM buildings_3d
                WHERE center_e BETWEEN ? AND ?
                  AND center_n BETWEEN ? AND ?
                  AND egid NOT IN ({placeholders})
            """, (
                object_center_e - sql_search_radius, object_center_e + sql_search_radius,
                object_center_n - sql_search_radius, object_center_n + sql_search_radius,
                *object_egids
            ))

            for row in cursor.fetchall():
                neighbor_egid = str(row[0] if isinstance(row, tuple) else row['egid'])
                if neighbor_egid in object_egid_set:
                    continue

                neighbor_e = row[2] if isinstance(row, tuple) else row['center_e']
                neighbor_n = row[3] if isinstance(row, tuple) else row['center_n']

                # Polygon parsen
                neighbor_polygon = None
                polygon_data = row[1] if isinstance(row, tuple) else row['polygon']
                if include_polygons and polygon_data:
                    try:
                        neighbor_polygon = json.loads(polygon_data) if isinstance(polygon_data, str) else polygon_data
                    except (json.JSONDecodeError, TypeError):
                        pass

                # Distanz = MIN(Distanz zu allen Objekt-Polygonen)
                # So findet man Nachbarn die nah an IRGENDEINEM Gebäude sind
                if object_polygons and neighbor_polygon:
                    distance = min(
                        self._polygon_distance(obj_poly, neighbor_polygon)
                        for obj_poly in object_polygons
                    )
                else:
                    # Fallback: Distanz zum Objektzentrum
                    dx = neighbor_e - object_center_e
                    dy = neighbor_n - object_center_n
                    distance = math.sqrt(dx*dx + dy*dy)

                # Nur Nachbarn innerhalb des User-Radius behalten
                if distance > radius_m:
                    continue

                # Richtung vom Objektzentrum
                direction = self._calculate_direction(object_center_e, object_center_n, neighbor_e, neighbor_n)

                neighbors.append(NeighborBuilding(
                    egid=neighbor_egid,
                    polygon=neighbor_polygon if include_polygons else None,
                    distance_m=round(distance, 2),
                    direction=direction,
                    center_e=neighbor_e,
                    center_n=neighbor_n,
                    traufhoehe_m=row[4] if isinstance(row, tuple) else row['traufhoehe_m'],
                    firsthoehe_m=row[5] if isinstance(row, tuple) else row['firsthoehe_m'],
                    gebaeudehoehe_m=row[6] if isinstance(row, tuple) else row['gebaeudehoehe_m']
                ))

            conn.close()

        # Nach Distanz sortieren
        neighbors.sort(key=lambda n: n.distance_m)

        query_time_ms = (time.time() - start_time) * 1000

        return NeighborsResult(
            target_egid=egid,
            target_polygon=target_polygon if include_polygons else None,
            target_center_e=object_center_e,
            target_center_n=object_center_n,
            neighbors=neighbors,
            radius_m=radius_m,
            query_time_ms=round(query_time_ms, 2),
            source="building_3d.duckdb"
        )

    def _polygon_distance(self, poly1: List, poly2: List) -> float:
        """Berechnet minimale Distanz zwischen zwei Polygonen."""
        min_dist = float('inf')

        for p in poly1:
            p_coords = (p[0], p[1]) if isinstance(p, (list, tuple)) else (p.get('x', 0), p.get('y', 0))
            for i in range(len(poly2) - 1):
                q1 = poly2[i]
                q2 = poly2[i + 1]
                q1_coords = (q1[0], q1[1]) if isinstance(q1, (list, tuple)) else (q1.get('x', 0), q1.get('y', 0))
                q2_coords = (q2[0], q2[1]) if isinstance(q2, (list, tuple)) else (q2.get('x', 0), q2.get('y', 0))
                dist = self._point_to_segment_distance(p_coords, q1_coords, q2_coords)
                min_dist = min(min_dist, dist)

        return min_dist

    def _point_to_segment_distance(self, p: Tuple, a: Tuple, b: Tuple) -> float:
        """Berechnet Distanz von Punkt p zur Strecke ab."""
        px, py = p
        ax, ay = a
        bx, by = b

        abx = bx - ax
        aby = by - ay
        apx = px - ax
        apy = py - ay

        ab_sq = abx * abx + aby * aby
        if ab_sq == 0:
            return math.sqrt(apx * apx + apy * apy)

        t = max(0, min(1, (apx * abx + apy * aby) / ab_sq))
        proj_x = ax + t * abx
        proj_y = ay + t * aby

        dx = px - proj_x
        dy = py - proj_y
        return math.sqrt(dx * dx + dy * dy)

    def _calculate_direction(self, from_e: float, from_n: float, to_e: float, to_n: float) -> str:
        """Berechnet Himmelsrichtung."""
        dx = to_e - from_e
        dy = to_n - from_n

        angle = math.degrees(math.atan2(dy, dx))
        if angle < 0:
            angle += 360

        compass = (90 - angle) % 360

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

# Singleton
_neighbors_service: Optional[NeighborsService] = None


def get_neighbors_service() -> NeighborsService:
    """Get singleton NeighborsService instance."""
    global _neighbors_service
    if _neighbors_service is None:
        _neighbors_service = NeighborsService()
    return _neighbors_service
