"""Gerüstbau-App Models für Projektmanagement."""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum


class ProjectStatus(str, Enum):
    """Status eines Gerüstbau-Projekts."""
    DRAFT = "draft"
    CAPTURED = "captured"
    ENRICHED = "enriched"
    REVIEWED = "reviewed"
    PLANNED = "planned"
    QUOTED = "quoted"
    COMMISSIONED = "commissioned"


class TenderData(BaseModel):
    """Ausschreibungs-Daten (aus PDF, Foto, simap.ch)."""
    tender_number: Optional[str] = None
    submission_deadline: Optional[str] = None
    project_start: Optional[str] = None
    project_end: Optional[str] = None
    is_urgent: Optional[bool] = None
    requires_special: Optional[bool] = None
    estimated_area_m2: Optional[float] = None
    source: Optional[str] = None
    raw_text: Optional[str] = None
    confidence: Optional[float] = None


class BuildingDataInput(BaseModel):
    """Gebäudedaten aus SmartBuildingService (für 3D-Modell)."""
    egid: Optional[str] = None
    coordinates: Optional[dict] = None  # {e, n, lat, lon}
    polygon: Optional[List[List[float]]] = None  # [[e, n], ...]
    traufhoehe_m: Optional[float] = None
    firsthoehe_m: Optional[float] = None
    gebaeudehoehe_m: Optional[float] = None
    height_source: Optional[str] = None
    floors: Optional[int] = None
    building_type: Optional[str] = None
    year_built: Optional[int] = None
    perimeter_m: Optional[float] = None
    area_m2: Optional[float] = None
    sides: Optional[List[dict]] = None  # Fassaden-Daten


class ProjectCreate(BaseModel):
    """Daten für Projekt-Erstellung."""
    name: str
    address: str
    client_name: Optional[str] = None
    client_contact: Optional[str] = None
    deadline: Optional[datetime] = None
    description: Optional[str] = None
    tender_data: Optional[TenderData] = None  # Ausschreibungs-Daten
    building_data: Optional[BuildingDataInput] = None  # Geodaten für 3D-Modell


class ProjectUpdate(BaseModel):
    """Daten für Projekt-Update."""
    name: Optional[str] = None
    status: Optional[ProjectStatus] = None
    client_name: Optional[str] = None
    client_contact: Optional[str] = None
    description: Optional[str] = None


class Project(BaseModel):
    """Vollständiges Projekt-Model."""
    id: str
    name: str
    address: str
    status: ProjectStatus
    egid: Optional[str] = None
    client_name: Optional[str] = None
    client_contact: Optional[str] = None
    deadline: Optional[datetime] = None
    description: Optional[str] = None
    building_data: Optional[dict] = None
    created_at: datetime
    updated_at: datetime


class PhotoUpload(BaseModel):
    """Daten für Foto-Upload."""
    project_id: str
    direction: Optional[str] = None  # N, NO, O, SO, S, SW, W, NW


class PhotoAnalysis(BaseModel):
    """Ergebnis der Foto-Analyse."""
    photo_id: str
    direction: str
    confidence: float
    detected_elements: List[str]
    visible_zones: List[str]
    estimated_area_m2: Optional[float] = None


class ScaffoldZone(BaseModel):
    """Eine Gerüst-Zone."""
    name: str
    zone_type: str  # turm, hauptgebaeude, anbau
    height_m: float
    width_m: float
    fields: int
    levels: int
    requires_special: bool = False


class ScaffoldConfig(BaseModel):
    """Gerüst-Konfiguration für ein Projekt."""
    project_id: str
    system: str = "Layher Blitz 70"
    bay_width: str = "W09"
    zones: List[ScaffoldZone]
    total_area_m2: float
    total_anchors: int
    access_points: int
