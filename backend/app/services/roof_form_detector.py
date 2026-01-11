"""
Roof Form Detector
==================

Erkennt die Dachform aus 3D-Geometrie des Roof_solid Layers.

Analyse basiert auf:
- Z-Level-Verteilung der Polygon-Punkte
- Räumliche Anordnung der höchsten Punkte (First)
- Geometrische Eigenschaften (Symmetrie, Konvexität)

Unterstützte Dachformen:
- flachdach: Alle Z-Werte nahezu gleich (< 0.5m Differenz)
- satteldach: Linearer First, zwei geneigte Flächen
- pultdach: Asymmetrische Neigung (eine Seite)
- walmdach: First kürzer als Traufe, 4 geneigte Flächen
- zeltdach: Zentrale Spitze, pyramidenförmig
- mansarddach: Gebrochene Neigung (2 verschiedene Winkel)
- komplex: Nicht eindeutig klassifizierbar

Version: 1.0 (11.01.2026)
"""

import math
import logging
from typing import List, Tuple, Optional, Dict, Any
from collections import Counter

logger = logging.getLogger(__name__)


def extract_z_from_geometry(geometry) -> List[float]:
    """
    Extrahiert alle Z-Koordinaten aus einer 3D-Geometrie.

    Args:
        geometry: Shapely Geometry (Polygon, MultiPolygon)

    Returns:
        Liste aller Z-Werte
    """
    z_values = []

    try:
        if hasattr(geometry, 'geoms'):
            # MultiPolygon
            for geom in geometry.geoms:
                z_values.extend(_extract_z_from_single(geom))
        else:
            # Single Polygon
            z_values.extend(_extract_z_from_single(geometry))
    except Exception as e:
        logger.warning(f"Fehler beim Z-Extrahieren: {e}")

    return z_values


def _extract_z_from_single(geom) -> List[float]:
    """Extrahiert Z-Werte aus einem einzelnen Polygon."""
    z_values = []

    if hasattr(geom, 'exterior'):
        for coord in geom.exterior.coords:
            if len(coord) >= 3:
                z_values.append(coord[2])

    if hasattr(geom, 'interiors'):
        for interior in geom.interiors:
            for coord in interior.coords:
                if len(coord) >= 3:
                    z_values.append(coord[2])

    return z_values


def get_points_3d(geometry) -> List[Tuple[float, float, float]]:
    """
    Extrahiert alle 3D-Punkte aus einer Geometrie.

    Returns:
        Liste von (x, y, z) Tuples
    """
    points = []

    try:
        if hasattr(geometry, 'geoms'):
            for geom in geometry.geoms:
                points.extend(_get_points_from_single(geom))
        else:
            points.extend(_get_points_from_single(geometry))
    except Exception as e:
        logger.warning(f"Fehler beim Punkte-Extrahieren: {e}")

    return points


def _get_points_from_single(geom) -> List[Tuple[float, float, float]]:
    """Extrahiert Punkte aus einem einzelnen Polygon."""
    points = []

    if hasattr(geom, 'exterior'):
        for coord in geom.exterior.coords:
            if len(coord) >= 3:
                points.append((coord[0], coord[1], coord[2]))
            elif len(coord) >= 2:
                points.append((coord[0], coord[1], 0.0))

    return points


def centroid_2d(points: List[Tuple]) -> Tuple[float, float]:
    """Berechnet den 2D-Zentroid einer Punktliste."""
    if not points:
        return (0.0, 0.0)

    sum_x = sum(p[0] for p in points)
    sum_y = sum(p[1] for p in points)
    n = len(points)

    return (sum_x / n, sum_y / n)


def calculate_orientation(p1: Tuple[float, float], p2: Tuple[float, float]) -> Optional[str]:
    """
    Berechnet First-Orientierung als Himmelsrichtung.

    Args:
        p1: Erster Punkt (x, y)
        p2: Zweiter Punkt (x, y)

    Returns:
        Orientierung wie 'N-S', 'O-W', 'NO-SW', etc.
    """
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]

    # Bei zu kleiner Differenz keine Orientierung
    if abs(dx) < 0.1 and abs(dy) < 0.1:
        return None

    # Azimut in Grad (0° = Nord, 90° = Ost)
    azimuth = math.degrees(math.atan2(dx, dy)) % 360

    # In Himmelsrichtung konvertieren (First-Verlauf)
    if 337.5 <= azimuth or azimuth < 22.5:
        return 'N-S'
    elif 22.5 <= azimuth < 67.5:
        return 'NO-SW'
    elif 67.5 <= azimuth < 112.5:
        return 'O-W'
    elif 112.5 <= azimuth < 157.5:
        return 'SO-NW'
    elif 157.5 <= azimuth < 202.5:
        return 'N-S'
    elif 202.5 <= azimuth < 247.5:
        return 'SW-NO'
    elif 247.5 <= azimuth < 292.5:
        return 'O-W'
    else:
        return 'NW-SO'


