"""
swissBUILDINGS3D Service
========================

Service für 3D-Gebäudedaten aus swissBUILDINGS3D.

Datenquellen:
- swissBUILDINGS3D 3.0 via STAC API: Polygon + Höhen (on-demand)
- sonnendach.ch API: Dachflächen mit Neigung/Ausrichtung
- Lokale SQLite DB: Cache für bereits abgerufene Daten

Änderungshistorie:
- 01.01.2026: geodienste.ch WFS deaktiviert, alles via swissBUILDINGS3D STAC API
- Der swissbuildings3d_fetcher.py ist der Low-Level STAC Client
"""

import logging
from typing import Optional, List, Tuple
from dataclasses import dataclass, field

from .swissbuildings3d_fetcher import (
    fetch_building_polygon_for_coordinates,
    fetch_height_for_coordinates,
)
from .building_3d_service import get_building_3d_service
from .sonnendach_service import get_sonnendach_service, RoofAnalysis

logger = logging.getLogger(__name__)


@dataclass
class Building3D:
    """3D-Gebäudedaten aus swissBUILDINGS3D."""

    # Identifikation
    egid: Optional[str] = None
    uuid: Optional[str] = None
    objektart: Optional[str] = None

    # Polygon (LV95 Koordinaten) - ALWAYS the original from swissBUILDINGS3D
    polygon: List[Tuple[float, float]] = field(default_factory=list)
    polygon_point_count: Optional[int] = None
    # Sides are calculated from on-the-fly simplified polygon
    sides_from_simplified: bool = True

    # Höhen (m über Terrain)
    trauf_height_m: Optional[float] = None
    first_height_m: Optional[float] = None
    building_height_m: Optional[float] = None

    # Absolute Höhen (m.ü.M.)
    z_min: Optional[float] = None  # Terrain-Höhe
    z_max: Optional[float] = None  # Firsthöhe absolut
    z_trauf: Optional[float] = None  # Traufhöhe absolut

    # Dachform
    roof_type: Optional[str] = None  # 'flat', 'gabled', 'hipped', 'complex'
    roof_surfaces: List[dict] = field(default_factory=list)

    # Fassadendaten (für ScaffoldConfigurator)
    sides: List[dict] = field(default_factory=list)
    perimeter_m: Optional[float] = None
    area_m2: Optional[float] = None

    # Qualitätsinformationen
    lod: str = "LOD2"
    source: str = "swissBUILDINGS3D"
    confidence: float = 1.0
    height_source: str = "unknown"

    # Koordinaten (Zentroid)
    center_e: Optional[float] = None  # LV95 E
    center_n: Optional[float] = None  # LV95 N

    def has_valid_heights(self) -> bool:
        """Prüft ob valide Höhendaten vorhanden sind."""
        return self.trauf_height_m is not None and self.trauf_height_m > 0


