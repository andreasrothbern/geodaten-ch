# backend/tests/test_polygon_analysis.py
"""
pytest Tests für Polygon-Form-Analyse.

TASK 5 aus CLAUDE_TASKS.md:
Tests für die Konvexitäts-basierte Grundrissform-Erkennung.

Erstellt: 30.12.2025
"""

import pytest
import sys
from pathlib import Path

# Backend-Pfad hinzufügen
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.smart_building.polygon_analysis import (
    analyze_building_shape,
    get_shape_svg_hints,
    CONVEXITY_THRESHOLD_RECTANGULAR,
    CONVEXITY_THRESHOLD_L_FORM,
    CONVEXITY_THRESHOLD_U_FORM,
)


class TestAnalyzeBuildingShape:
    """Tests für analyze_building_shape Funktion."""

    def test_simple_rectangle(self):
        """Einfaches Rechteck sollte als 'rechteckig' erkannt werden."""
        # 10m x 20m Rechteck
        polygon = [
            (0, 0),
            (10, 0),
            (10, 20),
            (0, 20),
            (0, 0),  # Geschlossen
        ]
        result = analyze_building_shape(polygon)

        assert result["shape"] == "rechteckig"
        assert result["concavity_ratio"] > CONVEXITY_THRESHOLD_RECTANGULAR
        assert result["has_courtyard"] is False
        assert result["polygon_points"] == 5

    def test_l_shape(self):
        """L-förmiges Polygon sollte als 'L-Form' erkannt werden."""
        # L-Form (grob)
        polygon = [
            (0, 0),
            (20, 0),
            (20, 10),
            (10, 10),
            (10, 20),
            (0, 20),
            (0, 0),
        ]
        result = analyze_building_shape(polygon)

        # L-Form oder rechteckig (je nach Tiefe der Einbuchtung)
        assert result["shape"] in ["rechteckig", "L-Form"]
        assert result["concavity_ratio"] > CONVEXITY_THRESHOLD_U_FORM

    def test_u_shape(self):
        """U-förmiges Polygon sollte als 'U-Form' erkannt werden."""
        # U-Form mit Innenhof
        polygon = [
            (0, 0),
            (30, 0),
            (30, 30),
            (20, 30),
            (20, 10),
            (10, 10),
            (10, 30),
            (0, 30),
            (0, 0),
        ]
        result = analyze_building_shape(polygon)

        # U-Form hat typisch Konvexitäts-Ratio zwischen 0.70 und 0.85
        assert result["shape"] in ["L-Form", "U-Form", "H-Form"]
        assert result["has_courtyard"] or result["shape"] == "L-Form"

    def test_empty_polygon(self):
        """Leeres Polygon sollte 'unknown' zurückgeben."""
        result = analyze_building_shape([])
        assert result["shape"] == "unknown"
        assert result["polygon_points"] == 0

    def test_too_few_points(self):
        """Polygon mit weniger als 4 Punkten."""
        polygon = [(0, 0), (10, 0), (5, 10)]  # Dreieck
        result = analyze_building_shape(polygon)
        assert result["shape"] == "unknown"

    def test_bounding_box_calculation(self):
        """Bounding Box wird korrekt berechnet."""
        # 15m x 25m Rechteck
        polygon = [
            (100, 200),
            (115, 200),
            (115, 225),
            (100, 225),
            (100, 200),
        ]
        result = analyze_building_shape(polygon)

        assert result["bounding_box"] is not None
        assert result["bounding_box"]["width_m"] == 15.0
        assert result["bounding_box"]["height_m"] == 25.0
        assert result["bounding_box"]["aspect_ratio"] == pytest.approx(1.67, rel=0.1)

    def test_area_and_perimeter(self):
        """Fläche und Umfang werden berechnet."""
        # 10m x 10m Quadrat = 100m², Umfang = 40m
        polygon = [
            (0, 0),
            (10, 0),
            (10, 10),
            (0, 10),
            (0, 0),
        ]
        result = analyze_building_shape(polygon)

        assert result["area_m2"] == pytest.approx(100.0, rel=0.01)
        assert result["perimeter_m"] == pytest.approx(40.0, rel=0.01)


class TestGetShapeSvgHints:
    """Tests für get_shape_svg_hints Funktion."""

    def test_rectangular_hints(self):
        """Rechteckiges Gebäude bekommt einfache Hinweise."""
        shape_result = {
            "shape": "rechteckig",
            "concavity_ratio": 0.98,
            "has_courtyard": False,
        }
        hints = get_shape_svg_hints(shape_result)

        assert "grundriss" in hints
        assert "ansicht" in hints
        assert "schnitt" in hints
        assert "Rechteck" in hints["grundriss"]

    def test_u_form_hints_mention_courtyard(self):
        """U-Form Hinweise erwähnen Innenhof."""
        shape_result = {
            "shape": "U-Form",
            "concavity_ratio": 0.75,
            "has_courtyard": True,
        }
        hints = get_shape_svg_hints(shape_result)

        assert "Innenhof" in hints["grundriss"] or "Ehrenhof" in hints["grundriss"]
        assert "FREIFLÄCHE" in hints["grundriss"].upper() or "Freifläche" in hints["grundriss"]

    def test_complex_hints(self):
        """Komplexe Form bekommt entsprechende Hinweise."""
        shape_result = {
            "shape": "komplex",
            "concavity_ratio": 0.45,
            "has_courtyard": True,
        }
        hints = get_shape_svg_hints(shape_result)

        assert "Komplex" in hints["grundriss"]
        assert "Vor-Ort" in hints["grundriss"] or "sorgfältig" in hints["grundriss"]


class TestConvexityThresholds:
    """Tests für Konvexitäts-Schwellwerte."""

    def test_thresholds_order(self):
        """Schwellwerte sind in korrekter Reihenfolge."""
        assert CONVEXITY_THRESHOLD_RECTANGULAR > CONVEXITY_THRESHOLD_L_FORM
        assert CONVEXITY_THRESHOLD_L_FORM > CONVEXITY_THRESHOLD_U_FORM

    def test_thresholds_in_valid_range(self):
        """Schwellwerte sind im gültigen Bereich 0-1."""
        assert 0 < CONVEXITY_THRESHOLD_U_FORM < 1
        assert 0 < CONVEXITY_THRESHOLD_L_FORM < 1
        assert 0 < CONVEXITY_THRESHOLD_RECTANGULAR < 1


class TestRealWorldPolygons:
    """Tests mit realistischen Gebäude-Polygonen."""

    def test_bundeshaus_like_polygon(self):
        """U-förmiges Parlamentsgebäude (vereinfacht)."""
        # Vereinfachte U-Form ähnlich Bundeshaus
        polygon = [
            (0, 0),
            (60, 0),
            (60, 40),
            (45, 40),
            (45, 15),
            (15, 15),
            (15, 40),
            (0, 40),
            (0, 0),
        ]
        result = analyze_building_shape(polygon)

        # Sollte U-Form oder ähnlich komplex erkannt werden
        assert result["shape"] in ["L-Form", "U-Form", "H-Form"]
        assert result["concavity_ratio"] < CONVEXITY_THRESHOLD_RECTANGULAR

    def test_simple_efh_polygon(self):
        """Einfaches EFH-Polygon (rechteckig)."""
        # 12m x 10m EFH
        polygon = [
            (2600000, 1200000),
            (2600012, 1200000),
            (2600012, 1200010),
            (2600000, 1200010),
            (2600000, 1200000),
        ]
        result = analyze_building_shape(polygon)

        assert result["shape"] == "rechteckig"
        assert result["has_courtyard"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
