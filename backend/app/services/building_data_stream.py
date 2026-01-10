"""
BuildingDataStreamService - Streaming beim Laden von Gebäudedaten.

Nutzt den SmartBuildingService intern und streamt jeden Schritt als SSE-Event.

Wird verwendet bei:
- Projekt-Erstellung (Adresse eingeben → Daten laden)
- Gebäude hinzufügen zu bestehendem Projekt
- Daten-Refresh

Liefert progressiv via Server-Sent Events (SSE):
1. geocoding - Adress-Match, Koordinaten, EGID (~100ms)
2. gwr - GWR-Daten (Geschosse, Fläche, Kategorie) (~50ms)
3. polygon - Gebäude-Polygon mit Fassaden (~200ms oder ~5s bei Tile-Download)
4. heights - Höhendaten (Trauf, First, Gesamt) (~50ms)
5. terrain - Terrain-Höhe, Hanglage (~200ms, optional)
6. zones - Zonen-Analyse (~500ms, Claude nur bei komplexen Gebäuden)
7. research - Gebäudename, Architekturstil (~1s, optional)
8. complete - Vollständiges BuildingDataBundle
"""

import json
import time
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import AsyncGenerator, Dict, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class StreamStep(str, Enum):
    """Schritte im Building-Data-Stream."""
    GEOCODING = "geocoding"
    GWR = "gwr"
    POLYGON = "polygon"
    POLYGON_PROGRESS = "polygon_progress"
    HEIGHTS = "heights"
    TERRAIN = "terrain"
    ZONES = "zones"
    RESEARCH = "research"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class SSEEvent:
    """Ein Server-Sent Event."""
    event: str
    data: Dict[str, Any]

    def to_sse(self) -> str:
        """Formatiert als SSE-String."""
        return f"event: {self.event}\ndata: {json.dumps(self.data, ensure_ascii=False)}\n\n"


