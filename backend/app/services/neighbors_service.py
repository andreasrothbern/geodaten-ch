"""
NeighborsService - Nachbar-Suche für Gerüstbau.

Findet Nachbargebäude basierend auf:
1. building_3d.db (primär - alle pre-processed Gebäude)
2. smart_building_cache (Fallback für Bundle-Daten)
3. tiles.db (EGID-Index, nur für Koordinaten)

WICHTIG: building_3d.db enthält ALLE Gebäude aus heruntergeladenen Tiles
(via tile_prefetch). Dies ist viel schneller als GDB-Parsing!

NEU 13.01.2026 17:00: DuckDB-kompatibel via get_building_3d_connection()
"""

import json
import math
import time
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

# NEU 13.01.2026 17:00: DuckDB-kompatible Connection
# FIX 14.01.2026 13:50: DATA_DIR aus config.py für Railway Volume
from app.config import get_building_3d_connection, BUILDING_3D_DB_PATH, DATA_DIR


@dataclass
class NeighborBuilding:
    """Ein Nachbargebäude mit Distanz-Informationen."""
    egid: str
    polygon: Optional[List[Tuple[float, float]]] = None
    distance_m: float = 0.0
    direction: Optional[str] = None
    center_e: Optional[float] = None
    center_n: Optional[float] = None
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
        Lädt Gebäude mit 3-Stufen Lookup.

        1. building_3d.db (primär) - Enthält alle pre-processed Gebäude
        2. smart_building_cache (Fallback) - Vollständige Bundle-Daten
        """
        # STUFE 1: building_3d.db prüfen (schnell!)
        try:
            building_3d_service = self._get_building_3d_service()
            building = building_3d_service.get_by_egid(int(egid))
            if building:
                # Polygon aus JSON parsen falls String
                polygon = building.get('polygon')
                if isinstance(polygon, str):
                    polygon = json.loads(polygon)

                return {
                    'egid': str(building.get('egid')),
                    'polygon': polygon,
                    'lv95_e': building.get('center_e'),
                    'lv95_n': building.get('center_n'),
                    'traufhoehe_m': building.get('traufhoehe_m'),
                    'firsthoehe_m': building.get('firsthoehe_m'),
                    'gebaeudehoehe_m': building.get('gebaeudehoehe_m'),
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
        Findet alle Nachbargebäude im Umkreis.

        Args:
            egid: EGID des Zielgebäudes
            radius_m: Suchradius in Metern
            include_polygons: Polygone mitliefern

        Returns:
            NeighborsResult mit Zielgebäude und Nachbarn
        """
        start_time = time.time()

        # 1. Zielgebäude aus Cache laden
        target_bundle = self._get_building_from_cache(egid)
        if not target_bundle:
            return None

        target_polygon = target_bundle.get('polygon')
        target_e = target_bundle.get('lv95_e')
        target_n = target_bundle.get('lv95_n')

        if not target_e or not target_n:
            return None

        # Koordinaten normalisieren (LV95)
        if target_e < 2000000:
            target_e += 2000000
        if target_n < 1000000:
            target_n += 1000000

        neighbors = []
        found_egids = set()
        found_egids.add(egid)  # Zielgebäude ausschließen

        # 2. PRIMÄR: Nachbarn aus building_3d DB suchen (schnell!)
        # Dies enthält ALLE Gebäude aus heruntergeladenen Tiles via prefetch
        # NEU 13.01.2026 17:00: get_building_3d_connection() für DuckDB/SQLite
        if self.building_3d_db_path.exists():
            conn = get_building_3d_connection()
            cursor = conn.cursor()

            search_radius = radius_m + 50
            cursor.execute("""
                SELECT egid, polygon, center_e, center_n,
                       traufhoehe_m, firsthoehe_m, gebaeudehoehe_m
                FROM buildings_3d
                WHERE center_e BETWEEN ? AND ?
                  AND center_n BETWEEN ? AND ?
                  AND egid != ?
            """, (
                target_e - search_radius, target_e + search_radius,
                target_n - search_radius, target_n + search_radius,
                int(egid)
            ))

            for row in cursor.fetchall():
                # DuckDB gibt Tuple zurück, SQLite mit row_factory gibt Row zurück
                neighbor_egid = str(row[0] if isinstance(row, tuple) else row['egid'])
                if neighbor_egid in found_egids:
                    continue

                neighbor_e = row[2] if isinstance(row, tuple) else row['center_e']
                neighbor_n = row[3] if isinstance(row, tuple) else row['center_n']

                # Polygon aus JSON parsen
                neighbor_polygon = None
                polygon_data = row[1] if isinstance(row, tuple) else row['polygon']
                if include_polygons and polygon_data:
                    try:
                        neighbor_polygon = json.loads(polygon_data) if isinstance(polygon_data, str) else polygon_data
                    except (json.JSONDecodeError, TypeError):
                        pass

                # Distanz berechnen
                if target_polygon and neighbor_polygon:
                    distance = self._polygon_distance(target_polygon, neighbor_polygon)
                else:
                    dx = neighbor_e - target_e
                    dy = neighbor_n - target_n
                    distance = math.sqrt(dx*dx + dy*dy)

                if distance > radius_m:
                    continue

                # Richtung berechnen
                direction = self._calculate_direction(target_e, target_n, neighbor_e, neighbor_n)

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
                found_egids.add(neighbor_egid)

            conn.close()

        # Nach Distanz sortieren
        neighbors.sort(key=lambda n: n.distance_m)

        query_time = (time.time() - start_time) * 1000

        return NeighborsResult(
            target_egid=egid,
            target_polygon=target_polygon if include_polygons else None,
            target_center_e=target_e,
            target_center_n=target_n,
            neighbors=neighbors,
            radius_m=radius_m,
            query_time_ms=round(query_time, 2),
            source="building_3d.db"
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
