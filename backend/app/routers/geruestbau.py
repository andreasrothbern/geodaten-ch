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
    Project, ProjectCreate, ProjectUpdate, ProjectStatus, ProjectWithGeodata,
    PhotoAnalysis, ScaffoldConfig
)
from ..services.geruestbau.project_service import ProjectService
from ..services.swissbuildings3d_service import get_swissbuildings3d_service
from ..services.swisstopo import SwisstopoService
from ..services.roof import get_roof_service
from ..services.address_parser import get_address_parser
from ..services.parzellen_service import get_parzellen_service
from ..services.neighbors_service import get_neighbors_service

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


@router.get("/projects/{project_id}", response_model=ProjectWithGeodata)
async def get_project(project_id: str):
    """Projekt-Details mit Geodaten aus smart_building_cache abrufen."""
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


@router.post("/projects/{project_id}/enrich", response_model=ProjectWithGeodata)
async def enrich_project(project_id: str):
    """Projekt mit Geodaten anreichern (GWR, HÃ¶hen, Polygon)."""
    project = await project_service.enrich_with_geodata(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden")
    return project


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


@router.post("/projects/{project_id}/export")
async def export_project(project_id: str, format: str = "pdf"):
    """Projekt exportieren (pdf, ifc, dxf, xlsx)."""
    if format not in ["pdf", "xlsx", "ifc", "dxf"]:
        raise HTTPException(status_code=400, detail="UngÃ¼ltiges Format")
    return await project_service.export_project(project_id, format)


@router.post("/extract", response_model=Dict[str, Any])
async def extract_from_document(file: UploadFile = File(...)):
    """
    Extrahiert Projektdaten aus einer Ausschreibung (PDF oder Foto).

    Verwendet Claude Vision API für OCR und Datenextraktion.

    UnterstÃ¼tzte Formate:
    - PDF-Dokumente
    - Bilder (JPG, PNG, GIF, WebP)

    Returns:
        OcrExtractionResult mit extrahierten Daten
    """
    # Read file content
    file_bytes = await file.read()

    if len(file_bytes) > 10 * 1024 * 1024:  # 10 MB limit
        raise HTTPException(status_code=400, detail="Datei zu gross (max. 10 MB)")

    # Get original filename
    filename = file.filename or "document.pdf"

    # Extract data
    extractor = get_extractor()
    result = await extractor.extract_from_file(file_bytes, filename)

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


@router.get("/configurator/facades", response_model=Dict[str, Any])
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

    Returns:
        ProjectInput-kompatibles JSON für ScaffoldConfigurator
    """
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

    try:
        # SmartBuildingService liefert zones, building_name, complexity, research_source
        bundle = await smart_service.collect_all_data(
            address=address,
            force_refresh=False,
            include_research=True,
            include_zones_analysis=False,  # Nur bekannte GebÃ¤ude, keine neue Claude-Analyse
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

    except Exception as zone_error:
        logger.warning(f"Konnte Zonen nicht laden: {zone_error}")
        # Fallback: Keine Zonen-Daten

    # 6. Response im ProjectInput-Format zusammenstellen
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
        "roof": roof_data.to_dict(),
        # Zonen-Daten für komplexe GebÃ¤ude (NEU 05.01.2026)
        "zones": zones_data,
        "building_name": building_name,
        "complexity": complexity,
        "research_source": research_source,
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

@router.get("/building/{egid}/neighbors", response_model=Dict[str, Any])
async def get_building_neighbors(
    egid: str,
    radius_m: float = Query(10.0, ge=0, le=100, description="Suchradius in Metern (0=angrenzend, max 100m)"),
    include_polygons: bool = Query(True, description="Polygone der Nachbarn mitliefern")
):
    """
    Findet alle NachbargebÃ¤ude im Umkreis.

    FÃ¼r GerÃ¼stbau: Erkennt angrenzende GebÃ¤ude die Fassaden blockieren.
    Bei ReihenhÃ¤usern (z.B. Knospenweg 2,4,6,8,10) wird erkannt,
    dass nur 2 von 4 Seiten eingerÃ¼stet werden kÃ¶nnen.

    Args:
        egid: EGID des ZielgebÃ¤udes
        radius_m: Suchradius (0=nur direkt angrenzend, 5=nah, 10=Kontext)
        include_polygons: Polygone für 3D-View mitliefern

    Returns:
        - target: ZielgebÃ¤ude mit Polygon
        - neighbors: Liste der Nachbarn mit Distanz und Richtung
        - blocked_sides: Liste der blockierten Fassadenrichtungen

    Beispiel Response:
    ```json
    {
        "target_egid": "123456",
        "target_polygon": [[x1,y1], ...],
        "neighbors": [
            {
                "egid": "123457",
                "distance_m": 0.0,
                "direction": "E",
                "polygon": [[x,y], ...]
            }
        ],
        "blocked_sides": ["E", "W"],
        "query_time_ms": 5.2
    }
    ```
    """
    neighbors_service = get_neighbors_service()
    result = neighbors_service.get_neighbors(
        egid=egid,
        radius_m=radius_m,
        include_polygons=include_polygons
    )

    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"GebÃ¤ude mit EGID {egid} nicht im smart_building_cache gefunden. "
                   "Bitte zuerst Ã¼ber SmartBuildingService laden."
        )

    # Blockierte Seiten aus Nachbarn ableiten
    blocked_sides = []
    for neighbor in result.neighbors:
        if neighbor.distance_m < 0.5:  # Direkt angrenzend
            if neighbor.direction and neighbor.direction not in blocked_sides:
                blocked_sides.append(neighbor.direction)

    response = result.to_dict()
    response["blocked_sides"] = blocked_sides

    return response


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
    max_radius_m: float = Query(100.0, ge=0, le=500, description="Maximaler Radius für Nachbar-Suche"),
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

    if project.egid and project.egid not in project_egids:
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


@router.get("/building/{egid}/blocked-facades", response_model=Dict[str, Any])
async def get_blocked_facades(
    egid: str,
    exclude_egids: str = Query(None, description="Komma-separierte EGIDs die nicht als Blocker gelten"),
    threshold_m: float = Query(2.0, ge=0.5, le=5.0, description="Distanz-Schwellenwert in Metern")
):
    """
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
                "direction": bf.blockers[0].direction if bf.blockers else None
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
