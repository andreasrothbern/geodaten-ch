"""
Tests für die Neighbors-API und NeighborsService.

Testet:
1. Polygon-Distanz-Berechnung
2. Richtungs-Berechnung
3. Nachbar-Erkennung
4. Reihenhäuser-Szenarien
5. Umgebungs-Szenarien

HINWEIS (04.01.2026): Umgestellt von geodata_service auf neighbors_service.
"""

import pytest
import math
from typing import List, Tuple

from app.services.neighbors_service import (
    NeighborsService,
    NeighborBuilding,
    NeighborsResult,
    get_neighbors_service,
)

# Die internen Hilfsfunktionen sind jetzt private Methoden der Klasse
# Wir holen eine Instanz und greifen auf die Methoden zu
_service = NeighborsService()
_polygon_distance = _service._polygon_distance
_point_to_segment_distance = _service._point_to_segment_distance
_calculate_direction = _service._calculate_direction


class TestPointToSegmentDistance:
    """Tests für Punkt-zu-Segment Distanzberechnung."""

    def test_point_on_segment(self):
        """Punkt liegt auf der Strecke → Distanz 0."""
        p = (5, 0)
        a = (0, 0)
        b = (10, 0)
        assert _point_to_segment_distance(p, a, b) == pytest.approx(0.0)

    def test_point_at_endpoint(self):
        """Punkt liegt am Endpunkt → Distanz 0."""
        p = (0, 0)
        a = (0, 0)
        b = (10, 0)
        assert _point_to_segment_distance(p, a, b) == pytest.approx(0.0)

    def test_point_perpendicular(self):
        """Punkt senkrecht zur Strecke."""
        p = (5, 3)
        a = (0, 0)
        b = (10, 0)
        assert _point_to_segment_distance(p, a, b) == pytest.approx(3.0)

    def test_point_beyond_segment(self):
        """Punkt liegt jenseits der Strecke."""
        p = (15, 0)
        a = (0, 0)
        b = (10, 0)
        assert _point_to_segment_distance(p, a, b) == pytest.approx(5.0)

    def test_point_before_segment(self):
        """Punkt liegt vor der Strecke."""
        p = (-3, 0)
        a = (0, 0)
        b = (10, 0)
        assert _point_to_segment_distance(p, a, b) == pytest.approx(3.0)

    def test_diagonal_segment(self):
        """Diagonale Strecke."""
        p = (0, 5)
        a = (0, 0)
        b = (10, 10)
        # Nächster Punkt auf der Diagonalen ist (2.5, 2.5)
        expected = math.sqrt((0-2.5)**2 + (5-2.5)**2)
        assert _point_to_segment_distance(p, a, b) == pytest.approx(expected, rel=0.01)


class TestPolygonDistance:
    """Tests für Polygon-zu-Polygon Distanz."""

    def test_overlapping_polygons(self):
        """Überlappende Polygone → Distanz ~0."""
        poly1 = [(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)]
        # Polygon 2 überlappt mit Polygon 1 (Ecke innerhalb)
        poly2 = [(5, 0), (15, 0), (15, 10), (5, 10), (5, 0)]
        dist = _polygon_distance(poly1, poly2)
        # Die Polygone teilen eine Kante, Distanz sollte 0 sein
        assert dist == pytest.approx(0.0, abs=0.1)

    def test_adjacent_polygons(self):
        """Angrenzende Polygone (Reihenhäuser) → Distanz ~0."""
        poly1 = [(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)]
        poly2 = [(10, 0), (20, 0), (20, 10), (10, 10), (10, 0)]
        dist = _polygon_distance(poly1, poly2)
        assert dist == pytest.approx(0.0, abs=0.1)

    def test_separated_polygons(self):
        """Getrennte Polygone mit Abstand."""
        poly1 = [(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)]
        poly2 = [(15, 0), (25, 0), (25, 10), (15, 10), (15, 0)]
        dist = _polygon_distance(poly1, poly2)
        assert dist == pytest.approx(5.0, abs=0.1)

    def test_diagonal_separation(self):
        """Diagonale Trennung."""
        poly1 = [(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)]
        poly2 = [(20, 20), (30, 20), (30, 30), (20, 30), (20, 20)]
        dist = _polygon_distance(poly1, poly2)
        # Nächster Punkt: (10, 10) zu (20, 20) = sqrt(200) ≈ 14.14
        expected = math.sqrt(200)
        assert dist == pytest.approx(expected, rel=0.1)


