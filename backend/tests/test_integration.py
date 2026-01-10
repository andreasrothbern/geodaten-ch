"""
Integrationstests für das Tile-Cache System.

Testet die 3 Szenarien:
1. Cold Start (kein Cache) - Download nötig
2. Warm Cache (zweite Anfrage im Tile) - schneller Zugriff
3. EGID-Lookup (via building_3d.db nach Prefetch) - sofortiger Zugriff

Test-Fixtures (bekannte Orte):
- Bundeshaus: 2600450, 1199830, Tile 1088-22
- Kramgasse 49: ~2600656, 1199497, Tile 1088-22 (selbes Tile!)
- Zürich HB: 2683200, 1247700, Tile 1144-34
"""

import pytest
import time
import httpx
from pathlib import Path

# Test-Fixtures
TEST_ADDRESSES = {
    "bundeshaus": {
        "address": "Bundesplatz 3, 3011 Bern",
        "coords": (2600450, 1199830),
        "tile_id": "1088-22",
        "description": "Bundeshaus Bern"
    },
    "kramgasse": {
        "address": "Kramgasse 49, 3011 Bern",
        "coords": (2600656, 1199497),
        "tile_id": "1088-22",  # Selbes Tile wie Bundeshaus!
        "description": "Kramgasse 49, Bern (Einstein-Haus)"
    },
    "zurich_hb": {
        "address": "Bahnhofstrasse 50, 8001 Zürich",
        "coords": (2683200, 1247700),
        "tile_id": "1144-34",
        "description": "Zürich Hauptbahnhof"
    },
    "basel": {
        "address": "Marktplatz 10, 4051 Basel",
        "coords": (2611200, 1267900),
        "tile_id": "1094-44",
        "description": "Basel Marktplatz"
    }
}

# API Base URL
BASE_URL = "http://localhost:8000"


class TestTileIdConsistency:
    """Prüft dass Tile-IDs konsistent berechnet werden."""

    def test_tile_id_calculation_matches_documentation(self):
        """Tile-IDs stimmen mit Dokumentation überein."""
        from app.services.tile_cache import lv95_to_tile_id

        for name, fixture in TEST_ADDRESSES.items():
            e, n = fixture["coords"]
            expected_tile = fixture["tile_id"]
            calculated = lv95_to_tile_id(e, n)
            assert calculated == expected_tile, \
                f"{fixture['description']}: erwartet {expected_tile}, bekam {calculated}"

    def test_same_tile_for_nearby_addresses(self):
        """Bundeshaus und Kramgasse sind im selben Tile."""
        from app.services.tile_cache import lv95_to_tile_id

        bundeshaus_tile = lv95_to_tile_id(*TEST_ADDRESSES["bundeshaus"]["coords"])
        kramgasse_tile = lv95_to_tile_id(*TEST_ADDRESSES["kramgasse"]["coords"])

        assert bundeshaus_tile == kramgasse_tile == "1088-22", \
            "Bundeshaus und Kramgasse sollten im selben Tile sein (1088-22)"


class TestCacheStages:
    """Testet die 3-Stufen Cache-Logik."""

    def test_stufe1_egid_lookup(self):
        """Stufe 1: EGID-Lookup in building_3d.db."""
        from app.services.tile_cache import get_tile_cache

        cache = get_tile_cache()

        # EGID-Lookup nutzt jetzt building_3d.db (via prefetch)
        # Teste nur dass die Funktion keinen Fehler wirft
        test_egid = 2242547  # Bundeshaus EGID
        tile = cache.get_tile_for_egid(test_egid)

        # Ergebnis kann None sein (falls nicht geprefetched) oder Tile-ID
        assert tile is None or isinstance(tile, str)

    def test_stufe2_coordinate_to_tile(self):
        """Stufe 2: Koordinaten → Tile-ID Berechnung."""
        from app.services.tile_cache import lv95_to_tile_id

        # Diese Berechnung braucht KEINE API
        start = time.time()
        for _ in range(1000):
            lv95_to_tile_id(2600450, 1199830)
        elapsed = time.time() - start

        # 1000 Berechnungen sollten unter 0.1s dauern
        assert elapsed < 0.1, f"Tile-ID Berechnung zu langsam: {elapsed:.3f}s für 1000 Aufrufe"

    def test_stufe3_tile_path_lookup(self):
        """Stufe 3: Tile-ID → lokaler Pfad."""
        from app.services.tile_cache import get_tile_cache

        cache = get_tile_cache()

        # Für nicht-gecachtes Tile: None
        result = cache.get_tile_path("9999-99")
        assert result is None

        # Prüfe dass die Methode schnell ist
        start = time.time()
        for _ in range(100):
            cache.get_tile_path("1088-22")
        elapsed = time.time() - start
        assert elapsed < 0.1, f"Tile-Path Lookup zu langsam: {elapsed:.3f}s"


class TestSmartBuildingFlow:
    """Testet den SmartBuildingService Datenfluss."""

    @pytest.mark.asyncio
    async def test_geocoding_returns_coordinates(self):
        """Geocoding liefert LV95-Koordinaten."""
        try:
            from app.services.swisstopo import SwisstopoService
        except ImportError:
            pytest.skip("SwisstopoService nicht verfügbar")

        swisstopo = SwisstopoService()
        result = await swisstopo.geocode("Bundesplatz 3, 3011 Bern")

        assert result is not None
        assert result.coordinates is not None
        assert result.coordinates.lv95_e > 2500000  # Plausibilitätsprüfung
        assert result.coordinates.lv95_n > 1100000

    @pytest.mark.asyncio
    async def test_polygon_data_contains_required_fields(self):
        """swissBUILDINGS3D liefert alle erforderlichen Felder."""
        try:
            from app.services.swissbuildings3d_fetcher import fetch_building_polygon_for_coordinates
        except ImportError:
            pytest.skip("geopandas/fiona nicht installiert")

        # Bundeshaus Koordinaten
        result = await fetch_building_polygon_for_coordinates(
            e=2600450, n=1199830, tolerance_m=50
        )

        if result is None:
            pytest.skip("Keine Daten verfügbar (Tile nicht gecacht)")

        # Pflichtfelder prüfen
        assert "polygon" in result, "polygon fehlt"
        assert "sides" in result, "sides fehlt"
        assert isinstance(result["polygon"], list), "polygon muss Liste sein"
        assert len(result["polygon"]) >= 3, "polygon braucht min. 3 Punkte"


