"""
NeighborsService - Nachbar-Suche für Gerüstbau.

Findet Nachbargebäude basierend auf:
1. smart_building_cache (Zielgebäude)
2. tiles.db (EGID-Index für alle Gebäude in heruntergeladenen Tiles)
3. On-demand GDB-Parsing für Polygone
"""

import json
import math
import sqlite3
import time
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple


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
    source: str = "smart_building_cache+tiles.db"

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result["neighbors"] = [n.to_dict() if hasattr(n, 'to_dict') else n for n in self.neighbors]
        return result


class NeighborsService:
    """
    Service für Nachbar-Suche.

    Verwendet SmartBuildingService für das Zielgebäude und
    smart_building_cache + tiles.db für die Nachbar-Suche.
    """

    def __init__(self):
        self.data_path = Path(__file__).parent.parent / "data"
        self.contexts_db_path = self.data_path / "building_contexts.db"
        self.tiles_db_path = self.data_path / "tiles.db"
        self._smart_service = None

    def _get_smart_service(self):
        """Lazy-Loading des SmartBuildingService."""
        if self._smart_service is None:
            from .smart_building import get_smart_building_service
            self._smart_service = get_smart_building_service()
        return self._smart_service

    def _get_building_from_cache(self, egid: str) -> Optional[Dict]:
        """
        Lädt Gebäude über SmartBuildingService.

        Für das Zielgebäude wird der SmartBuildingService verwendet,
        der den Cache verwaltet.
        """
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

        # 2. Nachbarn aus smart_building_cache suchen
        if self.contexts_db_path.exists():
            conn = sqlite3.connect(self.contexts_db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            search_radius = radius_m + 50
            cursor.execute("""
                SELECT egid, bundle_json
                FROM smart_building_cache
                WHERE egid != ?
            """, (egid,))

            for row in cursor.fetchall():
                neighbor_egid = row['egid']
                if neighbor_egid in found_egids:
                    continue

                bundle = json.loads(row['bundle_json'])
                neighbor_e = bundle.get('lv95_e', 0)
                neighbor_n = bundle.get('lv95_n', 0)

                # Koordinaten normalisieren
                if neighbor_e < 2000000:
                    neighbor_e += 2000000
                if neighbor_n < 1000000:
                    neighbor_n += 1000000

                # Grobe Filterung
                if abs(neighbor_e - target_e) > search_radius or abs(neighbor_n - target_n) > search_radius:
                    continue

                neighbor_polygon = bundle.get('polygon')

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
                    traufhoehe_m=bundle.get('traufhoehe_m'),
                    firsthoehe_m=bundle.get('firsthoehe_m'),
                    gebaeudehoehe_m=bundle.get('gebaeudehoehe_m')
                ))
                found_egids.add(neighbor_egid)

            conn.close()

        # 3. Zusätzlich im tiles.db EGID-Index suchen
        if self.tiles_db_path.exists():
            conn = sqlite3.connect(self.tiles_db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            search_radius = radius_m + 50
            cursor.execute("""
                SELECT egid, lv95_e, lv95_n, tile_id
                FROM egid_tile_index
                WHERE lv95_e BETWEEN ? AND ?
                  AND lv95_n BETWEEN ? AND ?
            """, (
                target_e - search_radius, target_e + search_radius,
                target_n - search_radius, target_n + search_radius
            ))

            for row in cursor.fetchall():
                neighbor_egid = str(row['egid'])
                if neighbor_egid in found_egids:
                    continue

                neighbor_e = row['lv95_e']
                neighbor_n = row['lv95_n']

                # Distanz berechnen (Zentrum-zu-Zentrum)
                dx = neighbor_e - target_e
                dy = neighbor_n - target_n
                distance = math.sqrt(dx*dx + dy*dy)

                if distance > radius_m:
                    continue

                direction = self._calculate_direction(target_e, target_n, neighbor_e, neighbor_n)

                # Polygon on-demand laden wenn nötig und nah genug
                neighbor_polygon = None
                if include_polygons and distance < 20:
                    neighbor_polygon = self._load_polygon_from_tile(row['tile_id'], int(row['egid']))

                neighbors.append(NeighborBuilding(
                    egid=neighbor_egid,
                    polygon=neighbor_polygon,
                    distance_m=round(distance, 2),
                    direction=direction,
                    center_e=neighbor_e,
                    center_n=neighbor_n,
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
            source="smart_building_cache+tiles.db"
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

    def _load_polygon_from_tile(self, tile_id: str, egid: int) -> Optional[List]:
        """Lädt Polygon aus GDB-Tile on-demand."""
        try:
            from .tile_cache import get_tile_cache
            tile_cache = get_tile_cache()
            gdb_path = tile_cache.get_tile_path(tile_id)

            if not gdb_path or not gdb_path.exists():
                return None

            import geopandas as gpd
            import fiona

            layers = fiona.listlayers(gdb_path)
            target_layer = None
            for layer in layers:
                if 'building' in layer.lower():
                    target_layer = layer
                    break
            if not target_layer and layers:
                target_layer = layers[0]

            if not target_layer:
                return None

            gdf = gpd.read_file(gdb_path, layer=target_layer, engine='fiona')
            matching = gdf[gdf['EGID'] == egid]

            if matching.empty:
                return None

            geom = matching.iloc[0].geometry
            if geom is None:
                return None

            if hasattr(geom, 'exterior'):
                return [(round(c[0], 2), round(c[1], 2)) for c in geom.exterior.coords]

            return None

        except Exception:
            return None


# Singleton
_neighbors_service: Optional[NeighborsService] = None


def get_neighbors_service() -> NeighborsService:
    """Get singleton NeighborsService instance."""
    global _neighbors_service
    if _neighbors_service is None:
        _neighbors_service = NeighborsService()
    return _neighbors_service