class TestCalculateDirection:
    """Tests für Himmelsrichtungs-Berechnung."""

    def test_north(self):
        """Richtung nach Norden."""
        direction = _calculate_direction(0, 0, 0, 10)
        assert direction == "N"

    def test_south(self):
        """Richtung nach Süden."""
        direction = _calculate_direction(0, 0, 0, -10)
        assert direction == "S"

    def test_east(self):
        """Richtung nach Osten."""
        direction = _calculate_direction(0, 0, 10, 0)
        assert direction == "E"

    def test_west(self):
        """Richtung nach Westen."""
        direction = _calculate_direction(0, 0, -10, 0)
        assert direction == "W"

    def test_northeast(self):
        """Richtung nach Nordosten."""
        direction = _calculate_direction(0, 0, 10, 10)
        assert direction == "NE"

    def test_southwest(self):
        """Richtung nach Südwesten."""
        direction = _calculate_direction(0, 0, -10, -10)
        assert direction == "SW"


class TestNeighborsResult:
    """Tests für NeighborsResult Dataclass."""

    def test_to_dict(self):
        """Konvertierung zu Dictionary."""
        neighbor = NeighborBuilding(
            egid="123",
            distance_m=5.0,
            direction="E"
        )
        result = NeighborsResult(
            target_egid="456",
            neighbors=[neighbor],
            radius_m=10.0
        )
        d = result.to_dict()

        assert d["target_egid"] == "456"
        assert d["radius_m"] == 10.0
        assert len(d["neighbors"]) == 1
        assert d["neighbors"][0]["egid"] == "123"

    def test_empty_neighbors(self):
        """Keine Nachbarn gefunden."""
        result = NeighborsResult(
            target_egid="456",
            neighbors=[],
            radius_m=10.0
        )
        assert len(result.neighbors) == 0


class TestReihenhausScenario:
    """Tests für Reihenhaus-Szenarien (z.B. Knospenweg 2-10)."""

    @pytest.fixture
    def reihenhaus_polygons(self):
        """
        Simuliert 5 Reihenhäuser nebeneinander.

        Layout (Vogelperspektive):
        ┌────┬────┬────┬────┬────┐
        │ 2  │ 4  │ 6  │ 8  │ 10 │
        └────┴────┴────┴────┴────┘
        """
        # Jedes Haus ist 8m breit, 12m tief
        houses = {}
        for i, nr in enumerate([2, 4, 6, 8, 10]):
            x = i * 8
            houses[str(nr)] = [
                (x, 0), (x + 8, 0), (x + 8, 12), (x, 12), (x, 0)
            ]
        return houses

    def test_middle_house_has_two_neighbors(self, reihenhaus_polygons):
        """Mittleres Haus (Nr. 6) hat genau 2 direkte Nachbarn."""
        house_6 = reihenhaus_polygons["6"]
        house_4 = reihenhaus_polygons["4"]
        house_8 = reihenhaus_polygons["8"]

        # Distanz zu Nachbarn
        dist_to_4 = _polygon_distance(house_6, house_4)
        dist_to_8 = _polygon_distance(house_6, house_8)

        assert dist_to_4 == pytest.approx(0.0, abs=0.1), "Haus 4 sollte angrenzend sein"
        assert dist_to_8 == pytest.approx(0.0, abs=0.1), "Haus 8 sollte angrenzend sein"

    def test_end_house_has_one_neighbor(self, reihenhaus_polygons):
        """Endhaus (Nr. 2) hat nur 1 direkten Nachbarn."""
        house_2 = reihenhaus_polygons["2"]
        house_4 = reihenhaus_polygons["4"]
        house_10 = reihenhaus_polygons["10"]

        dist_to_4 = _polygon_distance(house_2, house_4)
        dist_to_10 = _polygon_distance(house_2, house_10)

        assert dist_to_4 == pytest.approx(0.0, abs=0.1), "Haus 4 sollte angrenzend sein"
        assert dist_to_10 > 20, "Haus 10 sollte weit entfernt sein"

    def test_blocked_sides_calculation(self, reihenhaus_polygons):
        """Berechnung der blockierten Seiten für mittleres Haus."""
        # Haus 6 ist in der Mitte
        # Nachbarn sind links (W) und rechts (E)
        # Nord und Süd sind frei

        house_6_center = (20, 6)  # Mitte von Haus 6
        house_4_center = (12, 6)  # Mitte von Haus 4 (links)
        house_8_center = (28, 6)  # Mitte von Haus 8 (rechts)

        dir_to_4 = _calculate_direction(house_6_center[0], house_6_center[1],
                                         house_4_center[0], house_4_center[1])
        dir_to_8 = _calculate_direction(house_6_center[0], house_6_center[1],
                                         house_8_center[0], house_8_center[1])

        assert dir_to_4 == "W", "Haus 4 sollte westlich sein"
        assert dir_to_8 == "E", "Haus 8 sollte östlich sein"