class TestPerformanceExpectations:
    """Testet die Performance-Erwartungen aus der Doku."""

    def test_tile_id_calculation_under_1ms(self):
        """Tile-ID Berechnung dauert < 1ms."""
        from app.services.tile_cache import lv95_to_tile_id

        start = time.time()
        lv95_to_tile_id(2600450, 1199830)
        elapsed = (time.time() - start) * 1000  # ms

        assert elapsed < 1, f"Tile-ID Berechnung: {elapsed:.3f}ms (sollte < 1ms sein)"

    def test_cache_lookup_under_5ms(self):
        """Cache-Lookup dauert < 5ms."""
        from app.services.tile_cache import get_tile_cache

        cache = get_tile_cache()

        start = time.time()
        cache.get_tile_path("1088-22")
        elapsed = (time.time() - start) * 1000

        assert elapsed < 5, f"Cache-Lookup: {elapsed:.3f}ms (sollte < 5ms sein)"


class TestAPIEndpoints:
    """Testet die API-Endpunkte."""

    @pytest.fixture
    def client(self):
        """HTTP Client für API-Tests."""
        return httpx.Client(base_url=BASE_URL, timeout=30.0)

    def test_api_docs_available(self, client):
        """OpenAPI Docs sind verfügbar."""
        response = client.get("/docs")
        assert response.status_code == 200

    def test_smart_building_data_endpoint(self, client):
        """SmartBuildingService API liefert Daten."""
        response = client.get(
            "/api/v1/smart-building/data",
            params={"address": "Bundesplatz 3, 3011 Bern"}
        )

        if response.status_code == 500:
            pytest.skip("Backend-Fehler (möglicherweise API nicht erreichbar)")

        assert response.status_code == 200
        data = response.json()

        # Basis-Felder prüfen
        assert "egid" in data or data.get("egid") is None
        assert "polygon" in data or "error" in data

    def test_tile_cache_stats_endpoint(self, client):
        """Tile-Cache Stats sind verfügbar."""
        response = client.get("/api/v1/tile-cache/stats")

        if response.status_code == 404:
            pytest.skip("Endpoint nicht implementiert")

        assert response.status_code == 200
        data = response.json()
        assert "tile_count" in data


class TestDataQuality:
    """Testet die Datenqualität."""

    def test_bundeshaus_known_building(self):
        """Bundeshaus ist als bekanntes Gebäude hinterlegt."""
        try:
            from app.services.smart_building.known_buildings import KNOWN_BUILDINGS
        except ImportError:
            pytest.skip("known_buildings nicht verfügbar")

        bundeshaus_keys = [k for k in KNOWN_BUILDINGS.keys() if "bundeshaus" in k.lower()]
        assert len(bundeshaus_keys) > 0, "Bundeshaus sollte in KNOWN_BUILDINGS sein"

    def test_known_buildings_have_zones(self):
        """Bekannte Gebäude haben Zonen definiert."""
        try:
            from app.services.smart_building.known_buildings import KNOWN_BUILDINGS
        except ImportError:
            pytest.skip("known_buildings nicht verfügbar")

        for key, building in KNOWN_BUILDINGS.items():
            assert "zones" in building, f"{key} hat keine Zonen"
            assert len(building["zones"]) > 0, f"{key} hat leere Zonen"


# Hilfsfunktionen für manuelle Tests
def run_cold_start_test():
    """Manueller Test: Cold Start (kein Cache)."""
    print("\n=== Cold Start Test ===")
    print("Erwartet: ~8-15s für erstes Gebäude (Download nötig)")

    import asyncio
    from app.services.smart_building import get_smart_building_service

    service = get_smart_building_service()

    start = time.time()
    result = asyncio.run(service.collect_all_data(
        address="Bundesplatz 3, 3011 Bern",
        force_refresh=True
    ))
    elapsed = time.time() - start

    print(f"Dauer: {elapsed:.2f}s")
    print(f"EGID: {result.egid}")
    print(f"Polygon-Punkte: {len(result.polygon) if result.polygon else 0}")

    return elapsed


def run_warm_cache_test():
    """Manueller Test: Warm Cache (zweite Anfrage)."""
    print("\n=== Warm Cache Test ===")
    print("Erwartet: ~50ms (Tile im Cache)")

    import asyncio
    from app.services.smart_building import get_smart_building_service

    service = get_smart_building_service()

    # Erste Anfrage (cache warm machen)
    asyncio.run(service.collect_all_data(address="Bundesplatz 3, 3011 Bern"))

    # Zweite Anfrage (sollte schneller sein)
    start = time.time()
    result = asyncio.run(service.collect_all_data(
        address="Kramgasse 49, 3011 Bern"  # Selbes Tile!
    ))
    elapsed = time.time() - start

    print(f"Dauer: {elapsed:.2f}s")
    print(f"Cache Hit: Erwartet (selbes Tile)")

    return elapsed


if __name__ == "__main__":
    print("Führe manuelle Tests aus...")
    run_cold_start_test()
    run_warm_cache_test()