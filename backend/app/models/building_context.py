"""
Building Context Models

Datenmodelle für das Gebäude-Kontext-System.
Ermöglicht die Analyse komplexer Gebäude mit mehreren Höhenzonen.

Siehe: docs/poc_bundeshaus_mvp/BUILDING_CONTEXT.md
"""

from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import datetime
from enum import Enum


class ZoneType(str, Enum):
    """Typen von Gebäudezonen"""
    HAUPTGEBAEUDE = "hauptgebaeude"
    ANBAU = "anbau"
    TURM = "turm"
    KUPPEL = "kuppel"
    ARKADE = "arkade"
    VORDACH = "vordach"
    TREPPENHAUS = "treppenhaus"
    GARAGE = "garage"
    UNKNOWN = "unknown"


class ComplexityLevel(str, Enum):
    """Komplexitätsstufen eines Gebäudes"""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"


class ContextSource(str, Enum):
    """Quelle des Kontexts"""
    AUTO = "auto"       # Automatisch erstellt (einfache Gebäude)
    CLAUDE = "claude"   # Von Claude AI analysiert
    MANUAL = "manual"   # Manuell eingegeben/korrigiert


class BuildingZone(BaseModel):
    """Eine Höhenzone innerhalb eines Gebäudes"""

    # Identifikation
    id: str = Field(..., description="Zone-ID, z.B. 'zone_1', 'zone_arkade'")
    name: str = Field(..., description="Anzeigename, z.B. 'Hauptgebäude', 'Westturm'")
    type: ZoneType = Field(default=ZoneType.HAUPTGEBAEUDE, description="Typ der Zone")

    # Geometrie-Referenz
    polygon_point_indices: Optional[list[int]] = Field(
        default=None,
        description="Indizes der Punkte im Hauptpolygon, z.B. [0, 1, 2, 3]"
    )
    sub_polygon: Optional[list[tuple[float, float]]] = Field(
        default=None,
        description="Eigenes Sub-Polygon für komplexe Fälle [(e, n), ...]"
    )

    # Höhendaten
    traufhoehe_m: Optional[float] = Field(default=None, description="Traufhöhe in Metern")
    firsthoehe_m: Optional[float] = Field(default=None, description="Firsthöhe in Metern")
    gebaeudehoehe_m: float = Field(..., description="Effektive Höhe für Berechnung")

    # Terrain (für Hanglagen)
    terrain_hoehe_m: Optional[float] = Field(default=None, description="Mittlere Geländehöhe")
    terrain_min_m: Optional[float] = Field(default=None, description="Tiefster Punkt")
    terrain_max_m: Optional[float] = Field(default=None, description="Höchster Punkt")

    # Gerüst-Relevanz
    fassaden_ids: list[str] = Field(
        default_factory=list,
        description="Zugehörige Fassaden, z.B. ['N', 'E', 'S']"
    )
    beruesten: bool = Field(default=True, description="Soll eingerüstet werden?")
    sonderkonstruktion: bool = Field(
        default=False,
        description="Spezialgerüst nötig (Hängegerüst, etc.)?"
    )

    # Metadaten
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Konfidenz der Analyse (0.0-1.0)"
    )
    notes: Optional[str] = Field(default=None, description="Freitext-Notizen")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "zone_1",
                "name": "Hauptgebäude",
                "type": "hauptgebaeude",
                "polygon_point_indices": [0, 1, 2, 3],
                "traufhoehe_m": 9.5,
                "firsthoehe_m": 12.0,
                "gebaeudehoehe_m": 9.5,
                "fassaden_ids": ["N", "E", "S", "W"],
                "beruesten": True,
                "confidence": 0.95
            }
        }


class BuildingContext(BaseModel):
    """Vollständiger Kontext für ein Gebäude"""

    # Identifikation
    egid: str = Field(..., description="Eidgenössische Gebäude-ID")
    adresse: Optional[str] = Field(default=None, description="Vollständige Adresse")

    # Zonen
    zones: list[BuildingZone] = Field(
        default_factory=list,
        description="Liste der Höhenzonen"
    )

    # Beziehungen zwischen Zonen
    zone_adjacency: Optional[dict[str, list[str]]] = Field(
        default=None,
        description="Nachbarschaftsbeziehungen: {'zone_1': ['zone_2']}"
    )

    # Gebäude-Eigenschaften (aggregiert)
    complexity: ComplexityLevel = Field(
        default=ComplexityLevel.SIMPLE,
        description="Komplexitätsstufe"
    )
    has_height_variations: bool = Field(
        default=False,
        description="Hat unterschiedliche Höhen?"
    )
    has_setbacks: bool = Field(
        default=False,
        description="Hat Rücksprünge?"
    )
    has_towers: bool = Field(default=False, description="Hat Türme?")
    has_annexes: bool = Field(default=False, description="Hat Anbauten?")
    has_special_features: bool = Field(
        default=False,
        description="Hat Sonderelemente (Kuppeln, Arkaden)?"
    )

    # Terrain
    terrain_slope_percent: Optional[float] = Field(
        default=None,
        description="Gefälle in Prozent"
    )
    terrain_aspect: Optional[str] = Field(
        default=None,
        description="Gefälle-Richtung: 'N', 'NE', etc."
    )

    # Quelle und Qualität
    source: ContextSource = Field(
        default=ContextSource.AUTO,
        description="Wie wurde der Kontext erstellt?"
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Gesamt-Konfidenz"
    )
    validated_by_user: bool = Field(
        default=False,
        description="Wurde vom Benutzer validiert?"
    )
    reasoning: Optional[str] = Field(
        default=None,
        description="Begründung der Analyse (von Claude)"
    )

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "egid": "1234567",
                "adresse": "Musterstrasse 10, 3000 Bern",
                "zones": [
                    {
                        "id": "zone_1",
                        "name": "Hauptgebäude",
                        "type": "hauptgebaeude",
                        "gebaeudehoehe_m": 9.5,
                        "fassaden_ids": ["N", "E", "S", "W"],
                        "beruesten": True,
                        "confidence": 1.0
                    }
                ],
                "complexity": "simple",
                "source": "auto",
                "confidence": 1.0
            }
        }


class BuildingContextCreate(BaseModel):
    """Request-Model zum Erstellen/Aktualisieren eines Kontexts"""
    zones: list[BuildingZone]
    validated: bool = False


class BuildingContextResponse(BaseModel):
    """Response-Model für API"""
    status: Literal["found", "created", "not_found", "error"]
    context: Optional[BuildingContext] = None
    needs_validation: bool = False
    message: Optional[str] = None


class AnalyzeRequest(BaseModel):
    """Request für Claude-Analyse"""
    include_orthofoto: bool = Field(
        default=False,
        description="Orthofoto für bessere Analyse einbeziehen?"
    )
    force_reanalyze: bool = Field(
        default=False,
        description="Bestehende Analyse überschreiben?"
    )


class AnalyzeResponse(BaseModel):
    """Response nach Claude-Analyse"""
    status: Literal["success", "error", "already_exists"]
    context: Optional[BuildingContext] = None
    cost_estimate_usd: Optional[float] = None
    message: Optional[str] = None
