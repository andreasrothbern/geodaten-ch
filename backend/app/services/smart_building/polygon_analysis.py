# backend/app/services/smart_building/polygon_analysis.py
"""
Polygon-Form-Analyse für Gebäudegrundrisse.

TASK 5 aus CLAUDE_TASKS.md:
Erkennt automatisch U-Form, L-Form, etc. basierend auf Konvexitäts-Analyse.

Erstellt: 30.12.2025
"""

import logging
from typing import List, Tuple, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Schwellwerte für Form-Erkennung
CONVEXITY_THRESHOLD_RECTANGULAR = 0.95  # Fast konvex = rechteckig
CONVEXITY_THRESHOLD_L_FORM = 0.85       # Leichte Einbuchtung
CONVEXITY_THRESHOLD_U_FORM = 0.70       # Mittlere Einbuchtung
CONVEXITY_THRESHOLD_H_FORM = 0.55       # Starke Einbuchtung


def analyze_building_shape(polygon_coords: List[Tuple[float, float]]) -> Dict[str, Any]:
    """
    Analysiert die Grundrissform eines Gebäudes basierend auf dem Polygon.

    Erkennt:
    - rechteckig: Konvexitäts-Ratio > 95%
    - L-Form: Ratio 85-95%
    - U-Form: Ratio 70-85%
    - H-Form: Ratio 55-70%
    - komplex: Ratio < 55%

    Args:
        polygon_coords: Liste von (x, y) Koordinaten (LV95)

    Returns:
        dict mit:
        - shape: str (rechteckig, L-Form, U-Form, H-Form, komplex)
        - concavity_ratio: float (0-1, 1=konvex)
        - description: str (Beschreibung für Prompt)
        - bounding_box: dict (width_m, height_m, aspect_ratio)
        - polygon_points: int (Anzahl Punkte)
        - has_courtyard: bool (Innenhof vermutet)
    """
    try:
        from shapely.geometry import Polygon as ShapelyPolygon
    except ImportError:
        logger.error("shapely nicht installiert - pip install shapely")
        return _fallback_result(polygon_coords)

    # Mindestens 4 Punkte für sinnvolle Analyse
    if not polygon_coords or len(polygon_coords) < 4:
        return {
            "shape": "unknown",
            "concavity_ratio": 1.0,
            "description": "Zu wenige Punkte für Form-Analyse",
            "bounding_box": None,
            "polygon_points": len(polygon_coords) if polygon_coords else 0,
            "has_courtyard": False,
        }

    try:
        # Shapely Polygon erstellen
        poly = ShapelyPolygon(polygon_coords)

        # Validierung und Reparatur
        if not poly.is_valid:
            poly = poly.buffer(0)  # Fix self-intersections

        if poly.is_empty:
            return _fallback_result(polygon_coords)

        # Convex Hull berechnen
        convex_hull = poly.convex_hull

        # Konvexitäts-Verhältnis (Area / ConvexHull Area)
        # 1.0 = perfekt konvex, < 1.0 = Einbuchtungen
        if convex_hull.area > 0:
            concavity_ratio = poly.area / convex_hull.area
        else:
            concavity_ratio = 1.0

        # Bounding Box
        minx, miny, maxx, maxy = poly.bounds
        width = maxx - minx
        height = maxy - miny
        aspect_ratio = max(width, height) / min(width, height) if min(width, height) > 0 else 1.0

        # Form bestimmen
        shape, description, has_courtyard = _classify_shape(concavity_ratio, len(polygon_coords))

        return {
            "shape": shape,
            "concavity_ratio": round(concavity_ratio, 3),
            "description": description,
            "bounding_box": {
                "width_m": round(width, 1),
                "height_m": round(height, 1),
                "aspect_ratio": round(aspect_ratio, 2),
            },
            "polygon_points": len(polygon_coords),
            "has_courtyard": has_courtyard,
            "area_m2": round(poly.area, 1),
            "perimeter_m": round(poly.length, 1),
        }

    except Exception as e:
        logger.warning(f"Polygon-Analyse fehlgeschlagen: {e}")
        return _fallback_result(polygon_coords)


def _classify_shape(
    concavity_ratio: float,
    num_points: int
) -> Tuple[str, str, bool]:
    """
    Klassifiziert die Gebäudeform basierend auf Konvexität.

    Returns:
        Tuple (shape, description, has_courtyard)
    """
    if concavity_ratio > CONVEXITY_THRESHOLD_RECTANGULAR:
        return (
            "rechteckig",
            "Einfacher rechteckiger Grundriss ohne Einbuchtungen",
            False
        )

    elif concavity_ratio > CONVEXITY_THRESHOLD_L_FORM:
        return (
            "L-Form",
            "L-förmiger Grundriss mit einer Einbuchtung/Anbau",
            False
        )

    elif concavity_ratio > CONVEXITY_THRESHOLD_U_FORM:
        return (
            "U-Form",
            "U-förmiger Grundriss mit Innenhof oder Ehrenhof. "
            "Die offene Seite sollte als Freifläche (nicht eingerüstet) markiert werden.",
            True  # U-Form hat typischerweise Innenhof
        )

    elif concavity_ratio > CONVEXITY_THRESHOLD_H_FORM:
        return (
            "H-Form",
            "H-förmiger Grundriss mit zwei Innenhöfen oder tiefe Einschnitte. "
            "Komplexe Einrüstung mit mehreren Zugängen erforderlich.",
            True  # H-Form hat typischerweise zwei Innenhöfe
        )

    else:
        return (
            "komplex",
            "Komplexer Grundriss mit mehreren Einbuchtungen und/oder Innenhöfen. "
            "Detaillierte Vor-Ort-Begehung empfohlen.",
            True  # Komplexe Formen haben oft Innenhöfe
        )


