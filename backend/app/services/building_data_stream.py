"""
BuildingDataStreamService - Streaming beim Laden von Gebäudedaten.

Nutzt den SmartBuildingService intern und streamt jeden Schritt als SSE-Event.

NEU 18.01.2026: Unterstützt jetzt auch Multi-Adressen (z.B. "Knospenweg 4-6, Bern").
Beide Formate verwenden denselben SSE-Endpunkt:
- Single: event.data = {matched_address, egid, polygon, ...}
- Multi:  event.data = {buildings: [{matched_address, egid, polygon, ...}, {...}]}

Frontend prüft: if (data.buildings) → Multi else → Single

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
8. complete - Vollständiges BuildingDataBundle (oder Liste bei Multi)
"""

import asyncio
import json
import re
import time
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import AsyncGenerator, Dict, Any, Optional, List
from enum import Enum

logger = logging.getLogger(__name__)

# NEU 30.01.2026: Pipeline-Logger für detailliertes Timing
from .sse_pipeline_logger import SSEPipelineLogger, log_step_timing


def _wkb_to_coords(wkb_data: bytes) -> Optional[List[List[List[float]]]]:
    """
    Konvertiert WKB (Well-Known Binary) zu JSON-Koordinaten für das Frontend.

    NEU 31.01.2026: Dach-Geometrie im SSE Heights-Event übertragen.

    Args:
        wkb_data: WKB-kodierte Geometrie aus building_roofs.geometry_wkb

    Returns:
        Liste von Polygon-Koordinaten: [[[e, n, z], [e, n, z], ...], ...]
        None bei Fehler oder leeren Daten
    """
    if not wkb_data:
        return None
    try:
        from shapely import wkb

        geom = wkb.loads(wkb_data)

        def extract_coords(geometry):
            if geometry.is_empty:
                return []
            geom_type = geometry.geom_type
            if geom_type == 'Polygon':
                coords = list(geometry.exterior.coords)
                return [[[c[0], c[1], c[2] if len(c) > 2 else 0] for c in coords]]
            elif geom_type == 'MultiPolygon':
                result = []
                for poly in geometry.geoms:
                    coords = list(poly.exterior.coords)
                    result.append([[c[0], c[1], c[2] if len(c) > 2 else 0] for c in coords])
                return result
            elif geom_type in ('GeometryCollection', 'MultiSurface'):
                result = []
                for g in geometry.geoms:
                    result.extend(extract_coords(g))
                return result
            return []

        return extract_coords(geom)
    except Exception as e:
        logger.warning(f"[SSE] _wkb_to_coords Fehler: {e}")
        return None


