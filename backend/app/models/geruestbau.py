"""Geruestbau-App Models fuer Projektmanagement."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ProjectStatus(str, Enum):
    """Status eines Geruestbau-Projekts."""
    DRAFT = "draft"
    ENRICHED = "enriched"
    CONFIGURED = "configured"
    COMPLETED = "completed"


# =============================================================================
# Scaffold Configuration Models (stored as JSON in projects.config)
# =============================================================================

class ProjectOverrides(BaseModel):
    """Projekt-spezifische Ueberschreibungen der Geodaten."""
    polygon: Optional[List[List[float]]] = None  # Falls manuell angepasst
    traufhoehe_m: Optional[float] = None
    firsthoehe_m: Optional[float] = None
    simplify_epsilon: Optional[float] = None  # Douglas-Peucker Parameter
    simplify_angle_tolerance: Optional[float] = None


class ScaffoldSettings(BaseModel):
    """Geruest-System Einstellungen."""
    system: str = "layher_blitz"  # layher_blitz, layher_allround
    work_type: str = "facade"  # facade, roof, full
    level_height_m: float = 2.0
    field_length_ratio: int = 50  # 0-100 Slider (2.57m vs 3.07m)


class FacadeOpening(BaseModel):
    """Fenster oder Tuer in einer Fassade."""
    type: str  # window, door
    floor: int
    position: Optional[str] = None  # left, center, right
    width_m: Optional[float] = None
    height_m: Optional[float] = None
    count: int = 1


class FacadeObstacle(BaseModel):
    """Hindernis an einer Fassade (Balkon, Baum, etc.)."""
    type: str  # balcony, tree, awning, sign
    floor: Optional[int] = None
    position: Optional[str] = None
    depth_m: Optional[float] = None
    distance_m: Optional[float] = None


class FacadeConfig(BaseModel):
    """Konfiguration einer einzelnen Fassade."""
    index: int  # Index im Polygon
    direction: str  # N, NE, E, SE, S, SW, W, NW
    length_m: float
    height_m: float
    slope_percent: float = 0.0
    selected: bool = True
    has_lift: bool = False
    has_stairs: bool = False
    openings: List[FacadeOpening] = Field(default_factory=list)
    obstacles: List[FacadeObstacle] = Field(default_factory=list)
    photos: List[str] = Field(default_factory=list)  # Photo IDs
    enrichment_source: Optional[str] = None  # claude-vision, manual


class CornerConfig(BaseModel):
    """Konfiguration einer Ecke."""
    index: int
    type: str = "standard"  # standard, innen, aussen


class AccessPoint(BaseModel):
    """Zugang (Lift, Treppe)."""
    facade_index: int
    position_m: float  # Abstand vom Fassaden-Start
    type: str  # lift, stairs
    width_m: float = 2.57


class ScaffoldConfig(BaseModel):
    """Komplette Geruest-Konfiguration (als JSON in projects.config)."""
    overrides: ProjectOverrides = Field(default_factory=ProjectOverrides)
    settings: ScaffoldSettings = Field(default_factory=ScaffoldSettings)
    facades: List[FacadeConfig] = Field(default_factory=list)
    corners: List[CornerConfig] = Field(default_factory=list)
    access_points: List[AccessPoint] = Field(default_factory=list)


# =============================================================================
# Photo & Enrichment Models
# =============================================================================

class EnrichmentStatus(str, Enum):
    """Status der Foto-Analyse."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class FacadeAnalysis(BaseModel):
    """Analyseergebnis fuer Fassade aus Foto."""
    detected_direction: Optional[str] = None
    estimated_height_m: Optional[float] = None
    floor_count: Optional[int] = None


