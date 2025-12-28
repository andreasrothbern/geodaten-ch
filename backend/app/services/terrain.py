"""
Terrain Service - swissALTI3D Integration
==========================================

Holt Terrain-Höhendaten von der swisstopo API (swissALTI3D).

Endpunkte:
- Height API: Punkthöhe an Koordinate
- Profile API: Höhenprofil entlang einer Linie

Höhenmodelle:
- COMB: Kombiniert (beste verfügbare Auflösung)
- DTM2: swissALTI3D 2m (LiDAR, hochpräzise)
- DTM25: DHM25 25m (älteres Modell)
"""

import httpx
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from pydantic import BaseModel
import json
import urllib.parse


class TerrainPoint(BaseModel):
    """Einzelner Punkt mit Terrain-Höhe"""
    easting: float
    northing: float
    height_m: float
    distance_m: Optional[float] = None
    elevation_model: str = "COMB"


class TerrainProfile(BaseModel):
    """Terrain-Profil entlang einer Linie"""
    points: List[TerrainPoint]
    min_height_m: float
    max_height_m: float
    height_diff_m: float
    total_distance_m: float


class TerrainInfo(BaseModel):
    """Terrain-Informationen für ein Gebäude"""
    terrain_height_m: float  # Höhe am Referenzpunkt (m ü.M.)
    min_terrain_m: Optional[float] = None  # Min. Höhe am Gebäude
    max_terrain_m: Optional[float] = None  # Max. Höhe am Gebäude
    terrain_slope_m: Optional[float] = None  # Gefälle (max - min)
    elevation_model: str = "COMB"


