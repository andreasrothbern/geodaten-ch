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
- Nachbargebäude (TODO)
- Umgebungsdaten (TODO)

Generiert einheitliche Prompts für:
- SVG-Export (Claude.ai)
- Automatische SVG-Generierung (Claude API)

Stand: 29.12.2025
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
]