def _calculate_object_data(bundles: List[Any]) -> Optional[Dict[str, Any]]:
    """
    Berechnet das Objekt-Polygon für Gerüstplanung.

    Ein Projekt = Ein Objekt. Das Objekt-Polygon ist:
    - Single-Building: Das Polygon des einen Gebäudes
    - Multi-Building: Union aller Gebäude-Polygone (äussere Kontur)

    Das Frontend verwendet "polygon" für:
    - SVG-Visualisierung
    - 2D-Fassadenansicht
    - 3D-Gerüstplanung
    - Fassaden-Berechnung

    projectBuildings[] enthält die Metadaten (Adressen, EGIDs) aller Gebäude.

    Args:
        bundles: Liste von BuildingDataBundle Objekten (1 oder mehr)

    Returns:
        Dict mit polygon, facades_object, roof_object, projectBuildings, etc.
        oder None bei Fehler
    """
    if not bundles:
        return None

    try:
        from shapely.geometry import Polygon
        from shapely.ops import unary_union

        # Alle gültigen Polygone und Metadaten sammeln
        all_polygons = []
        project_buildings = []  # Metadaten für projectBuildings
        total_traufhoehe = 0
        trauf_count = 0

        # Dach-Höhen sammeln (m ü.M.)
        roof_z_mins = []  # Traufhöhen
        roof_z_maxs = []  # Firsthöhen

        for bundle in bundles:
            if bundle.polygon and len(bundle.polygon) >= 3:
                coords = [(p[0], p[1]) for p in bundle.polygon]
                all_polygons.append(Polygon(coords))

                # projectBuildings Metadaten sammeln
                project_buildings.append({
                    "egid": bundle.egid,
                    "address": bundle.address_matched or "",
                    "center_e": bundle.lv95_e,
                    "center_n": bundle.lv95_n,
                })

                if bundle.traufhoehe_m:
                    total_traufhoehe += bundle.traufhoehe_m
                    trauf_count += 1

                # Dach-Höhen aus roof_dach_min/max (m ü.M.)
                if bundle.roof_dach_min_m:
                    roof_z_mins.append(bundle.roof_dach_min_m)
                if bundle.roof_dach_max_m:
                    roof_z_maxs.append(bundle.roof_dach_max_m)

        if len(all_polygons) == 0:
            return None

        # NEU 19.01.2026: Unterscheide Single vs Multi-Building
        object_polygon = None
        outer_facades = []

        if len(all_polygons) == 1:
            # Single-Building: Das Polygon direkt verwenden
            single = all_polygons[0]
            object_polygon = [
                [round(c[0], 2), round(c[1], 2)]
                for c in single.exterior.coords
            ]
            avg_traufhoehe = total_traufhoehe / trauf_count if trauf_count > 0 else None
            outer_facades = _extract_facades_from_polygon(object_polygon, avg_traufhoehe)
            total_perimeter = round(single.length, 2)
        else:
            # Multi-Building: Union aller Polygone
            combined = unary_union(all_polygons)
            avg_traufhoehe = total_traufhoehe / trauf_count if trauf_count > 0 else None

            if hasattr(combined, 'exterior'):
                # Einfaches Polygon
                object_polygon = [
                    [round(c[0], 2), round(c[1], 2)]
                    for c in combined.exterior.coords
                ]
                outer_facades = _extract_facades_from_polygon(object_polygon, avg_traufhoehe)

            elif hasattr(combined, 'geoms'):
                # MultiPolygon - nehme das größte
                largest = max(combined.geoms, key=lambda p: p.area)
                if hasattr(largest, 'exterior'):
                    object_polygon = [
                        [round(c[0], 2), round(c[1], 2)]
                        for c in largest.exterior.coords
                    ]
                    outer_facades = _extract_facades_from_polygon(object_polygon, avg_traufhoehe)

            total_perimeter = round(combined.length if hasattr(combined, 'length') else 0, 2)

        if not object_polygon:
            return None

        # Statistiken
        total_area = round(sum(b.footprint_area_m2 or 0 for b in bundles), 2)

        # Dach-Höhen (min/max über alle Gebäude)
        roof_object = None
        if roof_z_mins or roof_z_maxs:
            roof_object = {
                "z_min": min(roof_z_mins) if roof_z_mins else None,  # Tiefste Traufe
                "z_max": max(roof_z_maxs) if roof_z_maxs else None,  # Höchster First
            }

        return {
            # FIX 19.01.2026: Einheitliches Naming - "polygon" statt "polygon_object"
            "polygon": object_polygon,
            "facades_object": outer_facades,
            "roof_object": roof_object,
            "projectBuildings": project_buildings,  # Metadaten aller Gebäude
            "total_area_m2": total_area,
            "total_perimeter_m": total_perimeter,
            "avg_traufhoehe_m": round(avg_traufhoehe, 2) if avg_traufhoehe else None,
            "building_count": len(bundles),
        }

    except Exception as e:
        logger.warning(f"[OBJECT] Fehler bei Objekt-Berechnung: {e}")
        return None


def _extract_facades_from_polygon(polygon_coords: List[List[float]], default_height: Optional[float]) -> List[Dict[str, Any]]:
    """
    Extrahiert Fassaden aus einem Polygon für das combined-Objekt.

    Args:
        polygon_coords: Liste von [e, n] Koordinaten
        default_height: Standard-Höhe für alle Fassaden

    Returns:
        Liste von Fassaden-Dicts
    """
    import math

    if len(polygon_coords) < 3:
        return []

    facades = []

    for i in range(len(polygon_coords) - 1):
        p1 = polygon_coords[i]
        p2 = polygon_coords[i + 1]

        # Länge berechnen
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        length = math.sqrt(dx * dx + dy * dy)

        if length < 0.5:  # Kurze Segmente ignorieren
            continue

        # Richtung bestimmen
        angle = math.degrees(math.atan2(dy, dx))
        direction = _angle_to_direction(angle)

        facades.append({
            "index": len(facades),
            "direction": direction,
            "start_point": p1,
            "end_point": p2,
            "length_m": round(length, 2),
            "height_m": default_height,
        })

    return facades


def _angle_to_direction(angle: float) -> str:
    """Konvertiert Winkel (Grad) zu Himmelsrichtung."""
    # Normalisieren auf 0-360
    angle = angle % 360
    if angle < 0:
        angle += 360

    # 8 Richtungen
    directions = ["E", "NE", "N", "NW", "W", "SW", "S", "SE"]
    index = round(angle / 45) % 8
    return directions[index]


