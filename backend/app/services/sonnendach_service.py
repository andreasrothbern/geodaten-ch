"""
Sonnendach.ch Service
=====================

Lädt detaillierte Dachgeometrien von sonnendach.ch (BFE).

Features:
- Exakte Dachflächen-Polygone
- Neigung pro Dachfläche
- Ausrichtung (Azimut)
- Solar-Eignung als Qualitätsindikator

Layer: ch.bfe.solarenergie-eignung-daecher
Quelle: https://www.uvek-gis.admin.ch/BFE/sonnendach/
"""

import httpx
import logging
from typing import Optional, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# API Configuration
IDENTIFY_URL = "https://api3.geo.admin.ch/rest/services/api/MapServer/identify"
LAYER_ID = "ch.bfe.solarenergie-eignung-daecher"

# HTTP Client Configuration
TIMEOUT_SECONDS = 30
USER_AGENT = "geodaten-ch/2.0 (sonnendach)"


@dataclass
class RoofSurface:
    """Eine Dachfläche aus Sonnendach.ch."""

    # Identifikation
    id: Optional[str] = None

    # Polygon (LV95 Koordinaten)
    polygon: List[tuple] = field(default_factory=list)

    # Geometrie
    area_m2: Optional[float] = None
    tilt_degrees: Optional[float] = None  # Neigung
    azimuth_degrees: Optional[float] = None  # Ausrichtung (0=N, 90=O, 180=S, 270=W)

    # Solar-Eignung
    eignung: Optional[str] = None  # 'hoch', 'mittel', 'gering'
    eignung_code: Optional[int] = None
    strahlung_kwh: Optional[float] = None  # kWh/m²/Jahr

    # Metadaten
    source: str = "sonnendach.ch"


@dataclass
class RoofAnalysis:
    """Zusammenfassung aller Dachflächen eines Gebäudes."""

    # Dachflächen
    surfaces: List[RoofSurface] = field(default_factory=list)

    # Aggregierte Werte
    total_area_m2: float = 0
    main_orientation: Optional[str] = None  # N, NE, E, SE, S, SW, W, NW
    main_tilt_degrees: Optional[float] = None
    roof_type: Optional[str] = None  # flat, gabled, hipped, complex

    # Metadaten
    surfaces_count: int = 0
    has_data: bool = False

    def is_flat_roof(self) -> bool:
        """Prüft ob Flachdach (Neigung < 5°)."""
        if not self.surfaces:
            return False
        avg_tilt = sum(s.tilt_degrees or 0 for s in self.surfaces) / len(self.surfaces)
        return avg_tilt < 5

    def is_steep_roof(self) -> bool:
        """Prüft ob steiles Dach (Neigung > 35°)."""
        if not self.surfaces:
            return False
        max_tilt = max(s.tilt_degrees or 0 for s in self.surfaces)
        return max_tilt > 35


