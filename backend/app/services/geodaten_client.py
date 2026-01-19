"""
Geodaten-Client - Client für Geodaten-API Aufrufe.

NEU 19.01.2026: Architektur-Trennung Geodaten ↔ Gerüstbau

Dieser Client abstrahiert den Zugriff auf Geodaten:
- Im Monolith (aktuell): Direkter Service-Aufruf (schnell)
- In Microservices (später): HTTP-Aufrufe via httpx

Verwendung in geruestbau.py:
    from app.services.geodaten_client import get_geodaten_client

    client = get_geodaten_client()
    buildings = await client.get_buildings_in_area(e=2596300, n=1199805, radius_m=100)

WICHTIG: Dieser Client ersetzt direkte DuckDB-Zugriffe in geruestbau.py!
Siehe: docs/architecture/ARCHITECTURE.md → "Architektur-Bruch: Aktueller Zustand"
"""

import os
import json
import math
import time
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional

# Konfiguration: Interner Service vs. HTTP-Client
# Wenn GEODATEN_API_URL gesetzt ist, verwende HTTP-Client
# Sonst: Direkter Service-Aufruf (schneller, für Monolith)
GEODATEN_API_URL = os.getenv("GEODATEN_API_URL")  # z.B. "http://geodaten-backend:8000"


