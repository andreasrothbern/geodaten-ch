"""
Polygon Simplifier Service
==========================

On-the-fly Vereinfachung von Gebäude-Polygonen.

Funktionen:
- Douglas-Peucker Vereinfachung
- Kollineare Segment-Verschmelzung
- Fassaden-Berechnung (sides)
- Dynamische Epsilon-Berechnung basierend auf Umfang

Verwendung:
- Polygon wird IMMER original gespeichert
- Vereinfachung erfolgt on-the-fly bei API-Aufrufen
- Erlaubt verschiedene Epsilon-Werte für verschiedene Anwendungen

Stand: 03.01.2026
"""

import math
from typing import List, Tuple, Dict, Any, Optional
from dataclasses import dataclass


# Default-Parameter
DEFAULT_SIMPLIFY_EPSILON = 0.3  # Meter
DEFAULT_COLLINEAR_ANGLE_TOLERANCE = 8.0  # Grad


@dataclass
class SimplificationResult:
    """Ergebnis der Polygon-Vereinfachung."""
    polygon: List[List[float]]  # Vereinfachtes Polygon [[e, n], ...]
    epsilon_used: float
    angle_tolerance_used: float
    original_point_count: int
    simplified_point_count: int
    sides: List[Dict[str, Any]]  # Berechnete Fassaden
    perimeter_m: float
    area_m2: float


def simplify_building_polygon(
    polygon: List[List[float]],
    epsilon: Optional[float] = None,
    angle_tolerance: float = DEFAULT_COLLINEAR_ANGLE_TOLERANCE,
    use_dynamic_epsilon: bool = True
) -> SimplificationResult:
    """
    Vereinfacht ein Gebäude-Polygon für Gerüstplanung.

    Kombiniert Douglas-Peucker mit kollinearer Segment-Verschmelzung.

    Args:
        polygon: Original-Polygon [[e, n], ...]
        epsilon: Douglas-Peucker Toleranz in Metern (None = dynamisch)
        angle_tolerance: Winkeltoleranz für kollineare Segmente (Grad)
        use_dynamic_epsilon: Wenn True und epsilon=None, wird epsilon
                            basierend auf Gebäudegrösse berechnet

    Returns:
        SimplificationResult mit vereinfachtem Polygon und Metadaten
    """
    if not polygon or len(polygon) < 3:
        return SimplificationResult(
            polygon=polygon or [],
            epsilon_used=0,
            angle_tolerance_used=angle_tolerance,
            original_point_count=len(polygon) if polygon else 0,
            simplified_point_count=len(polygon) if polygon else 0,
            sides=[],
            perimeter_m=0,
            area_m2=0
        )

    original_count = len(polygon)

    # Polygon zu Tupeln konvertieren für Berechnung
    polygon_tuples = [(p[0], p[1]) for p in polygon]

    # Umfang berechnen (für dynamisches Epsilon)
    perimeter = _calculate_perimeter(polygon_tuples)

    # Epsilon bestimmen
    if epsilon is None and use_dynamic_epsilon:
        epsilon = _calculate_dynamic_epsilon(perimeter)
    elif epsilon is None:
        epsilon = DEFAULT_SIMPLIFY_EPSILON

    # 1. Douglas-Peucker Vereinfachung
    simplified = _simplify_polygon_douglas_peucker(polygon_tuples, epsilon)

    # 2. Kollineare Segmente verschmelzen
    simplified = _merge_collinear_segments(simplified, angle_tolerance)

    # Zurück zu Listen-Format
    polygon_simplified = [[p[0], p[1]] for p in simplified]

    # 3. Fassaden berechnen
    sides = _calculate_sides(polygon_simplified)

    # 4. Fläche berechnen
    area = _calculate_polygon_area(polygon_simplified)

    # Neuer Umfang (aus vereinfachtem Polygon)
    new_perimeter = sum(s["length_m"] for s in sides)

    return SimplificationResult(
        polygon=polygon_simplified,
        epsilon_used=epsilon,
        angle_tolerance_used=angle_tolerance,
        original_point_count=original_count,
        simplified_point_count=len(polygon_simplified),
        sides=sides,
        perimeter_m=round(new_perimeter, 2),
        area_m2=round(area, 2)
    )


def calculate_sides_from_polygon(
    polygon: List[List[float]]
) -> List[Dict[str, Any]]:
    """
    Berechnet Fassaden-Segmente aus einem Polygon (ohne Vereinfachung).

    Args:
        polygon: Polygon [[e, n], ...]

    Returns:
        Liste von Fassaden-Dictionaries
    """
    return _calculate_sides(polygon)


