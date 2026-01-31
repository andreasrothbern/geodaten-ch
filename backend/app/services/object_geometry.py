"""
Zentralisierte Geometrie-Berechnungen für Objekte.

NEU 30.01.2026: Zentralisiert Centroid-Berechnungen die vorher
an mehreren Stellen dupliziert waren.

Verwendung:
    from app.services.object_geometry import (
        calculate_centroid_from_bundles,
        calculate_centroid_from_buildings,
        calculate_centroid_from_polygon,
        calculate_union_polygon,
    )
"""

from typing import Any, Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


def calculate_centroid_from_bundles(
    bundles: List[Any],
    coord_attr_e: str = "lv95_e",
    coord_attr_n: str = "lv95_n"
) -> Tuple[Optional[float], Optional[float]]:
    """
    Berechnet den Centroid (arithmetisches Mittel) aus BuildingDataBundle-Objekten.

    Args:
        bundles: Liste von BuildingDataBundle oder ähnlichen Objekten
        coord_attr_e: Name des E-Koordinaten-Attributs (default: lv95_e)
        coord_attr_n: Name des N-Koordinaten-Attributs (default: lv95_n)

    Returns:
        (center_e, center_n) oder (None, None) wenn keine Koordinaten vorhanden

    Example:
        center_e, center_n = calculate_centroid_from_bundles(bundles)
        if center_e and center_n:
            # Prefetch schedulen...
    """
    if not bundles:
        return (None, None)

    coords_e = [getattr(b, coord_attr_e, None) for b in bundles]
    coords_n = [getattr(b, coord_attr_n, None) for b in bundles]

    valid_e = [e for e in coords_e if e is not None]
    valid_n = [n for n in coords_n if n is not None]

    if not valid_e or not valid_n:
        return (None, None)

    return (sum(valid_e) / len(valid_e), sum(valid_n) / len(valid_n))


def calculate_centroid_from_buildings(
    buildings: List[Dict[str, Any]],
    key_e: str = "center_e",
    key_n: str = "center_n"
) -> Tuple[float, float]:
    """
    Berechnet den Centroid aus einer Liste von Building-Dicts.

    Args:
        buildings: Liste von Dicts mit Koordinaten
        key_e: Dict-Key für E-Koordinate (default: center_e)
        key_n: Dict-Key für N-Koordinate (default: center_n)

    Returns:
        (center_e, center_n) oder (0.0, 0.0) wenn keine gültigen Daten

    Example:
        buildings_data = [{"center_e": 2600450, "center_n": 1199830}, ...]
        center_e, center_n = calculate_centroid_from_buildings(buildings_data)
    """
    if not buildings:
        return (0.0, 0.0)

    total_e = 0.0
    total_n = 0.0
    count = 0

    for b in buildings:
        e = b.get(key_e)
        n = b.get(key_n)
        if e is not None and n is not None:
            total_e += e
            total_n += n
            count += 1

    if count == 0:
        return (0.0, 0.0)

    return (total_e / count, total_n / count)


def calculate_centroid_from_polygon(
    polygon: List[List[float]]
) -> Tuple[Optional[float], Optional[float]]:
    """
    Berechnet den Centroid eines Polygons (arithmetisches Mittel der Punkte).

    HINWEIS: Dies ist der geometrische Schwerpunkt der Polygon-Punkte,
    NICHT der Flächenschwerpunkt. Für präzise Flächenschwerpunkt-Berechnung
    verwende calculate_centroid_from_shapely().

    Args:
        polygon: Liste von [e, n] Koordinatenpaaren

    Returns:
        (center_e, center_n) oder (None, None) wenn Polygon leer

    Example:
        polygon = [[2600450, 1199830], [2600460, 1199830], ...]
        center_e, center_n = calculate_centroid_from_polygon(polygon)
    """
    if not polygon:
        return (None, None)

    center_e = sum(p[0] for p in polygon) / len(polygon)
    center_n = sum(p[1] for p in polygon) / len(polygon)

    return (center_e, center_n)


def calculate_centroid_from_shapely(geometry) -> Tuple[Optional[float], Optional[float]]:
    """
    Berechnet den präzisen Flächenschwerpunkt einer Shapely-Geometrie.

    Args:
        geometry: Shapely Polygon, MultiPolygon oder andere Geometrie

    Returns:
        (center_e, center_n) oder (None, None) wenn ungültig

    Example:
        from shapely.geometry import Polygon
        poly = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
        center_e, center_n = calculate_centroid_from_shapely(poly)
    """
    if geometry is None:
        return (None, None)

    try:
        centroid = geometry.centroid
        return (centroid.x, centroid.y)
    except Exception as e:
        logger.warning(f"[GEOMETRY] Fehler bei Centroid-Berechnung: {e}")
        return (None, None)


def calculate_union_polygon(
    polygons: List[List[List[float]]]
) -> Optional[List[List[float]]]:
    """
    Berechnet die Union mehrerer Polygone und gibt das Ergebnis-Polygon zurück.

    Args:
        polygons: Liste von Polygonen (je als Liste von [e, n] Paaren)

    Returns:
        Union-Polygon als Liste von [e, n] Paaren oder None bei Fehler

    Example:
        polygons = [
            [[0, 0], [10, 0], [10, 10], [0, 10]],  # Gebäude 1
            [[5, 5], [15, 5], [15, 15], [5, 15]],  # Gebäude 2 (überlappend)
        ]
        union = calculate_union_polygon(polygons)
    """
    if not polygons:
        return None

    try:
        from shapely.geometry import Polygon
        from shapely.ops import unary_union

        shapely_polygons = []
        for poly_coords in polygons:
            if len(poly_coords) >= 3:
                shapely_polygons.append(Polygon(poly_coords))

        if not shapely_polygons:
            return None

        combined = unary_union(shapely_polygons)

        if hasattr(combined, 'exterior'):
            # Einfaches Polygon
            return [
                [round(c[0], 2), round(c[1], 2)]
                for c in combined.exterior.coords
            ]
        elif hasattr(combined, 'geoms'):
            # MultiPolygon - nehme das größte
            largest = max(combined.geoms, key=lambda p: p.area)
            if hasattr(largest, 'exterior'):
                return [
                    [round(c[0], 2), round(c[1], 2)]
                    for c in largest.exterior.coords
                ]

        return None

    except Exception as e:
        logger.warning(f"[GEOMETRY] Fehler bei Union-Berechnung: {e}")
        return None


def get_bounding_box(
    polygon: List[List[float]]
) -> Optional[Dict[str, float]]:
    """
    Berechnet die Bounding-Box eines Polygons.

    Args:
        polygon: Liste von [e, n] Koordinatenpaaren

    Returns:
        Dict mit min_e, max_e, min_n, max_n oder None

    Example:
        bbox = get_bounding_box(polygon)
        width = bbox['max_e'] - bbox['min_e']
    """
    if not polygon:
        return None

    es = [p[0] for p in polygon]
    ns = [p[1] for p in polygon]

    return {
        "min_e": min(es),
        "max_e": max(es),
        "min_n": min(ns),
        "max_n": max(ns),
    }
