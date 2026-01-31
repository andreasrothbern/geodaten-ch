"""
ProjectContextStreamService - Streaming-Service für Projekt-Kontext.

Liefert progressiv via Server-Sent Events (SSE):
1. centroid (Projekt-Mittelpunkt)
2. project_buildings (Projekt-Gebäude mit Polygonen)
3. blocked_facades (blockierte Fassaden pro Gebäude)
4. neighbors (in Schichten: 20m, 50m, 100m)
5. complete (Abschluss-Signal)

WICHTIG: Siehe docs/architecture/STREAMING_ARCHITECTURE.md für Details.
"""

import json
import time
from dataclasses import dataclass, asdict
from typing import AsyncGenerator, List, Dict, Any, Optional, Tuple, Set
import logging

from app.config import NEIGHBOR_SEARCH_RADIUS_M
from .blocked_facades_service import get_blocked_facades_service, BlockedFacadesResult
from .neighbors_service import get_neighbors_service, NeighborBuilding
from .building_3d_service import get_building_3d_service

logger = logging.getLogger(__name__)


@dataclass
class SSEEvent:
    """Ein Server-Sent Event."""
    event: str
    data: Dict[str, Any]

    def to_sse(self) -> str:
        """Formatiert als SSE-String."""
        return f"event: {self.event}\ndata: {json.dumps(self.data)}\n\n"


@dataclass
class CentroidData:
    """Daten für centroid-Event."""
    center_e: float
    center_n: float
    project_egids: List[str]


@dataclass
class ProjectBuildingData:
    """Daten für ein Projekt-Gebäude."""
    egid: str
    polygon: Optional[List[List[float]]]
    center_e: Optional[float]
    center_n: Optional[float]
    traufhoehe_m: Optional[float]
    firsthoehe_m: Optional[float]
    gebaeudehoehe_m: Optional[float]