class TestUmgebungsScenario:
    """Tests für Umgebungs-Szenarien (Freistehend, Innenhof, etc.)."""

    def test_detached_house_no_neighbors(self):
        """Freistehendes Haus hat keine Nachbarn im 10m Radius."""
        house = [(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)]
        neighbor = [(100, 0), (110, 0), (110, 10), (100, 10), (100, 0)]

        dist = _polygon_distance(house, neighbor)
        assert dist > 10, "Nachbar sollte ausserhalb 10m Radius sein"

    def test_l_shaped_building(self):
        """L-förmiges Gebäude (z.B. Innenhof)."""
        # Hauptgebäude
        main = [(0, 0), (20, 0), (20, 10), (0, 10), (0, 0)]
        # L-Anbau (seitlich)
        anbau = [(20, 0), (30, 0), (30, 30), (20, 30), (20, 0)]

        dist = _polygon_distance(main, anbau)
        assert dist == pytest.approx(0.0, abs=0.1), "L-Anbau sollte angrenzend sein"

    def test_courtyard_building(self):
        """Gebäude mit Innenhof (U-Form)."""
        # Linker Flügel
        left = [(0, 0), (10, 0), (10, 30), (0, 30), (0, 0)]
        # Rechter Flügel
        right = [(20, 0), (30, 0), (30, 30), (20, 30), (20, 0)]
        # Verbindung hinten
        back = [(0, 20), (30, 20), (30, 30), (0, 30), (0, 20)]

        # Linker und rechter Flügel sind NICHT angrenzend (Innenhof dazwischen)
        dist_lr = _polygon_distance(left, right)
        assert dist_lr > 0, "Flügel sollten durch Innenhof getrennt sein"

        # Aber beide grenzen an den hinteren Verbindungsbau
        dist_left_back = _polygon_distance(left, back)
        dist_right_back = _polygon_distance(right, back)
        assert dist_left_back == pytest.approx(0.0, abs=0.1)
        assert dist_right_back == pytest.approx(0.0, abs=0.1)


@pytest.mark.skip(reason="NeighborsService verwendet smart_building_cache, benötigt echte Daten")
class TestNeighborsServiceIntegration:
    """
    Integrationstests für NeighborsService.get_neighbors().

    HINWEIS (04.01.2026): Diese Tests sind übersprungen, da NeighborsService
    jetzt aus smart_building_cache liest statt aus building_geodata.db.
    Für vollständige Tests benötigt man echte Daten in building_contexts.db.
    """

    def test_find_neighbors_requires_real_data(self):
        """Placeholder - NeighborsService benötigt echte Cache-Daten."""
        service = get_neighbors_service()
        # Ohne echte Daten in smart_building_cache gibt es keine Ergebnisse
        result = service.get_neighbors("1006", radius_m=10.0)
        # Wird None sein, wenn EGID nicht im Cache
        pass


# Entfernt: TestCalculateFacadeDirection
# Diese Funktion existiert nicht mehr in neighbors_service.
# Die Richtungsberechnung erfolgt jetzt nur noch über _calculate_direction
# basierend auf Zentrum-Koordinaten.