def _is_multi_address(address: str) -> bool:
    """
    Prüft ob eine Adresse ein Multi-Adress-Format hat.

    Erkannte Formate:
    - Range: "Knospenweg 4-6" oder "Knospenweg 4 - 6"
    - Slash: "Kramgasse 27/29"
    - Komma in Hausnummer: "Hauptstr. 10, 12, 14" (nicht Komma vor Stadt!)

    Returns:
        True wenn Multi-Adresse erkannt
    """
    # Muster: Zahl-Zahl (Range)
    if re.search(r'\d+\s*-\s*\d+', address):
        # Aber nicht wenn es eine PLZ ist (4 Ziffern gefolgt von Leerzeichen und Stadt)
        # z.B. "3006 Bern" sollte nicht als Range erkannt werden
        match = re.search(r'(\d+)\s*-\s*(\d+)', address)
        if match:
            # Prüfe ob es Teil einer PLZ sein könnte
            start = int(match.group(1))
            end = int(match.group(2))
            # PLZ in der Schweiz: 1000-9999
            if start >= 1000 and end >= 1000:
                return False
            return True

    # Muster: Zahl/Zahl (Slash)
    if re.search(r'\d+\s*/\s*\d+', address):
        return True

    return False


class StreamStep(str, Enum):
    """Schritte im Building-Data-Stream."""
    GEOCODING = "geocoding"
    GWR = "gwr"
    POLYGON = "polygon"
    POLYGON_PROGRESS = "polygon_progress"
    HEIGHTS = "heights"
    TERRAIN = "terrain"
    ZONES = "zones"
    ZONES_ANALYSIS = "zones_analysis"  # NEU 07.02.2026: Separater Claude API Schritt
    RESEARCH = "research"
    COMPLETE = "complete"
    ERROR = "error"
    HEARTBEAT = "heartbeat"  # FIX 07.02.2026: Keep-alive für Railway Timeout


# FIX 07.02.2026: Heartbeat-Intervall für Railway (Default-Timeout ~30s)
HEARTBEAT_INTERVAL_SECONDS = 10


@dataclass
class SSEEvent:
    """Ein Server-Sent Event."""
    event: str
    data: Dict[str, Any]

    def to_sse(self) -> str:
        """Formatiert als SSE-String."""
        return f"event: {self.event}\ndata: {json.dumps(self.data, ensure_ascii=False)}\n\n"