class SonnendachService:
    """Service für Sonnendach.ch Daten."""

    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Gibt HTTP Client zurück (Lazy Init)."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=TIMEOUT_SECONDS,
                headers={"User-Agent": USER_AGENT}
            )
        return self._client

    async def get_roof_surfaces(
        self,
        e: float,
        n: float,
        tolerance: float = 20.0
    ) -> List[RoofSurface]:
        """
        Holt Dachflächen für LV95-Koordinaten.

        Args:
            e: LV95 Ost-Koordinate
            n: LV95 Nord-Koordinate
            tolerance: Suchradius in Metern

        Returns:
            Liste von RoofSurface Objekten
        """
        params = {
            "geometryType": "esriGeometryPoint",
            "geometry": f"{e},{n}",
            "geometryFormat": "geojson",
            "layers": f"all:{LAYER_ID}",
            "tolerance": tolerance,
            "mapExtent": f"{e-50},{n-50},{e+50},{n+50}",
            "imageDisplay": "100,100,96",
            "returnGeometry": "true",
            "sr": "2056"
        }

        try:
            client = await self._get_client()
            response = await client.get(IDENTIFY_URL, params=params)
            response.raise_for_status()
            data = response.json()

            surfaces = []
            for result in data.get("results", []):
                surface = self._parse_surface(result)
                if surface:
                    surfaces.append(surface)

            logger.info(f"Found {len(surfaces)} roof surfaces at E={e}, N={n}")
            return surfaces

        except httpx.HTTPError as http_error:
            logger.error(f"HTTP error fetching roof surfaces: {http_error}")
            return []
        except Exception as error:
            logger.error(f"Error fetching roof surfaces: {error}")
            return []

    async def analyze_roof(
        self,
        e: float,
        n: float,
        tolerance: float = 20.0
    ) -> RoofAnalysis:
        """
        Analysiert alle Dachflächen eines Gebäudes.

        Args:
            e: LV95 Ost-Koordinate
            n: LV95 Nord-Koordinate
            tolerance: Suchradius in Metern

        Returns:
            RoofAnalysis mit allen Dachflächen und aggregierten Werten
        """
        surfaces = await self.get_roof_surfaces(e, n, tolerance)

        if not surfaces:
            return RoofAnalysis(has_data=False)

        # Aggregieren
        total_area = sum(s.area_m2 or 0 for s in surfaces)
        surfaces_count = len(surfaces)

        # Hauptausrichtung (Flächen-gewichteter Durchschnitt)
        main_orientation = self._calculate_main_orientation(surfaces)
        main_tilt = self._calculate_main_tilt(surfaces)

        # Dachtyp erkennen
        roof_type = self._detect_roof_type(surfaces)

        return RoofAnalysis(
            surfaces=surfaces,
            total_area_m2=round(total_area, 1),
            main_orientation=main_orientation,
            main_tilt_degrees=round(main_tilt, 1) if main_tilt else None,
            roof_type=roof_type,
            surfaces_count=surfaces_count,
            has_data=True
        )

    def _parse_surface(self, feature: dict) -> Optional[RoofSurface]:
        """Parsed Sonnendach Feature zu RoofSurface."""
        props = feature.get("properties", feature.get("attributes", {}))
        geom = feature.get("geometry", {})

        if not props:
            return None

        # Polygon extrahieren
        polygon = []
        if geom.get("type") == "Polygon":
            coords = geom.get("coordinates", [[]])[0]
            polygon = [(p[0], p[1]) for p in coords if len(p) >= 2]

        # Eignung-Mapping
        eignung_map = {
            1: "hoch",
            2: "mittel",
            3: "gering",
            4: "nicht geeignet"
        }

        eignung_code = props.get("klasse") or props.get("KLASSE")
        eignung = eignung_map.get(eignung_code, "unbekannt")

        return RoofSurface(
            id=str(props.get("id") or props.get("ID") or ""),
            polygon=polygon,
            area_m2=props.get("flaeche") or props.get("FLAECHE"),
            tilt_degrees=props.get("neigung") or props.get("NEIGUNG"),
            azimuth_degrees=props.get("ausrichtung") or props.get("AUSRICHTUNG"),
            eignung=eignung,
            eignung_code=eignung_code,
            strahlung_kwh=props.get("gstrahlung") or props.get("GSTRAHLUNG"),
        )

    def _calculate_main_orientation(self, surfaces: List[RoofSurface]) -> Optional[str]:
        """Berechnet die Hauptausrichtung (flächen-gewichtet)."""
        if not surfaces:
            return None

        # Flächen-gewichteter Durchschnitt des Azimuts
        total_weight = 0
        weighted_sum_sin = 0
        weighted_sum_cos = 0

        import math
        for surface in surfaces:
            if surface.azimuth_degrees is not None and surface.area_m2:
                weight = surface.area_m2
                rad = math.radians(surface.azimuth_degrees)
                weighted_sum_sin += weight * math.sin(rad)
                weighted_sum_cos += weight * math.cos(rad)
                total_weight += weight

        if total_weight == 0:
            return None

        avg_azimuth = math.degrees(math.atan2(
            weighted_sum_sin / total_weight,
            weighted_sum_cos / total_weight
        ))

        # Normalisieren auf 0-360
        if avg_azimuth < 0:
            avg_azimuth += 360

        # In Himmelsrichtung umwandeln
        return self._azimuth_to_direction(avg_azimuth)

    def _calculate_main_tilt(self, surfaces: List[RoofSurface]) -> Optional[float]:
        """Berechnet die Hauptneigung (flächen-gewichtet)."""
        if not surfaces:
            return None

        total_weight = 0
        weighted_sum = 0

        for surface in surfaces:
            if surface.tilt_degrees is not None and surface.area_m2:
                weight = surface.area_m2
                weighted_sum += weight * surface.tilt_degrees
                total_weight += weight

        return weighted_sum / total_weight if total_weight > 0 else None

    def _azimuth_to_direction(self, azimuth: float) -> str:
        """Konvertiert Azimut zu Himmelsrichtung."""
        # 0° = Nord, 90° = Ost, 180° = Süd, 270° = West
        directions = [
            (22.5, "N"),
            (67.5, "NE"),
            (112.5, "E"),
            (157.5, "SE"),
            (202.5, "S"),
            (247.5, "SW"),
            (292.5, "W"),
            (337.5, "NW"),
            (360, "N")
        ]

        for threshold, direction in directions:
            if azimuth < threshold:
                return direction

        return "N"

    def _detect_roof_type(self, surfaces: List[RoofSurface]) -> str:
        """Erkennt Dachtyp aus Dachflächen."""
        if not surfaces:
            return "unknown"

        # Anzahl signifikanter Flächen (> 5m²)
        significant = [s for s in surfaces if (s.area_m2 or 0) > 5]

        if not significant:
            return "unknown"

        # Durchschnittsneigung
        avg_tilt = self._calculate_main_tilt(significant) or 0

        # Anzahl verschiedene Ausrichtungen
        orientations = set()
        for s in significant:
            if s.azimuth_degrees is not None:
                orientations.add(self._azimuth_to_direction(s.azimuth_degrees))

        # Entscheidungslogik
        if avg_tilt < 5:
            return "flat"
        elif len(orientations) == 2:
            return "gabled"
        elif len(orientations) == 4:
            return "hipped"
        elif len(significant) > 4 or len(orientations) > 4:
            return "complex"
        else:
            return "gabled"  # Default für geneigte Dächer

    async def close(self):
        """Schliesst HTTP Client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


# Singleton-Instanz
_service_instance: Optional[SonnendachService] = None


def get_sonnendach_service() -> SonnendachService:
    """Gibt die Singleton-Instanz zurück."""
    global _service_instance
    if _service_instance is None:
        _service_instance = SonnendachService()
    return _service_instance


# Convenience Functions
async def get_roof_analysis(e: float, n: float) -> RoofAnalysis:
    """Shortcut für Dach-Analyse."""
    service = get_sonnendach_service()
    return await service.analyze_roof(e, n)
