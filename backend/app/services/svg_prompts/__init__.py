# backend/app/services/svg_prompts/__init__.py
"""
SVG Prompt Module für Gebäude-Visualisierung.

Enthält separate Prompts für:
- Einfache Gebäude (Wohnhäuser)
- Komplexe Gebäude (Kirchen, öffentliche Gebäude)
- Terrain/Hanglage
- Umgebung/Nachbargebäude

Version: 2.0 (29.12.2025)
"""

from .prompt_selector import (
    BuildingComplexity,
    detect_building_complexity,
    get_elevation_prompt,
    get_cross_section_prompt,
    get_prompt_metadata,
)

from .simple_building_prompt import (
    generate_simple_elevation_prompt,
    generate_simple_cross_section_prompt,
)

from .complex_building_prompt import (
    generate_complex_elevation_prompt,
    generate_complex_cross_section_prompt,
)

from .terrain_prompt import (
    generate_terrain_prompt,
    generate_terrain_overview_prompt,
)

from .environment_prompt import (
    generate_environment_prompt,
    generate_accessibility_prompt,
)

__all__ = [
    # Prompt Selector
    'BuildingComplexity',
    'detect_building_complexity',
    'get_elevation_prompt',
    'get_cross_section_prompt',
    'get_prompt_metadata',
    # Simple Building
    'generate_simple_elevation_prompt',
    'generate_simple_cross_section_prompt',
    # Complex Building
    'generate_complex_elevation_prompt',
    'generate_complex_cross_section_prompt',
    # Terrain (NEU)
    'generate_terrain_prompt',
    'generate_terrain_overview_prompt',
    # Environment (NEU)
    'generate_environment_prompt',
    'generate_accessibility_prompt',
]
