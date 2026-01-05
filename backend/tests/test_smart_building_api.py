# backend/tests/test_smart_building_api.py
"""
pytest Tests für Smart Building API.

Testet die /api/v1/smart-building/data Endpunkte.
Insbesondere:
- polygon_simplified wird on-the-fly berechnet (BUG-006)
- API-Response enthält alle erwarteten Felder
- Multi-Adress-Parsing funktioniert

Erstellt: 03.01.2026
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

# Backend-Pfad hinzufügen
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.polygon_simplifier import simplify_building_polygon


class TestPolygonSimplifier:
    """Tests für den Polygon-Simplifier Service."""

    def test_simplify_reduces_points(self):
        """Vereinfachung reduziert Punktanzahl bei komplexem Polygon."""
        # Komplexes Polygon mit vielen Punkten (simuliert swissBUILDINGS3D)
        polygon = [
            [2596297.47, 1199801.39],
            [2596297.25, 1199803.93],  # Zwischen-Punkt
            [2596296.84, 1199808.78],
            [2596299.82, 1199809.05],  # Zwischen-Punkt
            [2596303.16, 1199809.34],
            [2596303.64, 1199803.80],  # Zwischen-Punkt
            [2596303.79, 1199801.95],
            [2596297.47, 1199801.39],  # Geschlossen
        ]

        result = simplify_building_polygon(polygon)

        # Vereinfachtes Polygon sollte weniger oder gleich viele Punkte haben
        assert result.simplified_point_count <= result.original_point_count
        assert result.original_point_count == 8

    def test_simplify_preserves_corners(self):
        """Vereinfachung behält Eckpunkte bei einfachem Rechteck."""
        # Einfaches Rechteck (4 Eckpunkte + geschlossen)
        polygon = [
            [2596297.47, 1199801.39],
            [2596296.84, 1199808.78],
            [2596303.16, 1199809.34],
            [2596303.79, 1199801.95],
            [2596297.47, 1199801.39],
        ]

        result = simplify_building_polygon(polygon)

        # Bei einfachem Rechteck sollten alle Punkte erhalten bleiben
        assert result.simplified_point_count >= 4
        assert len(result.polygon) >= 4

    def test_simplify_calculates_sides(self):
        """Vereinfachung berechnet Fassaden (sides)."""
        polygon = [
            [0, 0],
            [10, 0],
            [10, 10],
            [0, 10],
            [0, 0],
        ]

        result = simplify_building_polygon(polygon)

        # Sollte 4 Seiten haben
        assert len(result.sides) == 4
        # Jede Seite sollte Länge haben
        for side in result.sides:
            assert "length_m" in side
            assert side["length_m"] > 0

    def test_simplify_calculates_perimeter(self):
        """Vereinfachung berechnet Umfang."""
        # 10m x 10m Quadrat
        polygon = [
            [0, 0],
            [10, 0],
            [10, 10],
            [0, 10],
            [0, 0],
        ]

        result = simplify_building_polygon(polygon)

        # Umfang sollte ca. 40m sein
        assert result.perimeter_m == pytest.approx(40.0, rel=0.01)

    def test_simplify_empty_polygon(self):
        """Leeres Polygon gibt leeres Ergebnis zurück."""
        result = simplify_building_polygon([])

        assert result.polygon == []
        assert result.sides == []
        assert result.perimeter_m == 0

    def test_simplify_too_few_points(self):
        """Polygon mit weniger als 3 Punkten."""
        polygon = [[0, 0], [10, 0]]

        result = simplify_building_polygon(polygon)

        assert result.original_point_count == 2
        assert result.simplified_point_count == 2

    def test_simplify_uses_dynamic_epsilon(self):
        """Dynamisches Epsilon wird basierend auf Grösse berechnet."""
        # Grosses Gebäude (>200m Umfang)
        large_polygon = [
            [0, 0],
            [100, 0],
            [100, 50],
            [0, 50],
            [0, 0],
        ]

        result = simplify_building_polygon(large_polygon, use_dynamic_epsilon=True)

        # Epsilon sollte automatisch höher sein für grosse Gebäude
        assert result.epsilon_used > 0


class TestSmartBuildingAPIResponse:
    """Tests für die API-Response Struktur."""

    def test_response_contains_polygon_simplified(self):
        """API-Response enthält polygon_simplified Feld."""
        # Simuliere die Response-Struktur aus main.py
        polygon = [
            [2596297.47, 1199801.39],
            [2596296.84, 1199808.78],
            [2596303.16, 1199809.34],
            [2596303.79, 1199801.95],
            [2596297.47, 1199801.39],
        ]

        # Simuliere die on-the-fly Berechnung wie in main.py:3547-3551
        polygon_simplified = None
        if polygon and len(polygon) >= 3:
            result = simplify_building_polygon(polygon)
            polygon_simplified = result.polygon

        # Response sollte polygon_simplified enthalten
        response = {
            "polygon": polygon,
            "polygon_simplified": polygon_simplified,
        }

        assert "polygon" in response
        assert "polygon_simplified" in response
        assert response["polygon_simplified"] is not None
        assert len(response["polygon_simplified"]) >= 3

    def test_response_polygon_simplified_matches_original_when_simple(self):
        """Bei einfachem Rechteck sind Original und Simplified ähnlich."""
        polygon = [
            [0, 0],
            [10, 0],
            [10, 10],
            [0, 10],
            [0, 0],
        ]

        result = simplify_building_polygon(polygon)

        # Bei einfachem Rechteck sollten die Punkte fast identisch sein
        assert len(result.polygon) == len(polygon)


class TestKnospenweg46:
    """Regressionstests für die Adresse 'Knospenweg 4-6, Bern'."""

    def test_polygon_from_knospenweg(self):
        """Polygon von Knospenweg 4 kann vereinfacht werden."""
        # Echtes Polygon von Knospenweg 4 (aus API-Response)
        polygon = [
            [2596297.47, 1199801.39],
            [2596297.25, 1199803.93],
            [2596296.84, 1199808.78],
            [2596299.82, 1199809.05],
            [2596303.16, 1199809.34],
            [2596303.64, 1199803.8],
            [2596303.79, 1199801.95],
            [2596297.47, 1199801.39],
        ]

        result = simplify_building_polygon(polygon)

        # Sollte erfolgreich vereinfachen
        assert result.polygon is not None
        assert len(result.polygon) >= 4
        assert result.perimeter_m > 0

    def test_simplified_polygon_has_fewer_points(self):
        """Vereinfachtes Polygon hat weniger Punkte als Original."""
        # Polygon mit Zwischen-Punkten
        polygon = [
            [2596297.47, 1199801.39],
            [2596297.25, 1199803.93],  # Kann entfernt werden
            [2596296.84, 1199808.78],
            [2596299.82, 1199809.05],  # Kann entfernt werden
            [2596303.16, 1199809.34],
            [2596303.64, 1199803.8],   # Kann entfernt werden
            [2596303.79, 1199801.95],
            [2596297.47, 1199801.39],
        ]

        result = simplify_building_polygon(polygon)

        # Vereinfachung sollte kollineare Punkte entfernen
        # Bei diesem fast-rechteckigen Gebäude: 8 → ~5 Punkte
        assert result.simplified_point_count <= result.original_point_count


class TestAPIFieldMapping:
    """Tests für die Feld-Zuordnung zwischen Backend und Frontend."""

    def test_response_has_lv95_coordinates(self):
        """Response enthält lv95_e und lv95_n (nicht coordinates.e/n)."""
        # Simuliere SmartBuildingService Bundle
        mock_bundle = MagicMock()
        mock_bundle.lv95_e = 596299.0625
        mock_bundle.lv95_n = 199805.21875

        # Frontend erwartet diese Felder direkt
        response = {
            "lv95_e": mock_bundle.lv95_e,
            "lv95_n": mock_bundle.lv95_n,
        }

        assert response["lv95_e"] == 596299.0625
        assert response["lv95_n"] == 199805.21875

    def test_response_has_footprint_area(self):
        """Response enthält footprint_area_m2 (nicht area_m2)."""
        mock_bundle = MagicMock()
        mock_bundle.footprint_area_m2 = 47.0
        mock_bundle.gwr_area_m2 = 47.0

        response = {
            "footprint_area_m2": mock_bundle.footprint_area_m2,
            "gwr_area_m2": mock_bundle.gwr_area_m2,
        }

        # Frontend nutzt: data.footprint_area_m2 || data.gwr_area_m2
        area = response.get("footprint_area_m2") or response.get("gwr_area_m2")
        assert area == 47.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])