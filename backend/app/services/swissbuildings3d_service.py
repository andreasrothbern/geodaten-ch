"""
swissBUILDINGS3D Composite Service
==================================

Kombinierter Service für 3D-Gebäudedaten:
- Polygon: geodienste.ch WFS (amtliche Vermessung)
- Höhen: Lokale SQLite DB (aus swissBUILDINGS3D Import)
- Dachflächen: sonnendach.ch API

HINWEIS: Die swissBUILDINGS3D-Daten sind NICHT per API verfügbar.
Sie müssen als GML/GeoPackage heruntergeladen und importiert werden.
Siehe: scripts/import_building_heights.py

Datenquellen:
- swissBUILDINGS3D 3.0 Beta (vorher importiert): Höhen
- geodienste.ch WFS: Gebäudepolygone
- sonnendach.ch API: Dachflächen mit Neigung/Ausrichtung
"""

import logging
from typing import Optional, List, Tuple
from dataclasses import dataclass, field

from .height_db import (
    get_building_height,
    get_building_heights_detailed,
    get_building_height_by_coordinates,
)
from .geodienste import GeodiensteService, BuildingGeometry
from .sonnendach_service import get_sonnendach_service, RoofAnalysis

logger = logging.getLogger(__name__)


@dataclass
class Building3D:
    """3D-Gebäudedaten aus kombinierten Quellen."""

    # Identifikation
    egid: Optional[str] = None
    uuid: Optional[str] = None
    objektart: Optional[str] = None

    # Polygon (LV95 Koordinaten)
    polygon: List[Tuple[float, float]] = field(default_factory=list)

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
    Kombinierter Service für 3D-Gebäudedaten.

    Aggregiert Daten aus:
    - Lokaler SQLite DB (Höhen aus swissBUILDINGS3D Import)
    - geodienste.ch WFS (Polygon)
    - sonnendach.ch API (Dachflächen)
    """

    def __init__(self):
        self._geodienste = GeodiensteService()
        self._sonnendach = get_sonnendach_service()

    async def get_building_by_coordinates(
        self,
        e: float,
        n: float,
        tolerance: float = 50.0,
        include_roof_analysis: bool = True
    ) -> Optional[Building3D]:
        """
        Holt 3D-Gebäudedaten für LV95-Koordinaten.

        Kombiniert:
        1. Polygon von geodienste.ch WFS
        2. Höhen aus lokaler DB (falls vorhanden)
        3. Dachflächen von sonnendach.ch (optional)

        Args:
            e: LV95 Ost-Koordinate
            n: LV95 Nord-Koordinate
            tolerance: Suchradius in Metern
            include_roof_analysis: Dachflächen einbeziehen (sonnendach.ch)

        Returns:
            Building3D oder None wenn nicht gefunden
        """
        building = Building3D(center_e=e, center_n=n)

        # 1. Polygon von geodienste.ch holen
        try:
            geometry = await self._geodienste.get_building_geometry(e, n)
            if geometry:
                building.polygon = geometry.polygon
                building.sides = geometry.sides
                building.perimeter_m = geometry.perimeter_m
                building.area_m2 = geometry.area_m2
                if geometry.egid:
                    building.egid = str(geometry.egid)
                logger.info(f"Polygon found at E={e}, N={n}: {len(building.polygon)} points")
            else:
                logger.debug(f"No polygon found at E={e}, N={n}")
        except Exception as err:
            logger.error(f"Error fetching polygon: {err}")

        # 2. Höhen aus lokaler DB (versuche mehrere Methoden)
        height_data = None
        height_source = "none"

        # Zuerst per EGID (falls vorhanden)
        if building.egid:
            try:
                egid_int = int(building.egid)
                height_data = get_building_heights_detailed(egid_int)
                if height_data:
                    height_source = "database_egid"
            except (ValueError, TypeError):
                pass

        # Fallback: Koordinaten-basierte Suche
        if not height_data:
            height_data = get_building_height_by_coordinates(e, n, tolerance)
            if height_data:
                height_source = "database_coord"

        # Höhendaten übernehmen
        if height_data:
            building.trauf_height_m = height_data.get("traufhoehe_m")
            building.first_height_m = height_data.get("firsthoehe_m")
            building.building_height_m = height_data.get("gebaeudehoehe_m")
            building.z_min = height_data.get("terrain_m")
            building.z_max = height_data.get("dach_max_m")
            building.z_trauf = height_data.get("dach_min_m")
            building.height_source = height_source
            building.confidence = 0.9 if height_source == "database_egid" else 0.7
            logger.info(f"Heights found via {height_source}: trauf={building.trauf_height_m}m")

        # 3. Dachanalyse von sonnendach.ch (optional)
        if include_roof_analysis:
            try:
                roof_analysis = await self._sonnendach.analyze_roof(e, n, tolerance)
                if roof_analysis.has_data:
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
                    logger.info(f"Roof analysis: {roof_analysis.surfaces_count} surfaces, type={roof_analysis.roof_type}")
            except Exception as err:
                logger.error(f"Error in roof analysis: {err}")

        # Dachtyp aus Höhendifferenz schätzen (falls nicht von sonnendach)
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

        building.source = "composite"
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
            height_data = get_building_heights_detailed(egid_int)

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
