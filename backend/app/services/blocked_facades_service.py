"""
BlockedFacadesService - Ermittelt blockierte Fassaden für Gerüstbau.

Eine Fassade gilt als "blockiert" wenn:
- Ein externes Gebäude (nicht im Projekt) < threshold_m entfernt ist
- Kein Gerüst aufgestellt werden kann

WICHTIG für Projekte mit mehreren Gebäuden:
- project_egids enthält alle Gebäude des Projekts
- Nur EXTERNE Gebäude blockieren Fassaden
- Projekt-Gebäude untereinander blockieren NICHT

NEU 13.01.2026 17:00: DuckDB-kompatibel via get_building_3d_connection()
"""

import json
import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Set

# NEU 13.01.2026 17:00: DuckDB-kompatible Connection
from app.config import get_building_3d_connection, BUILDING_3D_DB_PATH


@dataclass
class BlockerInfo:
    """Information über ein blockierendes Gebäude."""
    egid: str
    distance_m: float
    direction: str  # N, NE, E, SE, S, SW, W, NW


@dataclass
class BlockedFacade:
    """Eine blockierte Fassade."""
    facade_index: int  # 0-basiert, entspricht Polygon-Kante
    blockers: List[BlockerInfo] = field(default_factory=list)
    min_distance_m: float = 0.0


@dataclass
class BlockedFacadesResult:
    """Ergebnis der Fassaden-Analyse für ein Gebäude."""
    egid: str
    blocked_indices: List[int]  # Liste der blockierten Fassaden-Indizes
    blocked_facades: List[BlockedFacade] = field(default_factory=list)
    total_facades: int = 0
    free_facades: int = 0
    query_time_ms: float = 0.0


