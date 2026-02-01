"""GerÃ¼stbau-App API Router."""

import logging
import math
import uuid
from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from typing import List, Dict, Any, Optional
from sse_starlette.sse import EventSourceResponse

logger = logging.getLogger(__name__)

from ..models.geruestbau import (
    Project, ProjectCreate, ProjectUpdate, ProjectStatus,
    ProjectWithGeruestbaudata, PhotoAnalysis, ScaffoldConfig
)
from ..services.geruestbau.project_service import ProjectService
from ..services.swissbuildings3d_service import get_swissbuildings3d_service
from ..services.swisstopo import SwisstopoService
from ..services.roof import get_roof_service
from ..services.address_parser import get_address_parser
from ..services.parzellen_service import get_parzellen_service
# FIX 19.01.2026: get_neighbors_service Import entfernt - nutze GeodatenClient stattdessen
# Siehe: docs/architecture/ARCHITECTURE.md → "Architektur-Bruch: Aktueller Zustand"
from ..config import NEIGHBOR_SEARCH_RADIUS_M

router = APIRouter(prefix="/api/v1/geruestbau", tags=["GerÃ¼stbau"])

project_service = ProjectService()

# Lazy load tender extractor to avoid startup issues
_tender_extractor = None
_url_importer = None

def get_extractor():
    global _tender_extractor
    if _tender_extractor is None:
        from ..services.geruestbau.tender_extractor import get_tender_extractor
        _tender_extractor = get_tender_extractor()
    return _tender_extractor

def get_url_importer():
    global _url_importer
    if _url_importer is None:
        from ..services.geruestbau.url_importer import get_url_importer as _get_importer
        _url_importer = _get_importer()
    return _url_importer


@router.get("/projects", response_model=List[Project])
async def list_projects(status: ProjectStatus = None):
    """Liste aller Projekte, optional gefiltert nach Status."""
    return await project_service.list_projects(status)


@router.post("/projects", response_model=Project)
async def create_project(project: ProjectCreate):
    """Neues Projekt erstellen."""
    return await project_service.create_project(project)