class EnrichmentData(BaseModel):
    """Ergebnis der Claude Vision Analyse."""
    model: str = "claude-vision"
    model_version: Optional[str] = None
    analyzed_at: Optional[str] = None
    confidence: float = 0.0
    facade_analysis: Optional[FacadeAnalysis] = None
    openings: List[FacadeOpening] = Field(default_factory=list)
    obstacles: List[FacadeObstacle] = Field(default_factory=list)
    scaffolding_hints: List[str] = Field(default_factory=list)


class ProjectPhoto(BaseModel):
    """Foto eines Projekts mit Enrichment-Daten."""
    id: str
    project_id: str
    filename: str
    file_path: str
    file_size_bytes: Optional[int] = None
    mime_type: Optional[str] = None
    taken_at: Optional[datetime] = None
    uploaded_at: datetime
    facade_index: Optional[int] = None
    view_direction: Optional[str] = None
    enrichment_status: EnrichmentStatus = EnrichmentStatus.PENDING
    enrichment_at: Optional[datetime] = None
    enrichment_data: Optional[EnrichmentData] = None


class PhotoUpload(BaseModel):
    """Daten fuer Foto-Upload."""
    facade_index: Optional[int] = None
    view_direction: Optional[str] = None  # N, NE, E, SE, S, SW, W, NW


class PhotoUpdate(BaseModel):
    """Daten fuer Foto-Update."""
    facade_index: Optional[int] = None
    view_direction: Optional[str] = None


# =============================================================================
# Project Models
# =============================================================================

class ProjectCreate(BaseModel):
    """Daten fuer Projekt-Erstellung.

    Felder koennen aus SIMAP-Import befuellt werden (PDF/Link Extraktion).
    """
    name: str
    address: str
    egid: Optional[str] = None
    client_name: Optional[str] = None
    client_contact: Optional[str] = None
    deadline: Optional[str] = None
    description: Optional[str] = None  # Projektbeschreibung (z.B. aus SIMAP)


class ProjectUpdate(BaseModel):
    """Daten fuer Projekt-Update."""
    name: Optional[str] = None
    status: Optional[ProjectStatus] = None
    client_name: Optional[str] = None
    client_contact: Optional[str] = None
    deadline: Optional[str] = None
    description: Optional[str] = None  # Projektbeschreibung
    config: Optional[ScaffoldConfig] = None


class Project(BaseModel):
    """Vollstaendiges Projekt-Model."""
    id: str
    name: str
    address: str
    egid: Optional[str] = None
    status: ProjectStatus = ProjectStatus.DRAFT
    config: Optional[ScaffoldConfig] = None
    client_name: Optional[str] = None
    client_contact: Optional[str] = None
    deadline: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class ProjectWithGeodata(Project):
    """Projekt mit Geodaten aus Cache."""
    geodata: Optional[Dict[str, Any]] = None  # BuildingGeodata as dict


# =============================================================================
# Legacy Models (fuer Kompatibilitaet)
# =============================================================================

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
    """Gebaeudedaten aus SmartBuildingService (Legacy)."""
    egid: Optional[str] = None
    coordinates: Optional[dict] = None
    polygon: Optional[List[List[float]]] = None
    traufhoehe_m: Optional[float] = None
    firsthoehe_m: Optional[float] = None
    gebaeudehoehe_m: Optional[float] = None
    height_source: Optional[str] = None
    floors: Optional[int] = None
    building_type: Optional[str] = None
    year_built: Optional[int] = None
    perimeter_m: Optional[float] = None
    area_m2: Optional[float] = None
    sides: Optional[List[dict]] = None


class PhotoAnalysis(BaseModel):
    """Ergebnis der Foto-Analyse (Legacy)."""
    photo_id: str
    direction: str
    confidence: float
    detected_elements: List[str] = Field(default_factory=list)
    visible_zones: List[str] = Field(default_factory=list)
    estimated_area_m2: Optional[float] = None


class ScaffoldZone(BaseModel):
    """Eine Geruest-Zone (Legacy)."""
    name: str
    zone_type: str
    height_m: float
    width_m: float
    fields: int
    levels: int
    requires_special: bool = False
