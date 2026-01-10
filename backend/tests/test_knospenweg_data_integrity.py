"""
Test-Case: Knospenweg Datenintegrität

VERALTET (08.01.2026): Diese Tests sind obsolet.

Historischer Hintergrund:
- building_geodata.db wurde entfernt (siehe OPT-001 in known-bugs.md)
- Gebäudedaten werden jetzt in building_3d.db gespeichert (via tile_prefetch)
- Die Tabellen-Struktur hat sich grundlegend geändert

Diese Test-Datei wird bei allen Tests übersprungen (kein building_geodata.db).
Die Tests können gelöscht werden sobald die Migration vollständig verifiziert ist.
"""

import pytest
import sqlite3
import json
import os
from pathlib import Path


# Expected data for Knospenweg buildings
KNOSPENWEG_BUILDINGS = {
    "1243787": {"address_num": "1", "trauf_min": 5.0, "trauf_max": 6.0, "first_min": 7.5, "first_max": 9.0},
    "1243788": {"address_num": "2", "trauf_min": 5.0, "trauf_max": 6.0, "first_min": 7.0, "first_max": 8.5},
    "1243789": {"address_num": "3", "trauf_min": 5.0, "trauf_max": 6.0, "first_min": 7.5, "first_max": 9.0},
    "1243790": {"address_num": "4", "trauf_min": 5.0, "trauf_max": 6.0, "first_min": 7.0, "first_max": 8.5},
    "1243791": {"address_num": "5", "trauf_min": 5.0, "trauf_max": 6.0, "first_min": 7.5, "first_max": 9.0},
    "1243792": {"address_num": "6", "trauf_min": 5.0, "trauf_max": 6.0, "first_min": 7.0, "first_max": 8.5},
    "1243793": {"address_num": "7", "trauf_min": 5.0, "trauf_max": 6.0, "first_min": 7.5, "first_max": 9.0},
    "1243794": {"address_num": "8", "trauf_min": 5.0, "trauf_max": 6.5, "first_min": 7.0, "first_max": 8.5},
    "1243795": {"address_num": "9", "trauf_min": 5.0, "trauf_max": 6.0, "first_min": 7.5, "first_max": 9.0},
    "1243797": {"address_num": "10", "trauf_min": 5.0, "trauf_max": 6.5, "first_min": 7.0, "first_max": 8.5},
}

# Coordinate bounds for Knospenweg area (LV95)
KNOSPENWEG_BOUNDS = {
    "e_min": 2596260,
    "e_max": 2596310,
    "n_min": 1199790,
    "n_max": 1199830,
}


def get_db_path():
    """Get path to building_geodata.db"""
    # Try multiple paths
    possible_paths = [
        Path(__file__).parent.parent / "app" / "data" / "building_geodata.db",
        Path("app/data/building_geodata.db"),
        Path("backend/app/data/building_geodata.db"),
    ]
    for path in possible_paths:
        if path.exists():
            return str(path)
    return None


@pytest.fixture
def db_connection():
    """Create DB connection for tests"""
    db_path = get_db_path()
    if db_path is None:
        pytest.skip("building_geodata.db not found - run with populated DB")
    conn = sqlite3.connect(db_path)
    yield conn
    conn.close()


