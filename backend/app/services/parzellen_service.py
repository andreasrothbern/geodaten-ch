"""
Parzellen-Service (Amtliche Vermessung)
========================================

Zugriff auf Grundstücksdaten aus der amtlichen Vermessung.

Datenquelle:
- Layer: ch.swisstopo-vd.amtliche-vermessung
- API: api3.geo.admin.ch
- Daten: OpenData (frei verfügbar)

Features:
- Parzelle an Koordinaten finden
- Parzellenpolygon abrufen
- EGRID (Eidg. Grundstücksidentifikator) ermitteln
- Für Neubauten: Polygon aus Parzelle

Stand: 03.01.2026
"""

import logging
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)

# swisstopo API
SWISSTOPO_API_BASE = "https://api3.geo.admin.ch"
AV_LAYER = "ch.swisstopo-vd.amtliche-vermessung"


@dataclass
class Parzelle:
    """Grundstück aus der amtlichen Vermessung."""

    # Identifikation
    egrid: Optional[str] = None  # CH280652308630
    number: Optional[str] = None  # Parzellennummer
    bfsnr: Optional[int] = None  # Gemeinde-Nr.
    canton: Optional[str] = None  # Kanton (z.B. "BE")
    identnd: Optional[str] = None  # Kantonal-ID (z.B. "BE351")

    # Geometrie
    polygon: Optional[List[List[float]]] = None  # [[e, n], ...]
    area_m2: Optional[float] = None
    perimeter_m: Optional[float] = None

    # Zentrum (LV95)
    center_e: Optional[float] = None
    center_n: Optional[float] = None

    # Metadaten
    geoportal_url: Optional[str] = None
    realestate_type: Optional[int] = None

    # Für Neubau-Support
    has_building: bool = True  # Ist ein Gebäude auf der Parzelle?

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "egrid": self.egrid,
            "number": self.number,
            "bfsnr": self.bfsnr,
            "canton": self.canton,
            "identnd": self.identnd,
            "polygon": self.polygon,
            "area_m2": self.area_m2,
            "perimeter_m": self.perimeter_m,
            "center": {
                "lv95_e": self.center_e,
                "lv95_n": self.center_n,
            } if self.center_e else None,
            "geoportal_url": self.geoportal_url,
            "has_building": self.has_building,
        }