def _fallback_result(polygon_coords: Optional[List]) -> Dict[str, Any]:
    """Fallback wenn shapely fehlschlägt oder Daten ungültig."""
    return {
        "shape": "unknown",
        "concavity_ratio": 1.0,
        "description": "Form-Analyse nicht möglich",
        "bounding_box": None,
        "polygon_points": len(polygon_coords) if polygon_coords else 0,
        "has_courtyard": False,
    }


def get_shape_svg_hints(shape_result: Dict[str, Any]) -> Dict[str, str]:
    """
    Generiert SVG-Hinweise basierend auf der erkannten Form.

    Args:
        shape_result: Ergebnis von analyze_building_shape()

    Returns:
        dict mit SVG-Hinweisen für grundriss, ansicht, schnitt
    """
    shape = shape_result.get("shape", "unknown")
    has_courtyard = shape_result.get("has_courtyard", False)

    hints = {
        "grundriss": "",
        "ansicht": "",
        "schnitt": "",
    }

    if shape == "rechteckig":
        hints["grundriss"] = "Einfaches Rechteck zeichnen. Alle Fassaden gleichmässig einrüsten."
        hints["ansicht"] = "Standardansicht mit durchgehender Fassade."
        hints["schnitt"] = "Einfacher Querschnitt ohne Einbuchtungen."

    elif shape == "L-Form":
        hints["grundriss"] = "L-Form zeichnen. Innenecke als potentieller Zugangspunkt markieren."
        hints["ansicht"] = "Zwei Fassadenlängen beachten (langer und kurzer Schenkel)."
        hints["schnitt"] = "Querschnitt durch beide Schenkel zeigen falls relevant."

    elif shape == "U-Form":
        hints["grundriss"] = (
            "U-Form mit Innenhof zeichnen! "
            "Innenhof/Ehrenhof als FREIFLÄCHE markieren (keine Schraffur). "
            "Innenfassaden des Hofes separat berechnen."
        )
        hints["ansicht"] = (
            "Hauptfassade und ggf. Hofansicht separat. "
            "Drei unterschiedliche Fassadenlängen beachten."
        )
        hints["schnitt"] = "Querschnitt durch U-Form mit Innenhof zeigen."

    elif shape == "H-Form":
        hints["grundriss"] = (
            "H-Form mit zwei Innenhöfen zeichnen. "
            "Beide Höfe als Freiflächen markieren. "
            "Komplexe Gerüstführung um alle Fassaden."
        )
        hints["ansicht"] = "Mehrere Fassadenansichten erforderlich."
        hints["schnitt"] = "Querschnitt durch Mittelteil mit beiden Höfen."

    elif shape == "komplex":
        hints["grundriss"] = (
            "Komplexer Grundriss - alle Einbuchtungen und Höfe sorgfältig darstellen. "
            "Freiflächen (Innenhöfe) markieren."
        )
        hints["ansicht"] = "Mehrere Ansichten erforderlich - Hauptfassaden identifizieren."
        hints["schnitt"] = "Mehrere Schnitte für vollständige Darstellung empfohlen."

    return hints


# Hilfsfunktion für Integration in SmartBuildingService
def enrich_bundle_with_shape_analysis(bundle: "BuildingDataBundle") -> None:
    """
    Reichert ein BuildingDataBundle mit Polygon-Form-Analyse an.

    Args:
        bundle: BuildingDataBundle mit polygon-Attribut
    """
    if not bundle.polygon or len(bundle.polygon) < 4:
        return

    try:
        # Polygon-Analyse durchführen
        shape_result = analyze_building_shape(bundle.polygon)

        # Ergebnisse speichern
        bundle.building_shape = shape_result.get("shape")
        bundle.building_shape_description = shape_result.get("description")
        bundle.concavity_ratio = shape_result.get("concavity_ratio")
        bundle.has_courtyard = shape_result.get("has_courtyard", False)

        # SVG-Hints nur setzen wenn noch keine vorhanden (known_buildings haben Priorität)
        if not hasattr(bundle, 'svg_hints') or not bundle.svg_hints:
            bundle.svg_hints = get_shape_svg_hints(shape_result)

        logger.debug(
            f"Shape analysis: {bundle.building_shape} "
            f"(concavity={bundle.concavity_ratio:.2f}, courtyard={bundle.has_courtyard})"
        )

    except Exception as e:
        logger.warning(f"Shape analysis failed: {e}")