@pytest.mark.skip(reason="Funktion _calculate_facade_direction existiert nicht mehr")
class TestCalculateFacadeDirection:
    """
    Tests für Fassaden-basierte Richtungsberechnung.

    Diese Funktion wird bei angrenzenden Gebäuden (<1m) verwendet,
    um die Richtung basierend auf der blockierten Fassade zu bestimmen.

    Vorteile gegenüber Schwerpunkt-basierter Berechnung:
    - Korrekte Richtung bei Reihenhäusern (wo Schwerpunkte fast identisch sind)
    - Berücksichtigt die tatsächliche Gebäudegeometrie
    """

    def test_neighbor_to_east(self):
        """Nachbar östlich → Richtung E."""
        # Zielgebäude: 10x10m Quadrat
        target = [(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)]
        # Nachbar östlich (angrenzend)
        neighbor = [(10, 0), (20, 0), (20, 10), (10, 10), (10, 0)]

        direction = _calculate_facade_direction(target, neighbor)
        assert direction == "E", f"Erwartet E, erhalten {direction}"

    def test_neighbor_to_west(self):
        """Nachbar westlich → Richtung W."""
        target = [(10, 0), (20, 0), (20, 10), (10, 10), (10, 0)]
        neighbor = [(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)]

        direction = _calculate_facade_direction(target, neighbor)
        assert direction == "W", f"Erwartet W, erhalten {direction}"

    def test_neighbor_to_north(self):
        """Nachbar nördlich → Richtung N."""
        target = [(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)]
        neighbor = [(0, 10), (10, 10), (10, 20), (0, 20), (0, 10)]

        direction = _calculate_facade_direction(target, neighbor)
        assert direction == "N", f"Erwartet N, erhalten {direction}"

    def test_neighbor_to_south(self):
        """Nachbar südlich → Richtung S."""
        target = [(0, 10), (10, 10), (10, 20), (0, 20), (0, 10)]
        neighbor = [(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)]

        direction = _calculate_facade_direction(target, neighbor)
        assert direction == "S", f"Erwartet S, erhalten {direction}"

    def test_reihenhaus_overlapping_polygons(self):
        """
        Reihenhäuser mit überlappenden Polygonen.

        Bei Reihenhäusern teilen sich benachbarte Gebäude oft eine Wand,
        was zu überlappenden Polygonen führt. Die Schwerpunkte sind dann
        sehr nahe beieinander (<2m), was den Spezialfall triggert.
        """
        # Reihenhaus 1: x=0-8
        house1 = [(0, 0), (8, 0), (8, 12), (0, 12), (0, 0)]
        # Reihenhaus 2: x=8-16 (teilt sich die Wand bei x=8)
        house2 = [(8, 0), (16, 0), (16, 12), (8, 12), (8, 0)]

        # Von Haus 1 aus gesehen ist Haus 2 im Osten
        direction = _calculate_facade_direction(house1, house2)
        assert direction == "E", f"Erwartet E, erhalten {direction}"

        # Von Haus 2 aus gesehen ist Haus 1 im Westen
        direction = _calculate_facade_direction(house2, house1)
        assert direction == "W", f"Erwartet W, erhalten {direction}"

    def test_reihenhaus_north_south_orientation(self):
        """Reihenhäuser in Nord-Süd-Richtung."""
        # Reihenhaus unten
        house_s = [(0, 0), (10, 0), (10, 8), (0, 8), (0, 0)]
        # Reihenhaus oben (teilt Wand bei y=8)
        house_n = [(0, 8), (10, 8), (10, 16), (0, 16), (0, 8)]

        direction_from_s = _calculate_facade_direction(house_s, house_n)
        assert direction_from_s == "N", f"Erwartet N, erhalten {direction_from_s}"

        direction_from_n = _calculate_facade_direction(house_n, house_s)
        assert direction_from_n == "S", f"Erwartet S, erhalten {direction_from_n}"

    def test_close_centroids_uses_simplified_direction(self):
        """
        Bei sehr nahen Schwerpunkten (<2m) wird vereinfachte 4-Richtungen verwendet.

        Dies ist wichtig für überlappende Polygone wo die Kanten-Analyse
        unzuverlässig sein könnte.
        """
        # Zwei überlappende Polygone (Schwerpunkte ~1m auseinander)
        poly1 = [(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)]
        poly2 = [(1, 0), (11, 0), (11, 10), (1, 10), (1, 0)]

        # Schwerpunkt von poly1: (5, 5)
        # Schwerpunkt von poly2: (6, 5)
        # Differenz: dx=1, dy=0 → E dominiert

        direction = _calculate_facade_direction(poly1, poly2)
        assert direction == "E", f"Erwartet E bei überlappenden Polygonen, erhalten {direction}"

    def test_l_shaped_building_neighbor(self):
        """L-förmiges Gebäude mit Nachbar."""
        # L-förmiges Gebäude
        l_shape = [
            (0, 0), (20, 0), (20, 10), (10, 10), (10, 20), (0, 20), (0, 0)
        ]
        # Nachbar östlich des Hauptarms
        neighbor = [(20, 0), (30, 0), (30, 10), (20, 10), (20, 0)]

        direction = _calculate_facade_direction(l_shape, neighbor)
        assert direction == "E", f"Erwartet E, erhalten {direction}"

    def test_empty_polygon_fallback(self):
        """Leere Polygone geben Fallback 'N' zurück."""
        direction = _calculate_facade_direction([], [(0, 0), (10, 10)])
        assert direction == "N"

        direction = _calculate_facade_direction([(0, 0), (10, 10)], [])
        assert direction == "N"

    def test_diagonal_neighbor_northeast(self):
        """Diagonal gelegener Nachbar (Nordost)."""
        target = [(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)]
        # Nachbar diagonal rechts oben (mit Abstand)
        neighbor = [(15, 15), (25, 15), (25, 25), (15, 25), (15, 15)]

        direction = _calculate_facade_direction(target, neighbor)
        # Bei diagonalen Nachbarn mit Abstand sollte NE herauskommen
        assert direction in ["N", "NE", "E"], f"Erwartet N/NE/E, erhalten {direction}"