class BuildingDataStreamService:
    """
    Streaming-Service für Gebäudedaten beim Projekt-Erstellen.

    Nutzt die internen _collect_* Methoden des SmartBuildingService,
    sendet aber nach jedem Schritt ein Event ans Frontend.

    Vorteile:
    - Kein duplizierter Code
    - Nutzt die getestete Logik des SmartBuildingService
    - Progressive Events für bessere UX
    """

    def __init__(self):
        self._smart_service = None

    def _get_smart_service(self):
        """Lazy-Loading des SmartBuildingService."""
        if self._smart_service is None:
            from .smart_building import get_smart_building_service
            self._smart_service = get_smart_building_service()
        return self._smart_service

    async def stream_building_data(
        self,
        address: str,
        include_research: bool = True,
        include_zones: bool = True,
        include_terrain: bool = True,
        force_refresh: bool = False
    ) -> AsyncGenerator[SSEEvent, None]:
        """
        Generator für SSE Events beim Laden von Gebäudedaten.

        Ruft die Methoden des SmartBuildingService auf und sendet
        nach jedem Schritt ein Event.

        Args:
            address: Zu suchende Adresse
            include_research: Claude-Recherche für Gebäudename
            include_zones: Zonen-Analyse (Claude nur bei komplexen Gebäuden)
            include_terrain: Terrain-Daten laden
            force_refresh: Cache ignorieren

        Yields:
            SSEEvent Objekte in der Reihenfolge:
            1. geocoding (inkl. EGID aus GWR)
            2. gwr
            3. polygon (+ polygon_progress bei Tile-Download)
            4. heights
            5. terrain (optional)
            6. zones
            7. research (optional)
            8. complete
        """
        from .smart_building.models import BuildingDataBundle

        start_time = time.time()
        smart = self._get_smart_service()

        # Bundle erstellen (wie in SmartBuildingService.collect_all_data)
        bundle = BuildingDataBundle(
            address_input=address,
            collection_timestamp=datetime.now(),
        )

        try:
            # ═══════════════════════════════════════════════════════════════
            # 1. GEOCODING + GWR (für EGID)
            # ═══════════════════════════════════════════════════════════════
            step_start = time.time()

            await smart._collect_geocoding(bundle)

            if not bundle.lv95_e or not bundle.lv95_n:
                yield SSEEvent(
                    event=StreamStep.ERROR,
                    data={
                        "code": "GEOCODING_FAILED",
                        "message": f"Adresse nicht gefunden: {address}",
                        "step": StreamStep.GEOCODING
                    }
                )
                return

            # GWR-Daten holen (setzt EGID!)
            await smart._collect_gwr_data(bundle)

            yield SSEEvent(
                event=StreamStep.GEOCODING,
                data={
                    "matched_address": bundle.address_matched,
                    "egid": bundle.egid,
                    "coordinates": {
                        "lv95_e": bundle.lv95_e,
                        "lv95_n": bundle.lv95_n,
                    },
                    "duration_ms": round((time.time() - step_start) * 1000, 1)
                }
            )

            # ═══════════════════════════════════════════════════════════════
            # 2. GWR-DATEN (separates Event für UI)
            # ═══════════════════════════════════════════════════════════════
            yield SSEEvent(
                event=StreamStep.GWR,
                data={
                    "egid": bundle.egid,
                    "floors": bundle.gwr_floors,
                    "area_m2": bundle.gwr_area_m2,
                    "category": bundle.gwr_category_code,
                    "category_name": bundle.gwr_category,
                    "duration_ms": 0  # Bereits in geocoding gemessen
                }
            )

            # ═══════════════════════════════════════════════════════════════
            # 3. POLYGON + HEIGHTS (ein API-Aufruf, zwei Events)
            # ═══════════════════════════════════════════════════════════════
            step_start = time.time()

            # Prüfe ob Tile-Download nötig (für Progress-Event)
            from .tile_cache import get_tile_cache
            tile_cache = get_tile_cache()
            # get_tile_for_coordinates gibt direkt Path zurück (oder None)
            tile_path = tile_cache.get_tile_for_coordinates(bundle.lv95_e, bundle.lv95_n)

            if not tile_path:
                yield SSEEvent(
                    event=StreamStep.POLYGON_PROGRESS,
                    data={
                        "status": "downloading",
                        "message": "Lade Gebäudedaten von swisstopo...",
                    }
                )

            # Polygon + Höhen laden (ein Aufruf!)
            await smart._collect_building_3d_data(bundle)
            polygon_duration = round((time.time() - step_start) * 1000, 1)

            yield SSEEvent(
                event=StreamStep.POLYGON,
                data={
                    "polygon": bundle.polygon,
                    "sides": bundle.sides,
                    "perimeter_m": bundle.perimeter_m,
                    "area_m2": bundle.footprint_area_m2,
                    "egid": bundle.egid,
                    "cache_hit": tile_path is not None,
                    "duration_ms": polygon_duration
                }
            )

            # ═══════════════════════════════════════════════════════════════
            # 4. HEIGHTS (aus demselben Aufruf, separates Event)
            # ═══════════════════════════════════════════════════════════════
            height_source = "swissBUILDINGS3D"
            if not bundle.traufhoehe_m and not bundle.firsthoehe_m:
                height_source = "default"

            yield SSEEvent(
                event=StreamStep.HEIGHTS,
                data={
                    "traufhoehe_m": bundle.traufhoehe_m,
                    "firsthoehe_m": bundle.firsthoehe_m,
                    "gebaeudehoehe_m": bundle.gebaeudehoehe_m,
                    "source": height_source,
                    "duration_ms": 0  # Bereits in polygon gemessen
                }
            )

            # ═══════════════════════════════════════════════════════════════
            # 5. TERRAIN (optional)
            # ═══════════════════════════════════════════════════════════════
            if include_terrain:
                step_start = time.time()
                await smart._collect_terrain_data(bundle)

                terrain_data = {
                    "duration_ms": round((time.time() - step_start) * 1000, 1)
                }

                if bundle.terrain:
                    terrain_data.update({
                        "terrain_height_m": bundle.terrain.reference_height_m,
                        "min_terrain_m": bundle.terrain.min_height_m,
                        "max_terrain_m": bundle.terrain.max_height_m,
                        "slope_m": bundle.terrain.slope_m,
                        "slope_class": bundle.terrain.slope_class,
                    })

                yield SSEEvent(
                    event=StreamStep.TERRAIN,
                    data=terrain_data
                )

            # ═══════════════════════════════════════════════════════════════
            # 6. ZONES (immer, aber Claude nur bei komplexen Gebäuden)
            # ═══════════════════════════════════════════════════════════════
            if include_zones:
                step_start = time.time()

                # Komplexitäts-Check (wie in SmartBuildingService)
                if smart._needs_zones_analysis(bundle):
                    await smart._collect_zones_analysis(bundle)
                    zones_source = "claude"
                else:
                    smart._create_default_zone(bundle)
                    zones_source = "auto"

                # Zonen zu Dict konvertieren
                zones_list = []
                for zone in bundle.zones:
                    zone_dict = {
                        "id": zone.id,
                        "name": zone.name,
                        "zone_type": zone.zone_type.value if hasattr(zone.zone_type, 'value') else str(zone.zone_type),
                        "traufhoehe_m": zone.traufhoehe_m,
                        "firsthoehe_m": zone.firsthoehe_m,
                        "beruesten": zone.beruesten,
                    }
                    zones_list.append(zone_dict)

                yield SSEEvent(
                    event=StreamStep.ZONES,
                    data={
                        "zones": zones_list,
                        "complexity": bundle.complexity,
                        "source": zones_source,
                        "building_name": bundle.building_name,
                        "duration_ms": round((time.time() - step_start) * 1000, 1)
                    }
                )

            # ═══════════════════════════════════════════════════════════════
            # 7. RESEARCH (optional)
            # ═══════════════════════════════════════════════════════════════
            if include_research:
                step_start = time.time()
                await smart._collect_research_data(bundle, force_refresh)

                yield SSEEvent(
                    event=StreamStep.RESEARCH,
                    data={
                        "building_name": bundle.building_name,
                        "building_type": bundle.building_type,
                        "architectural_style": bundle.architectural_style,
                        "source": bundle.research_source,
                        "duration_ms": round((time.time() - step_start) * 1000, 1)
                    }
                )

            # ═══════════════════════════════════════════════════════════════
            # 8. COMPLETE
            # ═══════════════════════════════════════════════════════════════
            smart._assess_data_quality(bundle)
            total_duration = round((time.time() - start_time) * 1000, 1)

            yield SSEEvent(
                event=StreamStep.COMPLETE,
                data={
                    "status": "ok",
                    "duration_ms": total_duration,
                    "address": bundle.address_matched or address,
                    "egid": bundle.egid,
                    "summary": {
                        "has_polygon": bundle.polygon is not None and len(bundle.polygon) > 0,
                        "has_heights": bundle.traufhoehe_m is not None,
                        "has_terrain": bundle.terrain is not None,
                        "zones_count": len(bundle.zones),
                        "complexity": bundle.complexity,
                        "quality": bundle.overall_quality.value if bundle.overall_quality else "unknown",
                    },
                    "bundle": self._bundle_to_dict(bundle)
                }
            )

        except Exception as e:
            logger.exception(f"Error in stream_building_data: {e}")
            yield SSEEvent(
                event=StreamStep.ERROR,
                data={
                    "code": "STREAM_ERROR",
                    "message": str(e),
                    "step": "unknown"
                }
            )

    def _bundle_to_dict(self, bundle) -> Dict[str, Any]:
        """Konvertiert BuildingDataBundle zu Dict für JSON-Serialisierung."""
        zones_list = []
        for zone in bundle.zones:
            zones_list.append({
                "id": zone.id,
                "name": zone.name,
                "zone_type": zone.zone_type.value if hasattr(zone.zone_type, 'value') else str(zone.zone_type),
                "traufhoehe_m": zone.traufhoehe_m,
                "firsthoehe_m": zone.firsthoehe_m,
                "beruesten": zone.beruesten,
            })

        terrain_dict = None
        if bundle.terrain:
            terrain_dict = {
                "reference_height_m": bundle.terrain.reference_height_m,
                "min_height_m": bundle.terrain.min_height_m,
                "max_height_m": bundle.terrain.max_height_m,
                "slope_m": bundle.terrain.slope_m,
                "slope_class": bundle.terrain.slope_class,
            }

        return {
            "address_input": bundle.address_input,
            "address_matched": bundle.address_matched,
            "egid": bundle.egid,
            "lv95_e": bundle.lv95_e,
            "lv95_n": bundle.lv95_n,
            "polygon": bundle.polygon,
            "sides": bundle.sides,
            "perimeter_m": bundle.perimeter_m,
            "footprint_area_m2": bundle.footprint_area_m2,
            "traufhoehe_m": bundle.traufhoehe_m,
            "firsthoehe_m": bundle.firsthoehe_m,
            "gebaeudehoehe_m": bundle.gebaeudehoehe_m,
            "gwr_floors": bundle.gwr_floors,
            "gwr_area_m2": bundle.gwr_area_m2,
            "gwr_category": bundle.gwr_category,
            "gwr_category_code": bundle.gwr_category_code,
            "terrain": terrain_dict,
            "zones": zones_list,
            "complexity": bundle.complexity,
            "building_name": bundle.building_name,
            "building_type": bundle.building_type,
            "architectural_style": bundle.architectural_style,
            "research_source": bundle.research_source,
        }


# Singleton
_building_data_stream_service: Optional[BuildingDataStreamService] = None


def get_building_data_stream_service() -> BuildingDataStreamService:
    """Get singleton BuildingDataStreamService instance."""
    global _building_data_stream_service
    if _building_data_stream_service is None:
        _building_data_stream_service = BuildingDataStreamService()
    return _building_data_stream_service