async def _run_with_heartbeats(
    coro,
    step_name: str,
    heartbeat_interval: float = HEARTBEAT_INTERVAL_SECONDS
) -> AsyncGenerator[SSEEvent, None]:
    """
    FIX 07.02.2026: Führt eine Coroutine aus und yielded Heartbeats während sie läuft.

    Löst das Railway Timeout-Problem (~30s Default) bei langen Claude API Calls.

    Args:
        coro: Die auszuführende Coroutine (z.B. Claude API Call)
        step_name: Name des Schritts für Heartbeat-Message
        heartbeat_interval: Sekunden zwischen Heartbeats (Default: 10s)

    Yields:
        SSEEvent Heartbeats während die Coroutine läuft
    """
    task = asyncio.create_task(coro)
    heartbeat_count = 0

    while not task.done():
        try:
            # Warte auf Task-Fertigstellung oder Timeout
            await asyncio.wait_for(asyncio.shield(task), timeout=heartbeat_interval)
            break  # Task ist fertig
        except asyncio.TimeoutError:
            # Task läuft noch → Heartbeat senden
            heartbeat_count += 1
            yield SSEEvent(
                event=StreamStep.HEARTBEAT,
                data={
                    "step": step_name,
                    "elapsed_seconds": heartbeat_count * heartbeat_interval,
                    "message": f"Processing {step_name}..."
                }
            )

    # Exception vom Task weiterwerfen falls vorhanden
    if task.exception():
        raise task.exception()


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

        NEU 18.01.2026: Unterstützt Single UND Multi-Adressen in EINER Methode!
        Erkennt automatisch ob Multi (z.B. "Knospenweg 4-6") und verarbeitet
        alle Gebäude mit derselben Logik.

        Args:
            address: Zu suchende Adresse (Single oder Multi wie "Knospenweg 4-6")
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

        Event-Format:
            Single: {matched_address, egid, polygon, ...}
            Multi:  {buildings: [{...}, {...}], building_count: N}
        """
        from .smart_building.models import BuildingDataBundle
        from .address_parser import get_address_parser

        # NEU 30.01.2026: Pipeline-Logger für detailliertes Timing
        pipeline_logger = SSEPipelineLogger(address)

        is_multi = _is_multi_address(address)
        if is_multi:
            logger.info(f"[STREAM] Multi-Adresse erkannt: {address}")

        # Parse Adressen (Single = 1 Adresse, Multi = N Adressen)
        parser = get_address_parser()
        if is_multi:
            parsed = parser.parse(address)
            addresses_to_process = parsed.get_full_addresses()
            if not addresses_to_process:
                yield SSEEvent(
                    event=StreamStep.ERROR,
                    data={"code": "PARSE_FAILED", "message": f"Konnte keine Adressen aus '{address}' parsen", "step": StreamStep.GEOCODING}
                )
                return
            logger.info(f"[STREAM] {len(addresses_to_process)} Adressen geparst: {addresses_to_process}")
        else:
            addresses_to_process = [address]

        start_time = time.time()
        smart = self._get_smart_service()

        try:
            # ═══════════════════════════════════════════════════════════════
            # 1. GEOCODING + GWR (für alle Adressen)
            # ═══════════════════════════════════════════════════════════════
            pipeline_logger.start_step("geocoding", {"address_count": len(addresses_to_process)})
            step_start = time.time()
            bundles: List[BuildingDataBundle] = []
            geocoding_results = []

            for single_address in addresses_to_process:
                bundle = BuildingDataBundle(
                    address_input=single_address,
                    collection_timestamp=datetime.now(),
                )

                await smart._collect_geocoding(bundle)

                if not bundle.lv95_e or not bundle.lv95_n:
                    if is_multi:
                        logger.warning(f"[STREAM] Geocoding fehlgeschlagen für: {single_address}")
                        continue
                    else:
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
                bundles.append(bundle)

                geocoding_results.append({
                    "matched_address": bundle.address_matched,
                    "egid": bundle.egid,
                    "coordinates": {
                        "lv95_e": bundle.lv95_e,
                        "lv95_n": bundle.lv95_n,
                    },
                })

            if not bundles:
                yield SSEEvent(
                    event=StreamStep.ERROR,
                    data={
                        "code": "GEOCODING_FAILED",
                        "message": f"Keine Gebäude gefunden für: {address}",
                        "step": StreamStep.GEOCODING
                    }
                )
                return

            geocoding_duration = round((time.time() - step_start) * 1000, 1)
            pipeline_logger.end_step("geocoding", {
                "building_count": len(bundles),
                "egids": [b.egid for b in bundles if b.egid]
            })

            if is_multi:
                yield SSEEvent(
                    event=StreamStep.GEOCODING,
                    data={
                        "buildings": geocoding_results,
                        "building_count": len(geocoding_results),
                        "duration_ms": geocoding_duration
                    }
                )
            else:
                b = bundles[0]
                yield SSEEvent(
                    event=StreamStep.GEOCODING,
                    data={
                        "matched_address": b.address_matched,
                        "egid": b.egid,
                        "coordinates": {
                            "lv95_e": b.lv95_e,
                            "lv95_n": b.lv95_n,
                        },
                        "duration_ms": geocoding_duration
                    }
                )

            # ═══════════════════════════════════════════════════════════════
            # 2. GWR-DATEN (separates Event für UI)
            # ═══════════════════════════════════════════════════════════════
            if is_multi:
                gwr_results = [{
                    "egid": b.egid,
                    "matched_address": b.address_matched,
                    "floors": b.gwr_floors,
                    "area_m2": b.gwr_area_m2,
                    "category": b.gwr_category_code,
                    "category_name": b.gwr_category,
                } for b in bundles]
                yield SSEEvent(
                    event=StreamStep.GWR,
                    data={"buildings": gwr_results, "duration_ms": 0}
                )
            else:
                b = bundles[0]
                yield SSEEvent(
                    event=StreamStep.GWR,
                    data={
                        "egid": b.egid,
                        "floors": b.gwr_floors,
                        "area_m2": b.gwr_area_m2,
                        "category": b.gwr_category_code,
                        "category_name": b.gwr_category,
                        "duration_ms": 0
                    }
                )

            # ═══════════════════════════════════════════════════════════════
            # 3. POLYGON + HEIGHTS (ein API-Aufruf pro Gebäude)
            # ═══════════════════════════════════════════════════════════════
            pipeline_logger.start_step("polygon", {"building_count": len(bundles)})
            step_start = time.time()

            # Progress-Event für Tile-Download
            if is_multi:
                yield SSEEvent(
                    event=StreamStep.POLYGON_PROGRESS,
                    data={
                        "status": "loading",
                        "message": f"Lade Gebäudedaten für {len(bundles)} Gebäude...",
                        "building_count": len(bundles)
                    }
                )
            else:
                # FIX 21.01.2026: Prüfe Import-Status statt GDB-Pfad
                # Wenn Tile bereits importiert (status='imported'/'cleaned'),
                # sind die Daten in der DB - kein Download nötig!
                from .tile_cache import get_tile_cache, lv95_to_tile_id
                tile_cache = get_tile_cache()
                tile_id = lv95_to_tile_id(bundles[0].lv95_e, bundles[0].lv95_n)
                import_status = tile_cache.get_tile_import_status(tile_id)

                # Nur Download-Meldung zeigen wenn Tile NICHT importiert
                if not import_status or import_status == 'pending':
                    yield SSEEvent(
                        event=StreamStep.POLYGON_PROGRESS,
                        data={
                            "status": "downloading",
                            "message": "Lade Gebäudedaten von swisstopo...",
                        }
                    )

            # 3D-Daten für alle Gebäude laden
            polygon_results = []
            loaded_egids = []  # FIX 29.01.2026: Sammle EGIDs für Prefetch

            for bundle in bundles:
                # TIMING 21.01.2026: Messe jeden Schritt
                t0 = time.time()
                await smart._collect_building_3d_data(bundle)
                t1 = time.time()
                smart._load_roof_data_from_db(bundle)
                t2 = time.time()

                print(f"[SSE-TIMING] EGID {bundle.egid}: "
                      f"_collect_building_3d_data={round((t1-t0)*1000)}ms, "
                      f"_load_roof_data={round((t2-t1)*1000)}ms", flush=True)

                polygon_results.append({
                    "egid": bundle.egid,
                    "matched_address": bundle.address_matched,
                    "polygon": bundle.polygon,
                    "sides": bundle.sides,
                    "perimeter_m": bundle.perimeter_m,
                    "area_m2": bundle.footprint_area_m2,
                })

                # Sammle EGID für skip_egids
                if bundle.egid:
                    try:
                        loaded_egids.append(int(bundle.egid))
                    except (ValueError, TypeError):
                        pass

            # ════════════════════════════════════════════════════════════
            # FIX 31.01.2026: Blocking-Call entfernt!
            # schedule_prefetch_with_neighbors wurde hier aufgerufen und
            # blockierte ~141s. Prefetch läuft jetzt als Background-Task
            # NACH dem SSE-Event (siehe unten nach yield).
            # ════════════════════════════════════════════════════════════
            polygon_duration = round((time.time() - step_start) * 1000, 1)
            pipeline_logger.end_step("polygon", {"duration_ms": polygon_duration})

            if is_multi:
                yield SSEEvent(
                    event=StreamStep.POLYGON,
                    data={"buildings": polygon_results, "duration_ms": polygon_duration}
                )
            else:
                b = bundles[0]
                from .tile_cache import get_tile_cache
                tile_cache = get_tile_cache()
                tile_path = tile_cache.get_tile_for_coordinates(b.lv95_e, b.lv95_n)
                yield SSEEvent(
                    event=StreamStep.POLYGON,
                    data={
                        "polygon": b.polygon,
                        "sides": b.sides,
                        "perimeter_m": b.perimeter_m,
                        "area_m2": b.footprint_area_m2,
                        "egid": b.egid,
                        "cache_hit": tile_path is not None,
                        "duration_ms": polygon_duration
                    }
                )

            # ════════════════════════════════════════════════════════════
            # NEU 31.01.2026: 3-Stufen-Import für has_3d_layers=1
            # ════════════════════════════════════════════════════════════
            # STUFE 1: Angefragte Gebäude SOFORT speichern (~50ms pro Gebäude)
            #          → has_3d_layers=1 noch VOR dem Heights-Event!
            # STUFE 2+3: Nachbarn + Rest im Background (prefetch_and_cleanup)
            # ════════════════════════════════════════════════════════════
            if bundles and bundles[0].lv95_e and bundles[0].lv95_n:
                from .tile_cache import lv95_to_tile_id, get_tile_cache
                from .parquet_writer import import_single_building
                from pathlib import Path

                center_e, center_n = bundles[0].lv95_e, bundles[0].lv95_n
                tile_id = lv95_to_tile_id(center_e, center_n)

                # GDB-Pfad holen
                tile_cache = get_tile_cache()
                gdb_path_str = tile_cache.get_tile_for_coordinates(center_e, center_n)
                gdb_path = Path(gdb_path_str) if gdb_path_str else None

                # STUFE 1: Jedes angefragte Gebäude sofort speichern
                if gdb_path and gdb_path.exists():
                    for bundle in bundles:
                        if bundle.egid:
                            try:
                                egid_int = int(bundle.egid)
                                t_import_start = time.time()

                                # Single-Building Import (Building + Roof + Wall → DB)
                                import_result = await import_single_building(
                                    gdb_path=gdb_path,
                                    egid=egid_int,
                                    tile_id=tile_id,
                                    cleanup_after=True
                                )

                                t_import_end = time.time()
                                import_ms = round((t_import_end - t_import_start) * 1000)

                                if import_result.get('success'):
                                    # has_3d_layers=1 ist jetzt in der DB gesetzt!
                                    bundle.has_3d_layers = True
                                    print(f"[SSE-TIMING] STUFE 1: EGID {egid_int} importiert ({import_ms}ms) → has_3d_layers=1", flush=True)
                                else:
                                    print(f"[SSE-TIMING] STUFE 1: EGID {egid_int} nicht gefunden ({import_result.get('reason')})", flush=True)

                            except (ValueError, TypeError) as e:
                                print(f"[SSE-TIMING] STUFE 1: EGID {bundle.egid} ungültig: {e}", flush=True)

                # STUFE 2+3: Nachbarn + Rest im Background
                from .tile_prefetch import prefetch_and_cleanup

                asyncio.create_task(
                    prefetch_and_cleanup(
                        tile_id=tile_id,
                        center_e=center_e,
                        center_n=center_n,
                        skip_egids=loaded_egids  # Die gerade importierten überspringen
                    )
                )
                print(f"[SSE-TIMING] STUFE 2+3: Background prefetch_and_cleanup started for tile {tile_id}", flush=True)

            # ═══════════════════════════════════════════════════════════════
            # 4. HEIGHTS (separates Event)
            # ═══════════════════════════════════════════════════════════════
            # FIX 29.01.2026: DEPRECATED traufhoehe_m/firsthoehe_m ENTFERNT
            # Korrekte Höhen: roof_dach_min_m/roof_dach_max_m (m ü.M.)
            # Frontend berechnet: traufhoehe = roof_dach_min_m - terrain_z_min
            heights_results = []
            for bundle in bundles:
                height_source = "swissBUILDINGS3D" if bundle.roof_dach_min_m or bundle.roof_dach_max_m else "default"
                # NEU 31.01.2026: roof_geometry_coords für Frontend 3D-Rendering
                roof_coords = _wkb_to_coords(bundle.roof_geometry_wkb) if bundle.roof_geometry_wkb else None
                heights_results.append({
                    "egid": bundle.egid,
                    "matched_address": bundle.address_matched,
                    # DEPRECATED ENTFERNT: traufhoehe_m, firsthoehe_m
                    "gebaeudehoehe_m": bundle.gebaeudehoehe_m,
                    "source": height_source,
                    "has_3d_layers": bundle.has_3d_layers,
                    "has_roof_geometry": bundle.has_roof_geometry,
                    "roof_geometry_coords": roof_coords,  # NEU 31.01.2026
                    "roof_dach_min_m": bundle.roof_dach_min_m,
                    "roof_dach_max_m": bundle.roof_dach_max_m,
                    "roof_gebaeudeeinheit": bundle.roof_gebaeudeeinheit,
                    "roof_type": bundle.roof_type,
                    "roof_orientation": bundle.roof_orientation,
                    "roof_angle_deg": bundle.roof_angle_deg,
                })

            if is_multi:
                yield SSEEvent(
                    event=StreamStep.HEIGHTS,
                    data={"buildings": heights_results, "duration_ms": 0}
                )
            else:
                h = heights_results[0]
                yield SSEEvent(
                    event=StreamStep.HEIGHTS,
                    data={
                        # DEPRECATED ENTFERNT: traufhoehe_m, firsthoehe_m
                        "gebaeudehoehe_m": h["gebaeudehoehe_m"],
                        "source": h["source"],
                        "duration_ms": 0,
                        "has_3d_layers": h["has_3d_layers"],
                        "has_roof_geometry": h["has_roof_geometry"],
                        "roof_geometry_coords": h["roof_geometry_coords"],  # NEU 31.01.2026
                        "roof_dach_min_m": h["roof_dach_min_m"],
                        "roof_dach_max_m": h["roof_dach_max_m"],
                        "roof_gebaeudeeinheit": h["roof_gebaeudeeinheit"],
                        "roof_type": h["roof_type"],
                        "roof_orientation": h["roof_orientation"],
                        "roof_angle_deg": h["roof_angle_deg"],
                    }
                )

            # ═══════════════════════════════════════════════════════════════
            # 5. TERRAIN (optional)
            # ═══════════════════════════════════════════════════════════════
            if include_terrain:
                pipeline_logger.start_step("terrain")
                step_start = time.time()
                terrain_results = []

                for bundle in bundles:
                    # FIX 01.02.2026: _collect_terrain_data() wieder aktiviert!
                    # Der Code verwendet jetzt building_walls.z_min (nicht mehr swissALTI3D).
                    # Die reference_height_m wird aus min(building_walls.z_min) berechnet.
                    await smart._collect_terrain_data(bundle)

                    terrain_data = {"egid": bundle.egid, "matched_address": bundle.address_matched}
                    if bundle.terrain:
                        terrain_data.update({
                            "terrain_height_m": bundle.terrain.reference_height_m,
                            "min_terrain_m": bundle.terrain.min_height_m,
                            "max_terrain_m": bundle.terrain.max_height_m,
                            # DEPRECATED ENTFERNT: slope_m, slope_class
                            "facade_z_min": bundle.terrain.facade_z_min,
                            "facade_z_max": bundle.terrain.facade_z_max,
                            "facade_heights_source": bundle.terrain.facade_heights_source,
                        })
                    terrain_results.append(terrain_data)

                terrain_duration = round((time.time() - step_start) * 1000, 1)
                pipeline_logger.end_step("terrain", {"duration_ms": terrain_duration})

                if is_multi:
                    yield SSEEvent(
                        event=StreamStep.TERRAIN,
                        data={"buildings": terrain_results, "duration_ms": terrain_duration}
                    )
                else:
                    t = terrain_results[0]
                    yield SSEEvent(
                        event=StreamStep.TERRAIN,
                        data={
                            "duration_ms": terrain_duration,
                            "terrain_height_m": t.get("terrain_height_m"),
                            "min_terrain_m": t.get("min_terrain_m"),
                            "max_terrain_m": t.get("max_terrain_m"),
                            # DEPRECATED ENTFERNT: slope_m, slope_class
                            "facade_z_min": t.get("facade_z_min"),
                            "facade_z_max": t.get("facade_z_max"),
                            "facade_heights_source": t.get("facade_heights_source"),
                        }
                    )

            # ═══════════════════════════════════════════════════════════════
            # 6. ZONES (immer, aber Claude nur bei komplexen Gebäuden)
            # NEU 07.02.2026: Separates "zones_analysis" Event für Claude API
            # FIX 07.02.2026: Heartbeats während Claude API Call senden
            # ═══════════════════════════════════════════════════════════════
            if include_zones:
                pipeline_logger.start_step("zones")
                step_start = time.time()
                zones_results = []

                for bundle in bundles:
                    if smart._needs_zones_analysis(bundle):
                        # NEU 07.02.2026: Explizites Event für Claude-Analyse
                        yield SSEEvent(
                            event=StreamStep.ZONES_ANALYSIS,
                            data={
                                "status": "starting",
                                "egid": bundle.egid,
                                "matched_address": bundle.address_matched,
                                "message": "Claude API wird für Zonen-Analyse aufgerufen...",
                                "complexity": bundle.complexity,
                            }
                        )

                        # FIX 07.02.2026: Heartbeats während Claude-Call
                        claude_start = time.time()
                        async for heartbeat in _run_with_heartbeats(
                            smart._collect_zones_analysis(bundle),
                            step_name="zones_analysis"
                        ):
                            yield heartbeat

                        claude_duration = round((time.time() - claude_start) * 1000, 1)
                        yield SSEEvent(
                            event=StreamStep.ZONES_ANALYSIS,
                            data={
                                "status": "complete",
                                "egid": bundle.egid,
                                "matched_address": bundle.address_matched,
                                "duration_ms": claude_duration,
                                "zones_count": len(bundle.zones),
                            }
                        )
                        zones_source = "claude"
                    else:
                        smart._create_default_zone(bundle)
                        zones_source = "auto"

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

                    zones_results.append({
                        "egid": bundle.egid,
                        "matched_address": bundle.address_matched,
                        "zones": zones_list,
                        "complexity": bundle.complexity,
                        "source": zones_source,
                        "building_name": bundle.building_name,
                    })

                zones_duration = round((time.time() - step_start) * 1000, 1)
                pipeline_logger.end_step("zones", {"duration_ms": zones_duration})

                if is_multi:
                    yield SSEEvent(
                        event=StreamStep.ZONES,
                        data={"buildings": zones_results, "duration_ms": zones_duration}
                    )
                else:
                    z = zones_results[0]
                    yield SSEEvent(
                        event=StreamStep.ZONES,
                        data={
                            "zones": z["zones"],
                            "complexity": z["complexity"],
                            "source": z["source"],
                            "building_name": z["building_name"],
                            "duration_ms": zones_duration
                        }
                    )

            # ═══════════════════════════════════════════════════════════════
            # 7. RESEARCH (optional)
            # ═══════════════════════════════════════════════════════════════
            if include_research:
                pipeline_logger.start_step("research")
                step_start = time.time()
                research_results = []

                for bundle in bundles:
                    await smart._collect_research_data(bundle, force_refresh)

                    research_results.append({
                        "egid": bundle.egid,
                        "matched_address": bundle.address_matched,
                        "building_name": bundle.building_name,
                        "building_type": bundle.building_type,
                        "architectural_style": bundle.architectural_style,
                        "source": bundle.research_source,
                    })

                research_duration = round((time.time() - step_start) * 1000, 1)
                pipeline_logger.end_step("research", {"duration_ms": research_duration})

                if is_multi:
                    yield SSEEvent(
                        event=StreamStep.RESEARCH,
                        data={"buildings": research_results, "duration_ms": research_duration}
                    )
                else:
                    r = research_results[0]
                    yield SSEEvent(
                        event=StreamStep.RESEARCH,
                        data={
                            "building_name": r["building_name"],
                            "building_type": r["building_type"],
                            "architectural_style": r["architectural_style"],
                            "source": r["source"],
                            "duration_ms": research_duration
                        }
                    )

            # ═══════════════════════════════════════════════════════════════
            # 8. COMPLETE
            # ═══════════════════════════════════════════════════════════════
            pipeline_logger.start_step("complete")
            total_duration = round((time.time() - start_time) * 1000, 1)

            complete_results = []
            for bundle in bundles:
                smart._assess_data_quality(bundle)
                complete_results.append({
                    "egid": bundle.egid,
                    "matched_address": bundle.address_matched,
                    "summary": {
                        "has_polygon": bundle.polygon is not None and len(bundle.polygon) > 0,
                        "has_heights": bundle.traufhoehe_m is not None,
                        "has_terrain": bundle.terrain is not None,
                        "zones_count": len(bundle.zones),
                        "complexity": bundle.complexity,
                        "quality": bundle.overall_quality.value if bundle.overall_quality else "unknown",
                    },
                    "bundle": self._bundle_to_dict(bundle)
                })

            # NEU 19.01.2026: object_data wird IMMER berechnet (Single + Multi)
            # Ein Projekt = Ein Objekt. Das Frontend verwendet "polygon" für alles.
            object_data = _calculate_object_data(bundles)

            if is_multi:
                yield SSEEvent(
                    event=StreamStep.COMPLETE,
                    data={
                        "status": "ok",
                        "duration_ms": total_duration,
                        "address": address,
                        "building_count": len(bundles),
                        "buildings": complete_results,
                        # NEU 19.01.2026: object_data statt combined (IMMER vorhanden)
                        "object_data": object_data,
                    }
                )
            else:
                c = complete_results[0]
                yield SSEEvent(
                    event=StreamStep.COMPLETE,
                    data={
                        "status": "ok",
                        "duration_ms": total_duration,
                        "address": c["matched_address"] or address,
                        "egid": c["egid"],
                        "summary": c["summary"],
                        "bundle": c["bundle"],
                        # NEU 19.01.2026: object_data auch bei Single-Building
                        "object_data": object_data,
                    }
                )

            # NEU 30.01.2026: Pipeline-Logging abschliessen
            pipeline_logger.end_step("complete", {"total_duration_ms": total_duration})
            pipeline_logger.finish()

        except Exception as e:
            logger.exception(f"Error in stream_building_data: {e}")
            pipeline_logger.add_error(str(e))
            pipeline_logger.finish()
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

        # FIX 29.01.2026: DEPRECATED slope_m/slope_class ENTFERNT
        terrain_dict = None
        if bundle.terrain:
            terrain_dict = {
                "reference_height_m": bundle.terrain.reference_height_m,
                "min_height_m": bundle.terrain.min_height_m,
                "max_height_m": bundle.terrain.max_height_m,
                # DEPRECATED ENTFERNT: slope_m, slope_class (Frontend berechnet)
                # NEU 14.01.2026 (T3): Fassaden-Höhen aus Wall-Layer
                "facade_z_min": bundle.terrain.facade_z_min,
                "facade_z_max": bundle.terrain.facade_z_max,
                "facade_heights_source": bundle.terrain.facade_heights_source,
            }

        # FIX 04.02.2026: Backend liefert NUR Rohdaten (roof_dach_min/max_m, terrain).
        # Frontend berechnet relative Höhen (traufhoehe, firsthoehe) eigenständig.

        return {
            "address_input": bundle.address_input,
            "address_matched": bundle.address_matched,
            "egid": bundle.egid,
            "lv95_e": bundle.lv95_e,
            "lv95_n": bundle.lv95_n,
            "polygon": bundle.polygon,
            "sides": bundle.sides,
            # NEU 18.01.2026: Fassaden mit Höhen pro Fassade (für GeruestbauData)
            "facades": bundle.facades,
            "perimeter_m": bundle.perimeter_m,
            "footprint_area_m2": bundle.footprint_area_m2,
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
            # NEU 12.01.2026 22:15 - 3D-Layer Daten
            "has_3d_layers": bundle.has_3d_layers,
            "has_roof_geometry": bundle.has_roof_geometry,
            "roof_dach_min_m": bundle.roof_dach_min_m,
            "roof_dach_max_m": bundle.roof_dach_max_m,
            "roof_gebaeudeeinheit": bundle.roof_gebaeudeeinheit,
            # NEU 12.01.2026 22:45 - Dach-Analyse Daten
            "roof_type": bundle.roof_type,
            "roof_orientation": bundle.roof_orientation,
            "roof_angle_deg": bundle.roof_angle_deg,
        }


# Singleton
_building_data_stream_service: Optional[BuildingDataStreamService] = None


def get_building_data_stream_service() -> BuildingDataStreamService:
    """Get singleton BuildingDataStreamService instance."""
    global _building_data_stream_service
    if _building_data_stream_service is None:
        _building_data_stream_service = BuildingDataStreamService()
    return _building_data_stream_service