class ProjectContextStreamService:
    """
    Streaming-Service für Projekt-Kontext.

    Berechnet und streamt:
    - Projekt-Mittelpunkt (Centroid aller Projekt-Gebäude)
    - Projekt-Gebäude mit Polygonen
    - Blockierte Fassaden (nur durch EXTERNE Gebäude)
    - Nachbarn in mehreren Radien
    """

    # Radien für Nachbar-Suche (progressiv)
    NEIGHBOR_RADII = [20, 50, 100]

    def __init__(self):
        self._blocked_facades_service = None
        self._neighbors_service = None
        self._building_3d_service = None

    def _get_blocked_facades_service(self):
        if self._blocked_facades_service is None:
            self._blocked_facades_service = get_blocked_facades_service()
        return self._blocked_facades_service

    def _get_neighbors_service(self):
        if self._neighbors_service is None:
            self._neighbors_service = get_neighbors_service()
        return self._neighbors_service

    def _get_building_3d_service(self):
        if self._building_3d_service is None:
            self._building_3d_service = get_building_3d_service()
        return self._building_3d_service

    async def stream_context(
        self,
        project_egids: List[str],
        max_radius_m: float = NEIGHBOR_SEARCH_RADIUS_M,
        include_blocked_facades: bool = True,
        include_neighbors: bool = True
    ) -> AsyncGenerator[SSEEvent, None]:
        """
        Generator für SSE Events.

        Args:
            project_egids: Liste aller EGIDs im Projekt
            max_radius_m: Maximaler Radius für Nachbar-Suche
            include_blocked_facades: Blockierte Fassaden berechnen
            include_neighbors: Nachbarn laden

        Yields:
            SSEEvent Objekte in der Reihenfolge:
            1. centroid
            2. project_buildings
            3. blocked_facades (optional)
            4. neighbors (mehrere, optional)
            5. complete oder error
        """
        start_time = time.time()
        project_egids_set = set(str(e) for e in project_egids)

        # DEBUG 10.01.2026 21:05 - Welche EGIDs sind im Projekt?
        print(f"[SSE] stream_context called with project_egids: {project_egids}")
        print(f"[SSE] project_egids_set (exclude for blocked_facades): {project_egids_set}")

        try:
            # ===============================
            # 1. Projekt-Gebäude laden
            # ===============================
            buildings_data = []
            for egid in project_egids:
                building = self._load_building(str(egid))
                if building:
                    buildings_data.append(building)

            if not buildings_data:
                yield SSEEvent(
                    event="error",
                    data={
                        "code": "NO_BUILDINGS_FOUND",
                        "message": f"Keine Gebäude gefunden für EGIDs: {project_egids}"
                    }
                )
                return

            # ===============================
            # 2. Centroid berechnen
            # ===============================
            center_e, center_n = self.calculate_centroid(buildings_data)

            yield SSEEvent(
                event="centroid",
                data={
                    "center_e": round(center_e, 2),
                    "center_n": round(center_n, 2),
                    "project_egids": list(project_egids_set),
                    "building_count": len(buildings_data)
                }
            )

            # ===============================
            # 3. Projekt-Gebäude senden
            # ===============================
            buildings_response = []
            for b in buildings_data:
                buildings_response.append({
                    "egid": b["egid"],
                    "polygon": b.get("polygon"),
                    "center_e": b.get("center_e"),
                    "center_n": b.get("center_n"),
                    "traufhoehe_m": b.get("traufhoehe_m"),
                    "firsthoehe_m": b.get("firsthoehe_m"),
                    "gebaeudehoehe_m": b.get("gebaeudehoehe_m")
                })

            yield SSEEvent(
                event="project_buildings",
                data={"buildings": buildings_response}
            )

            # ===============================
            # 4. Blockierte Fassaden berechnen
            # ===============================
            if include_blocked_facades:
                blocked_facades_service = self._get_blocked_facades_service()
                print(f"[SSE] Calling calculate_for_project with egids: {list(project_egids_set)}")
                blocked_results = blocked_facades_service.calculate_for_project(
                    project_egids=list(project_egids_set),
                    threshold_m=2.0  # Standard-Schwellenwert
                )
                print(f"[SSE] blocked_results: {list(blocked_results.keys())} - blocked: {[(k, v.blocked_indices) for k,v in blocked_results.items()]}")

                # Formatieren für Frontend
                # NEU 22.01.2026: blocked_segments für partielle Blockierung
                blocked_data = {}
                for egid, result in blocked_results.items():
                    blocked_data[egid] = {
                        "blocked_indices": result.blocked_indices,
                        "total_facades": result.total_facades,
                        "free_facades": result.free_facades,
                        "blockers": [
                            {
                                "facade_index": bf.facade_index,
                                "egid": bf.blockers[0].egid if bf.blockers else None,
                                "distance_m": bf.min_distance_m,
                                "direction": bf.blockers[0].direction if bf.blockers else None,
                                # NEU 22.01.2026: Partielle Blockierung
                                "fully_blocked": bf.fully_blocked,
                                "blocked_segments": [
                                    {
                                        "start_ratio": seg.start_ratio,
                                        "end_ratio": seg.end_ratio,
                                        "blocker_egid": seg.blocker_egid,
                                        "min_distance_m": seg.min_distance_m,
                                        "length_ratio": seg.length_ratio
                                    }
                                    for seg in bf.blocked_segments
                                ]
                            }
                            for bf in result.blocked_facades
                        ]
                    }

                yield SSEEvent(
                    event="blocked_facades",
                    data=blocked_data
                )

                # ===============================
                # 4b. Blocking Neighbors senden (NEU 25.01.2026)
                # ===============================
                # Sammle alle Nachbarn die Fassaden blockieren (Polygon-zu-Polygon < 2m)
                # Diese haben bereits korrekte Polygon-Distanzen aus _find_neighbors()
                blocking_neighbors_set = set()
                for egid, result in blocked_results.items():
                    for bf in result.blocked_facades:
                        for blocker in bf.blockers:
                            blocking_neighbors_set.add(blocker.egid)

                if blocking_neighbors_set:
                    # Lade die Polygon-Daten für die blockierenden Nachbarn
                    blocking_neighbors_data = []
                    for blocker_egid in blocking_neighbors_set:
                        blocker_building = self._load_building(str(blocker_egid))
                        if blocker_building and blocker_building.get('polygon'):
                            # Berechne Distanz zum Projekt-Centroid (für Sortierung)
                            b_center_e = blocker_building.get('center_e', 0)
                            b_center_n = blocker_building.get('center_n', 0)
                            dx = b_center_e - center_e
                            dy = b_center_n - center_n
                            center_dist = round((dx*dx + dy*dy)**0.5, 2)

                            blocking_neighbors_data.append({
                                "egid": blocker_building['egid'],
                                "polygon": blocker_building['polygon'],
                                "center_e": b_center_e,
                                "center_n": b_center_n,
                                "distance_m": center_dist,  # Center distance for sorting
                                "traufhoehe_m": blocker_building.get('traufhoehe_m'),
                                "firsthoehe_m": blocker_building.get('firsthoehe_m'),
                                "gebaeudehoehe_m": blocker_building.get('gebaeudehoehe_m'),
                            })

                    # Sortieren nach Distanz
                    blocking_neighbors_data.sort(key=lambda x: x['distance_m'])

                    yield SSEEvent(
                        event="blocking_neighbors",
                        data={
                            "count": len(blocking_neighbors_data),
                            "buildings": blocking_neighbors_data
                        }
                    )
                    print(f"[SSE] blocking_neighbors: {len(blocking_neighbors_data)} buildings")

            # ===============================
            # 5. Nachbarn in Schichten laden
            # ===============================
            if include_neighbors:
                neighbors_service = self._get_neighbors_service()
                seen_egids = project_egids_set.copy()

                # Progressive Radien bis max_radius_m
                radii_to_use = [r for r in self.NEIGHBOR_RADII if r <= max_radius_m]
                if max_radius_m not in radii_to_use:
                    radii_to_use.append(max_radius_m)

                for radius in radii_to_use:
                    # Nachbarn für Projekt-Centroid suchen
                    # Wir nutzen ein beliebiges Projekt-Gebäude als Basis
                    # und filtern nach Distanz zum Centroid
                    all_neighbors = []

                    # Für jedes Projekt-Gebäude Nachbarn suchen
                    for egid in project_egids_set:
                        result = neighbors_service.get_neighbors(
                            egid=egid,
                            radius_m=radius,
                            include_polygons=True
                        )
                        if result and result.neighbors:
                            for n in result.neighbors:
                                if n.egid not in seen_egids:
                                    all_neighbors.append(n)
                                    seen_egids.add(n.egid)

                    if all_neighbors:
                        # Nach Distanz zum Centroid sortieren
                        for n in all_neighbors:
                            if n.center_e and n.center_n:
                                dx = n.center_e - center_e
                                dy = n.center_n - center_n
                                n.distance_m = round((dx*dx + dy*dy)**0.5, 2)

                        all_neighbors.sort(key=lambda x: x.distance_m)

                        yield SSEEvent(
                            event="neighbors",
                            data={
                                "radius_m": radius,
                                "count": len(all_neighbors),
                                "buildings": [
                                    {
                                        "egid": n.egid,
                                        "polygon": n.polygon,
                                        "distance_m": n.distance_m,
                                        "direction": n.direction,
                                        "center_e": n.center_e,
                                        "center_n": n.center_n,
                                        "traufhoehe_m": n.traufhoehe_m,
                                        "firsthoehe_m": n.firsthoehe_m,
                                        # FIX 21.01.2026: Höhendaten für heuristisches Dach im 3D-Viewer
                                        "gebaeudehoehe_m": n.gebaeudehoehe_m,
                                    }
                                    for n in all_neighbors
                                ]
                            }
                        )

            # ===============================
            # 6. Abschluss
            # ===============================
            duration_ms = round((time.time() - start_time) * 1000, 2)

            yield SSEEvent(
                event="complete",
                data={
                    "status": "ok",
                    "duration_ms": duration_ms,
                    "project_buildings": len(buildings_data),
                    "total_neighbors": len(seen_egids) - len(project_egids_set) if include_neighbors else 0
                }
            )

        except Exception as e:
            logger.exception(f"Error in stream_context: {e}")
            yield SSEEvent(
                event="error",
                data={
                    "code": "STREAM_ERROR",
                    "message": str(e)
                }
            )

    def calculate_centroid(
        self,
        buildings: List[Dict[str, Any]]
    ) -> Tuple[float, float]:
        """
        Berechnet geometrischen Mittelpunkt aller Projekt-Gebäude.

        FIX 30.01.2026: Delegiert an zentralisierte Funktion in object_geometry.py

        Args:
            buildings: Liste von Building-Dicts mit center_e, center_n

        Returns:
            (center_e, center_n) Tuple
        """
        from .object_geometry import calculate_centroid_from_buildings
        return calculate_centroid_from_buildings(buildings)

    def _load_building(self, egid: str) -> Optional[Dict[str, Any]]:
        """Lädt Gebäude aus building_3d.db."""
        try:
            building_3d_service = self._get_building_3d_service()
            building = building_3d_service.get_by_egid(int(egid))

            if not building:
                return None

            # Polygon aus JSON parsen falls String
            polygon = building.get('polygon')
            if isinstance(polygon, str):
                import json
                polygon = json.loads(polygon)

            return {
                'egid': str(building.get('egid')),
                'polygon': polygon,
                'center_e': building.get('center_e'),
                'center_n': building.get('center_n'),
                'traufhoehe_m': building.get('traufhoehe_m'),
                'firsthoehe_m': building.get('firsthoehe_m'),
                'gebaeudehoehe_m': building.get('gebaeudehoehe_m')
            }
        except Exception as e:
            logger.warning(f"Could not load building {egid}: {e}")
            return None


# Singleton
_project_context_stream_service: Optional[ProjectContextStreamService] = None


def get_project_context_stream_service() -> ProjectContextStreamService:
    """Get singleton ProjectContextStreamService instance."""
    global _project_context_stream_service
    if _project_context_stream_service is None:
        _project_context_stream_service = ProjectContextStreamService()
    return _project_context_stream_service
