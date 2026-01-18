# backend/app/services/smart_building/models.py
"""
Datenmodelle für den SmartBuildingService.

Alle Daten die für Gerüstplanung gesammelt werden, strukturiert in
einem BuildingDataBundle. Dieses Bundle wird für die Prompt-Generierung
verwendet.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any


class DataSource(str, Enum):
    """Quelle der Daten"""
    SWISSTOPO_GEOCODING = "swisstopo_geocoding"
    SWISSTOPO_GWR = "swisstopo_gwr"
    SWISSBUILDINGS3D = "swissbuildings3d"
    SWISSALTI3D = "swissalti3d"
    GEODIENSTE_WFS = "geodienste_wfs"
    SONNENDACH = "sonnendach"  # BFE Sonnendach.ch Dachgeometrie
    CLAUDE_RESEARCH = "claude_research"
    CLAUDE_ANALYSIS = "claude_analysis"
    CALCULATED = "calculated"
    MANUAL = "manual"
    CACHE = "cache"


class DataQuality(str, Enum):
    """Qualität/Zuverlässigkeit der Daten"""
    HIGH = "high"          # Gemessen, verifiziert
    MEDIUM = "medium"      # Berechnet, geschätzt mit guter Basis
    LOW = "low"            # Grobe Schätzung
    UNKNOWN = "unknown"    # Keine Qualitätsinfo


@dataclass
class ZoneInfo:
    """Eine Höhenzone des Gebäudes"""
    id: str
    name: str
    zone_type: str  # hauptgebaeude, anbau, turm, kuppel, arkade, etc.

    # Höhen
    traufhoehe_m: Optional[float] = None
    firsthoehe_m: Optional[float] = None
    gebaeudehoehe_m: Optional[float] = None

    # Position in der Ansicht (für Claude SVG-Generierung)
    position: Optional[str] = None  # "zentral", "links", "rechts", "aussen", "verdeckt"

    # Zuordnung
    fassaden_ids: List[str] = field(default_factory=list)
    polygon_point_indices: Optional[List[int]] = None

    # Gerüstplanung
    beruesten: bool = True
    sonderkonstruktion: bool = False
    geruesthoehe_m: Optional[float] = None

    # Meta
    confidence: float = 0.8
    source: DataSource = DataSource.CALCULATED
    notes: Optional[str] = None


@dataclass
class NeighborInfo:
    """Nachbargebäude-Informationen"""
    egid: Optional[str] = None
    direction: str = ""  # N, NE, E, SE, S, SW, W, NW
    distance_m: float = 0.0
    height_m: Optional[float] = None

    # Auswirkung auf Gerüst
    blocks_access: bool = False
    blocks_facade: Optional[str] = None  # Welche Fassade betroffen
    requires_coordination: bool = False

    notes: Optional[str] = None


@dataclass
class TerrainProfile:
    """Terrain-Profil für Hanglage-Erkennung"""
    # Referenzpunkt (Haupteingang)
    reference_height_m: float = 0.0

    # Profil um das Gebäude
    min_height_m: Optional[float] = None
    max_height_m: Optional[float] = None
    slope_m: Optional[float] = None  # Differenz min-max

    # Detaillierte Höhen pro Fassade (Terrain am Fassaden-Startpunkt)
    facade_heights: Dict[str, float] = field(default_factory=dict)
    # {"N": 543.1, "E": 544.2, "S": 545.0, "W": 543.5}

    # NEU 14.01.2026: Fassaden-Höhen aus Wall-Layer (z_min/z_max pro Fassade)
    # Quelle: WallFacadeMatcher → swissBUILDINGS3D Wall-Layer
    facade_z_min: Dict[str, float] = field(default_factory=dict)
    # {"N": 541.0, "E": 543.5, ...} - Terrain-Höhe (m ü.M.) an der Fassade
    facade_z_max: Dict[str, float] = field(default_factory=dict)
    # {"N": 550.0, "E": 552.0, ...} - Wandoberkante (m ü.M.) an der Fassade
    facade_heights_source: str = "global"
    # "wall_layer" | "terrain_sampled" | "global"

    # Klassifikation
    is_sloped: bool = False  # > 1m Differenz
    slope_direction: Optional[str] = None  # Haupt-Gefällerichtung
    slope_class: str = "eben"  # eben/leicht/mittel/stark

    # Gerüst-Auswirkungen
    requires_level_compensation: bool = False
    max_compensation_m: Optional[float] = None


@dataclass
class AccessPoint:
    """Gerüst-Zugang (Treppe)"""
    id: str  # Z1, Z2, etc.
    fassade_id: str
    position_percent: float  # 0.0 - 1.0
    reason: str

    # Prüfung
    suva_compliant: bool = True
    max_escape_distance_m: Optional[float] = None


@dataclass
class BuildingDataBundle:
    """
    Gesamtpaket aller gesammelten Gebäudedaten.

    Dies ist das zentrale Datenmodell das durch den SmartBuildingService
    schrittweise befüllt wird und dann für die Prompt-Generierung verwendet wird.
    """

    # === IDENTIFIKATION ===
    egid: Optional[str] = None  # Primary EGID (swissBUILDINGS3D preferred)
    gwr_egid: Optional[str] = None  # GWR EGID (may differ for row houses)
    address_input: Optional[str] = None
    address_matched: Optional[str] = None

    # Koordinaten (LV95)
    lv95_e: Optional[float] = None
    lv95_n: Optional[float] = None

    # Gebäude-Identifikation (aus Claude-Recherche)
    building_name: Optional[str] = None
    building_type: Optional[str] = None  # Wohnhaus, Kirche, etc.
    architectural_style: Optional[str] = None  # Neugotik, Modern, etc.
    construction_year: Optional[int] = None

    # === GWR-DATEN ===
    gwr_category: Optional[str] = None
    gwr_category_code: Optional[int] = None
    gwr_floors: Optional[int] = None
    gwr_area_m2: Optional[float] = None
    gwr_dwellings: Optional[int] = None

    # === GEOMETRIE ===
    # Polygon (ALWAYS the original from swissBUILDINGS3D)
    polygon: Optional[List[List[float]]] = None  # [[e, n], ...] - Original
    polygon_source: DataSource = DataSource.SWISSBUILDINGS3D
    polygon_point_count: Optional[int] = None  # Anzahl Punkte im Original

    # Sides are calculated from on-the-fly simplified polygon
    sides_from_simplified: bool = True

    # Fassaden (aus Polygon berechnet)
    sides: Optional[List[Dict[str, Any]]] = None
    perimeter_m: Optional[float] = None
    footprint_area_m2: Optional[float] = None

    # NEU 18.01.2026: Fassaden mit Höhen pro Fassade (für GeruestbauData)
    # Kombiniert sides[] + terrain.facade_z_min/max
    # Jede Fassade hat: index, direction, start_point, end_point, length_m,
    #                   terrain_z_min, terrain_z_max, wall_z_max, height_m, slope_m
    facades: Optional[List[Dict[str, Any]]] = None

    # Bounding Box
    bbox_width_m: Optional[float] = None
    bbox_depth_m: Optional[float] = None

    # === HÖHENDATEN ===
    # Gemessen (swissBUILDINGS3D)
    traufhoehe_m: Optional[float] = None
    firsthoehe_m: Optional[float] = None
    gebaeudehoehe_m: Optional[float] = None
    height_source: DataSource = DataSource.SWISSBUILDINGS3D
    height_quality: DataQuality = DataQuality.UNKNOWN

    # Berechnet/Geschätzt
    estimated_height_m: Optional[float] = None
    floors_estimated: Optional[int] = None

    # === TERRAIN ===
    terrain: Optional[TerrainProfile] = None

    # === DACH ===
    roof_type: Optional[str] = None  # flachdach, satteldach, walmdach, etc.
    roof_angle_deg: Optional[float] = None
    roof_orientation: Optional[str] = None  # O-W, N-S
    roof_area_m2: Optional[float] = None
    roof_confidence: float = 0.5

    # === DACH (SONNENDACH.CH) ===
    # Detaillierte Dachgeometrie aus Sonnendach.ch (BFE)
    roof_overhang_m: float = 0.4  # Dachüberstand (Standard: 40cm)
    roof_surfaces: Optional[List[Dict[str, Any]]] = None  # Dachflächen aus Sonnendach
    roof_tilt_deg: Optional[float] = None  # Genaue Neigung aus Sonnendach
    roof_azimuth_deg: Optional[float] = None  # Genaue Ausrichtung (0-360°)
    sonnendach_available: bool = False  # Sonnendach.ch Daten verfügbar?

    # === DACH (swissBUILDINGS3D Roof_solid) - NEU 11.01.2026 ===
    # Echte 3D-Dachgeometrie aus Roof_solid Layer
    roof_geometry_wkb: Optional[bytes] = None  # 3D-Geometrie als WKB (für Frontend)
    has_roof_geometry: bool = False  # Echte Geometrie verfügbar?
    has_3d_layers: bool = False  # Wall/Roof/Floor 3D-Layer vorhanden? (FIX 12.01.2026)
    roof_z_levels: Optional[List[float]] = None  # Z-Level Verteilung für Analyse
    roof_dach_min_m: Optional[float] = None  # Traufhöhe (m ü.M.) aus Roof_solid
    roof_dach_max_m: Optional[float] = None  # Firsthöhe (m ü.M.) aus Roof_solid
    roof_gebaeudeeinheit: Optional[str] = None  # Verknüpfung zu Roof_solid

    # === ZONEN ===
    zones: List[ZoneInfo] = field(default_factory=list)
    complexity: str = "simple"  # simple, moderate, complex
    has_height_variations: bool = False
    has_towers: bool = False
    has_annexes: bool = False
    has_courtyards: bool = False

    # Turm-Konfiguration (für Kirchen, etc.)
    tower_config: Optional[Dict[str, Any]] = None  # {"count": 1, "position": "zentral", "form": "Spitzhelm", "height_m": 54.6}

    # === GEBÄUDEFORM (NEU 30.12.2025) ===
    # Für korrekte SVG-Grundriss-Darstellung
    building_shape: Optional[str] = None  # "U-Form", "L-Form", "Kreuzform", "rechteckig"
    building_shape_description: Optional[str] = None  # Detaillierte Beschreibung
    special_features: List[str] = field(default_factory=list)  # ["Ehrenhof", "Kuppel", ...]

    # SVG-Generierungs-Hinweise pro Typ
    svg_hints: Optional[Dict[str, str]] = None  # {"grundriss": "...", "ansicht": "...", "schnitt": "..."}

    # Bevorzugte Ansichtsrichtung (für Fassadenansicht)
    preferred_view: Optional[Dict[str, str]] = None  # {"direction": "west", "description": "...", "reason": "..."}

    # === ZUGÄNGE ===
    access_points: List[AccessPoint] = field(default_factory=list)
    suva_compliant: bool = True
    max_escape_distance_m: Optional[float] = None

    # === UMGEBUNG (TODO) ===
    neighbors: List[NeighborInfo] = field(default_factory=list)
    has_blocking_neighbors: bool = False
    street_access: Optional[Dict[str, Any]] = None

    # === META ===
    data_sources: List[DataSource] = field(default_factory=list)
    collection_timestamp: Optional[datetime] = None
    overall_quality: DataQuality = DataQuality.UNKNOWN

    # Recherche-Ergebnisse
    research_confidence: float = 0.0
    analysis_confidence: float = 0.0

    # Datenherkunft für UI-Feedback (NEU 05.01.2026)
    # "known_buildings" = bekanntes Gebäude (sofort, kostenlos)
    # "claude_api" = Claude Research API (1-3 Sekunden, kostenpflichtig)
    # "cache" = aus Cache geladen
    # "auto" = automatisch berechnet
    research_source: str = "unknown"

    # Fehler/Warnungen
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def add_warning(self, msg: str):
        """Fügt eine Warnung hinzu"""
        if msg not in self.warnings:
            self.warnings.append(msg)

    def add_error(self, msg: str):
        """Fügt einen Fehler hinzu"""
        if msg not in self.errors:
            self.errors.append(msg)

    def add_source(self, source: DataSource):
        """Registriert eine Datenquelle"""
        if source not in self.data_sources:
            self.data_sources.append(source)

    def get_active_height(self) -> Optional[float]:
        """Gibt die beste verfügbare Höhe zurück"""
        # Priorität: First > Trauf > Gebäude > Geschätzt
        if self.firsthoehe_m:
            return self.firsthoehe_m
        if self.traufhoehe_m:
            return self.traufhoehe_m
        if self.gebaeudehoehe_m:
            return self.gebaeudehoehe_m
        if self.estimated_height_m:
            return self.estimated_height_m
        return None

    def has_extreme_height_diff(self) -> bool:
        """Prüft auf extreme Höhendifferenz (→ mehrere Zonen)"""
        if self.traufhoehe_m and self.firsthoehe_m:
            diff = self.firsthoehe_m - self.traufhoehe_m
            return diff > 15  # Mehr als 15m = sehr wahrscheinlich Kuppel/Turm
        return False

    def to_prompt_context(self) -> Dict[str, Any]:
        """Konvertiert Bundle in Dictionary für Prompt-Template"""
        return {
            # Identifikation
            "egid": self.egid,
            "address": self.address_matched or self.address_input,
            "coordinates": f"E {self.lv95_e:.0f}, N {self.lv95_n:.0f}" if self.lv95_e else None,
            "building_name": self.building_name,
            "building_type": self.building_type,
            "architectural_style": self.architectural_style,
            "construction_year": self.construction_year,

            # GWR
            "gwr_category": self.gwr_category,
            "gwr_floors": self.gwr_floors,
            "gwr_area_m2": self.gwr_area_m2,

            # Geometrie
            "polygon_points": len(self.polygon) if self.polygon else 0,
            "perimeter_m": self.perimeter_m,
            "footprint_area_m2": self.footprint_area_m2,
            "bbox_width_m": self.bbox_width_m,
            "bbox_depth_m": self.bbox_depth_m,

            # Höhen
            "traufhoehe_m": self.traufhoehe_m,
            "firsthoehe_m": self.firsthoehe_m,
            "gebaeudehoehe_m": self.gebaeudehoehe_m,
            "height_source": self.height_source.value if self.height_source else None,
            "floors": self.gwr_floors or self.floors_estimated,

            # Terrain
            "terrain_height_m": self.terrain.reference_height_m if self.terrain else None,
            "terrain_slope_m": self.terrain.slope_m if self.terrain else None,
            "is_sloped": self.terrain.is_sloped if self.terrain else False,

            # Dach
            "roof_type": self.roof_type,
            "roof_angle_deg": self.roof_angle_deg,
            "roof_orientation": self.roof_orientation,

            # Zonen
            "zones": [
                {
                    "name": z.name,
                    "type": z.zone_type,
                    "traufhoehe_m": z.traufhoehe_m,
                    "firsthoehe_m": z.firsthoehe_m,
                    "gebaeudehoehe_m": z.gebaeudehoehe_m,
                    "position": z.position,  # Räumliche Anordnung für 3D-Modell
                    "beruesten": z.beruesten,
                    "sonderkonstruktion": z.sonderkonstruktion,
                }
                for z in self.zones
            ],
            "complexity": self.complexity,

            # Zugänge
            "access_points": [
                {"id": a.id, "fassade": a.fassade_id, "position": a.position_percent}
                for a in self.access_points
            ],
            "suva_compliant": self.suva_compliant,

            # Umgebung
            "neighbors_count": len(self.neighbors),
            "has_blocking_neighbors": self.has_blocking_neighbors,

            # Meta
            "data_sources": [s.value for s in self.data_sources],
            "warnings": self.warnings,
        }