class SwissBuildings3DService:
    """
    Service für 3D-Gebäudedaten.

    Nutzt den swissbuildings3d_fetcher für STAC API Zugriff und
    ergänzt mit sonnendach.ch für Dachanalyse.
    """

    def __init__(self):
        self._sonnendach = get_sonnendach_service()

    async def get_building_by_coordinates(
        self,
        e: float,
        n: float,
        tolerance: float = 50.0,
        include_roof_analysis: bool = True,
        simplify_epsilon: Optional[float] = None
    ) -> Optional[Building3D]:
        """
        Holt 3D-Gebäudedaten für LV95-Koordinaten.

        Kombiniert:
        1. Polygon + Höhen von swissBUILDINGS3D STAC API
        2. Dachflächen von sonnendach.ch (optional)

        Args:
            e: LV95 Ost-Koordinate
            n: LV95 Nord-Koordinate
            tolerance: Suchradius in Metern
            include_roof_analysis: Dachflächen einbeziehen (sonnendach.ch)

        Returns:
            Building3D oder None wenn nicht gefunden
        """
        building = Building3D(center_e=e, center_n=n)

        # 1. Polygon + Höhen von swissBUILDINGS3D STAC API (EIN Aufruf!)
        try:
            result = await fetch_building_polygon_for_coordinates(
                e, n, tolerance, simplify_epsilon=simplify_epsilon
            )
            if result:
                # Polygon (ALWAYS original from swissBUILDINGS3D)
                polygon_raw = result.get("polygon", [])
                building.polygon = [(p[0], p[1]) for p in polygon_raw]
                building.polygon_point_count = result.get("polygon_point_count")
                building.sides_from_simplified = result.get("sides_from_simplified", True)

                # Fassaden/Seiten
                building.sides = result.get("sides", [])
                building.perimeter_m = result.get("perimeter_m")
                building.area_m2 = result.get("area_m2")

                # EGID
                if result.get("egid"):
                    building.egid = str(result.get("egid"))

                # Höhen direkt aus swissBUILDINGS3D
                building.trauf_height_m = result.get("traufhoehe_m")
                building.first_height_m = result.get("firsthoehe_m")
                building.building_height_m = result.get("gebaeudehoehe_m")
                building.z_min = result.get("terrain_m")
                building.z_max = result.get("dach_max_m")
                building.z_trauf = result.get("dach_min_m")
                building.height_source = "swissBUILDINGS3D_STAC"
                building.confidence = 0.95

                # FIX 02.02.2026: roof_form aus 3D-Daten übernehmen (hat Priorität!)
                if result.get("roof_form"):
                    building.roof_type = result.get("roof_form")
                    logger.info(f"Roof type from 3D data: {building.roof_type}")

                logger.info(
                    f"Building found at E={e}, N={n}: "
                    f"{len(building.polygon)} points, "
                    f"trauf={building.trauf_height_m}m"
                )
            else:
                logger.debug(f"No building found at E={e}, N={n}")
        except Exception as err:
            logger.error(f"Error fetching from swissBUILDINGS3D: {err}")

        # 2. Fallback: Höhen aus lokaler DB (falls STAC keine Höhen liefert)
        if not building.has_valid_heights():
            height_data = None
            height_source = "none"

            # Per EGID
            b3d_service = get_building_3d_service()
            if building.egid:
                try:
                    egid_int = int(building.egid)
                    height_data = b3d_service.get_by_egid(egid_int)
                    if height_data:
                        height_source = "database_egid"
                except (ValueError, TypeError):
                    pass

            # Per Koordinaten
            if not height_data:
                height_data = b3d_service.get_by_coordinates(e, n, tolerance)
                if height_data:
                    height_source = "database_coord"

            if height_data:
                building.trauf_height_m = height_data.get("traufhoehe_m")
                building.first_height_m = height_data.get("firsthoehe_m")
                building.building_height_m = height_data.get("gebaeudehoehe_m")
                building.z_min = height_data.get("terrain_m")
                building.z_max = height_data.get("dach_max_m")
                building.z_trauf = height_data.get("dach_min_m")
                building.height_source = height_source
                building.confidence = 0.9 if height_source == "database_egid" else 0.7
                logger.info(f"Heights from DB via {height_source}: trauf={building.trauf_height_m}m")

        # 3. Dachanalyse von sonnendach.ch (optional)
        # FIX 02.02.2026: Nur verwenden wenn keine 3D-basierte roof_form vorhanden
        if include_roof_analysis:
            try:
                roof_analysis = await self._sonnendach.analyze_roof(e, n, tolerance)
                if roof_analysis.has_data:
                    # Sonnendach nur als Fallback wenn keine 3D-Daten
                    if not building.roof_type:
                        building.roof_type = roof_analysis.roof_type
                    building.roof_surfaces = [
                        {
                            "area_m2": s.area_m2,
                            "tilt_degrees": s.tilt_degrees,
                            "azimuth_degrees": s.azimuth_degrees,
                            "eignung": s.eignung
                        }
                        for s in roof_analysis.surfaces
                    ]
                    logger.info(
                        f"Roof analysis: {roof_analysis.surfaces_count} surfaces, "
                        f"type={roof_analysis.roof_type}"
                    )
            except Exception as err:
                logger.error(f"Error in roof analysis: {err}")

        # 4. Dachtyp aus Höhendifferenz schätzen (falls nicht von sonnendach)
        if not building.roof_type and building.trauf_height_m and building.first_height_m:
            diff = building.first_height_m - building.trauf_height_m
            if diff < 0.5:
                building.roof_type = "flat"
            elif diff < 3:
                building.roof_type = "gabled"
            else:
                building.roof_type = "complex"

        # Prüfen ob wir genug Daten haben
        if not building.polygon and not building.has_valid_heights():
            logger.debug(f"Insufficient data at E={e}, N={n}")
            return None

        building.source = "swissBUILDINGS3D"
        return building

    async def get_building_by_egid(self, egid: str) -> Optional[Building3D]:
        """
        Holt 3D-Gebäudedaten für EGID.

        Args:
            egid: Eidg. Gebäudeidentifikator

        Returns:
            Building3D oder None wenn nicht gefunden
        """
        # Erst Höhendaten aus lokaler DB prüfen
        try:
            egid_int = int(egid)
            b3d_service = get_building_3d_service()
            height_data = b3d_service.get_by_egid(egid_int)

            if height_data:
                building = Building3D(egid=egid)
                building.trauf_height_m = height_data.get("traufhoehe_m")
                building.first_height_m = height_data.get("firsthoehe_m")
                building.building_height_m = height_data.get("gebaeudehoehe_m")
                building.height_source = "database_egid"
                building.confidence = 0.9
                return building
        except (ValueError, TypeError) as err:
            logger.error(f"Invalid EGID {egid}: {err}")

        return None

    async def close(self):
        """Schliesst alle HTTP Clients."""
        if self._sonnendach:
            await self._sonnendach.close()


# Singleton-Instanz
_service_instance: Optional[SwissBuildings3DService] = None


def get_swissbuildings3d_service() -> SwissBuildings3DService:
    """Gibt die Singleton-Instanz zurück."""
    global _service_instance
    if _service_instance is None:
        _service_instance = SwissBuildings3DService()
    return _service_instance


# Convenience Functions
async def get_building_3d(e: float, n: float) -> Optional[Building3D]:
    """Shortcut für Koordinaten-Lookup."""
    service = get_swissbuildings3d_service()
    return await service.get_building_by_coordinates(e, n)


async def get_building_3d_by_egid(egid: str) -> Optional[Building3D]:
    """Shortcut für EGID-Lookup."""
    service = get_swissbuildings3d_service()
    return await service.get_building_by_egid(egid)