@router.get("/projects/{project_id}", response_model=ProjectWithGeruestbaudata)
async def get_project(project_id: str):
    """Projekt-Details mit GeruestbauData abrufen."""
    project = await project_service.get_project_with_data(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden")
    return project


@router.put("/projects/{project_id}", response_model=Project)
async def update_project(project_id: str, update: ProjectUpdate):
    """Projekt aktualisieren."""
    project = await project_service.update_project(project_id, update)
    if not project:
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden")
    return project


@router.delete("/projects/{project_id}")
async def delete_project(project_id: str):
    """Projekt lÃ¶schen."""
    success = await project_service.delete_project(project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden")
    return {"status": "deleted"}


@router.post("/projects/{project_id}/photos")
async def upload_photo(project_id: str, file: UploadFile = File(...)):
    """Foto hochladen."""
    return await project_service.upload_photo(project_id, file)


@router.post("/projects/{project_id}/photos/{photo_id}/analyze", response_model=PhotoAnalysis)
async def analyze_photo(project_id: str, photo_id: str):
    """Foto mit Claude Vision analysieren (Blickrichtung erkennen)."""
    result = await project_service.analyze_photo(project_id, photo_id)
    if not result:
        raise HTTPException(status_code=404, detail="Foto nicht gefunden")
    return result


@router.get("/projects/{project_id}/scaffold", response_model=ScaffoldConfig)
async def get_scaffold_config(project_id: str):
    """Aktuelle GerÃ¼st-Konfiguration abrufen."""
    config = await project_service.get_scaffold_config(project_id)
    if not config:
        raise HTTPException(status_code=404, detail="Keine GerÃ¼st-Konfiguration")
    return config


@router.put("/projects/{project_id}/scaffold", response_model=ScaffoldConfig)
async def update_scaffold_config(project_id: str, config: ScaffoldConfig):
    """GerÃ¼st-Konfiguration aktualisieren."""
    return await project_service.update_scaffold_config(project_id, config)


# NEU 16.01.2026 11:00: GeruestbauData im Projekt speichern
@router.post("/projects/{project_id}/geruestbaudata", response_model=Dict[str, Any])
async def save_geruestbaudata(
    project_id: str,
    egid: str = Query(..., description="EGID des Gebäudes"),
    address: str = Query(..., description="Adresse des Gebäudes")
):
    """
    Speichert alle Gebäudedaten (inkl. 3D-Layer) als GeruestbauData im Projekt.

    Wird nach dem SSE-Stream aufgerufen, wenn alle Daten geladen sind.
    Die GeruestbauData enthält:
    - Gebäude-Grunddaten (EGID, Polygon, Koordinaten)
    - Höhendaten (Trauf-, First-, Gebäudehöhe)
    - 3D-Layer (building_walls, building_roofs)
    - Terrain-Daten (Geländehöhe, Hanglage)
    - Zonen (bei komplexen Gebäuden)

    Returns:
        {"success": true/false, "message": "..."}
    """
    success = await project_service.save_geruestbaudata_to_project(project_id, egid, address)

    if success:
        return {"success": True, "message": "GeruestbauData gespeichert"}
    else:
        return {"success": False, "message": "Fehler beim Speichern der GeruestbauData"}


# NEU 19.01.2026: Einziger Einstiegspunkt für Projekt-Geodaten
# FIX 19.01.2026 23:30: Direkter DuckDB-Zugriff statt GeodatenClient (Monolith!)
@router.get("/projects/{project_id}/geodata", response_model=Dict[str, Any])
async def get_project_geodata(
    project_id: str,
    radius_m: float = Query(100, ge=1, le=500, description="Suchradius in Metern"),
    include_walls: bool = Query(True, description="3D-Wall-Daten mitliefern"),
    include_roofs: bool = Query(True, description="3D-Roof-Daten mitliefern")
):
    """
    Lädt Geodaten für ein Projekt direkt aus DuckDB.

    FIX 19.01.2026: Direkter Service-Aufruf statt GeodatenClient (HTTP zu sich selbst).
    Wir sind ein Monolith - geruestbau.py und main.py teilen sich dieselben Services!

    WICHTIG: Ein Projekt = Ein Objekt.
    - polygon: Union-Polygon aller Projekt-Gebäude (IMMER vorhanden)
    - Bei Single-Building: Das eine Polygon
    - Bei Multi-Building: Union aller Polygone (äussere Kontur)

    Datenfluss:
    1. Projekt laden → center_e, center_n, project_egids
    2. DuckDB BBox-Query → Alle Gebäude im Umkreis
    3. Kategorisierung: project_egids → Projekt-Gebäude, Rest → Nachbarn
    4. Union-Polygon berechnen → polygon

    Returns:
        {
            "polygon": [[x,y], ...],      # Das Projekt-Polygon (Union)
            "project_buildings": [...],   # Details für 3D-View (walls, roofs)
            "neighbors": [...],           # Nachbar-Gebäude
            "center": {"e": ..., "n": ...},
            "radius_m": 100,
            "query_time_ms": 1.2
        }
    """
    import time
    import json
    import math
    from app.config import get_building_3d_connection

    start_time = time.time()

    # 1. Projekt laden
    project = await project_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden")

    # 2. Koordinaten und EGIDs aus Projekt
    center_e = project.center_e
    center_n = project.center_n
    project_egids = project.project_egids or []

    # Fallback: EGIDs aus buildings[] (für ältere Projekte ohne project_egids)
    if not project_egids and project.buildings:
        project_egids = [b.egid for b in project.buildings if b.egid]

    # Auch das einzelne egid-Feld berücksichtigen
    if project.egid and project.egid not in project_egids:
        # Multi-EGID Format: "1243790+1243792" aufteilen
        for egid in project.egid.split('+'):
            if egid and egid not in project_egids:
                project_egids.append(egid)

    # Fallback: Falls keine Koordinaten gespeichert, aus erstem Building
    if not center_e and project.buildings:
        first_building = project.buildings[0]
        if first_building.coordinates:
            center_e = first_building.coordinates.get('lv95_e') or first_building.coordinates.get('e')
            center_n = first_building.coordinates.get('lv95_n') or first_building.coordinates.get('n')

    if not center_e or not center_n:
        raise HTTPException(
            status_code=400,
            detail="Projekt hat keine Koordinaten. Bitte Projekt mit Adresse erstellen."
        )

    # LV95 Koordinaten normalisieren
    e, n = center_e, center_n
    if e < 2000000:
        e += 2000000
    if n < 1000000:
        n += 1000000

    # 3. Direkte DuckDB-Query (wie main.py:/api/v1/building/area)
    conn = get_building_3d_connection(read_only=True)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT egid, ST_AsGeoJSON(geom) as polygon, center_e, center_n,
               traufhoehe_m, firsthoehe_m, gebaeudehoehe_m, gebaeudeeinheit
        FROM buildings_3d
        WHERE center_e BETWEEN ? AND ?
          AND center_n BETWEEN ? AND ?
    """, (e - radius_m, e + radius_m, n - radius_m, n + radius_m))

    rows = cursor.fetchall()
    buildings = []
    gebaeudeeinheit_to_building = {}

    for row in rows:
        egid = str(row[0])
        bld_center_e = row[2]
        bld_center_n = row[3]
        gebaeudeeinheit = row[7]

        # Distanz zum Projekt-Zentrum
        dx = bld_center_e - e
        dy = bld_center_n - n
        distance_m = round(math.sqrt(dx*dx + dy*dy), 2)

        if distance_m > radius_m:
            continue

        # Polygon parsen (ST_AsGeoJSON liefert GeoJSON-Format)
        polygon_data = row[1]
        polygon = None
        if polygon_data:
            try:
                geojson = json.loads(polygon_data) if isinstance(polygon_data, str) else polygon_data
                # ST_AsGeoJSON: {"type": "Polygon", "coordinates": [[[x,y], ...]]}
                if isinstance(geojson, dict) and 'coordinates' in geojson:
                    polygon = geojson['coordinates'][0]
                else:
                    polygon = geojson  # Fallback
            except (json.JSONDecodeError, TypeError, KeyError, IndexError):
                pass

        building = {
            "egid": egid,
            "polygon": polygon,
            "center_e": bld_center_e,
            "center_n": bld_center_n,
            "distance_m": distance_m,
            "traufhoehe_m": row[4],
            "firsthoehe_m": row[5],
            "gebaeudehoehe_m": row[6]
        }
        buildings.append(building)

        if gebaeudeeinheit:
            gebaeudeeinheit_to_building[gebaeudeeinheit] = building

    # 3D-Layer laden (walls, roofs)
    if include_walls or include_roofs:
        gebaeudeeinheit_list = list(gebaeudeeinheit_to_building.keys())

        if include_walls and gebaeudeeinheit_list:
            cursor.execute(f"""
                SELECT gebaeudeeinheit, z_min, z_max, geometry_wkb
                FROM building_walls
                WHERE gebaeudeeinheit IN ({','.join(['?' for _ in gebaeudeeinheit_list])})
            """, gebaeudeeinheit_list)

            walls_by_ge = {}
            for wall_row in cursor.fetchall():
                wall_ge = wall_row[0]
                if wall_ge not in walls_by_ge:
                    walls_by_ge[wall_ge] = []
                geometry = None
                geometry_type = None
                if wall_row[3]:
                    try:
                        from shapely import wkb
                        geom = wkb.loads(wall_row[3])
                        geometry_type = geom.geom_type
                        # FIX 20.01.2026: OGC-Standard Format wie in /configurator/facades
                        # Polygon: [[[x,y,z], ...]] (Array of rings)
                        # MultiPolygon: [[[[x,y,z], ...]]] (Array of polygons with rings)
                        if geom.geom_type == 'Polygon':
                            geometry = [
                                [list(c) for c in ring.coords]
                                for ring in [geom.exterior] + list(geom.interiors)
                            ]
                        elif geom.geom_type == 'MultiPolygon':
                            geometry = [
                                [
                                    [list(c) for c in ring.coords]
                                    for ring in [poly.exterior] + list(poly.interiors)
                                ]
                                for poly in geom.geoms
                            ]
                    except Exception:
                        geometry = None
                walls_by_ge[wall_ge].append({
                    "z_min": wall_row[1],
                    "z_max": wall_row[2],
                    "geometry_type": geometry_type,
                    "geometry": geometry
                })

            for ge, bld in gebaeudeeinheit_to_building.items():
                bld["walls"] = walls_by_ge.get(ge, [])

        if include_roofs and gebaeudeeinheit_list:
            cursor.execute(f"""
                SELECT gebaeudeeinheit, dach_min, dach_max, geometry_wkb
                FROM building_roofs
                WHERE gebaeudeeinheit IN ({','.join(['?' for _ in gebaeudeeinheit_list])})
            """, gebaeudeeinheit_list)

            roofs_by_ge = {}
            for roof_row in cursor.fetchall():
                roof_ge = roof_row[0]
                if roof_ge not in roofs_by_ge:
                    roofs_by_ge[roof_ge] = []
                geometry = None
                geometry_type = None
                if roof_row[3]:
                    try:
                        from shapely import wkb
                        geom = wkb.loads(roof_row[3])
                        geometry_type = geom.geom_type
                        # FIX 20.01.2026: OGC-Standard Format wie in /configurator/facades
                        # Polygon: [[[x,y,z], ...]] (Array of rings)
                        # MultiPolygon: [[[[x,y,z], ...]]] (Array of polygons with rings)
                        if geom.geom_type == 'Polygon':
                            geometry = [
                                [list(c) for c in ring.coords]
                                for ring in [geom.exterior] + list(geom.interiors)
                            ]
                        elif geom.geom_type == 'MultiPolygon':
                            geometry = [
                                [
                                    [list(c) for c in ring.coords]
                                    for ring in [poly.exterior] + list(poly.interiors)
                                ]
                                for poly in geom.geoms
                            ]
                    except Exception:
                        geometry = None
                roofs_by_ge[roof_ge].append({
                    "dach_min": roof_row[1],
                    "dach_max": roof_row[2],
                    "geometry_type": geometry_type,
                    "geometry": geometry
                })

            for ge, bld in gebaeudeeinheit_to_building.items():
                bld["roofs"] = roofs_by_ge.get(ge, [])

    conn.close()

    # Nach Distanz sortieren
    buildings.sort(key=lambda x: x["distance_m"])

    # 4. Kategorisierung: Projekt-Gebäude vs. Nachbarn
    project_buildings = []
    neighbors = []

    for building in buildings:
        if building["egid"] in project_egids:
            project_buildings.append(building)
        else:
            neighbors.append(building)

    # 5. Union-Polygon berechnen
    from app.utils.polygon_utils import calculate_union_polygon, extract_polygons_from_buildings

    project_polygons = extract_polygons_from_buildings(project_buildings)
    union_polygon = calculate_union_polygon(project_polygons)

    query_time_ms = round((time.time() - start_time) * 1000, 2)

    return {
        "polygon": union_polygon,
        "project_buildings": project_buildings,
        "neighbors": neighbors,
        "center": {"e": e, "n": n},
        "radius_m": radius_m,
        "buildings_count": len(buildings),
        "project_egids": project_egids,
        "query_time_ms": query_time_ms
    }


@router.post("/projects/{project_id}/export")
async def export_project(project_id: str, format: str = "pdf"):
    """Projekt exportieren (pdf, ifc, dxf, xlsx)."""
    if format not in ["pdf", "xlsx", "ifc", "dxf"]:
        raise HTTPException(status_code=400, detail="Ungültiges Format")
    return await project_service.export_project(project_id, format)


@router.post("/extract", response_model=Dict[str, Any])
async def extract_from_document(
    file: UploadFile = File(...),
    fallback_lat: Optional[float] = Query(None, description="Fallback GPS Latitude (WGS84) - für iOS Safari"),
    fallback_lon: Optional[float] = Query(None, description="Fallback GPS Longitude (WGS84) - für iOS Safari"),
):
    """
    Intelligente Foto/Dokument-Analyse für Gerüstbau-Projekte.

    NEU 01.02.2026: Erkennt automatisch den Bildtyp und extrahiert relevante Daten:
    - Gebäudefotos: GPS aus EXIF, Dachform, Geschosse, Hindernisse, 3D-Daten Pre-Load
    - Dokumente: OCR für Ausschreibungen (Adresse, Projektname, Deadline)
    - Skizzen: Arbeitstyp erkennen, Masse extrahieren

    NEU: Fallback-GPS für iOS Safari (capture="environment" entfernt EXIF-GPS)

    Unterstützte Formate:
    - PDF-Dokumente
    - Bilder (JPG, PNG, GIF, WebP, HEIC)

    Returns:
        SmartExtractionResult mit:
        - image_type: "building_photo", "document", "sketch", etc.
        - gps_data: GPS-Koordinaten aus EXIF oder Fallback
        - building_analysis: Dachform, Geschosse, Hindernisse (bei Gebäudefotos)
        - sketch_analysis: Arbeitstyp, Masse (bei Skizzen)
        - preloaded_*: 3D-Daten aus der DB (bei GPS-Koordinaten)
        - data: OCR-Extraktion (bei Dokumenten)
    """
    # Read file content
    file_bytes = await file.read()

    if len(file_bytes) > 20 * 1024 * 1024:  # 20 MB limit (HEIC können gross sein)
        raise HTTPException(status_code=400, detail="Datei zu gross (max. 20 MB)")

    # Get original filename
    filename = file.filename or "document.pdf"

    # Fallback GPS coordinates (for iOS Safari which strips EXIF)
    fallback_gps = None
    if fallback_lat is not None and fallback_lon is not None:
        fallback_gps = (fallback_lat, fallback_lon)
        logger.info(f"[Extract] Fallback-GPS empfangen: ({fallback_lat}, {fallback_lon})")

    # Use smart photo analyzer
    from app.services.geruestbau.photo_analyzer import get_photo_analyzer
    analyzer = get_photo_analyzer()
    result = await analyzer.analyze(file_bytes, filename, fallback_gps=fallback_gps)

    return result.to_dict()


from pydantic import BaseModel

class UrlImportRequest(BaseModel):
    """Request für URL-Import"""
    url: str


@router.post("/import/url", response_model=Dict[str, Any])
async def import_from_url(request: UrlImportRequest):
    """
    Importiert Ausschreibungsdaten von einer URL (z.B. simap.ch).

    UnterstÃ¼tzte URLs:
    - simap.ch Projekt-Details

    Args:
        request: URL-Import Request mit URL

    Returns:
        OcrExtractionResult mit extrahierten Daten
    """
    if not request.url:
        raise HTTPException(status_code=400, detail="URL erforderlich")

    importer = get_url_importer()
    result = await importer.import_from_url(request.url)

    return result.to_dict()


# ============ SCAFFOLD CONFIGURATOR API ============

def _calculate_azimuth(dx: float, dy: float) -> float:
    """Berechnet Azimut in Grad (0 = Nord, 90 = Ost)."""
    azimuth = math.degrees(math.atan2(dx, dy))
    if azimuth < 0:
        azimuth += 360
    return azimuth


def _azimuth_to_direction(azimuth: float) -> str:
    """Konvertiert Azimut zu Himmelsrichtung."""
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


@router.get("/configurator/facades", response_model=Dict[str, Any], deprecated=True)
async def get_facade_data_for_configurator(
    address: str = Query(..., description="Adresse des GebÃ¤udes"),
    include_roof: bool = Query(True, description="Dachanalyse einbeziehen"),
    simplify_epsilon: Optional[float] = Query(
        None,
        description="Douglas-Peucker Toleranz in Metern (None = dynamisch basierend auf GebÃ¤udegrÃ¶sse)",
        ge=0.1,
        le=5.0
    )
):
    """
    LÃ¤dt Fassaden-Daten für den Scaffold Configurator.

    Kombiniert Daten aus:
    - geodienste.ch WFS (Polygon)
    - sonnendach.ch API (DachflÃ¤chen)
    - Lokale DB (HÃ¶hen)

    NEU 22.01.2026: Multi-Building Support via komma-getrennte Adressen.
    Bei Multi-Building wird ein Union-Polygon berechnet.

    Returns:
        ProjectInput-kompatibles JSON für ScaffoldConfigurator
    """
    # NEU 22.01.2026: Multi-Building Support
    # Prüfe ob komma-getrennte Adressen (Multi-Building)
    # Heuristik: Mindestens 2 Kommas UND Wiederholung des Ortsnamens
    addresses = []
    if address.count(',') >= 2:
        # Versuche Adressen zu splitten
        # Format: "Knospenweg 1, Bern, Knospenweg 3, Bern" oder "Strasse 1, 3001 Bern, Strasse 3, 3001 Bern"
        parts = [p.strip() for p in address.split(',')]

        # Gruppiere immer 2 Teile (Strasse, Ort)
        # Falls ungerade Anzahl, nehme alles als eine Adresse
        if len(parts) >= 4 and len(parts) % 2 == 0:
            for i in range(0, len(parts), 2):
                addr = f"{parts[i]}, {parts[i+1]}"
                addresses.append(addr)
            logger.info(f"[MULTI-BUILDING] Erkannt: {len(addresses)} Adressen aus '{address}'")
        else:
            addresses = [address]
    else:
        addresses = [address]

    # Multi-Building: SmartBuildingService mit Liste aufrufen
    if len(addresses) > 1:
        from app.services.smart_building.service import get_smart_building_service
        from app.services.building_data_stream import _calculate_object_data

        smart_service = get_smart_building_service()
        bundles = await smart_service.collect_all_data(
            address=addresses,  # Liste übergeben!
            force_refresh=False,
            include_research=True,
            include_zones_analysis=False,
            include_terrain=True,
        )

        if not bundles or len(bundles) == 0:
            raise HTTPException(status_code=404, detail="Keine GebÃ¤ude gefunden für Multi-Building Anfrage")

        # object_data mit Union-Polygon berechnen
        object_data = _calculate_object_data(bundles)
        if not object_data:
            raise HTTPException(status_code=404, detail="Konnte Union-Polygon nicht berechnen")

        # Multi-Building Response im gleichen Format wie Single-Building
        # aber mit zusätzlichem project_buildings Array
        first_bundle = bundles[0]

        # FIX 27.01.2026 11:00: Korrigierte Traufhöhe aus _calculate_object_data
        # Die Berechnung erfolgt jetzt korrekt: roof_dach_min_m - min(terrain_z_min)
        avg_traufhoehe = object_data.get("avg_traufhoehe_m")

        # Fallback nur wenn object_data keine Traufhöhe hat
        if not avg_traufhoehe:
            # Korrigierte Berechnung auch im Fallback
            corrected_traufs = []
            for b in bundles:
                if b.roof_dach_min_m and b.terrain and b.terrain.facade_z_min:
                    min_terrain = min(b.terrain.facade_z_min.values())
                    corrected_traufs.append(b.roof_dach_min_m - min_terrain)
                elif b.traufhoehe_m:
                    corrected_traufs.append(b.traufhoehe_m)
            avg_traufhoehe = sum(corrected_traufs) / len(corrected_traufs) if corrected_traufs else 0

        return {
            "address": address,
            "matched_address": ", ".join([b.address_matched or "" for b in bundles if b.address_matched]),
            "egid": "+".join([str(b.egid) for b in bundles if b.egid]),
            "lv95_e": object_data.get("center_e") or first_bundle.lv95_e,
            "lv95_n": object_data.get("center_n") or first_bundle.lv95_n,
            "polygon": object_data.get("polygon", []),
            "sides": object_data.get("sides", []),
            "selected_facades": object_data.get("facades_object", []),
            "traufhoehe_m": round(avg_traufhoehe, 2) if avg_traufhoehe else 0,
            "firsthoehe_m": max((b.firsthoehe_m or 0 for b in bundles), default=None),
            "gebaeudehoehe_m": max((b.gebaeudehoehe_m or 0 for b in bundles), default=None),
            "terrain_z_min": min((b.terrain.min_height_m if b.terrain and b.terrain.min_height_m else 999 for b in bundles), default=None),
            "roof": object_data.get("roof_object", {}),
            "zones": [],  # Multi-Building: Zonen pro Gebäude nicht kombinierbar
            "building_name": f"Multi-Building ({len(bundles)} GebÃ¤ude)",
            "complexity": "complex",
            "research_source": "multi_building",
            "building_walls": [],  # TODO: Wall-Daten für alle Gebäude sammeln
            "building_roofs": [],
            "project_buildings": object_data.get("projectBuildings", []),  # FIX 22.01.2026: CamelCase key
            "is_multi_building": True,
            "building_count": len(bundles),
        }

    # Single-Building: Original-Logik
    # 1. Geocoding - Adresse in Koordinaten umwandeln
    swisstopo = SwisstopoService()
    geocode_result = await swisstopo.geocode(address)

    if not geocode_result:
        raise HTTPException(status_code=404, detail="Adresse nicht gefunden")

    e = geocode_result.coordinates.lv95_e
    n = geocode_result.coordinates.lv95_n

    # 2. GebÃ¤udedaten vom Composite Service holen
    service = get_swissbuildings3d_service()
    building = await service.get_building_by_coordinates(
        e, n,
        include_roof_analysis=include_roof,
        simplify_epsilon=simplify_epsilon
    )

    if not building or not building.polygon:
        raise HTTPException(
            status_code=404,
            detail="Keine GebÃ¤udegeometrie gefunden. MÃ¶glicherweise unterstÃ¼tzt dieser Kanton geodienste.ch WFS nicht."
        )

    # 3. Fassaden aus Polygon-Seiten ableiten
    selected_facades = []
    default_height = building.trauf_height_m or 10.0  # Fallback 10m

    for i, side in enumerate(building.sides):
        # Berechne Richtung der Fassade
        # Handle both dict format {'x': ..., 'y': ...} and list format [x, y]
        start = side.get("start", {})
        end = side.get("end", {})

        # Extract coordinates from dict or list format
        if isinstance(start, dict):
            start_x = start.get("x", 0)
            start_y = start.get("y", 0)
        else:
            start_x = start[0] if len(start) > 0 else 0
            start_y = start[1] if len(start) > 1 else 0

        if isinstance(end, dict):
            end_x = end.get("x", 0)
            end_y = end.get("y", 0)
        else:
            end_x = end[0] if len(end) > 0 else 0
            end_y = end[1] if len(end) > 1 else 0

        dx = end_x - start_x
        dy = end_y - start_y
        length = side.get("length_m", math.sqrt(dx*dx + dy*dy))

        # Azimut der Fassade (senkrecht zur Wand, nach aussen)
        # Die Fassade zeigt nach aussen, also 90Â° zur Wandrichtung
        wall_azimuth = _calculate_azimuth(dx, dy)
        facade_azimuth = (wall_azimuth + 90) % 360  # Nach aussen zeigend
        direction = _azimuth_to_direction(facade_azimuth)

        facade = {
            "id": f"facade_{i+1}",
            "direction": direction,
            "length_m": round(length, 2),
            "height_m": round(default_height, 2),
            "slope_percent": 0.0,  # Terrain-Neigung (TODO: aus swissALTI3D)
            "start_point": [start_x, start_y],
            "end_point": [end_x, end_y],
        }
        selected_facades.append(facade)

    # 4. Dach-Daten berechnen
    roof_service = get_roof_service()
    trauf_height = building.trauf_height_m or default_height
    first_height = building.first_height_m or (default_height + 3)

    roof_data = roof_service.calculate(
        traufhoehe_m=trauf_height,
        firsthoehe_m=first_height,
        ground_area_m2=building.area_m2,
        polygon=[(p[0], p[1]) for p in building.polygon],
    )

    # 5. Zonen-Daten aus SmartBuildingService holen (für komplexe GebÃ¤ude)
    from app.services.smart_building.service import get_smart_building_service
    smart_service = get_smart_building_service()

    zones_data = []
    building_name = None
    complexity = "simple"
    research_source = "auto"
    bundle = None  # NEU 14.01.2026: Initialisierung für 3D-Geometrie

    try:
        # SmartBuildingService liefert zones, building_name, complexity, research_source
        # NEU 16.01.2026: include_terrain=True für fassaden-spezifische Höhen
        bundle = await smart_service.collect_all_data(
            address=address,
            force_refresh=False,
            include_research=True,
            include_zones_analysis=False,  # Nur bekannte Gebäude, keine neue Claude-Analyse
            include_terrain=True,  # Fassaden-Höhen aus Terrain-Sampling
        )

        if bundle.zones:
            zones_data = [
                {
                    "id": z.id,
                    "name": z.name,
                    "zone_type": z.zone_type,
                    "position": z.position,
                    "traufhoehe_m": z.traufhoehe_m,
                    "firsthoehe_m": z.firsthoehe_m,
                    "beruesten": z.beruesten,
                    "sonderkonstruktion": z.sonderkonstruktion,
                }
                for z in bundle.zones
            ]

        building_name = bundle.building_name
        complexity = bundle.complexity
        research_source = bundle.research_source

        # FIX 02.02.2026: roof_type aus 3D-Daten übernehmen (hat Priorität über Heuristik!)
        if bundle.roof_type and bundle.roof_confidence and bundle.roof_confidence >= 0.8:
            from app.services.roof import RoofType
            try:
                roof_data.roof_type = RoofType(bundle.roof_type)
                logger.info(
                    f"[ROOF-FIX] roof_type aus 3D-Daten übernommen: {bundle.roof_type} "
                    f"(confidence={bundle.roof_confidence:.2f})"
                )
            except ValueError:
                logger.warning(f"[ROOF-FIX] Unbekannter roof_type: {bundle.roof_type}, behalte Heuristik")

        # NEU 14.01.2026: 3D-Dachgeometrie aus Bundle übernehmen
        if bundle.has_roof_geometry and bundle.roof_geometry_wkb:
            from shapely import wkb

            def _wkb_to_coords(wkb_data: bytes):
                """Konvertiert WKB zu JSON-Koordinaten."""
                if not wkb_data:
                    return None
                try:
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
                except Exception:
                    return None

            roof_geometry_coords = _wkb_to_coords(bundle.roof_geometry_wkb)
        else:
            roof_geometry_coords = None

    except Exception as zone_error:
        logger.warning(f"Konnte Zonen nicht laden: {zone_error}")
        # Fallback: Keine Zonen-Daten
        roof_geometry_coords = None

    # 6. Building Walls laden (NEU 15.01.2026 - BUG-024)
    # FIX 15.01.2026: DB-Naming (building_walls), ALLE Geometrie-Daten (nicht nur erstes Polygon)
    # FIX 21.01.2026: Zuerst per gebaeudeeinheit suchen (wie Roofs)
    building_walls = []
    if building.egid:
        try:
            from app.services.layer_fetcher import get_layer_fetcher_service
            from shapely import wkb as shapely_wkb

            layer_fetcher = get_layer_fetcher_service()

            # FIX 21.01.2026: Zuerst per gebaeudeeinheit suchen (wie Roofs)
            raw_walls = []

            # gebaeudeeinheit aus buildings_3d laden (falls noch nicht vorhanden)
            wall_gebaeudeeinheit = None
            if hasattr(building, 'gebaeudeeinheit') and building.gebaeudeeinheit:
                wall_gebaeudeeinheit = building.gebaeudeeinheit
            else:
                from app.config import get_building_3d_connection
                try:
                    conn = get_building_3d_connection(read_only=True)
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT gebaeudeeinheit FROM buildings_3d WHERE egid = ?",
                        (int(building.egid),)
                    )
                    row = cursor.fetchone()
                    if row and row[0]:
                        wall_gebaeudeeinheit = row[0]
                    conn.close()
                except Exception as ge_err:
                    logger.debug(f"[BUILDING-WALLS] Konnte gebaeudeeinheit nicht laden: {ge_err}")

            if wall_gebaeudeeinheit:
                raw_walls = layer_fetcher.get_walls_by_gebaeudeeinheit(wall_gebaeudeeinheit)
                if raw_walls:
                    logger.debug(f"[BUILDING-WALLS] {len(raw_walls)} Walls per gebaeudeeinheit gefunden: {wall_gebaeudeeinheit}")
                else:
                    logger.warning(f"[BUILDING-WALLS] Keine Walls für gebaeudeeinheit {wall_gebaeudeeinheit}")
            else:
                logger.warning(f"[BUILDING-WALLS] Keine gebaeudeeinheit für EGID {building.egid} - 3D-Walls nicht verfügbar")

            for wall in raw_walls:
                wall_wkb = wall.get('geometry_wkb')
                geometry_type = None
                # FIX 19.01.2026: Umbenennung coords_3d → geometry (konsistent mit DB geometry_wkb)
                geometry = None  # Volle 3D-Koordinaten (ALLE Polygone!)

                if wall_wkb:
                    try:
                        geom = shapely_wkb.loads(wall_wkb)
                        geometry_type = geom.geom_type

                        # FIX 16.01.2026 21:30: OGC-Standard Ring-Struktur BEIBEHALTEN!
                        # MultiPolygon[Polygon[Ring[Point]]] für U-Form, Löcher, Innenhöfe
                        # Polygon: geometry[ring_index][point_index] = [E, N, Z]
                        # MultiPolygon: geometry[polygon_index][ring_index][point_index] = [E, N, Z]
                        if geom.geom_type == 'Polygon':
                            # Alle Rings: exterior + interiors (Löcher)
                            geometry = [
                                [list(c) for c in ring.coords]
                                for ring in [geom.exterior] + list(geom.interiors)
                            ]

                        elif geom.geom_type == 'MultiPolygon':
                            # Jedes Polygon mit allen seinen Rings
                            geometry = [
                                [
                                    [list(c) for c in ring.coords]
                                    for ring in [poly.exterior] + list(poly.interiors)
                                ]
                                for poly in geom.geoms
                            ]

                        elif geom.geom_type == 'LineString':
                            geometry = [[list(c) for c in geom.coords]]

                    except Exception as wkb_err:
                        logger.debug(f"WKB-Parsing für Wall fehlgeschlagen: {wkb_err}")

                # DB-Feldnamen exakt übernehmen
                building_walls.append({
                    "gebaeudeeinheit": wall.get('gebaeudeeinheit', ''),
                    "egid": wall.get('egid'),
                    "z_min": wall.get('z_min'),  # Terrain-Höhe (m ü.M.)
                    "z_max": wall.get('z_max'),  # Trauf-Höhe (m ü.M.)
                    "geometry_type": geometry_type,
                    "geometry": geometry,  # Volle 3D-Geometrie
                })

            # DEBUG 21.01.2026: Detailliertes Logging für 3D-Walls-Problem
            walls_with_geometry = [w for w in building_walls if w.get('geometry')]
            logger.info(f"[BUILDING-WALLS] {len(building_walls)} walls für EGID {building.egid} geladen, davon {len(walls_with_geometry)} mit geometry")
            if walls_with_geometry:
                first_wall = walls_with_geometry[0]
                logger.info(f"[BUILDING-WALLS] Erste Wall: geometry_type={first_wall.get('geometry_type')}, geometry_len={len(first_wall['geometry']) if first_wall.get('geometry') else 0}")
            else:
                logger.warning(f"[BUILDING-WALLS] KEINE Wall hat geometry! raw_walls: {len(raw_walls)}")
        except Exception as wall_err:
            logger.warning(f"Building walls konnten nicht geladen werden: {wall_err}")

    # 7. Building Roofs laden (NEU 15.01.2026 23:30 - analog zu building_walls)
    # Analog zu building_walls: DB-Naming, volle 3D-Geometrie
    building_roofs = []
    if building.egid:
        try:
            from app.services.layer_fetcher import get_layer_fetcher_service
            from app.services.roof_3d_service import get_roof_3d_service
            from shapely import wkb as shapely_wkb

            layer_fetcher = get_layer_fetcher_service()
            roof_service = get_roof_3d_service()

            # FIX 21.01.2026: Zuerst per gebaeudeeinheit suchen (wie /3d-layers API)
            # Die building_roofs Tabelle hat oft kein EGID, nur gebaeudeeinheit!
            raw_roofs = []

            # FIX 21.01.2026: gebaeudeeinheit aus buildings_3d laden (building-Objekt hat es nicht!)
            gebaeudeeinheit = None
            if hasattr(building, 'gebaeudeeinheit') and building.gebaeudeeinheit:
                gebaeudeeinheit = building.gebaeudeeinheit
            else:
                # Aus DB laden per EGID
                from app.config import get_building_3d_connection
                try:
                    conn = get_building_3d_connection(read_only=True)
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT gebaeudeeinheit FROM buildings_3d WHERE egid = ?",
                        (int(building.egid),)
                    )
                    row = cursor.fetchone()
                    if row and row[0]:
                        gebaeudeeinheit = row[0]
                        logger.debug(f"[BUILDING-ROOFS] gebaeudeeinheit aus DB geladen: {gebaeudeeinheit}")
                    conn.close()
                except Exception as ge_err:
                    logger.warning(f"[BUILDING-ROOFS] Konnte gebaeudeeinheit nicht laden: {ge_err}")

            if gebaeudeeinheit:
                roof_by_geb = roof_service.get_by_gebaeudeeinheit(gebaeudeeinheit)
                if roof_by_geb and roof_by_geb.get('geometry_wkb'):
                    raw_roofs = [roof_by_geb]
                    logger.debug(f"[BUILDING-ROOFS] Dach per gebaeudeeinheit gefunden: {gebaeudeeinheit}")
                else:
                    logger.warning(f"[BUILDING-ROOFS] Keine Roofs für gebaeudeeinheit {gebaeudeeinheit}")
            else:
                logger.warning(f"[BUILDING-ROOFS] Keine gebaeudeeinheit für EGID {building.egid} - 3D-Roofs nicht verfügbar")

            for roof in raw_roofs:
                roof_wkb = roof.get('geometry_wkb')
                geometry_type = None
                # FIX 19.01.2026: Umbenennung coords_3d → geometry (konsistent mit DB geometry_wkb)
                geometry = None  # Volle 3D-Koordinaten (ALLE Polygone!)

                if roof_wkb:
                    try:
                        geom = shapely_wkb.loads(roof_wkb)
                        geometry_type = geom.geom_type

                        # FIX 16.01.2026 21:30: OGC-Standard Ring-Struktur BEIBEHALTEN!
                        # MultiPolygon[Polygon[Ring[Point]]] für U-Form, Löcher, Innenhöfe
                        # Polygon: geometry[ring_index][point_index] = [E, N, Z]
                        # MultiPolygon: geometry[polygon_index][ring_index][point_index] = [E, N, Z]
                        if geom.geom_type == 'Polygon':
                            # Alle Rings: exterior + interiors (Löcher)
                            geometry = [
                                [list(c) for c in ring.coords]
                                for ring in [geom.exterior] + list(geom.interiors)
                            ]

                        elif geom.geom_type == 'MultiPolygon':
                            # Jedes Polygon mit allen seinen Rings
                            geometry = [
                                [
                                    [list(c) for c in ring.coords]
                                    for ring in [poly.exterior] + list(poly.interiors)
                                ]
                                for poly in geom.geoms
                            ]

                        elif geom.geom_type == 'LineString':
                            geometry = [[list(c) for c in geom.coords]]

                    except Exception as wkb_err:
                        logger.debug(f"WKB-Parsing für Roof fehlgeschlagen: {wkb_err}")

                # DB-Feldnamen exakt übernehmen
                building_roofs.append({
                    "gebaeudeeinheit": roof.get('gebaeudeeinheit', ''),
                    "egid": roof.get('egid'),
                    "dach_min": roof.get('dach_min'),  # Trauf-Höhe (m ü.M.)
                    "dach_max": roof.get('dach_max'),  # First-Höhe (m ü.M.)
                    "roof_form": roof.get('roof_form'),
                    "roof_angle_deg": roof.get('roof_angle_deg'),
                    "roof_orientation": roof.get('roof_orientation'),
                    "geometry_type": geometry_type,
                    "geometry": geometry,  # Volle 3D-Geometrie
                })

            logger.info(f"[BUILDING-ROOFS] {len(building_roofs)} roofs für EGID {building.egid} geladen")
        except Exception as roof_err:
            logger.warning(f"Building roofs konnten nicht geladen werden: {roof_err}")

    # FIX 16.01.2026 15:30: Korrekte Traufhöhen-Berechnung bei Hanglagen
    # Das alte traufhoehe_m aus swissBUILDINGS3D verwendet GELAENDEPUNKT (ein einzelner Punkt),
    # der bei Hanglagen NICHT das niedrigste Terrain ist.
    #
    # Korrekte Berechnung: dach_min (m ü.M.) - min(facade_z_min) (niedrigstes Terrain)
    #
    # Beispiel Knospenweg 9:
    #   ALT:  traufhoehe_m = 562.94 - 557.45 = 5.49m (GELAENDEPUNKT)
    #   NEU:  traufhoehe_m = 562.94 - 555.80 = 7.14m (min(facade_z_min))
    #
    # Die korrigierten Werte werden im roof-Objekt als 'traufhoehe_m' und 'firsthoehe_m' geliefert.
    # Das Frontend verwendet diese für die konsistente 3D-Darstellung.
    if bundle and bundle.roof_dach_min_m and bundle.terrain and bundle.terrain.facade_z_min:
        min_terrain = min(bundle.terrain.facade_z_min.values())
        corrected_trauf = round(bundle.roof_dach_min_m - min_terrain, 2)

        # Auch firsthoehe korrigieren wenn verfügbar
        corrected_first = None
        if bundle.roof_dach_max_m:
            corrected_first = round(bundle.roof_dach_max_m - min_terrain, 2)

        # Log zur Diagnose
        logger.info(
            f"[HEIGHT-FIX] Traufhöhe korrigiert: {trauf_height:.2f}m → {corrected_trauf:.2f}m "
            f"(dach_min={bundle.roof_dach_min_m:.2f}, min_terrain={min_terrain:.2f})"
        )

        # Überschreibe die alten Werte
        trauf_height = corrected_trauf
        if corrected_first:
            first_height = corrected_first
            logger.info(f"[HEIGHT-FIX] Firsthöhe korrigiert: → {corrected_first:.2f}m")

        # FIX 24.01.2026: selected_facades wurden VOR der Korrektur erstellt!
        # Die Fassaden-Höhen müssen ebenfalls aktualisiert werden.
        for facade in selected_facades:
            facade["height_m"] = round(trauf_height, 2)
        logger.info(f"[HEIGHT-FIX] {len(selected_facades)} Fassaden-Höhen aktualisiert auf {trauf_height:.2f}m")

    # 8. Response im ProjectInput-Format zusammenstellen
    project_id = str(uuid.uuid4())[:8]

    response = {
        "project_id": project_id,
        "building": {
            "egid": building.egid or "",
            "address": geocode_result.matched_address or address,
            "name": building_name or (geocode_result.matched_address.split(",")[0] if geocode_result.matched_address else address),
            "polygon": [(p[0], p[1]) for p in building.polygon],
            "trauf_height_m": trauf_height,
            "first_height_m": first_height,
            "center_e": e,
            "center_n": n,
        },
        "selected_facades": selected_facades,
        "roof": {
            # FIX 16.01.2026 17:00: traufhoehe_m/firsthoehe_m aus roof_data.to_dict() ENTFERNT!
            # Stattdessen nur Rohdaten liefern - Frontend berechnet selbst.
            **{k: v for k, v in roof_data.to_dict().items() if k not in ('traufhoehe_m', 'firsthoehe_m')},
            # NEU 14.01.2026: Echte 3D-Dachgeometrie aus swissBUILDINGS3D
            "roof_geometry_coords": roof_geometry_coords,
            "has_roof_geometry": roof_geometry_coords is not None and len(roof_geometry_coords) > 0,
            # Rohdaten für Höhenberechnung (Frontend: trauf = dach_min - terrain_z_min)
            "roof_dach_min_m": bundle.roof_dach_min_m if bundle else None,
            "roof_dach_max_m": bundle.roof_dach_max_m if bundle else None,
            "terrain_z_min": min(bundle.terrain.facade_z_min.values()) if bundle and bundle.terrain and bundle.terrain.facade_z_min else None,
        },
        # Zonen-Daten für komplexe GebÃ¤ude (NEU 05.01.2026)
        "zones": zones_data,
        "building_name": building_name,
        "complexity": complexity,
        "research_source": research_source,
        # NEU 15.01.2026 BUG-024: Building Walls direkt aus DB (DB-Naming!)
        # FIX: Volle 3D-Geometrie, ALLE Polygone (nicht nur erstes)
        "building_walls": building_walls,
        # NEU 15.01.2026 23:30: Building Roofs direkt aus DB (DB-Naming!)
        # Analog zu building_walls: volle 3D-Geometrie für Dach-Rendering
        "building_roofs": building_roofs,
        # NEU 16.01.2026 21:45: Fassaden-spezifische Höhen aus Terrain-Sampling
        # Siehe docs/architecture/3D_LAYER_USAGE_SCAFFOLDING.md
        "facade_z_min": bundle.terrain.facade_z_min if bundle and bundle.terrain else None,
        "facade_z_max": bundle.terrain.facade_z_max if bundle and bundle.terrain else None,
        # FIX 16.01.2026 17:00: traufhoehe_m/firsthoehe_m ENTFERNT vom Top-Level!
        # Korrekte Höhen aus Rohdaten berechnen: roof_dach_min_m - terrain_z_min
        # Die Rohdaten sind: roof.roof_dach_min_m, roof.roof_dach_max_m, roof.terrain_z_min
        "sides": [
            {
                "direction": s.get("direction"),
                "length_m": s.get("length_m"),
                "start": s.get("start"),
                "end": s.get("end"),
            }
            for s in building.sides
        ] if building.sides else [],
        "metadata": {
            "source": "swissBUILDINGS3D_composite",
            "polygon_points": len(building.polygon),
            "facade_count": len(selected_facades),
            "perimeter_m": building.perimeter_m,
            "area_m2": building.area_m2,
            "roof_type": roof_data.roof_type.value,
            "roof_surfaces_count": len(building.roof_surfaces) if building.roof_surfaces else 0,
            "height_source": building.height_source,
            "confidence": building.confidence,
            "zones_count": len(zones_data),
            "research_source": research_source,
            "building_walls_count": len(building_walls),  # NEU 15.01.2026 BUG-024
            "building_roofs_count": len(building_roofs),  # NEU 15.01.2026 23:30
        }
    }

    return response


@router.get("/configurator/address-search")
async def search_addresses(q: str = Query(..., min_length=3)):
    """
    Autocomplete für Adresssuche.

    Verwendet swisstopo SearchServer API.
    """
    swisstopo = SwisstopoService()
    results = await swisstopo.search_addresses(q, limit=10)
    return {
        "suggestions": [
            {
                "label": r.label,
                "detail": r.detail,
            }
            for r in results
        ]
    }


# ============ NEIGHBORS API ============
# FIX 19.01.2026 23:30: Direkter Service-Aufruf statt GeodatenClient (Monolith!)

@router.get("/building/{egid}/neighbors", response_model=Dict[str, Any],
            deprecated=True,
            summary="[DEPRECATED] Nutze /api/v1/building/neighbors/{egid} stattdessen")
async def get_building_neighbors(
    egid: str,
    radius_m: float = Query(10.0, ge=0, le=100, description="Suchradius in Metern (0=angrenzend, max 100m)"),
    include_polygons: bool = Query(True, description="Polygone der Nachbarn mitliefern")
):
    """
    **DEPRECATED:** Nutze `/api/v1/building/neighbors/{egid}` stattdessen!

    FIX 19.01.2026: Direkter Service-Aufruf statt GeodatenClient.

    Args:
        egid: EGID des Zielgebäudes
        radius_m: Suchradius (0=nur direkt angrenzend, 5=nah, 10=Kontext)
        include_polygons: Polygone für 3D-View mitliefern

    Returns:
        - target: Zielgebäude mit Polygon
        - neighbors: Liste der Nachbarn mit Distanz und Richtung
        - blocked_sides: Liste der blockierten Fassadenrichtungen
    """
    from app.services.neighbors_service import get_neighbors_service

    service = get_neighbors_service()
    result = service.get_neighbors(
        egid=egid,
        radius_m=radius_m,
        include_polygons=include_polygons
    )

    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Gebäude mit EGID {egid} nicht gefunden. "
                   "Bitte zuerst über SmartBuildingService laden."
        )

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


# NEU 18.01.2026: Koordinaten-basierte Nachbar-Suche
# FIX 19.01.2026: Direkte DuckDB-Abfrage (Monolith-Architektur)
@router.get("/neighbors/by-coordinates", response_model=Dict[str, Any],
            deprecated=True,
            summary="[DEPRECATED] Nutze /api/v1/building/area stattdessen")
async def get_neighbors_by_coordinates(
    e: float = Query(..., description="LV95 Easting (z.B. 2596299.9)"),
    n: float = Query(..., description="LV95 Northing (z.B. 1199805.0)"),
    radius_m: float = Query(10.0, ge=1, le=100, description="Suchradius in Metern"),
    include_polygons: bool = Query(True, description="Polygone mitliefern")
):
    """
    **DEPRECATED:** Nutze `/api/v1/building/area` stattdessen!

    Dieser Endpunkt ist für Rückwärtskompatibilität vorhanden.

    FIX 19.01.2026: Direkte DuckDB-Abfrage statt GeodatenClient (Monolith!)

    Args:
        e: LV95 Easting (Ost-Koordinate)
        n: LV95 Northing (Nord-Koordinate)
        radius_m: Suchradius (1-100m)
        include_polygons: Polygone für 3D-View mitliefern

    Returns:
        - center: Suchzentrum
        - buildings: Liste aller Gebäude im Radius
        - query_time_ms: Abfragezeit
    """
    import time
    import math
    import json
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
        SELECT egid, ST_AsGeoJSON(geom) as polygon, center_e, center_n,
               traufhoehe_m, firsthoehe_m, gebaeudehoehe_m
        FROM buildings_3d
        WHERE center_e BETWEEN ? AND ?
          AND center_n BETWEEN ? AND ?
    """, (
        e - radius_m, e + radius_m,
        n - radius_m, n + radius_m
    ))

    rows = cursor.fetchall()
    conn.close()

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

        # Polygon parsen (ST_AsGeoJSON liefert GeoJSON-Format)
        polygon_data = row[1]
        polygon = None
        if include_polygons and polygon_data:
            try:
                geojson = json.loads(polygon_data) if isinstance(polygon_data, str) else polygon_data
                # ST_AsGeoJSON: {"type": "Polygon", "coordinates": [[[x,y], ...]]}
                if isinstance(geojson, dict) and 'coordinates' in geojson:
                    polygon = geojson['coordinates'][0]
                else:
                    polygon = geojson  # Fallback
            except (json.JSONDecodeError, TypeError, KeyError, IndexError):
                pass

        buildings.append({
            "egid": egid,
            "center_e": center_e,
            "center_n": center_n,
            "distance_m": distance_m,
            "traufhoehe_m": row[4],
            "firsthoehe_m": row[5],
            "gebaeudehoehe_m": row[6],
            "polygon": polygon
        })

    # Nach Distanz sortieren
    buildings.sort(key=lambda x: x["distance_m"])

    query_time_ms = round((time.time() - start_time) * 1000, 2)

    return {
        "center": {"e": e, "n": n},
        "radius_m": radius_m,
        "buildings_count": len(buildings),
        "buildings": buildings,
        "query_time_ms": query_time_ms
    }


# ============ ADDRESS RANGE API ============

@router.get("/address/resolve", response_model=Dict[str, Any])
async def resolve_address_range(
    address: str = Query(..., description="Adresse mit Bereich, z.B. 'Knospenweg 2-10, Bern'")
):
    """
    LÃ¶st eine Adresse mit Hausnummern-Bereich zu einzelnen EGIDs auf.

    UnterstÃ¼tzte Formate:
    - Range: "Knospenweg 2-10, Bern" â†’ [2, 4, 6, 8, 10]
    - Explizit: "Kramgasse 27/29, Bern" â†’ [27, 29]
    - Liste: "Hauptstrasse 1, 3, 5, ZÃ¼rich" â†’ [1, 3, 5]

    Returns:
        - parsed: Parsing-Ergebnis (Strasse, Nummern, Typ)
        - buildings: Liste der gefundenen GebÃ¤ude mit EGID
        - errors: Nicht gefundene Adressen

    Beispiel Response:
    ```json
    {
        "parsed": {
            "street": "Knospenweg",
            "city": "Bern",
            "numbers": ["2", "4", "6", "8", "10"],
            "range_type": "range"
        },
        "buildings": [
            {"address": "Knospenweg 2, Bern", "egid": "123456", ...},
            {"address": "Knospenweg 4, Bern", "egid": "123457", ...}
        ],
        "building_count": 5,
        "errors": [],
        "error_count": 0
    }
    ```
    """
    parser = get_address_parser()
    result = await parser.resolve_to_egids(address)
    return result


@router.get("/address/parse", response_model=Dict[str, Any])
async def parse_address_only(
    address: str = Query(..., description="Adresse zum Parsen")
):
    """
    Parst eine Adresse ohne Geocoding (nur Syntax-Analyse).

    NÃ¼tzlich zum Testen des Parsers oder für Vorschau.

    Returns:
        - street: Erkannte Strasse
        - city: Erkannter Ort
        - numbers: Liste der Hausnummern
        - range_type: single, range, oder explicit
        - full_addresses: Generierte vollstÃ¤ndige Adressen
    """
    parser = get_address_parser()
    parsed = parser.parse(address)

    return {
        "street": parsed.street,
        "city": parsed.city,
        "postal_code": parsed.postal_code,
        "numbers": parsed.numbers,
        "range_type": parsed.range_type.value,
        "raw_number_part": parsed.raw_number_part,
        "full_addresses": parsed.get_full_addresses(),
        "original_input": parsed.original_input,
    }


# ============ PARZELLEN API ============

@router.get("/parzelle/at", response_model=Dict[str, Any])
async def get_parzelle_at_coordinates(
    e: float = Query(..., description="LV95 Ost-Koordinate"),
    n: float = Query(..., description="LV95 Nord-Koordinate"),
    include_geometry: bool = Query(True, description="Polygon-Geometrie einbeziehen")
):
    """
    Findet die Parzelle an den gegebenen LV95-Koordinaten.

    Verwendet die swisstopo Identify-API für die amtliche Vermessung.

    Returns:
        - egrid: Eidg. GrundstÃ¼cksidentifikator
        - number: Parzellennummer
        - canton: Kanton
        - polygon: Parzellengrenze (optional)
        - area_m2: FlÃ¤che
        - has_building: Ob ein GebÃ¤ude auf der Parzelle existiert

    Anwendungsfall Neubau:
        Wenn kein GebÃ¤ude auf der Parzelle existiert, kann das
        Parzellen-Polygon als Baufeld-Grenze verwendet werden.
    """
    parzellen_service = get_parzellen_service()
    parzelle = await parzellen_service.get_parzelle_at_coordinates(
        e=e,
        n=n,
        include_geometry=include_geometry
    )

    if not parzelle:
        raise HTTPException(
            status_code=404,
            detail=f"Keine Parzelle bei E={e}, N={n} gefunden"
        )

    return parzelle.to_dict()


@router.get("/parzelle/by-egrid/{egrid}", response_model=Dict[str, Any])
async def get_parzelle_by_egrid(egrid: str):
    """
    Findet eine Parzelle anhand der EGRID.

    Args:
        egrid: Eidg. GrundstÃ¼cksidentifikator (z.B. "CH280652308630")

    Returns:
        Parzellen-Daten mit Polygon und Metadaten
    """
    parzellen_service = get_parzellen_service()
    parzelle = await parzellen_service.get_parzelle_by_egrid(egrid)

    if not parzelle:
        raise HTTPException(
            status_code=404,
            detail=f"Keine Parzelle mit EGRID {egrid} gefunden"
        )

    return parzelle.to_dict()


@router.get("/parzelle/for-address", response_model=Dict[str, Any])
async def get_parzelle_for_address(
    address: str = Query(..., description="Adresse für Parzellen-Suche")
):
    """
    Findet die Parzelle für eine Adresse.

    Kombination aus Geocoding + Parzellen-Abfrage.

    Returns:
        - geocoding: Adress-Match und Koordinaten
        - parzelle: Parzellen-Daten (EGRID, Polygon, etc.)
        - building: GebÃ¤ude-Infos falls vorhanden
    """
    # 1. Geocoding
    swisstopo = SwisstopoService()
    geocode_result = await swisstopo.geocode(address)

    if not geocode_result:
        raise HTTPException(
            status_code=404,
            detail=f"Adresse nicht gefunden: {address}"
        )

    # 2. Parzelle an Koordinaten
    parzellen_service = get_parzellen_service()
    parzelle = await parzellen_service.get_parzelle_at_coordinates(
        e=geocode_result.coordinates.lv95_e,
        n=geocode_result.coordinates.lv95_n,
        include_geometry=True
    )

    # 3. GebÃ¤ude prÃ¼fen
    has_building = True
    if parzelle:
        has_building = await parzellen_service.check_building_on_parcel(parzelle)

    return {
        "geocoding": {
            "input": address,
            "matched_address": geocode_result.matched_address,
            "egid": geocode_result.egid,
            "coordinates": {
                "lv95_e": geocode_result.coordinates.lv95_e,
                "lv95_n": geocode_result.coordinates.lv95_n,
            }
        },
        "parzelle": parzelle.to_dict() if parzelle else None,
        "has_building": has_building,
        "neubau_possible": not has_building,  # Neubau-Support Flag
    }


# ============ PROJECT CONTEXT STREAMING API ============

from ..services.project_context_stream import get_project_context_stream_service


@router.get("/projects/{project_id}/context/stream")
async def stream_project_context(
    project_id: str,
    max_radius_m: float = Query(default=NEIGHBOR_SEARCH_RADIUS_M, ge=0, le=500, description="Suchradius für Nachbarn (Default aus Config)"),
    include_blocked_facades: bool = Query(True, description="Blockierte Fassaden berechnen"),
    include_neighbors: bool = Query(True, description="Nachbarn laden")
):
    """
    Streamt Projekt-Kontext via Server-Sent Events (SSE).

    Progressive Datenlieferung:
    1. centroid - Projekt-Mittelpunkt (~10ms)
    2. project_buildings - Projekt-GebÃ¤ude mit Polygonen (~20ms)
    3. blocked_facades - Blockierte Fassaden pro GebÃ¤ude (~50ms)
    4. neighbors - Nachbarn in Schichten (20m, 50m, 100m)
    5. complete - Abschluss-Signal

    WICHTIG für Multi-Building Projekte:
    - Centroid wird aus allen Projekt-GebÃ¤uden berechnet
    - blocked_facades exkludiert Projekt-GebÃ¤ude (nur externe blockieren)

    Beispiel mit EventSource:
    ```javascript
    const es = new EventSource('/api/v1/geruestbau/projects/abc123/context/stream');
    es.addEventListener('centroid', (e) => console.log('Centroid:', JSON.parse(e.data)));
    es.addEventListener('blocked_facades', (e) => markBlockedFacades(JSON.parse(e.data)));
    es.addEventListener('complete', (e) => es.close());
    ```

    Returns:
        text/event-stream mit SSE Events
    """
    # Projekt laden
    project = await project_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden")

    # DEBUG 10.01.2026 21:10 - Was enthält das Projekt?
    print(f"[SSE] Project {project_id}: egid={project.egid}, buildings={[b.egid for b in project.buildings] if project.buildings else []}")

    # EGIDs sammeln (aus buildings Liste oder einzelnes egid)
    project_egids = []

    if project.buildings:
        project_egids = [b.egid for b in project.buildings if b.egid]

    # FIX 21.01.2026: Multi-EGID Format (z.B. "1243790+1243792") aufteilen
    # NICHT als einzelne EGID hinzufügen - das verursacht int() Fehler!
    if project.egid:
        if '+' in project.egid:
            # Multi-EGID: Aufteilen und einzeln hinzufügen
            for single_egid in project.egid.split('+'):
                if single_egid and single_egid not in project_egids:
                    project_egids.append(single_egid)
        elif project.egid not in project_egids:
            project_egids.append(project.egid)

    print(f"[SSE] Final project_egids for stream: {project_egids}")

    if not project_egids:
        raise HTTPException(
            status_code=400,
            detail="Projekt hat keine GebÃ¤ude (keine EGIDs definiert)"
        )

    # Streaming Service
    stream_service = get_project_context_stream_service()

    async def event_generator():
        """Generator für SSE Events."""
        import json
        async for event in stream_service.stream_context(
            project_egids=project_egids,
            max_radius_m=max_radius_m,
            include_blocked_facades=include_blocked_facades,
            include_neighbors=include_neighbors
        ):
            # FIX 10.01.2026 20:50 - data muss als JSON-String übergeben werden
            yield {
                "event": event.event,
                "data": json.dumps(event.data)
            }

    return EventSourceResponse(event_generator())


@router.get("/building/{egid}/blocked-facades", response_model=Dict[str, Any], deprecated=True)
async def get_blocked_facades(
    egid: str,
    exclude_egids: str = Query(None, description="Komma-separierte EGIDs die nicht als Blocker gelten"),
    threshold_m: float = Query(2.0, ge=0.5, le=5.0, description="Distanz-Schwellenwert in Metern")
):
    """
    DEPRECATED 15.01.2026: Verwende Frontend-Berechnung mit Nachbar-Polygonen stattdessen.
    Siehe BUG-024 und TODO_CURRENT.md für Details.

    Berechnet blockierte Fassaden für ein GebÃ¤ude.

    Eine Fassade gilt als blockiert wenn ein externes GebÃ¤ude
    nÃ¤her als threshold_m ist (Standard: 2m = GerÃ¼stbreite).

    Args:
        egid: EGID des zu analysierenden GebÃ¤udes
        exclude_egids: Komma-separierte EGIDs die ignoriert werden (z.B. andere Projekt-GebÃ¤ude)
        threshold_m: Schwellenwert für Blockierung

    Returns:
        - egid: Analysiertes GebÃ¤ude
        - blocked_indices: Liste der blockierten Fassaden-Indizes (0-basiert)
        - total_facades: Gesamtzahl Fassaden
        - free_facades: Anzahl freier Fassaden
        - blockers: Details zu jedem blockierenden GebÃ¤ude

    Beispiel Response:
    ```json
    {
        "egid": "123456",
        "blocked_indices": [1, 3],
        "total_facades": 4,
        "free_facades": 2,
        "blockers": [
            {"facade_index": 1, "egid": "123457", "distance_m": 0.8, "direction": "E"},
            {"facade_index": 3, "egid": "123458", "distance_m": 1.2, "direction": "W"}
        ]
    }
    ```
    """
    from ..services.blocked_facades_service import get_blocked_facades_service

    # exclude_egids parsen
    exclude_set = set()
    if exclude_egids:
        exclude_set = set(e.strip() for e in exclude_egids.split(",") if e.strip())

    blocked_service = get_blocked_facades_service()
    result = blocked_service.calculate_blocked_facades(
        egid=egid,
        exclude_egids=exclude_set,
        threshold_m=threshold_m
    )

    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"GebÃ¤ude {egid} nicht in building_3d.db gefunden. "
                   "Bitte zuerst Ã¼ber SmartBuildingService laden."
        )

    # NEU 22.01.2026: blocked_segments für partielle Blockierung
    return {
        "egid": result.egid,
        "blocked_indices": result.blocked_indices,
        "total_facades": result.total_facades,
        "free_facades": result.free_facades,
        "query_time_ms": result.query_time_ms,
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


# ============ BUILDING DATA STREAMING API ============

from ..services.building_data_stream import get_building_data_stream_service


@router.get("/building/data/stream")
async def stream_building_data(
    address: str = Query(..., description="Adresse des GebÃ¤udes"),
    include_research: bool = Query(True, description="GebÃ¤udename-Recherche"),
    include_zones: bool = Query(True, description="Zonen-Analyse"),
    include_terrain: bool = Query(True, description="Terrain-Daten"),
    force_refresh: bool = Query(False, description="Cache ignorieren")
):
    """
    Streamt GebÃ¤udedaten via Server-Sent Events (SSE).

    Wird verwendet bei Projekt-Erstellung für progressives Feedback.

    Progressive Datenlieferung:
    1. geocoding - Adress-Match, Koordinaten, EGID (~50ms)
    2. gwr - GWR-Daten (Geschosse, Kategorie) (~100ms)
    3. polygon - GebÃ¤ude-Polygon (~200ms oder ~5s bei Tile-Download)
    4. heights - HÃ¶hendaten (~50ms)
    5. terrain - Terrain-HÃ¶he, Hanglage (~200ms)
    6. zones - Zonen-Analyse (~500ms)
    7. research - GebÃ¤udename (~1s, optional)
    8. complete - VollstÃ¤ndiges Bundle

    Bei Tile-Download wird zusÃ¤tzlich "polygon_progress" gesendet:
    ```json
    {"status": "downloading", "message": "Lade GebÃ¤udedaten..."}
    ```

    Beispiel mit EventSource:
    ```javascript
    const es = new EventSource('/api/v1/geruestbau/building/data/stream?address=Kramgasse+10,+Bern');

    es.addEventListener('geocoding', (e) => {
        const data = JSON.parse(e.data);
        setCoordinates(data.coordinates);
    });

    es.addEventListener('polygon', (e) => {
        const data = JSON.parse(e.data);
        renderPolygon(data.polygon);
    });

    es.addEventListener('complete', (e) => {
        const data = JSON.parse(e.data);
        setFullBundle(data.bundle);
        es.close();
    });
    ```

    Returns:
        text/event-stream mit SSE Events
    """
    stream_service = get_building_data_stream_service()

    async def event_generator():
        """Generator für SSE Events."""
        import json
        async for event in stream_service.stream_building_data(
            address=address,
            include_research=include_research,
            include_zones=include_zones,
            include_terrain=include_terrain,
            force_refresh=force_refresh
        ):
            # WICHTIG: data muss als JSON-String Ã¼bergeben werden, nicht als Dict!
            # EventSourceResponse konvertiert Dicts mit str() statt json.dumps()
            yield {
                "event": event.event,
                "data": json.dumps(event.data, ensure_ascii=False)
            }

    return EventSourceResponse(event_generator())
