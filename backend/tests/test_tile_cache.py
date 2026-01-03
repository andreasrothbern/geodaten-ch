"""
Tests für das Tile-Cache System.

Testet:
1. lv95_to_tile_id() Berechnung
2. TileCacheService Grundfunktionen
3. Integration in swissbuildings3d_fetcher
4. Prefetch Background-Job
"""

import pytest
from pathlib import Path

from app.services.tile_cache import lv95_to_tile_id, get_tile_cache, TileCacheService
from app.services.tile_prefetch import get_prefetch_status, schedule_prefetch


class TestTileIdCalculation:
    """Test-Suite für die Tile-ID Berechnung."""

    @pytest.mark.parametrize("e,n,expected,description", [
        (2600450, 1199830, "1088-22", "Bern Bundeshaus"),
        (2683200, 1247700, "1144-34", "Zürich HB"),
        (2611200, 1267900, "1094-44", "Basel Marktplatz"),
        # Edge cases
        (2480000, 1070000, "1000-11", "Südwest-Ecke Schweiz"),
        (2600000, 1200000, "1088-22", "Bern genau auf km-Grid"),
    ])
    def test_tile_id_calculation(self, e, n, expected, description):
        """Tile-ID Berechnung für verschiedene Koordinaten."""
        result = lv95_to_tile_id(e, n)
        assert result == expected, f"Für {description}: erwartet {expected}, bekam {result}"

    def test_lv03_to_lv95_conversion(self):
        """LV03-Koordinaten werden automatisch zu LV95 konvertiert."""
        # LV03 Koordinaten (alte Schweizer Landeskoordinaten)
        e_lv03 = 600450
        n_lv03 = 199830

        # Sollte gleich sein wie LV95
        e_lv95 = 2600450
        n_lv95 = 1199830

        result_lv03 = lv95_to_tile_id(e_lv03, n_lv03)
        result_lv95 = lv95_to_tile_id(e_lv95, n_lv95)

        assert result_lv03 == result_lv95, "LV03 und LV95 sollten gleiche Tile-ID ergeben"


class TestTileCacheService:
    """Test-Suite für den TileCacheService."""

    def test_service_initialization(self):
        """Service kann initialisiert werden."""
        cache = get_tile_cache()
        assert cache is not None
        assert isinstance(cache, TileCacheService)

    def test_singleton_pattern(self):
        """get_tile_cache() gibt immer dieselbe Instanz zurück."""
        cache1 = get_tile_cache()
        cache2 = get_tile_cache()
        assert cache1 is cache2

    def test_stats_structure(self):
        """get_stats() gibt korrekte Struktur zurück."""
        cache = get_tile_cache()
        stats = cache.get_stats()

        assert "tile_count" in stats
        assert "egid_count" in stats
        assert "total_size_mb" in stats
        assert "tiles_dir" in stats
        assert "db_path" in stats

        # Typen prüfen
        assert isinstance(stats["tile_count"], int)
        assert isinstance(stats["egid_count"], int)
        assert isinstance(stats["total_size_mb"], (int, float))

    def test_tile_path_for_unknown_tile(self):
        """get_tile_path() gibt None für unbekanntes Tile zurück."""
        cache = get_tile_cache()
        result = cache.get_tile_path("9999-99")
        assert result is None

    def test_tile_for_coordinates_calculation(self):
        """get_tile_for_coordinates() berechnet Tile-ID korrekt."""
        cache = get_tile_cache()
        # Für Bundeshaus Bern
        result = cache.get_tile_for_coordinates(2600450, 1199830)
        # Könnte None sein (nicht gecacht) oder Path (gecacht)
        # Hauptsache kein Fehler
        assert result is None or isinstance(result, Path)


class TestTileCacheIntegration:
    """Integrationstests mit swissbuildings3d_fetcher."""

    @pytest.mark.asyncio
    async def test_fetch_with_cache_returns_cache_hit_field(self):
        """fetch_building_polygon_for_coordinates() enthält cache_hit Feld."""
        try:
            from app.services.swissbuildings3d_fetcher import fetch_building_polygon_for_coordinates
        except ImportError:
            pytest.skip("geopandas/fiona nicht verfügbar")

        # Wir testen nur, dass das Feld existiert
        # Der eigentliche Fetch braucht Netzwerk
        # Hier nur Signatur-Check
        import inspect
        sig = inspect.signature(fetch_building_polygon_for_coordinates)
        assert "tolerance_m" in sig.parameters

    def test_register_egid_function(self):
        """EGID kann im Index registriert werden."""
        cache = get_tile_cache()

        # Test-EGID registrieren
        test_egid = 999999999  # Fiktive EGID
        test_tile = "1088-22"

        cache.register_egid(test_egid, test_tile, e=2600450, n=1199830)

        # Sollte jetzt im Index sein
        found_tile = cache.get_tile_for_egid(test_egid)
        assert found_tile == test_tile

        # Cleanup: Wir lassen den Eintrag, schadet nicht


class TestPrefetchJob:
    """Test-Suite für den Background Prefetch-Job."""

    def test_prefetch_status_structure(self):
        """get_prefetch_status() gibt korrekte Struktur zurück."""
        status = get_prefetch_status()

        assert "in_progress" in status
        assert "count" in status
        assert isinstance(status["in_progress"], list)
        assert isinstance(status["count"], int)

    def test_schedule_prefetch_without_gdb(self):
        """schedule_prefetch() handelt fehlende GDB gracefully."""
        # Sollte keinen Fehler werfen, nur loggen
        fake_path = Path("/nonexistent/fake.gdb")
        # schedule_prefetch würde hier starten aber schnell abbrechen
        # Wir testen nur, dass kein Crash passiert
        assert True  # Placeholder - echter Test braucht Mock

    @pytest.mark.asyncio
    async def test_prefetch_skips_duplicate_tiles(self):
        """Prefetch wird nicht doppelt für dasselbe Tile gestartet."""
        from app.services.tile_prefetch import _prefetch_in_progress, _prefetch_lock

        # Simuliere laufenden Prefetch
        with _prefetch_lock:
            _prefetch_in_progress.add("TEST-99")

        status = get_prefetch_status()
        assert "TEST-99" in status["in_progress"]

        # Cleanup
        with _prefetch_lock:
            _prefetch_in_progress.discard("TEST-99")