def is_linear_ridge(high_points: List[Tuple], tolerance: float = 2.0) -> bool:
    """
    Prüft ob die höchsten Punkte einen linearen First bilden.

    Ein linearer First ist typisch für Satteldächer.
    """
    if len(high_points) < 2:
        return False

    if len(high_points) == 2:
        return True

    # Erste und letzte Punkte als Referenzlinie
    p1 = high_points[0]
    p2 = high_points[-1]

    # Prüfen ob alle anderen Punkte nahe der Linie sind
    for p in high_points[1:-1]:
        dist = _point_line_distance(p, p1, p2)
        if dist > tolerance:
            return False

    return True


def _point_line_distance(point: Tuple, line_p1: Tuple, line_p2: Tuple) -> float:
    """Berechnet den Abstand eines Punktes zu einer Linie (2D)."""
    x0, y0 = point[0], point[1]
    x1, y1 = line_p1[0], line_p1[1]
    x2, y2 = line_p2[0], line_p2[1]

    # Länge der Linie
    line_len = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
    if line_len < 0.01:
        return math.sqrt((x0 - x1)**2 + (y0 - y1)**2)

    # Abstand
    return abs((y2 - y1) * x0 - (x2 - x1) * y0 + x2 * y1 - y2 * x1) / line_len


def is_pyramid_roof(geometry, high_points: List[Tuple]) -> bool:
    """
    Prüft ob das Dach pyramidenförmig ist (Zeltdach).

    Zeltdach: Zentrale Spitze, alle Seiten geneigt zur Mitte.
    """
    if len(high_points) > 4:
        return False

    # Zentroid der Geometrie
    all_points = get_points_3d(geometry)
    if not all_points:
        return False

    centroid = centroid_2d(all_points)
    high_centroid = centroid_2d(high_points)

    # Prüfen ob höchste Punkte nahe am Zentrum sind
    dist_to_center = math.sqrt(
        (high_centroid[0] - centroid[0])**2 +
        (high_centroid[1] - centroid[1])**2
    )

    # Durchmesser der Geometrie schätzen
    max_dist = 0
    for p in all_points:
        d = math.sqrt((p[0] - centroid[0])**2 + (p[1] - centroid[1])**2)
        max_dist = max(max_dist, d)

    # Spitze sollte nahe am Zentrum sein (< 20% des Durchmessers)
    return dist_to_center < max_dist * 0.2


def is_hipped_roof(low_points: List[Tuple], high_points: List[Tuple]) -> bool:
    """
    Prüft ob das Dach ein Walmdach ist.

    Walmdach: First ist kürzer als die Traufe, 4 geneigte Flächen.
    """
    if len(high_points) < 2:
        return False

    # Länge des Firsts
    high_centroid = centroid_2d(high_points)
    ridge_span = 0
    for p in high_points:
        d = math.sqrt((p[0] - high_centroid[0])**2 + (p[1] - high_centroid[1])**2)
        ridge_span = max(ridge_span, d * 2)

    # Länge der Traufe
    low_centroid = centroid_2d(low_points)
    eave_span = 0
    for p in low_points:
        d = math.sqrt((p[0] - low_centroid[0])**2 + (p[1] - low_centroid[1])**2)
        eave_span = max(eave_span, d * 2)

    # Walmdach: First < 80% der Traufe
    if eave_span > 0.1:
        ratio = ridge_span / eave_span
        return ratio < 0.8 and ratio > 0.1

    return False


