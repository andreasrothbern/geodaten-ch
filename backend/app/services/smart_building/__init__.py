# backend/app/services/smart_building/__init__.py
"""
Smart Building Service
======================

Zentraler Service für die schrittweise Datengewinnung und Prompt-Generierung.

Vereint:
- Geocoding & GWR-Daten
- Höhendaten (swissBUILDINGS3D)
- Terrain (swissALTI3D, Hanglage)
- Polygon & Fassaden
- Dach-Analyse
- Claude-Recherche (Gebäude-Identifikation)
- Zonen-Analyse (komplexe Gebäude)
- Wall→Facade Matching (NEU 13.01.2026)
- Nachbargebäude (TODO)
- Umgebungsdaten (TODO)

Generiert einheitliche Prompts für:
- SVG-Export (Claude.ai)
- Automatische SVG-Generierung (Claude API)

Stand: 13.01.2026
"""

from .models import (
    BuildingDataBundle,
    DataSource,
    DataQuality,
    ZoneInfo,
    NeighborInfo,
    TerrainProfile,
    AccessPoint,
)
from .service import (
    SmartBuildingService,
    get_smart_building_service,
)
from .prompt_generator import (
    UnifiedPromptGenerator,
    get_prompt_generator,
    SVGType,
)
from .wall_facade_matcher import (
    WallFacadeMatcher,
    get_wall_facade_matcher,
    WallSegment,
    FacadeHeight,
)

__all__ = [
    # Models
    "BuildingDataBundle",
    "DataSource",
    "DataQuality",
    "ZoneInfo",
    "NeighborInfo",
    "TerrainProfile",
    "AccessPoint",
    # Service
    "SmartBuildingService",
    "get_smart_building_service",
    # Prompt Generator
    "UnifiedPromptGenerator",
    "get_prompt_generator",
    "SVGType",
    # Wall-Facade Matcher (NEU 13.01.2026)
    "WallFacadeMatcher",
    "get_wall_facade_matcher",
    "WallSegment",
    "FacadeHeight",
]