class ParzellenService:
    """
    Service für Grundstücksdaten aus der amtlichen Vermessung.

    Verwendet die swisstopo Identify-API für Koordinaten-Abfragen.
    """

    def __init__(self):
        self._client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        """HTTP Client schliessen."""
        await self._client.aclose()

    async def get_parzelle_at_coordinates(
        self,
        e: float,
        n: float,
        tolerance: float = 5.0,
        include_geometry: bool = True
    ) -> Optional[Parzelle]:
        """
        Findet die Parzelle an den gegebenen LV95-Koordinaten.

        Args:
            e: LV95 Ost-Koordinate
            n: LV95 Nord-Koordinate
            tolerance: Toleranz in Pixeln (für die Identify-API)
            include_geometry: Polygon-Geometrie einbeziehen

        Returns:
            Parzelle oder None wenn nicht gefunden
        """
        try:
            # Identify-API aufrufen
            url = f"{SWISSTOPO_API_BASE}/rest/services/api/MapServer/identify"

            params = {
                "geometryType": "esriGeometryPoint",
                "geometry": f"{e},{n}",
                "layers": f"all:{AV_LAYER}",
                "tolerance": int(tolerance),
                "returnGeometry": str(include_geometry).lower(),
                "sr": "2056",  # LV95
            }

            response = await self._client.get(url, params=params)
            response.raise_for_status()

            data = response.json()

            if not data.get("results"):
                logger.debug(f"Keine Parzelle bei E={e}, N={n}")
                return None

            # Erste Parzelle nehmen
            result = data["results"][0]
            attrs = result.get("properties", result.get("attributes", {}))

            parzelle = Parzelle(
                egrid=attrs.get("egris_egrid"),
                number=attrs.get("number"),
                bfsnr=attrs.get("bfsnr"),
                canton=attrs.get("ak"),
                identnd=attrs.get("identnd"),
                geoportal_url=attrs.get("geoportal_url"),
                realestate_type=attrs.get("realestate_type"),
                center_e=e,
                center_n=n,
            )

            # Geometrie extrahieren
            if include_geometry and "geometry" in result:
                geometry = result["geometry"]
                if geometry.get("type") == "Polygon":
                    rings = geometry.get("rings", geometry.get("coordinates", []))
                    if rings:
                        # Äusserer Ring
                        outer_ring = rings[0] if isinstance(rings[0][0], list) else rings
                        parzelle.polygon = [[round(p[0], 2), round(p[1], 2)] for p in outer_ring]

                        # Fläche und Umfang berechnen
                        parzelle.area_m2 = self._calculate_area(parzelle.polygon)
                        parzelle.perimeter_m = self._calculate_perimeter(parzelle.polygon)

            logger.info(
                f"Parzelle gefunden: EGRID={parzelle.egrid}, "
                f"Nr.={parzelle.number}, Fläche={parzelle.area_m2}m²"
            )

            return parzelle

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP-Fehler bei Parzellen-Abfrage: {e}")
            return None
        except Exception as e:
            logger.error(f"Fehler bei Parzellen-Abfrage: {e}")
            return None

    async def get_parzelle_by_egrid(self, egrid: str) -> Optional[Parzelle]:
        """
        Findet eine Parzelle anhand der EGRID.

        Args:
            egrid: Eidg. Grundstücksidentifikator (z.B. "CH280652308630")

        Returns:
            Parzelle oder None wenn nicht gefunden
        """
        try:
            # Find-API aufrufen
            url = f"{SWISSTOPO_API_BASE}/rest/services/api/MapServer/find"

            params = {
                "layer": AV_LAYER,
                "searchText": egrid,
                "searchField": "egris_egrid",
                "returnGeometry": "true",
                "sr": "2056",
            }

            response = await self._client.get(url, params=params)
            response.raise_for_status()

            data = response.json()

            if not data.get("results"):
                logger.debug(f"Keine Parzelle mit EGRID={egrid}")
                return None

            result = data["results"][0]
            attrs = result.get("properties", result.get("attributes", {}))

            parzelle = Parzelle(
                egrid=egrid,
                number=attrs.get("number"),
                bfsnr=attrs.get("bfsnr"),
                canton=attrs.get("ak"),
                identnd=attrs.get("identnd"),
                geoportal_url=attrs.get("geoportal_url"),
            )

            # Geometrie extrahieren
            if "geometry" in result:
                geometry = result["geometry"]
                if geometry.get("type") == "Polygon":
                    rings = geometry.get("rings", geometry.get("coordinates", []))
                    if rings:
                        outer_ring = rings[0] if isinstance(rings[0][0], list) else rings
                        parzelle.polygon = [[round(p[0], 2), round(p[1], 2)] for p in outer_ring]
                        parzelle.area_m2 = self._calculate_area(parzelle.polygon)
                        parzelle.perimeter_m = self._calculate_perimeter(parzelle.polygon)

                        # Zentrum berechnen
                        if parzelle.polygon:
                            xs = [p[0] for p in parzelle.polygon]
                            ys = [p[1] for p in parzelle.polygon]
                            parzelle.center_e = sum(xs) / len(xs)
                            parzelle.center_n = sum(ys) / len(ys)

            return parzelle

        except Exception as e:
            logger.error(f"Fehler bei EGRID-Abfrage: {e}")
            return None

    async def check_building_on_parcel(
        self,
        parzelle: Parzelle,
        building_radius_m: float = 5.0
    ) -> bool:
        """
        Prüft ob auf der Parzelle ein Gebäude existiert.

        Für Neubau-Support: Wenn kein Gebäude, kann das
        Parzellen-Polygon als Baufeld verwendet werden.

        Args:
            parzelle: Die zu prüfende Parzelle
            building_radius_m: Suchradius für Gebäude

        Returns:
            True wenn Gebäude vorhanden
        """
        if not parzelle.center_e or not parzelle.center_n:
            return True  # Im Zweifel: Gebäude vorhanden

        try:
            # swissBUILDINGS3D abfragen
            from app.services.swissbuildings3d_fetcher import fetch_building_polygon_for_coordinates

            result = await fetch_building_polygon_for_coordinates(
                parzelle.center_e,
                parzelle.center_n,
                tolerance=building_radius_m
            )

            parzelle.has_building = result is not None
            return parzelle.has_building

        except Exception as e:
            logger.error(f"Fehler bei Gebäude-Prüfung: {e}")
            return True  # Im Zweifel: Gebäude vorhanden

    def _calculate_area(self, polygon: List[List[float]]) -> float:
        """Berechnet Fläche mit Shoelace-Formel."""
        if len(polygon) < 3:
            return 0

        n = len(polygon)
        area = 0

        for i in range(n - 1):
            area += polygon[i][0] * polygon[i + 1][1]
            area -= polygon[i + 1][0] * polygon[i][1]

        # Polygon schliessen
        if polygon[0] != polygon[-1]:
            area += polygon[-1][0] * polygon[0][1]
            area -= polygon[0][0] * polygon[-1][1]

        return round(abs(area) / 2, 2)

    def _calculate_perimeter(self, polygon: List[List[float]]) -> float:
        """Berechnet Umfang."""
        if len(polygon) < 2:
            return 0

        import math

        total = 0
        for i in range(len(polygon) - 1):
            dx = polygon[i + 1][0] - polygon[i][0]
            dy = polygon[i + 1][1] - polygon[i][1]
            total += math.sqrt(dx * dx + dy * dy)

        return round(total, 2)


# Singleton
_parzellen_service: Optional[ParzellenService] = None


def get_parzellen_service() -> ParzellenService:
    """Gibt Singleton-Instanz zurück."""
    global _parzellen_service
    if _parzellen_service is None:
        _parzellen_service = ParzellenService()
    return _parzellen_service


# Convenience-Funktionen
async def get_parzelle_at(e: float, n: float) -> Optional[Parzelle]:
    """Shortcut für Koordinaten-Abfrage."""
    service = get_parzellen_service()
    return await service.get_parzelle_at_coordinates(e, n)


async def get_parzelle_by_egrid(egrid: str) -> Optional[Parzelle]:
    """Shortcut für EGRID-Abfrage."""
    service = get_parzellen_service()
    return await service.get_parzelle_by_egrid(egrid)
