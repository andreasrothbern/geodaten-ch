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


class ProjectCreate(BaseModel):
    """Daten für Projekt-Erstellung."""
    name: str
    address: str
    client_name: Optional[str] = None
    client_contact: Optional[str] = None
    deadline: Optional[datetime] = None
    description: Optional[str] = None


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