class TerrainService:
    """Service für swissALTI3D Terrain-Daten"""

    BASE_URL = "https://api3.geo.admin.ch"
    DEFAULT_MODEL = "COMB"  # Beste verfügbare Auflösung

    def __init__(self):
        self.timeout = httpx.Timeout(10.0, connect=5.0)

    async def get_height(
        self,
        easting: float,
        northing: float,
        elevation_model: str = None
    ) -> Optional[float]:
        """
        Holt Terrain-Höhe an einem Punkt.

        Args:
            easting: LV95 E-Koordinate
            northing: LV95 N-Koordinate
            elevation_model: COMB, DTM2, oder DTM25

        Returns:
            Höhe in Metern über Meer (m ü.M.) oder None bei Fehler
        """
        params = {
            "easting": easting,
            "northing": northing,
        }
        if elevation_model:
            params["elevation_model"] = elevation_model

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                url = f"{self.BASE_URL}/rest/services/height"
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                height_str = data.get("height")
                if height_str:
                    return float(height_str)
                return None

        except Exception as e:
            print(f"[TerrainService] Fehler bei get_height: {e}")
            return None

    async def get_terrain_info(
        self,
        easting: float,
        northing: float,
        polygon: List[Tuple[float, float]] = None
    ) -> Optional[TerrainInfo]:
        """
        Holt Terrain-Informationen für einen Punkt oder ein Polygon.

        Args:
            easting: LV95 E-Koordinate (Referenzpunkt)
            northing: LV95 N-Koordinate (Referenzpunkt)
            polygon: Optional - Liste von (E, N) Koordinaten für Gebäudeumriss

        Returns:
            TerrainInfo mit Höhe und optional Gefälle
        """
        # Hauptpunkt-Höhe
        main_height = await self.get_height(easting, northing)
        if main_height is None:
            return None

        info = TerrainInfo(
            terrain_height_m=main_height,
            elevation_model=self.DEFAULT_MODEL
        )

        # Falls Polygon vorhanden: Min/Max Höhe an Ecken berechnen
        if polygon and len(polygon) >= 3:
            heights = []
            for e, n in polygon:
                h = await self.get_height(e, n)
                if h is not None:
                    heights.append(h)

            if heights:
                info.min_terrain_m = min(heights)
                info.max_terrain_m = max(heights)
                info.terrain_slope_m = info.max_terrain_m - info.min_terrain_m

        return info

    async def get_profile(
        self,
        coordinates: List[Tuple[float, float]],
        nb_points: int = 10
    ) -> Optional[TerrainProfile]:
        """
        Holt Terrain-Profil entlang einer Linie.

        Args:
            coordinates: Liste von (E, N) Koordinaten
            nb_points: Anzahl Punkte für das Profil

        Returns:
            TerrainProfile mit allen Punkten und Statistiken
        """
        if len(coordinates) < 2:
            return None

        # GeoJSON LineString erstellen
        geom = {
            "type": "LineString",
            "coordinates": [[e, n] for e, n in coordinates]
        }
        geom_json = json.dumps(geom)

        params = {
            "geom": geom_json,
            "nb_points": nb_points
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                url = f"{self.BASE_URL}/rest/services/profile.json"
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                if not data:
                    return None

                points = []
                for item in data:
                    # Profile API gibt mehrere Höhenmodelle zurück
                    alts = item.get("alts", {})
                    height = alts.get("COMB") or alts.get("DTM2") or alts.get("DTM25")

                    if height is not None:
                        points.append(TerrainPoint(
                            easting=item.get("easting"),
                            northing=item.get("northing"),
                            height_m=height,
                            distance_m=item.get("dist"),
                            elevation_model="COMB"
                        ))

                if not points:
                    return None

                heights = [p.height_m for p in points]
                return TerrainProfile(
                    points=points,
                    min_height_m=min(heights),
                    max_height_m=max(heights),
                    height_diff_m=max(heights) - min(heights),
                    total_distance_m=points[-1].distance_m or 0
                )

        except Exception as e:
            print(f"[TerrainService] Fehler bei get_profile: {e}")
            return None

    async def get_facade_profile(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
        nb_points: int = 5
    ) -> Optional[TerrainProfile]:
        """
        Holt Terrain-Profil entlang einer Fassade.

        Args:
            start: Start-Koordinate (E, N)
            end: End-Koordinate (E, N)
            nb_points: Anzahl Punkte

        Returns:
            TerrainProfile entlang der Fassade
        """
        return await self.get_profile([start, end], nb_points)

    async def get_building_terrain(
        self,
        polygon: List[Tuple[float, float]],
        sample_interval_m: float = 5.0
    ) -> Dict[str, Any]:
        """
        Holt Terrain-Daten für ein komplettes Gebäude.

        Args:
            polygon: Gebäude-Polygon als Liste von (E, N) Koordinaten
            sample_interval_m: Abstand zwischen Messpunkten in Metern

        Returns:
            Dict mit terrain_heights, min, max, slope, profiles
        """
        if len(polygon) < 3:
            return {}

        # Eckhöhen
        corner_heights = []
        for e, n in polygon:
            h = await self.get_height(e, n)
            if h is not None:
                corner_heights.append({
                    "easting": e,
                    "northing": n,
                    "height_m": h
                })

        if not corner_heights:
            return {}

        heights = [c["height_m"] for c in corner_heights]

        # Zentroid berechnen
        center_e = sum(p[0] for p in polygon) / len(polygon)
        center_n = sum(p[1] for p in polygon) / len(polygon)
        center_height = await self.get_height(center_e, center_n)

        return {
            "corners": corner_heights,
            "center": {
                "easting": center_e,
                "northing": center_n,
                "height_m": center_height
            },
            "min_height_m": min(heights),
            "max_height_m": max(heights),
            "slope_m": max(heights) - min(heights),
            "reference_height_m": center_height or min(heights)
        }


# Singleton-Instanz
_terrain_service: Optional[TerrainService] = None


def get_terrain_service() -> TerrainService:
    """Gibt die TerrainService-Instanz zurück."""
    global _terrain_service
    if _terrain_service is None:
        _terrain_service = TerrainService()
    return _terrain_service
