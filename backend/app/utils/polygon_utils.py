"""
Polygon Utilities - Zentrale Funktionen für Polygon-Operationen.

NEU 19.01.2026: Einheitliche Union-Berechnung für Multi-Building Projekte.

Verwendung:
    from app.utils.polygon_utils import calculate_union_polygon

    polygons = [[[x1,y1], [x2,y2], ...], [[x3,y3], ...]]
    union = calculate_union_polygon(polygons)
    # union = [[x1,y1], [x2,y2], ...] (äussere Kontur)
"""

from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


def calculate_union_polygon(
    polygons: List[List[List[float]]],
    round_decimals: int = 2
) -> Optional[List[List[float]]]:
    """
    Berechnet das Union-Polygon aus einer Liste von Polygonen.

    Ein Projekt = Ein Objekt. Das Ergebnis ist:
    - Bei 1 Polygon: Das Polygon selbst (unverändert)
    - Bei mehreren: Union aller Polygone (äussere Kontur)
    - Bei MultiPolygon-Ergebnis: Das grösste Polygon

    Args:
        polygons: Liste von Polygonen, jedes als [[x,y], [x,y], ...]
        round_decimals: Anzahl Dezimalstellen für Koordinaten (default: 2)

    Returns:
        Union-Polygon als [[x,y], [x,y], ...] oder None bei Fehler

    Example:
        >>> polygons = [
        ...     [[2596290, 1199800], [2596300, 1199800], [2596300, 1199810], [2596290, 1199810]],
        ...     [[2596298, 1199800], [2596308, 1199800], [2596308, 1199810], [2596298, 1199810]]
        ... ]
        >>> union = calculate_union_polygon(polygons)
        >>> # Ergebnis: Äussere Kontur beider Polygone
    """
    if not polygons:
        return None

    try:
        from shapely.geometry import Polygon as ShapelyPolygon
        from shapely.ops import unary_union

        # Polygone zu Shapely konvertieren
        shapely_polygons = []
        for poly in polygons:
            if poly and len(poly) >= 3:
                coords = [(p[0], p[1]) for p in poly]
                try:
                    shapely_poly = ShapelyPolygon(coords)
                    if shapely_poly.is_valid:
                        shapely_polygons.append(shapely_poly)
                    else:
                        # Versuche zu reparieren
                        repaired = shapely_poly.buffer(0)
                        if repaired.is_valid and not repaired.is_empty:
                            shapely_polygons.append(repaired)
                except Exception as e:
                    logger.warning(f"[calculate_union_polygon] Ungültiges Polygon übersprungen: {e}")
                    continue

        if not shapely_polygons:
            return None

        # Single-Building: Polygon direkt zurückgeben
        if len(shapely_polygons) == 1:
            single = shapely_polygons[0]
            return [
                [round(c[0], round_decimals), round(c[1], round_decimals)]
                for c in single.exterior.coords
            ]

        # Multi-Building: Union berechnen
        combined = unary_union(shapely_polygons)

        # Ergebnis extrahieren
        if hasattr(combined, 'exterior'):
            # Einfaches Polygon
            return [
                [round(c[0], round_decimals), round(c[1], round_decimals)]
                for c in combined.exterior.coords
            ]
        elif hasattr(combined, 'geoms'):
            # MultiPolygon - nimm das grösste
            largest = max(combined.geoms, key=lambda p: p.area if hasattr(p, 'area') else 0)
            if hasattr(largest, 'exterior'):
                return [
                    [round(c[0], round_decimals), round(c[1], round_decimals)]
                    for c in largest.exterior.coords
                ]

        logger.warning(f"[calculate_union_polygon] Unerwarteter Geometrie-Typ: {type(combined)}")
        return None

    except ImportError:
        logger.error("[calculate_union_polygon] shapely nicht installiert")
        return None
    except Exception as e:
        logger.error(f"[calculate_union_polygon] Fehler: {e}")
        return None


def extract_polygons_from_buildings(
    buildings: List[dict],
    polygon_key: str = "polygon"
) -> List[List[List[float]]]:
    """
    Extrahiert Polygone aus einer Liste von Building-Dicts.

    Args:
        buildings: Liste von Building-Dicts mit polygon-Feld
        polygon_key: Name des Polygon-Felds (default: "polygon")

    Returns:
        Liste von Polygonen
    """
    import json

    polygons = []
    for b in buildings:
        polygon = b.get(polygon_key)
        if polygon:
            # Falls JSON-String, parsen
            if isinstance(polygon, str):
                try:
                    polygon = json.loads(polygon)
                except (json.JSONDecodeError, TypeError):
                    continue
            if polygon and len(polygon) >= 3:
                polygons.append(polygon)
    return polygons