def _calculate_perimeter(polygon: List[Tuple[float, float]]) -> float:
    """Berechnet den Umfang eines Polygons."""
    if len(polygon) < 2:
        return 0

    total = 0
    for i in range(len(polygon) - 1):
        dx = polygon[i + 1][0] - polygon[i][0]
        dy = polygon[i + 1][1] - polygon[i][1]
        total += math.sqrt(dx * dx + dy * dy)

    return total


def _calculate_dynamic_epsilon(perimeter: float) -> float:
    """
    Berechnet dynamisches Epsilon basierend auf Gebäudegrösse.

    Grössere Gebäude vertragen mehr Vereinfachung.

    Args:
        perimeter: Umfang in Metern

    Returns:
        Epsilon in Metern
    """
    if perimeter > 200:  # Grosses Gebäude (öffentlich, Industrie)
        return 1.5
    elif perimeter > 50:  # MFH
        return 0.8
    else:  # EFH
        return 0.3


def _calculate_sides(polygon: List[List[float]]) -> List[Dict[str, Any]]:
    """
    Berechnet Fassaden-Segmente aus Polygon.

    Jede Seite enthält:
    - index: Segment-Index
    - start, end: Koordinaten
    - length_m: Länge in Metern
    - azimuth_deg: Richtung (0=Nord, 90=Ost)
    - direction: Himmelsrichtung (N, NE, E, ...)
    """
    if not polygon or len(polygon) < 2:
        return []

    sides = []

    for i in range(len(polygon) - 1):
        p1 = polygon[i]
        p2 = polygon[i + 1]

        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        length = math.sqrt(dx * dx + dy * dy)

        # Azimut berechnen (0 = Nord, im Uhrzeigersinn)
        azimuth = math.degrees(math.atan2(dx, dy))
        if azimuth < 0:
            azimuth += 360

        # Himmelsrichtung
        direction = _azimuth_to_direction(azimuth)

        sides.append({
            "index": i,
            "start": {"x": p1[0], "y": p1[1]},
            "end": {"x": p2[0], "y": p2[1]},
            "start_point": p1,  # Legacy-Format
            "end_point": p2,    # Legacy-Format
            "length_m": round(length, 2),
            "azimuth_deg": round(azimuth, 1),
            "angle_deg": round(azimuth, 1),  # Alias für Frontend
            "direction": direction
        })

    return sides


def _azimuth_to_direction(azimuth: float) -> str:
    """Konvertiert Azimut (0-360) zu Himmelsrichtung."""
    azimuth = azimuth % 360

    if azimuth >= 337.5 or azimuth < 22.5:
        return "N"
    elif azimuth < 67.5:
        return "NE"
    elif azimuth < 112.5:
        return "E"
    elif azimuth < 157.5:
        return "SE"
    elif azimuth < 202.5:
        return "S"
    elif azimuth < 247.5:
        return "SW"
    elif azimuth < 292.5:
        return "W"
    else:
        return "NW"


def _calculate_polygon_area(polygon: List[List[float]]) -> float:
    """
    Berechnet die Fläche eines Polygons (Shoelace-Formel).
    """
    if len(polygon) < 3:
        return 0

    n = len(polygon)
    area = 0

    for i in range(n - 1):
        area += polygon[i][0] * polygon[i + 1][1]
        area -= polygon[i + 1][0] * polygon[i][1]

    # Polygon schliessen falls nötig
    if polygon[0] != polygon[-1]:
        area += polygon[-1][0] * polygon[0][1]
        area -= polygon[0][0] * polygon[-1][1]

    return abs(area) / 2


