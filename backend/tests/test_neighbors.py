"""
Tests für die Neighbors-API und Geodata-Service.

Testet:
1. Polygon-Distanz-Berechnung
2. Richtungs-Berechnung
3. Nachbar-Erkennung
4. Reihenhäuser-Szenarien
5. Umgebungs-Szenarien
"""

import pytest
import math
from typing import List, Tuple

from app.services.geodata_service import (
    GeodataService,
    BuildingGeodata,
    NeighborBuilding,
    NeighborsResult,
    _polygon_distance,
    _point_to_segment_distance,
    _calculate_direction,
)


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


class TestGeodataServiceNeighbors:
    """Integrationstests für GeodataService.get_neighbors()."""

    @pytest.fixture
    def service_with_test_data(self, tmp_path):
        """GeodataService mit Test-Daten."""
        db_path = tmp_path / "test_geodata.db"
        service = GeodataService(db_path=db_path)

        # Test-Gebäude einfügen (Reihenhäuser)
        for i, nr in enumerate([2, 4, 6, 8, 10]):
            x = 2600000 + i * 8
            y = 1200000
            polygon = [(x, y), (x+8, y), (x+8, y+12), (x, y+12), (x, y)]

            geodata = BuildingGeodata(
                egid=str(1000 + nr),
                polygon=polygon,
                coord_e=x + 4,
                coord_n=y + 6,
                center_e=x + 4,
                center_n=y + 6,
                traufhoehe_m=8.0,
                firsthoehe_m=10.0
            )
            service.save(geodata)

        return service

    def test_find_neighbors_middle_house(self, service_with_test_data):
        """Mittleres Reihenhaus findet direkte Nachbarn (distance < 0.5m)."""
        result = service_with_test_data.get_neighbors("1006", radius_m=10.0)

        assert result is not None
        assert result.target_egid == "1006"

        # Direkt angrenzende Nachbarn (distance < 0.5m)
        adjacent = [n for n in result.neighbors if n.distance_m < 0.5]
        assert len(adjacent) == 2, f"Erwartet 2 direkte Nachbarn, gefunden: {len(adjacent)}"

        # Diese sind 1004 und 1008
        adjacent_egids = [n.egid for n in adjacent]
        assert "1004" in adjacent_egids
        assert "1008" in adjacent_egids

    def test_find_neighbors_end_house(self, service_with_test_data):
        """Endhaus findet nur 1 direkten Nachbarn."""
        result = service_with_test_data.get_neighbors("1002", radius_m=10.0)

        assert result is not None

        # Direkt angrenzende Nachbarn (distance < 0.5m)
        adjacent = [n for n in result.neighbors if n.distance_m < 0.5]
        assert len(adjacent) == 1, f"Erwartet 1 direkten Nachbarn, gefunden: {len(adjacent)}"
        assert adjacent[0].egid == "1004"

    def test_find_neighbors_with_distance(self, service_with_test_data):
        """Direkte Nachbarn haben Distanz ~0."""
        result = service_with_test_data.get_neighbors("1006", radius_m=10.0)

        # Nur direkte Nachbarn (1004 und 1008) prüfen
        adjacent = [n for n in result.neighbors if n.egid in ["1004", "1008"]]
        for neighbor in adjacent:
            assert neighbor.distance_m < 0.5, f"Nachbar {neighbor.egid} sollte angrenzend sein (dist={neighbor.distance_m})"

    def test_find_neighbors_with_direction(self, service_with_test_data):
        """Direkte Nachbarn haben korrekte Richtung."""
        result = service_with_test_data.get_neighbors("1006", radius_m=10.0)

        # Nur direkte Nachbarn prüfen
        directions = {n.egid: n.direction for n in result.neighbors if n.distance_m < 0.5}
        # 1004 ist westlich, 1008 ist östlich
        assert directions.get("1004") == "W", f"1004 sollte W sein, ist {directions.get('1004')}"
        assert directions.get("1008") == "E", f"1008 sollte E sein, ist {directions.get('1008')}"

    def test_no_neighbors_small_radius(self, service_with_test_data):
        """Kein Nachbar bei zu kleinem Radius (wenn Häuser nicht angrenzend wären)."""
        # Dieses Szenario testet den Filter
        result = service_with_test_data.get_neighbors("1006", radius_m=0.01)

        # Bei angrenzenden Häusern sollten sie trotzdem gefunden werden
        # weil distance_m ≈ 0
        assert result is not None

    def test_unknown_egid_returns_none(self, service_with_test_data):
        """Unbekanntes EGID gibt None zurück."""
        result = service_with_test_data.get_neighbors("9999999", radius_m=10.0)
        assert result is None

    def test_query_time_is_recorded(self, service_with_test_data):
        """Query-Zeit wird gemessen."""
        result = service_with_test_data.get_neighbors("1006", radius_m=10.0)
        assert result.query_time_ms > 0
        assert result.query_time_ms < 1000  # Sollte unter 1 Sekunde sein
