"""
Orthofoto Service
==================

Ruft Orthofotos von map.geo.admin.ch ab für Claude-Analyse.

Features:
- WMTS-basierter Abruf von Orthofotos
- Automatische Zentrierung auf Gebäude
- Base64-Encoding für Claude Vision API

Version: 1.0
Datum: 28.12.2025
"""

import httpx
import base64
import math
from typing import Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class OrthofotoResult:
    """Ergebnis eines Orthofoto-Abrufs"""
    image_base64: str           # Base64-kodiertes PNG
    width_px: int
    height_px: int
    center_e: float             # LV95 E-Koordinate Zentrum
    center_n: float             # LV95 N-Koordinate Zentrum
    resolution_m: float         # Meter pro Pixel
    bbox: Tuple[float, float, float, float]  # min_e, min_n, max_e, max_n
    source: str                 # "swisstopo" / "swissimage"
    media_type: str             # "image/png"


class OrthofotoService:
    """
    Service für Orthofoto-Abruf.

    Verwendet swisstopo WMTS für Orthofotos.
    """

    # WMTS Endpunkt
    WMTS_BASE = "https://wmts.geo.admin.ch/1.0.0"

    # Verfügbare Layer
    LAYERS = {
        "orthofoto": "ch.swisstopo.swissimage-product",
        "karte": "ch.swisstopo.pixelkarte-farbe",
        "luftbild": "ch.swisstopo.images-swissimage",
    }

    # Standard-Parameter
    DEFAULT_RESOLUTION = 0.5  # Meter pro Pixel
    DEFAULT_SIZE = 512        # Pixel

    def __init__(self):
        self.timeout = httpx.Timeout(30.0, connect=10.0)

    async def get_orthofoto(
        self,
        center_e: float,
        center_n: float,
        width_m: float = 100.0,
        height_m: float = 100.0,
        resolution_m: float = 0.5,
        layer: str = "orthofoto"
    ) -> Optional[OrthofotoResult]:
        """
        Ruft ein Orthofoto für einen Bereich ab.

        Args:
            center_e: LV95 E-Koordinate des Zentrums
            center_n: LV95 N-Koordinate des Zentrums
            width_m: Breite des Ausschnitts in Metern
            height_m: Höhe des Ausschnitts in Metern
            resolution_m: Auflösung in Metern pro Pixel
            layer: "orthofoto", "karte" oder "luftbild"

        Returns:
            OrthofotoResult mit Base64-kodiertem Bild oder None bei Fehler
        """
        try:
            # Bounding Box berechnen
            half_w = width_m / 2
            half_h = height_m / 2
            bbox = (
                center_e - half_w,  # min_e
                center_n - half_h,  # min_n
                center_e + half_w,  # max_e
                center_n + half_h   # max_n
            )

            # Pixel-Größe berechnen
            width_px = int(width_m / resolution_m)
            height_px = int(height_m / resolution_m)

            # WMS GetMap URL (einfacher als WMTS für rechteckige Ausschnitte)
            wms_url = "https://wms.geo.admin.ch/"
            layer_name = self.LAYERS.get(layer, self.LAYERS["orthofoto"])

            params = {
                "SERVICE": "WMS",
                "VERSION": "1.3.0",
                "REQUEST": "GetMap",
                "LAYERS": layer_name,
                "CRS": "EPSG:2056",
                "BBOX": f"{bbox[1]},{bbox[0]},{bbox[3]},{bbox[2]}",  # WMS 1.3: N,E,N,E
                "WIDTH": str(width_px),
                "HEIGHT": str(height_px),
                "FORMAT": "image/png",
            }

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(wms_url, params=params)
                response.raise_for_status()

                # Prüfen ob Bild zurückgekommen ist
                content_type = response.headers.get("content-type", "")
                if "image" not in content_type:
                    logger.warning(f"Unexpected content type: {content_type}")
                    return None

                # Base64 kodieren
                image_base64 = base64.standard_b64encode(response.content).decode("utf-8")

                return OrthofotoResult(
                    image_base64=image_base64,
                    width_px=width_px,
                    height_px=height_px,
                    center_e=center_e,
                    center_n=center_n,
                    resolution_m=resolution_m,
                    bbox=bbox,
                    source="swisstopo",
                    media_type="image/png"
                )

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching orthofoto: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching orthofoto: {e}")
            return None

    async def get_building_orthofoto(
        self,
        center_e: float,
        center_n: float,
        building_width_m: float,
        building_depth_m: float,
        padding_factor: float = 1.5,
        resolution_m: float = 0.25
    ) -> Optional[OrthofotoResult]:
        """
        Ruft ein Orthofoto für ein Gebäude ab mit automatischem Padding.

        Args:
            center_e: Gebäudezentrum E-Koordinate
            center_n: Gebäudezentrum N-Koordinate
            building_width_m: Gebäudebreite
            building_depth_m: Gebäudetiefe
            padding_factor: Faktor für Umgebung (1.5 = 50% mehr)
            resolution_m: Auflösung in m/px

        Returns:
            OrthofotoResult oder None
        """
        # Ausschnitt-Größe mit Padding
        width_m = max(building_width_m, 20) * padding_factor
        height_m = max(building_depth_m, 20) * padding_factor

        # Mindestgröße für Kontext
        width_m = max(width_m, 50)
        height_m = max(height_m, 50)

        # Maximalgröße (API-Limit)
        width_m = min(width_m, 500)
        height_m = min(height_m, 500)

        return await self.get_orthofoto(
            center_e=center_e,
            center_n=center_n,
            width_m=width_m,
            height_m=height_m,
            resolution_m=resolution_m
        )


# Singleton
_orthofoto_service: Optional[OrthofotoService] = None


def get_orthofoto_service() -> OrthofotoService:
    """Gibt die OrthofotoService-Instanz zurück (Singleton)."""
    global _orthofoto_service
    if _orthofoto_service is None:
        _orthofoto_service = OrthofotoService()
    return _orthofoto_service
