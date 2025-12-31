"""Gerüstbau-App API Router."""

from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import List, Dict, Any

from ..models.geruestbau import (
    Project, ProjectCreate, ProjectUpdate, ProjectStatus,
    PhotoAnalysis, ScaffoldConfig
)
from ..services.geruestbau.project_service import ProjectService
from ..services.geruestbau.tender_extractor import get_tender_extractor

router = APIRouter(prefix="/api/v1/geruestbau", tags=["Gerüstbau"])

project_service = ProjectService()
tender_extractor = get_tender_extractor()


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
    result = await tender_extractor.extract_from_file(file_bytes, filename)

    return result.to_dict()
