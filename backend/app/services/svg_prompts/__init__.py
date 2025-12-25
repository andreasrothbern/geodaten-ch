# backend/app/services/svg_prompts/__init__.py
"""
SVG Prompt Module für Gebäude-Visualisierung.

Enthält separate Prompts für einfache und komplexe Gebäude.
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

__all__ = [
    'BuildingComplexity',
    'detect_building_complexity',
    'get_elevation_prompt',
    'get_cross_section_prompt',
    'get_prompt_metadata',
    'generate_simple_elevation_prompt',
    'generate_simple_cross_section_prompt',
    'generate_complex_elevation_prompt',
    'generate_complex_cross_section_prompt',
]
