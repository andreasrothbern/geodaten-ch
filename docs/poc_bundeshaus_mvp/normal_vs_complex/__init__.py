# backend/app/services/svg_prompts/__init__.py
"""
SVG Prompt Module für die Claude API SVG-Generierung.

Dieses Modul trennt Prompts für einfache und komplexe Gebäude,
um zu verhindern dass normale Wohnhäuser mit Kuppeln gezeichnet werden.

Version: 1.0
Datum: 25.12.2025

Verwendung:
    from app.services.svg_prompts import (
        get_elevation_prompt,
        get_cross_section_prompt,
        detect_building_complexity,
        get_prompt_metadata
    )
    
    # Automatische Auswahl des richtigen Prompts
    prompt = get_elevation_prompt(zones, building_data, scaffolding_data)
    
    # Oder manuell prüfen
    complexity = detect_building_complexity(zones, building_data)
    if complexity == BuildingComplexity.SIMPLE:
        # Einfaches Gebäude
        pass
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
    SIMPLE_SVG_DEFS,
    SIMPLE_COLORS,
)

from .complex_building_prompt import (
    generate_complex_elevation_prompt,
    generate_complex_cross_section_prompt,
    COMPLEX_SVG_DEFS,
    COMPLEX_COLORS,
    ZONE_TYPE_DESCRIPTIONS,
)

__all__ = [
    # Hauptfunktionen
    'get_elevation_prompt',
    'get_cross_section_prompt',
    'detect_building_complexity',
    'get_prompt_metadata',
    
    # Enum
    'BuildingComplexity',
    
    # Einfache Gebäude
    'generate_simple_elevation_prompt',
    'generate_simple_cross_section_prompt',
    'SIMPLE_SVG_DEFS',
    'SIMPLE_COLORS',
    
    # Komplexe Gebäude
    'generate_complex_elevation_prompt',
    'generate_complex_cross_section_prompt',
    'COMPLEX_SVG_DEFS',
    'COMPLEX_COLORS',
    'ZONE_TYPE_DESCRIPTIONS',
]