class TestKnoswenpwegDataIntegrity:
    """Test suite for Knospenweg building data integrity"""

    def test_all_buildings_exist(self, db_connection):
        """Verify all 10 Knospenweg buildings exist in DB"""
        cursor = db_connection.cursor()

        missing = []
        for egid in KNOSPENWEG_BUILDINGS.keys():
            cursor.execute("SELECT COUNT(*) FROM buildings WHERE egid = ?", (egid,))
            count = cursor.fetchone()[0]
            if count == 0:
                missing.append(egid)

        assert len(missing) == 0, f"Missing buildings: {missing}"

    def test_buildings_have_valid_heights(self, db_connection):
        """Verify all buildings have valid height data"""
        cursor = db_connection.cursor()

        errors = []
        for egid, expected in KNOSPENWEG_BUILDINGS.items():
            cursor.execute(
                "SELECT traufhoehe_m, firsthoehe_m FROM buildings WHERE egid = ?",
                (egid,)
            )
            result = cursor.fetchone()

            if result is None:
                errors.append(f"EGID {egid}: not found")
                continue

            trauf, first = result

            # Check Traufhöhe
            if trauf is None or trauf < expected["trauf_min"] or trauf > expected["trauf_max"]:
                errors.append(f"EGID {egid}: Traufhöhe {trauf}m not in range [{expected['trauf_min']}, {expected['trauf_max']}]")

            # Check Firsthöhe
            if first is None or first < expected["first_min"] or first > expected["first_max"]:
                errors.append(f"EGID {egid}: Firsthöhe {first}m not in range [{expected['first_min']}, {expected['first_max']}]")

        assert len(errors) == 0, f"Height validation errors:\n" + "\n".join(errors)

    def test_buildings_have_valid_polygons(self, db_connection):
        """Verify all buildings have valid polygon data"""
        cursor = db_connection.cursor()

        errors = []
        for egid in KNOSPENWEG_BUILDINGS.keys():
            cursor.execute("SELECT polygon FROM buildings WHERE egid = ?", (egid,))
            result = cursor.fetchone()

            if result is None:
                errors.append(f"EGID {egid}: not found")
                continue

            polygon_str = result[0]

            # Check polygon exists
            if polygon_str is None or len(polygon_str) < 10:
                errors.append(f"EGID {egid}: missing or empty polygon")
                continue

            # Check polygon is valid JSON
            try:
                polygon = json.loads(polygon_str)
            except json.JSONDecodeError:
                errors.append(f"EGID {egid}: invalid polygon JSON")
                continue

            # Check polygon has at least 3 points (minimum for a valid polygon)
            if len(polygon) < 3:
                errors.append(f"EGID {egid}: polygon has only {len(polygon)} points (need >= 3)")

        assert len(errors) == 0, f"Polygon validation errors:\n" + "\n".join(errors)

    def test_buildings_in_correct_location(self, db_connection):
        """Verify buildings are in the correct geographic area"""
        cursor = db_connection.cursor()

        errors = []
        for egid in KNOSPENWEG_BUILDINGS.items():
            cursor.execute(
                "SELECT coord_e, coord_n FROM buildings WHERE egid = ?",
                (egid[0],)
            )
            result = cursor.fetchone()

            if result is None:
                errors.append(f"EGID {egid[0]}: not found")
                continue

            e, n = result

            # Handle both LV95 and LV03 coordinate systems
            # LV95: E ~2596xxx, N ~1199xxx
            # LV03: E ~596xxx, N ~199xxx (subtract 2000000/1000000)
            e_normalized = e if e > 2000000 else e + 2000000
            n_normalized = n if n > 1000000 else n + 1000000

            # Check coordinates are in Knospenweg area (with 100m tolerance)
            if e_normalized < KNOSPENWEG_BOUNDS["e_min"] - 100 or e_normalized > KNOSPENWEG_BOUNDS["e_max"] + 100:
                errors.append(f"EGID {egid[0]}: E-coord {e} (normalized: {e_normalized}) outside expected area")

            if n_normalized < KNOSPENWEG_BOUNDS["n_min"] - 100 or n_normalized > KNOSPENWEG_BOUNDS["n_max"] + 100:
                errors.append(f"EGID {egid[0]}: N-coord {n} (normalized: {n_normalized}) outside expected area")

        assert len(errors) == 0, f"Location validation errors:\n" + "\n".join(errors)

    def test_coordinate_range_lookup_performance(self, db_connection):
        """Verify coordinate range lookup is fast (<10ms)"""
        import time

        cursor = db_connection.cursor()

        start = time.perf_counter()
        cursor.execute(
            """
            SELECT egid FROM buildings
            WHERE coord_e BETWEEN ? AND ?
            AND coord_n BETWEEN ? AND ?
            """,
            (
                KNOSPENWEG_BOUNDS["e_min"],
                KNOSPENWEG_BOUNDS["e_max"],
                KNOSPENWEG_BOUNDS["n_min"],
                KNOSPENWEG_BOUNDS["n_max"],
            )
        )
        results = cursor.fetchall()
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Should find at least 5 buildings in the area
        assert len(results) >= 5, f"Expected >=5 buildings, found {len(results)}"

        # Should be fast (<10ms)
        assert elapsed_ms < 10, f"Coordinate lookup took {elapsed_ms:.2f}ms (expected <10ms)"

    def test_egid_lookup_performance(self, db_connection):
        """Verify EGID lookup is fast (<1ms average)"""
        import time

        cursor = db_connection.cursor()

        total_time = 0
        for egid in KNOSPENWEG_BUILDINGS.keys():
            start = time.perf_counter()
            cursor.execute(
                "SELECT egid, polygon, traufhoehe_m, firsthoehe_m FROM buildings WHERE egid = ?",
                (egid,)
            )
            cursor.fetchone()
            total_time += time.perf_counter() - start

        avg_ms = (total_time / len(KNOSPENWEG_BUILDINGS)) * 1000

        # Average should be <1ms
        assert avg_ms < 1, f"Average EGID lookup took {avg_ms:.2f}ms (expected <1ms)"


class TestAddressRangeResolution:
    """Test suite for address range resolution (Szenario 1)"""

    def test_range_2_10_parses_5_numbers(self):
        """Verify 'Knospenweg 2-10' parses to 5 even numbers"""
        from app.services.address_parser import parse_address_range

        result = parse_address_range("Knospenweg 2-10, Bern")

        assert result is not None
        # ParsedAddressRange is a Pydantic model, use attribute access
        assert result.street == "Knospenweg"
        assert result.city == "Bern"
        assert result.numbers == ["2", "4", "6", "8", "10"]
        assert len(result.numbers) == 5

    def test_range_1_9_parses_5_numbers(self):
        """Verify 'Knospenweg 1-9' parses to 5 odd numbers"""
        from app.services.address_parser import parse_address_range

        result = parse_address_range("Knospenweg 1-9, Bern")

        assert result is not None
        # ParsedAddressRange is a Pydantic model, use attribute access
        assert result.street == "Knospenweg"
        assert result.numbers == ["1", "3", "5", "7", "9"]
        assert len(result.numbers) == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