@dataclass
class BuildingData:
    """Gebäude-Daten aus der Geodaten-API."""
    egid: str
    polygon: Optional[List[List[float]]] = None
    center_e: Optional[float] = None
    center_n: Optional[float] = None
    distance_m: float = 0.0
    traufhoehe_m: Optional[float] = None
    firsthoehe_m: Optional[float] = None
    gebaeudehoehe_m: Optional[float] = None
    walls: Optional[List[Dict]] = None
    roofs: Optional[List[Dict]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AreaResponse:
    """Response von /api/v1/building/area."""
    center: Dict[str, float]
    radius_m: float
    buildings_count: int
    buildings: List[BuildingData]
    query_time_ms: float

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result["buildings"] = [b.to_dict() if hasattr(b, 'to_dict') else b for b in self.buildings]
        return result


class GeodatenClient:
    """
    Client für Geodaten-API Aufrufe.

    Abstrahiert den Zugriff auf Gebäudedaten:
    - Monolith: Direkter DuckDB-Zugriff (schnell)
    - Microservices: HTTP-Aufrufe (flexibel)
    """

    def __init__(self, api_url: Optional[str] = None):
        """
        Args:
            api_url: URL der Geodaten-API (None = direkter Service-Aufruf)
        """
        self.api_url = api_url or GEODATEN_API_URL
        self._http_client = None

    async def _get_http_client(self):
        """Lazy-Loading des HTTP-Clients."""
        if self._http_client is None:
            import httpx
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client

    async def get_buildings_in_area(
        self,
        e: float,
        n: float,
        radius_m: float = 100,
        include_walls: bool = False,
        include_roofs: bool = False
    ) -> AreaResponse:
        """
        Alle Gebäude im Umkreis einer Koordinate.

        Args:
            e: LV95 Easting
            n: LV95 Northing
            radius_m: Suchradius in Metern
            include_walls: 3D-Wall-Daten mitliefern
            include_roofs: 3D-Roof-Daten mitliefern

        Returns:
            AreaResponse mit allen Gebäuden
        """
        if self.api_url:
            # HTTP-Aufruf (Microservices-Modus)
            return await self._http_get_buildings_in_area(
                e, n, radius_m, include_walls, include_roofs
            )
        else:
            # Direkter Service-Aufruf (Monolith-Modus)
            return await self._direct_get_buildings_in_area(
                e, n, radius_m, include_walls, include_roofs
            )

    async def _http_get_buildings_in_area(
        self,
        e: float,
        n: float,
        radius_m: float,
        include_walls: bool,
        include_roofs: bool
    ) -> AreaResponse:
        """HTTP-Aufruf an Geodaten-API."""
        client = await self._get_http_client()

        params = {
            "e": e,
            "n": n,
            "radius_m": radius_m,
            "include_walls": include_walls,
            "include_roofs": include_roofs
        }

        response = await client.get(
            f"{self.api_url}/api/v1/building/area",
            params=params
        )
        response.raise_for_status()
        data = response.json()

        buildings = [
            BuildingData(**b) for b in data.get("buildings", [])
        ]

        return AreaResponse(
            center=data["center"],
            radius_m=data["radius_m"],
            buildings_count=data["buildings_count"],
            buildings=buildings,
            query_time_ms=data["query_time_ms"]
        )

    async def _direct_get_buildings_in_area(
        self,
        e: float,
        n: float,
        radius_m: float,
        include_walls: bool,
        include_roofs: bool
    ) -> AreaResponse:
        """
        Direkter DuckDB-Zugriff (Monolith-Modus).

        Dies ist die gleiche Logik wie in main.py:/api/v1/building/area,
        aber als direkte Funktion für Performance.
        """
        from app.config import get_building_3d_connection

        start_time = time.time()

        # LV95 Koordinaten normalisieren
        if e < 2000000:
            e += 2000000
        if n < 1000000:
            n += 1000000

        conn = get_building_3d_connection(read_only=True)
        cursor = conn.cursor()

        # BBox-Query für Kandidaten
        cursor.execute("""
            SELECT egid, polygon, center_e, center_n,
                   traufhoehe_m, firsthoehe_m, gebaeudehoehe_m
            FROM buildings_3d
            WHERE center_e BETWEEN ? AND ?
              AND center_n BETWEEN ? AND ?
        """, (
            e - radius_m, e + radius_m,
            n - radius_m, n + radius_m
        ))

        rows = cursor.fetchall()

        buildings = []
        for row in rows:
            egid = str(row[0])
            center_e = row[2]
            center_n = row[3]

            # Distanz zum Abfrage-Zentrum
            dx = center_e - e
            dy = center_n - n
            distance_m = round(math.sqrt(dx*dx + dy*dy), 2)

            # Nur Gebäude innerhalb des Radius
            if distance_m > radius_m:
                continue

            # Polygon parsen
            polygon_data = row[1]
            polygon = None
            if polygon_data:
                try:
                    polygon = json.loads(polygon_data) if isinstance(polygon_data, str) else polygon_data
                except (json.JSONDecodeError, TypeError):
                    pass

            building = BuildingData(
                egid=egid,
                polygon=polygon,
                center_e=center_e,
                center_n=center_n,
                distance_m=distance_m,
                traufhoehe_m=row[4],
                firsthoehe_m=row[5],
                gebaeudehoehe_m=row[6]
            )

            buildings.append(building)

        # Optional: 3D-Layer laden
        if include_walls or include_roofs:
            egid_list = [b.egid for b in buildings]

            if include_walls and egid_list:
                # FIX 19.01.2026: Spalte heisst geometry_wkb (WKB)
                # Umbenennung coords_3d → geometry (konsistent mit DB geometry_wkb)
                cursor.execute(f"""
                    SELECT egid, z_min, z_max, geometry_wkb
                    FROM building_walls
                    WHERE egid IN ({','.join(['?' for _ in egid_list])})
                """, egid_list)

                walls_by_egid = {}
                for wall_row in cursor.fetchall():
                    wall_egid = str(wall_row[0])
                    if wall_egid not in walls_by_egid:
                        walls_by_egid[wall_egid] = []

                    # WKB zu Koordinaten konvertieren (falls vorhanden)
                    geometry = None
                    if wall_row[3]:
                        try:
                            from shapely import wkb
                            geom = wkb.loads(wall_row[3])
                            # MultiPolygon oder Polygon zu Koordinaten
                            if hasattr(geom, 'geoms'):
                                geometry = [list(g.exterior.coords) for g in geom.geoms]
                            elif hasattr(geom, 'exterior'):
                                geometry = [list(geom.exterior.coords)]
                        except Exception:
                            geometry = None

                    walls_by_egid[wall_egid].append({
                        "z_min": wall_row[1],
                        "z_max": wall_row[2],
                        "geometry": geometry
                    })

                for b in buildings:
                    b.walls = walls_by_egid.get(b.egid, [])

            if include_roofs and egid_list:
                cursor.execute(f"""
                    SELECT egid, dach_min, dach_max
                    FROM building_roofs
                    WHERE egid IN ({','.join(['?' for _ in egid_list])})
                """, egid_list)

                roofs_by_egid = {}
                for roof_row in cursor.fetchall():
                    roof_egid = str(roof_row[0])
                    if roof_egid not in roofs_by_egid:
                        roofs_by_egid[roof_egid] = []
                    roofs_by_egid[roof_egid].append({
                        "dach_min": roof_row[1],
                        "dach_max": roof_row[2]
                    })

                for b in buildings:
                    b.roofs = roofs_by_egid.get(b.egid, [])

        conn.close()

        # Nach Distanz sortieren
        buildings.sort(key=lambda x: x.distance_m)

        query_time_ms = round((time.time() - start_time) * 1000, 2)

        return AreaResponse(
            center={"e": e, "n": n},
            radius_m=radius_m,
            buildings_count=len(buildings),
            buildings=buildings,
            query_time_ms=query_time_ms
        )

    async def get_neighbors(
        self,
        egid: str,
        radius_m: float = 100,
        include_polygons: bool = True
    ) -> Dict[str, Any]:
        """
        Nachbar-Gebäude per EGID.

        Args:
            egid: EGID des Zielgebäudes (oder Multi-EGID wie "1243787+1243789")
            radius_m: Suchradius in Metern
            include_polygons: Polygone mitliefern

        Returns:
            Dict mit target, neighbors, blocked_sides
        """
        if self.api_url:
            return await self._http_get_neighbors(egid, radius_m, include_polygons)
        else:
            return await self._direct_get_neighbors(egid, radius_m, include_polygons)

    async def _http_get_neighbors(
        self,
        egid: str,
        radius_m: float,
        include_polygons: bool
    ) -> Dict[str, Any]:
        """HTTP-Aufruf an Geodaten-API."""
        client = await self._get_http_client()

        params = {
            "radius_m": radius_m,
            "include_polygons": include_polygons
        }

        response = await client.get(
            f"{self.api_url}/api/v1/building/neighbors/{egid}",
            params=params
        )
        response.raise_for_status()
        return response.json()

    async def _direct_get_neighbors(
        self,
        egid: str,
        radius_m: float,
        include_polygons: bool
    ) -> Dict[str, Any]:
        """Direkter Service-Aufruf (Monolith-Modus)."""
        from app.services.neighbors_service import get_neighbors_service

        neighbors_service = get_neighbors_service()
        result = neighbors_service.get_neighbors(
            egid=egid,
            radius_m=radius_m,
            include_polygons=include_polygons
        )

        if not result:
            return None

        # Blockierte Fassaden berechnen (< 2m Distanz)
        BLOCKING_THRESHOLD_M = 2.0
        blocked_sides = []
        for neighbor in result.neighbors:
            if neighbor.distance_m < BLOCKING_THRESHOLD_M:
                if neighbor.direction and neighbor.direction not in blocked_sides:
                    blocked_sides.append(neighbor.direction)

        response = result.to_dict()
        response["blocked_sides"] = blocked_sides

        return response

    async def close(self):
        """HTTP-Client schliessen."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None


# Singleton-Instanz
_geodaten_client: Optional[GeodatenClient] = None


def get_geodaten_client() -> GeodatenClient:
    """Get singleton GeodatenClient instance."""
    global _geodaten_client
    if _geodaten_client is None:
        _geodaten_client = GeodatenClient()
    return _geodaten_client
