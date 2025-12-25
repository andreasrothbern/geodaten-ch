# backend/app/services/svg_prompts/prompt_selector.py
"""
Prompt-Selektor für SVG-Generierung.

Wählt den richtigen Prompt basierend auf Gebäude-Komplexität.
Verhindert, dass normale Wohnhäuser mit Kuppeln gezeichnet werden.

Version: 1.0
Datum: 25.12.2025
"""

from typing import List, Dict, Any, Literal
from enum import Enum

from .simple_building_prompt import generate_simple_elevation_prompt, generate_simple_cross_section_prompt
from .complex_building_prompt import generate_complex_elevation_prompt, generate_complex_cross_section_prompt


class BuildingComplexity(Enum):
    """Gebäude-Komplexitätsstufen"""
    SIMPLE = "simple"           # Normales Wohnhaus, rechteckig
    MODERATE = "moderate"       # L-Form, Anbau
    COMPLEX = "complex"         # Bundeshaus, Kirche, öffentliche Gebäude


# Zone-Typen die auf Komplexität hindeuten
COMPLEX_ZONE_TYPES = {'kuppel', 'turm', 'arkade', 'treppenhaus'}
MODERATE_ZONE_TYPES = {'anbau', 'garage', 'vordach'}


def detect_building_complexity(
    zones: List[Dict[str, Any]],
    building_data: Dict[str, Any]
) -> BuildingComplexity:
    """
    Erkennt die Komplexität eines Gebäudes.

    Args:
        zones: Liste der Gebäudezonen
        building_data: Gebäudedaten (GWR, Polygon, etc.)

    Returns:
        BuildingComplexity Enum
    """

    # Zone-Typen extrahieren
    zone_types = set()
    for zone in zones:
        zone_type = zone.get('type') or zone.get('typ') or 'hauptgebaeude'
        zone_types.add(zone_type.lower())

    # Komplexe Zone-Typen vorhanden?
    if zone_types & COMPLEX_ZONE_TYPES:
        return BuildingComplexity.COMPLEX

    # Mehrere Zonen mit unterschiedlichen Höhen?
    if len(zones) > 1:
        heights = [z.get('gebaeudehoehe_m', 0) or z.get('building_height_m', 0) or z.get('firsthoehe_m', 0) for z in zones]
        heights = [h for h in heights if h > 0]
        if len(set(heights)) > 1:  # Unterschiedliche Höhen
            height_diff = max(heights) - min(heights) if heights else 0
            if height_diff > 5:  # Mehr als 5m Unterschied
                return BuildingComplexity.COMPLEX
            else:
                return BuildingComplexity.MODERATE

    # Moderate Zone-Typen?
    if zone_types & MODERATE_ZONE_TYPES:
        return BuildingComplexity.MODERATE

    # Gebäudekategorie prüfen
    gkat = building_data.get('gkat') or building_data.get('building_category_code')
    complex_categories = {
        1040,  # Gebäude mit Nebennutzung (öffentlich)
        1060,  # Gebäude für Bildung/Kultur
        1080,  # Gebäude für Gesundheit
        1110,  # Kirchen
        1130,  # Museen, Bibliotheken
        1212,  # Industrie
    }
    if gkat in complex_categories:
        return BuildingComplexity.COMPLEX

    # Polygon-Komplexität
    polygon_points = building_data.get('sides') or building_data.get('polygon_points', 4)
    if polygon_points > 12:
        return BuildingComplexity.COMPLEX
    elif polygon_points > 6:
        return BuildingComplexity.MODERATE

    # Grundfläche prüfen
    area = building_data.get('area_m2') or building_data.get('garea', 0)
    if area > 1000:
        return BuildingComplexity.COMPLEX
    elif area > 500:
        return BuildingComplexity.MODERATE

    # Default: Einfaches Gebäude
    return BuildingComplexity.SIMPLE


def get_elevation_prompt(
    zones: List[Dict[str, Any]],
    building_data: Dict[str, Any],
    scaffolding_data: Dict[str, Any] = None
) -> str:
    """
    Gibt den passenden Elevation-Prompt zurück.

    Args:
        zones: Gebäudezonen
        building_data: Gebäudedaten
        scaffolding_data: Gerüst-Konfiguration (optional)

    Returns:
        Prompt-String für Claude API
    """

    complexity = detect_building_complexity(zones, building_data)

    if complexity == BuildingComplexity.SIMPLE:
        return generate_simple_elevation_prompt(zones, building_data, scaffolding_data)
    else:
        return generate_complex_elevation_prompt(zones, building_data, scaffolding_data)


def get_cross_section_prompt(
    zones: List[Dict[str, Any]],
    building_data: Dict[str, Any],
    scaffolding_data: Dict[str, Any] = None
) -> str:
    """
    Gibt den passenden Cross-Section-Prompt zurück.

    Args:
        zones: Gebäudezonen
        building_data: Gebäudedaten
        scaffolding_data: Gerüst-Konfiguration (optional)

    Returns:
        Prompt-String für Claude API
    """

    complexity = detect_building_complexity(zones, building_data)

    if complexity == BuildingComplexity.SIMPLE:
        return generate_simple_cross_section_prompt(zones, building_data, scaffolding_data)
    else:
        return generate_complex_cross_section_prompt(zones, building_data, scaffolding_data)


def get_prompt_metadata(
    zones: List[Dict[str, Any]],
    building_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Gibt Metadaten zur Prompt-Auswahl zurück (für Debugging/Logging).

    Returns:
        Dict mit complexity, zone_types, reasons
    """

    complexity = detect_building_complexity(zones, building_data)

    zone_types = set()
    for zone in zones:
        zone_type = zone.get('type') or zone.get('typ') or 'hauptgebaeude'
        zone_types.add(zone_type.lower())

    reasons = []

    if zone_types & COMPLEX_ZONE_TYPES:
        reasons.append(f"Komplexe Zone-Typen: {zone_types & COMPLEX_ZONE_TYPES}")

    if len(zones) > 1:
        reasons.append(f"Mehrere Zonen: {len(zones)}")

    polygon_points = building_data.get('sides', 4)
    if polygon_points > 6:
        reasons.append(f"Komplexes Polygon: {polygon_points} Punkte")

    area = building_data.get('area_m2', 0)
    if area > 500:
        reasons.append(f"Grosse Grundfläche: {area} m²")

    gkat = building_data.get('gkat') or building_data.get('building_category_code')
    if gkat:
        reasons.append(f"Gebäudekategorie: {gkat}")

    if not reasons:
        reasons.append("Standard-Wohngebäude")

    return {
        "complexity": complexity.value,
        "zone_types": list(zone_types),
        "zone_count": len(zones),
        "polygon_points": polygon_points,
        "area_m2": area,
        "gkat": gkat,
        "reasons": reasons,
        "prompt_type": "simple" if complexity == BuildingComplexity.SIMPLE else "complex"
    }