class BlockedFacadesService:
    """
    Service zur Ermittlung blockierter Fassaden.

    Workflow:
    1. Polygon des Zielgebäudes laden
    2. Nachbarn im Umkreis von threshold_m suchen
    3. Projekt-Gebäude ausfiltern (exclude_egids)
    4. Für jede Fassade prüfen ob ein Nachbar-Polygon nahe ist
    """

    # Schwellenwert: Unter dieser Distanz gilt Fassade als blockiert
    DEFAULT_THRESHOLD_M = 2.0  # Gerüstbreite + Arbeitsraum

    def __init__(self):
        self.data_path = Path(__file__).parent.parent / "data"
        # NEU 13.01.2026 17:00: Nutzt BUILDING_3D_DB_PATH (DuckDB oder SQLite)
        self.building_3d_db_path = BUILDING_3D_DB_PATH

    def calculate_blocked_facades(
        self,
        egid: str,
        exclude_egids: Optional[Set[str]] = None,
        threshold_m: float = DEFAULT_THRESHOLD_M
    ) -> Optional[BlockedFacadesResult]:
        """
        Berechnet blockierte Fassaden für ein Gebäude.

        Args:
            egid: EGID des zu analysierenden Gebäudes
            exclude_egids: EGIDs die nicht als Blocker gelten (Projekt-Gebäude)
            threshold_m: Distanz-Schwellenwert für Blockierung

        Returns:
            BlockedFacadesResult mit blockierten Fassaden-Indizes
        """
        start_time = time.time()
        exclude_egids = exclude_egids or set()
        exclude_egids.add(egid)  # Eigenes Gebäude ausschliessen

        # 1. Zielgebäude laden
        building = self._load_building(egid)
        if not building or not building.get('polygon'):
            return None

        polygon = building['polygon']
        center_e = building['center_e']
        center_n = building['center_n']

        # Polygon muss mindestens 3 Punkte haben
        if len(polygon) < 3:
            return None

        # 2. Fassaden (Kanten) des Polygons extrahieren
        facades = self._extract_facades(polygon)
        total_facades = len(facades)

        # 3. Nachbarn im erweiterten Suchradius finden
        search_radius = threshold_m + 20  # Extra-Puffer für grosse Gebäude
        neighbors = self._find_neighbors(
            center_e, center_n,
            search_radius,
            exclude_egids
        )

        # 4. Für jede Fassade prüfen ob blockiert
        blocked_facades = []
        blocked_indices = []

        for idx, facade in enumerate(facades):
            blockers = self._check_facade_blocked(
                facade,
                neighbors,
                threshold_m,
                center_e, center_n
            )

            if blockers:
                min_dist = min(b.distance_m for b in blockers)
                blocked_facades.append(BlockedFacade(
                    facade_index=idx,
                    blockers=blockers,
                    min_distance_m=min_dist
                ))
                blocked_indices.append(idx)

        query_time = (time.time() - start_time) * 1000

        return BlockedFacadesResult(
            egid=egid,
            blocked_indices=blocked_indices,
            blocked_facades=blocked_facades,
            total_facades=total_facades,
            free_facades=total_facades - len(blocked_indices),
            query_time_ms=round(query_time, 2)
        )

    def calculate_for_project(
        self,
        project_egids: List[str],
        threshold_m: float = DEFAULT_THRESHOLD_M
    ) -> Dict[str, BlockedFacadesResult]:
        """
        Berechnet blockierte Fassaden für alle Projekt-Gebäude.

        Projekt-Gebäude untereinander blockieren sich NICHT.
        Nur externe Gebäude werden als Blocker berücksichtigt.

        Args:
            project_egids: Liste aller EGIDs im Projekt
            threshold_m: Distanz-Schwellenwert

        Returns:
            Dict mit EGID -> BlockedFacadesResult
        """
        project_egids_set = set(str(e) for e in project_egids)
        results = {}

        for egid in project_egids:
            result = self.calculate_blocked_facades(
                egid=str(egid),
                exclude_egids=project_egids_set.copy(),
                threshold_m=threshold_m
            )
            if result:
                results[str(egid)] = result

        return results

    def _load_building(self, egid: str) -> Optional[Dict]:
        """Lädt Gebäude aus building_3d DB (DuckDB oder SQLite)."""
        if not self.building_3d_db_path.exists():
            return None

        try:
            # NEU 13.01.2026 17:00: get_building_3d_connection() für DuckDB/SQLite
            conn = get_building_3d_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT egid, polygon, center_e, center_n,
                       traufhoehe_m, firsthoehe_m, gebaeudehoehe_m
                FROM buildings_3d
                WHERE egid = ?
            """, (int(egid),))

            row = cursor.fetchone()
            conn.close()

            if not row:
                return None

            # DuckDB gibt Tuple zurück, SQLite mit row_factory gibt Row zurück
            # Einheitlicher Zugriff per Index
            polygon = None
            polygon_data = row[1] if isinstance(row, tuple) else row['polygon']
            if polygon_data:
                try:
                    polygon = json.loads(polygon_data) if isinstance(polygon_data, str) else polygon_data
                except (json.JSONDecodeError, TypeError):
                    pass

            return {
                'egid': str(row[0] if isinstance(row, tuple) else row['egid']),
                'polygon': polygon,
                'center_e': row[2] if isinstance(row, tuple) else row['center_e'],
                'center_n': row[3] if isinstance(row, tuple) else row['center_n'],
                'traufhoehe_m': row[4] if isinstance(row, tuple) else row['traufhoehe_m'],
                'firsthoehe_m': row[5] if isinstance(row, tuple) else row['firsthoehe_m'],
                'gebaeudehoehe_m': row[6] if isinstance(row, tuple) else row['gebaeudehoehe_m']
            }
        except Exception:
            return None

    def _find_neighbors(
        self,
        center_e: float,
        center_n: float,
        search_radius: float,
        exclude_egids: Set[str]
    ) -> List[Dict]:
        """Findet Nachbargebäude aus building_3d DB (DuckDB oder SQLite)."""
        if not self.building_3d_db_path.exists():
            return []

        neighbors = []

        try:
            # NEU 13.01.2026 17:00: get_building_3d_connection() für DuckDB/SQLite
            conn = get_building_3d_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT egid, polygon, center_e, center_n
                FROM buildings_3d
                WHERE center_e BETWEEN ? AND ?
                  AND center_n BETWEEN ? AND ?
            """, (
                center_e - search_radius, center_e + search_radius,
                center_n - search_radius, center_n + search_radius
            ))

            for row in cursor.fetchall():
                # DuckDB gibt Tuple zurück, SQLite mit row_factory gibt Row zurück
                neighbor_egid = str(row[0] if isinstance(row, tuple) else row['egid'])
                if neighbor_egid in exclude_egids:
                    continue

                polygon = None
                polygon_data = row[1] if isinstance(row, tuple) else row['polygon']
                if polygon_data:
                    try:
                        polygon = json.loads(polygon_data) if isinstance(polygon_data, str) else polygon_data
                    except (json.JSONDecodeError, TypeError):
                        continue  # Ohne Polygon können wir nicht analysieren

                if polygon:
                    neighbors.append({
                        'egid': neighbor_egid,
                        'polygon': polygon,
                        'center_e': row[2] if isinstance(row, tuple) else row['center_e'],
                        'center_n': row[3] if isinstance(row, tuple) else row['center_n']
                    })

            conn.close()
        except Exception:
            pass

        return neighbors

    def _extract_facades(self, polygon: List) -> List[Tuple[Tuple[float, float], Tuple[float, float]]]:
        """
        Extrahiert Fassaden (Kanten) aus einem Polygon.

        Returns:
            Liste von (start_point, end_point) Tupeln
        """
        facades = []
        n = len(polygon)

        for i in range(n):
            p1 = polygon[i]
            p2 = polygon[(i + 1) % n]

            # Koordinaten normalisieren
            x1, y1 = self._get_coords(p1)
            x2, y2 = self._get_coords(p2)

            facades.append(((x1, y1), (x2, y2)))

        return facades

    def _get_coords(self, point) -> Tuple[float, float]:
        """Extrahiert x,y Koordinaten aus verschiedenen Formaten."""
        if isinstance(point, (list, tuple)):
            return (point[0], point[1])
        elif isinstance(point, dict):
            return (point.get('x', 0), point.get('y', 0))
        return (0, 0)

    def _check_facade_blocked(
        self,
        facade: Tuple[Tuple[float, float], Tuple[float, float]],
        neighbors: List[Dict],
        threshold_m: float,
        ref_e: float,
        ref_n: float
    ) -> List[BlockerInfo]:
        """
        Prüft ob eine Fassade durch Nachbar-Polygone blockiert ist.

        Args:
            facade: (start, end) Koordinaten der Fassade
            neighbors: Liste der Nachbargebäude mit Polygonen
            threshold_m: Distanz-Schwellenwert
            ref_e, ref_n: Referenzpunkt für Richtungsberechnung

        Returns:
            Liste der blockierenden Gebäude
        """
        blockers = []
        (x1, y1), (x2, y2) = facade

        # Mittelpunkt der Fassade
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2

        for neighbor in neighbors:
            neighbor_polygon = neighbor['polygon']

            # Minimale Distanz zwischen Fassade und Nachbar-Polygon
            min_dist = self._facade_to_polygon_distance(facade, neighbor_polygon)

            if min_dist < threshold_m:
                # Richtung berechnen
                direction = self._calculate_direction(
                    mid_x, mid_y,
                    neighbor['center_e'], neighbor['center_n']
                )

                blockers.append(BlockerInfo(
                    egid=neighbor['egid'],
                    distance_m=round(min_dist, 2),
                    direction=direction
                ))

        return blockers

    def _facade_to_polygon_distance(
        self,
        facade: Tuple[Tuple[float, float], Tuple[float, float]],
        polygon: List
    ) -> float:
        """
        Berechnet minimale Distanz zwischen Fassade und Polygon.
        """
        min_dist = float('inf')
        (fx1, fy1), (fx2, fy2) = facade

        # Distanz von Fassaden-Punkten zum Polygon
        for point in [facade[0], facade[1]]:
            for i in range(len(polygon)):
                p1 = self._get_coords(polygon[i])
                p2 = self._get_coords(polygon[(i + 1) % len(polygon)])
                dist = self._point_to_segment_distance(point, p1, p2)
                min_dist = min(min_dist, dist)

        # Distanz von Polygon-Punkten zur Fassade
        for p in polygon:
            point = self._get_coords(p)
            dist = self._point_to_segment_distance(point, facade[0], facade[1])
            min_dist = min(min_dist, dist)

        return min_dist

    def _point_to_segment_distance(
        self,
        p: Tuple[float, float],
        a: Tuple[float, float],
        b: Tuple[float, float]
    ) -> float:
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

    def _calculate_direction(
        self,
        from_e: float,
        from_n: float,
        to_e: float,
        to_n: float
    ) -> str:
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
_blocked_facades_service: Optional[BlockedFacadesService] = None


def get_blocked_facades_service() -> BlockedFacadesService:
    """Get singleton BlockedFacadesService instance."""
    global _blocked_facades_service
    if _blocked_facades_service is None:
        _blocked_facades_service = BlockedFacadesService()
    return _blocked_facades_service