def calculate_roof_form(
    z_values: List[float],
    geometry=None
) -> Tuple[str, float, float, Optional[str]]:
    """
    Erkennt Dachform aus 3D-Geometrie.

    Args:
        z_values: Liste aller Z-Koordinaten
        geometry: Optional Shapely Geometry für räumliche Analyse

    Returns:
        Tuple von (roof_form, confidence, angle_deg, orientation)
    """
    if not z_values or len(z_values) < 3:
        return 'unbekannt', 0.0, 0.0, None

    z_min = min(z_values)
    z_max = max(z_values)
    z_range = z_max - z_min

    # 1. Flachdach: Alle Z-Werte nahezu gleich
    if z_range < 0.5:
        return 'flachdach', 0.95, 0.0, None

    # 2. Z-Level-Verteilung analysieren
    z_rounded = [round(z, 1) for z in z_values]
    z_distribution = Counter(z_rounded)
    unique_levels = len(z_distribution)

    # Punkte nach Z-Höhe gruppieren
    points = get_points_3d(geometry) if geometry else []

    if not points:
        # Nur Z-Level-basierte Analyse möglich
        return _analyze_z_levels_only(z_values, z_range, unique_levels)

    # Punkte bei Min und Max Z
    z_tolerance = max(0.3, z_range * 0.05)
    min_z_points = [p for p in points if p[2] < z_min + z_tolerance]
    max_z_points = [p for p in points if p[2] > z_max - z_tolerance]

    if not min_z_points or not max_z_points:
        return _analyze_z_levels_only(z_values, z_range, unique_levels)

    # Zentren berechnen
    min_center = centroid_2d(min_z_points)
    max_center = centroid_2d(max_z_points)

    # Horizontale Distanz
    horiz_dist = math.sqrt(
        (max_center[0] - min_center[0])**2 +
        (max_center[1] - min_center[1])**2
    )

    # Dachneigung berechnen
    if horiz_dist > 0.1:
        angle_deg = math.degrees(math.atan(z_range / horiz_dist))
    else:
        angle_deg = 90.0  # Spitzer Turm

    # First-Orientierung
    orientation = calculate_orientation(min_center, max_center)

    # 3. Dachform erkennen

    # Satteldach: 2-4 Z-Levels, lineare Verteilung, moderate Neigung
    if 2 <= unique_levels <= 6 and 15 < angle_deg < 50:
        if is_linear_ridge(max_z_points):
            return 'satteldach', 0.85, angle_deg, orientation

    # Pultdach: Asymmetrische Verteilung, flache Neigung
    if unique_levels == 2 and 5 < angle_deg < 30:
        # Prüfen ob nur eine Seite geneigt
        return 'pultdach', 0.80, angle_deg, orientation

    # Walmdach: First kürzer als Traufe, 4 geneigte Flächen
    if 3 <= unique_levels <= 6 and 15 < angle_deg < 45:
        if is_hipped_roof(min_z_points, max_z_points):
            return 'walmdach', 0.75, angle_deg, orientation

    # Zeltdach: Zentrale Spitze
    if unique_levels >= 3 and len(max_z_points) <= 4:
        if is_pyramid_roof(geometry, max_z_points):
            return 'zeltdach', 0.70, angle_deg, None

    # Steile Neigung ohne klare Form
    if angle_deg > 50:
        return 'komplex', 0.50, angle_deg, orientation

    # Fallback: Komplex
    return 'komplex', 0.50, angle_deg, orientation


def _analyze_z_levels_only(
    z_values: List[float],
    z_range: float,
    unique_levels: int
) -> Tuple[str, float, float, Optional[str]]:
    """
    Fallback-Analyse nur basierend auf Z-Werten.

    Verwendet wenn keine räumliche Geometrie verfügbar ist.
    """
    # Grobe Neigungsschätzung (ohne horizontale Distanz)
    # Annahme: Typische Dachbreite ~10m
    estimated_width = 10.0
    angle_deg = math.degrees(math.atan(z_range / (estimated_width / 2)))

    if z_range < 0.5:
        return 'flachdach', 0.90, 0.0, None

    if unique_levels <= 2 and angle_deg < 30:
        return 'pultdach', 0.60, angle_deg, None

    if unique_levels <= 4 and angle_deg < 50:
        return 'satteldach', 0.60, angle_deg, None

    return 'komplex', 0.40, angle_deg, None


def analyze_roof(geometry) -> Dict[str, Any]:
    """
    Vollständige Dachanalyse für ein Gebäude.

    Args:
        geometry: Shapely 3D-Geometrie des Roof_solid

    Returns:
        Dict mit roof_form, confidence, angle_deg, orientation, z_levels
    """
    z_values = extract_z_from_geometry(geometry)

    if not z_values:
        return {
            "roof_form": "unbekannt",
            "confidence": 0.0,
            "angle_deg": 0.0,
            "orientation": None,
            "z_levels": [],
            "z_min": None,
            "z_max": None
        }

    roof_form, confidence, angle_deg, orientation = calculate_roof_form(z_values, geometry)

    # Einzigartige Z-Levels für Speicherung
    unique_z = sorted(set(round(z, 2) for z in z_values))

    return {
        "roof_form": roof_form,
        "confidence": round(confidence, 2),
        "angle_deg": round(angle_deg, 1),
        "orientation": orientation,
        "z_levels": unique_z[:20],  # Max 20 Levels speichern
        "z_min": round(min(z_values), 2),
        "z_max": round(max(z_values), 2)
    }