def _simplify_polygon_douglas_peucker(
    polygon: List[Tuple[float, float]],
    epsilon: float = 0.5
) -> List[Tuple[float, float]]:
    """
    Douglas-Peucker Algorithmus zur Polygon-Vereinfachung.

    Reduziert die Anzahl der Punkte, behält aber die Form bei.

    Args:
        polygon: Liste von (x, y) Koordinaten
        epsilon: Toleranz in Metern (grösser = weniger Punkte)

    Returns:
        Vereinfachtes Polygon
    """
    if len(polygon) < 3:
        return polygon

    def perpendicular_distance(point, line_start, line_end):
        """Senkrechter Abstand eines Punktes zu einer Linie"""
        if line_start == line_end:
            return math.sqrt((point[0] - line_start[0])**2 + (point[1] - line_start[1])**2)

        # Linienvektor
        dx = line_end[0] - line_start[0]
        dy = line_end[1] - line_start[1]
        line_length = math.sqrt(dx*dx + dy*dy)

        if line_length == 0:
            return math.sqrt((point[0] - line_start[0])**2 + (point[1] - line_start[1])**2)

        # Normalisierter Vektor
        dx /= line_length
        dy /= line_length

        # Projektion des Punktes auf die Linie
        t = (point[0] - line_start[0]) * dx + (point[1] - line_start[1]) * dy

        # Nächster Punkt auf der Linie
        nearest_x = line_start[0] + t * dx
        nearest_y = line_start[1] + t * dy

        return math.sqrt((point[0] - nearest_x)**2 + (point[1] - nearest_y)**2)

    def simplify_recursive(points, start, end, epsilon):
        """Rekursive Vereinfachung"""
        if end - start < 2:
            return [points[start]]

        # Finde den Punkt mit maximaler Distanz zur Linie start-end
        max_dist = 0
        max_idx = start

        for i in range(start + 1, end):
            dist = perpendicular_distance(points[i], points[start], points[end])
            if dist > max_dist:
                max_dist = dist
                max_idx = i

        if max_dist > epsilon:
            # Rekursiv beide Teile vereinfachen
            left = simplify_recursive(points, start, max_idx, epsilon)
            right = simplify_recursive(points, max_idx, end, epsilon)
            return left + right
        else:
            # Alle Zwischenpunkte entfernen
            return [points[start]]

    # Prüfen ob geschlossen
    closed = polygon[-1] == polygon[0]
    if closed:
        polygon = polygon[:-1]

    result = simplify_recursive(polygon, 0, len(polygon) - 1, epsilon)
    result.append(polygon[-1])

    if closed:
        result.append(result[0])

    return result


def _merge_collinear_segments(
    polygon: List[Tuple[float, float]],
    angle_tolerance_deg: float = 10.0,
    min_length_m: float = 1.0
) -> List[Tuple[float, float]]:
    """
    Verschmilzt fast parallele (kollineare) Segmente zu einem.

    Entfernt Punkte zwischen Segmenten, die fast die gleiche Richtung haben.

    Args:
        polygon: Liste von (x, y) Koordinaten
        angle_tolerance_deg: Maximale Winkelabweichung für Verschmelzung
        min_length_m: Minimale Segmentlänge

    Returns:
        Vereinfachtes Polygon mit weniger Segmenten
    """
    if len(polygon) < 4:
        return polygon

    def segment_angle(p1, p2):
        """Winkel eines Segments in Grad"""
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        return math.degrees(math.atan2(dy, dx))

    def angle_difference(a1, a2):
        """Winkeldifferenz (0-180)"""
        diff = abs(a1 - a2) % 360
        return min(diff, 360 - diff)

    # Prüfen ob geschlossen
    closed = polygon[-1] == polygon[0]
    if closed:
        polygon = polygon[:-1]

    result = [polygon[0]]
    current_angle = segment_angle(polygon[0], polygon[1])

    for i in range(1, len(polygon) - 1):
        next_angle = segment_angle(polygon[i], polygon[i + 1])

        if angle_difference(current_angle, next_angle) > angle_tolerance_deg:
            # Signifikante Richtungsänderung -> Punkt behalten
            result.append(polygon[i])
            current_angle = next_angle

    # Letzten Punkt hinzufügen
    result.append(polygon[-1])

    if closed:
        result.append(result[0])

    return result


# Singleton für einfachen Zugriff
_simplifier_instance = None


class PolygonSimplifier:
    """Service-Wrapper für Polygon-Vereinfachung."""

    def simplify(
        self,
        polygon: List[List[float]],
        epsilon: Optional[float] = None,
        angle_tolerance: float = DEFAULT_COLLINEAR_ANGLE_TOLERANCE
    ) -> SimplificationResult:
        """Vereinfacht ein Polygon."""
        return simplify_building_polygon(polygon, epsilon, angle_tolerance)

    def calculate_sides(self, polygon: List[List[float]]) -> List[Dict[str, Any]]:
        """Berechnet Fassaden aus Polygon."""
        return calculate_sides_from_polygon(polygon)


def get_polygon_simplifier() -> PolygonSimplifier:
    """Gibt Singleton-Instanz zurück."""
    global _simplifier_instance
    if _simplifier_instance is None:
        _simplifier_instance = PolygonSimplifier()
    return _simplifier_instance
