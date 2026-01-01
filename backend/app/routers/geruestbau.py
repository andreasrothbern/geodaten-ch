"""Gerüstbau-App API Router."""

import math
import uuid
from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from typing import List, Dict, Any, Optional

from ..models.geruestbau import (
    Project, ProjectCreate, ProjectUpdate, ProjectStatus,
    PhotoAnalysis, ScaffoldConfig
)
from ..services.geruestbau.project_service import ProjectService
from ..services.swissbuildings3d_service import get_swissbuildings3d_service
from ..services.swisstopo import SwisstopoService

router = APIRouter(prefix="/api/v1/geruestbau", tags=["Gerüstbau"])

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


@router.get("/projects/{project_id}", response_model=Project)
async def get_project(project_id: str):
    """Projekt-Details abrufen."""
    project = await project_service.get_project(project_id)
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
    """Projekt löschen."""
    success = await project_service.delete_project(project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden")
    return {"status": "deleted"}


@router.post("/projects/{project_id}/enrich", response_model=Project)
async def enrich_project(project_id: str):
    """Projekt mit Geodaten anreichern (GWR, Höhen, Polygon)."""
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
    """Aktuelle Gerüst-Konfiguration abrufen."""
    config = await project_service.get_scaffold_config(project_id)
    if not config:
        raise HTTPException(status_code=404, detail="Keine Gerüst-Konfiguration")
    return config


@router.put("/projects/{project_id}/scaffold", response_model=ScaffoldConfig)
async def update_scaffold_config(project_id: str, config: ScaffoldConfig):
    """Gerüst-Konfiguration aktualisieren."""
    return await project_service.update_scaffold_config(project_id, config)


@router.post("/projects/{project_id}/export")
async def export_project(project_id: str, format: str = "pdf"):
    """Projekt exportieren (pdf, ifc, dxf, xlsx)."""
    if format not in ["pdf", "xlsx", "ifc", "dxf"]:
        raise HTTPException(status_code=400, detail="Ungültiges Format")
    return await project_service.export_project(project_id, format)


@router.post("/extract", response_model=Dict[str, Any])
async def extract_from_document(file: UploadFile = File(...)):
    """
    Extrahiert Projektdaten aus einer Ausschreibung (PDF oder Foto).

    Verwendet Claude Vision API für OCR und Datenextraktion.

    Unterstützte Formate:
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

    Unterstützte URLs:
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
    address: str = Query(..., description="Adresse des Gebäudes"),
    include_roof: bool = Query(True, description="Dachanalyse einbeziehen")
):
    """
    Lädt Fassaden-Daten für den Scaffold Configurator.

    Kombiniert Daten aus:
    - geodienste.ch WFS (Polygon)
    - sonnendach.ch API (Dachflächen)
    - Lokale DB (Höhen)

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

    # 2. Gebäudedaten vom Composite Service holen
    service = get_swissbuildings3d_service()
    building = await service.get_building_by_coordinates(
        e, n,
        include_roof_analysis=include_roof
    )

    if not building or not building.polygon:
        raise HTTPException(
            status_code=404,
            detail="Keine Gebäudegeometrie gefunden. Möglicherweise unterstützt dieser Kanton geodienste.ch WFS nicht."
        )

    # 3. Fassaden aus Polygon-Seiten ableiten
    selected_facades = []
    default_height = building.trauf_height_m or 10.0  # Fallback 10m

    for i, side in enumerate(building.sides):
        # Berechne Richtung der Fassade
        start = side.get("start", [0, 0])
        end = side.get("end", [0, 0])
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        length = side.get("length", math.sqrt(dx*dx + dy*dy))

        # Azimut der Fassade (senkrecht zur Wand, nach aussen)
        # Die Fassade zeigt nach aussen, also 90° zur Wandrichtung
        wall_azimuth = _calculate_azimuth(dx, dy)
        facade_azimuth = (wall_azimuth + 90) % 360  # Nach aussen zeigend
        direction = _azimuth_to_direction(facade_azimuth)

        facade = {
            "id": f"facade_{i+1}",
            "direction": direction,
            "length_m": round(length, 2),
            "height_m": round(default_height, 2),
            "slope_percent": 0.0,  # Terrain-Neigung (TODO: aus swissALTI3D)
            "start_point": start,
            "end_point": end,
        }
        selected_facades.append(facade)

    # 4. Response im ProjectInput-Format zusammenstellen
    project_id = str(uuid.uuid4())[:8]

    response = {
        "project_id": project_id,
        "building": {
            "egid": building.egid or "",
            "address": geocode_result.matched_address or address,
            "name": geocode_result.matched_address.split(",")[0] if geocode_result.matched_address else address,
            "polygon": [(p[0], p[1]) for p in building.polygon],
            "trauf_height_m": building.trauf_height_m or default_height,
            "first_height_m": building.first_height_m or (default_height + 3),
            "center_e": e,
            "center_n": n,
        },
        "selected_facades": selected_facades,
        "metadata": {
            "source": "swissBUILDINGS3D_composite",
            "polygon_points": len(building.polygon),
            "facade_count": len(selected_facades),
            "perimeter_m": building.perimeter_m,
            "area_m2": building.area_m2,
            "roof_type": building.roof_type,
            "roof_surfaces_count": len(building.roof_surfaces) if building.roof_surfaces else 0,
            "height_source": building.height_source,
            "confidence": building.confidence,
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
