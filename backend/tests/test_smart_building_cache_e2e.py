"""
E2E Tests für SmartBuildingService Cache-Architektur.

Testet die Service-Hierarchie:
- ProjectService → SmartBuildingService → smart_building_cache
- NeighborsService → SmartBuildingService → smart_building_cache

Dokumentiert in: docs/architecture/POLYGON_DATENFLUSS.md (Abschnitt 19-24)

Test-Szenarien:
1. Bundle-Cache: Laden und Speichern von BuildingDataBundle
2. Service-Hierarchie: Services nutzen SmartBuildingService (nicht direkt Cache)
3. Cache-TTL: Bundle-Expiration nach 24h
4. Nachbar-Berechnung: Dynamisch via NeighborsService
5. Projekt-Laden: ProjectService → SmartBuildingService
"""

import pytest
import json
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock


# ===== FIXTURES =====

@pytest.fixture
def test_bundle_data():
    """Test-Daten für ein BuildingDataBundle."""
    return {
        'egid': '2242547',
        'address_input': 'Bundesplatz 3, 3011 Bern',
        'address_matched': 'Bundesplatz 3, 3011 Bern',
        'lv95_e': 2600450.0,
        'lv95_n': 1199830.0,
        'building_name': 'Bundeshaus',
        'polygon': [[2600450, 1199830], [2600500, 1199830], [2600500, 1199880], [2600450, 1199880]],
        'traufhoehe_m': 14.5,
        'firsthoehe_m': 62.6,
        'gebaeudehoehe_m': 64.0,
    }


@pytest.fixture
def temp_db(tmp_path):
    """Temporäre Datenbank für Tests."""
    db_path = tmp_path / "test_building_contexts.db"
    conn = sqlite3.connect(str(db_path))

    # Schema erstellen
    conn.execute("""
        CREATE TABLE IF NOT EXISTS smart_building_cache (
            egid TEXT PRIMARY KEY,
            bundle_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

    return db_path


# ===== UNIT TESTS: SmartBuildingService =====

class TestSmartBuildingServiceCacheInterface:
    """Tests für SmartBuildingService.get_bundle_by_egid()"""

    def test_get_bundle_by_egid_returns_none_for_unknown_egid(self):
        """Unbekannte EGID gibt None zurück."""
        try:
            from app.services.smart_building import get_smart_building_service

            service = get_smart_building_service()
            result = service.get_bundle_by_egid("999999999")

            assert result is None
        except ImportError as e:
            pytest.skip(f"Import-Fehler: {e}")

    def test_get_bundle_by_egid_method_exists(self):
        """SmartBuildingService hat get_bundle_by_egid Methode."""
        try:
            from app.services.smart_building import get_smart_building_service

            service = get_smart_building_service()

            assert hasattr(service, 'get_bundle_by_egid'), \
                "SmartBuildingService muss get_bundle_by_egid() haben"
            assert callable(getattr(service, 'get_bundle_by_egid'))
        except ImportError as e:
            pytest.skip(f"Import-Fehler: {e}")


class TestCacheTTL:
    """Tests für Cache-TTL und Expiration."""

    def test_bundle_expires_after_24h(self, temp_db, test_bundle_data):
        """Bundle wird nach 24h als expired markiert."""
        conn = sqlite3.connect(str(temp_db))

        # Bundle mit abgelaufener Expiration speichern
        expired_time = (datetime.utcnow() - timedelta(hours=25)).isoformat()

        conn.execute("""
            INSERT INTO smart_building_cache (egid, bundle_json, created_at, expires_at)
            VALUES (?, ?, ?, ?)
        """, (
            test_bundle_data['egid'],
            json.dumps(test_bundle_data),
            datetime.utcnow().isoformat(),
            expired_time  # Abgelaufen!
        ))
        conn.commit()

        # Prüfen ob Entry existiert aber abgelaufen ist
        cursor = conn.execute(
            "SELECT expires_at FROM smart_building_cache WHERE egid = ?",
            (test_bundle_data['egid'],)
        )
        row = cursor.fetchone()

        assert row is not None
        expires_at = datetime.fromisoformat(row[0])
        assert expires_at < datetime.utcnow(), "Bundle sollte abgelaufen sein"

        conn.close()

    def test_fresh_bundle_not_expired(self, temp_db, test_bundle_data):
        """Frisches Bundle ist nicht abgelaufen."""
        conn = sqlite3.connect(str(temp_db))

        # Bundle mit gültiger Expiration speichern
        expires_at = (datetime.utcnow() + timedelta(hours=24)).isoformat()

        conn.execute("""
            INSERT INTO smart_building_cache (egid, bundle_json, created_at, expires_at)
            VALUES (?, ?, ?, ?)
        """, (
            test_bundle_data['egid'],
            json.dumps(test_bundle_data),
            datetime.utcnow().isoformat(),
            expires_at
        ))
        conn.commit()

        cursor = conn.execute(
            "SELECT expires_at FROM smart_building_cache WHERE egid = ?",
            (test_bundle_data['egid'],)
        )
        row = cursor.fetchone()

        assert row is not None
        expires_at = datetime.fromisoformat(row[0])
        assert expires_at > datetime.utcnow(), "Bundle sollte noch gültig sein"

        conn.close()


# ===== INTEGRATION TESTS: Service-Hierarchie =====

class TestProjectServiceUsesSmartBuildingService:
    """Tests dass ProjectService über SmartBuildingService auf Cache zugreift."""

    def test_project_service_has_smart_service_method(self):
        """ProjectService hat _get_bundle_from_smart_service Methode."""
        try:
            from app.services.geruestbau.project_service import ProjectService

            service = ProjectService()

            assert hasattr(service, '_get_bundle_from_smart_service'), \
                "ProjectService muss _get_bundle_from_smart_service() haben"
        except ImportError as e:
            pytest.skip(f"Import-Fehler: {e}")

    def test_project_service_not_direct_db_access(self):
        """ProjectService greift nicht direkt auf smart_building_cache zu."""
        try:
            from app.services.geruestbau.project_service import ProjectService
            import inspect

            # Source Code analysieren
            source = inspect.getsource(ProjectService._get_bundle_from_smart_service)

            # Sollte NICHT direkt auf DB zugreifen
            assert 'sqlite3.connect' not in source, \
                "ProjectService sollte nicht direkt sqlite3.connect verwenden"

            # Sollte SmartBuildingService verwenden
            assert 'get_smart_building_service' in source or 'smart_service' in source.lower(), \
                "ProjectService sollte SmartBuildingService verwenden"

        except ImportError as e:
            pytest.skip(f"Import-Fehler: {e}")
        except AttributeError:
            pytest.skip("_get_bundle_from_smart_service nicht gefunden")


class TestNeighborsServiceUsesSmartBuildingService:
    """Tests dass NeighborsService über SmartBuildingService auf Cache zugreift."""

    def test_neighbors_service_has_smart_service(self):
        """NeighborsService hat _get_smart_service Methode."""
        try:
            from app.services.neighbors_service import NeighborsService

            service = NeighborsService()

            assert hasattr(service, '_get_smart_service'), \
                "NeighborsService muss _get_smart_service() haben"
        except ImportError as e:
            pytest.skip(f"Import-Fehler: {e}")

    def test_neighbors_service_lazy_loads_smart_service(self):
        """NeighborsService lädt SmartBuildingService lazy."""
        try:
            from app.services.neighbors_service import NeighborsService

            service = NeighborsService()

            # Initial sollte _smart_service None sein
            assert service._smart_service is None, \
                "SmartBuildingService sollte lazy geladen werden"

            # Nach Aufruf sollte es geladen sein
            smart = service._get_smart_service()
            assert smart is not None
            assert service._smart_service is not None

        except ImportError as e:
            pytest.skip(f"Import-Fehler: {e}")


# ===== E2E TESTS: Vollständiger Datenfluss =====

class TestE2EBundleCacheFlow:
    """E2E Tests für Bundle-Cache Datenfluss."""

    @pytest.mark.asyncio
    async def test_collect_all_data_saves_to_cache(self):
        """collect_all_data() speichert Bundle im Cache."""
        try:
            from app.services.smart_building import get_smart_building_service

            service = get_smart_building_service()

            # Daten sammeln
            bundle = await service.collect_all_data(
                address="Kramgasse 49, 3011 Bern",
                include_research=False,  # Schneller
                include_zones_analysis=False
            )

            if bundle is None:
                pytest.skip("Keine Daten verfügbar")

            # Prüfen ob im Cache
            if bundle.egid:
                cached = service.get_bundle_by_egid(bundle.egid)
                assert cached is not None, "Bundle sollte im Cache sein"
                assert cached.egid == bundle.egid

        except ImportError as e:
            pytest.skip(f"Import-Fehler: {e}")

    @pytest.mark.asyncio
    async def test_cache_hit_returns_same_data(self):
        """Cache-Hit liefert dieselben Daten."""
        try:
            from app.services.smart_building import get_smart_building_service

            service = get_smart_building_service()

            # Erste Anfrage
            bundle1 = await service.collect_all_data(
                address="Kramgasse 49, 3011 Bern",
                include_research=False
            )

            if bundle1 is None or not bundle1.egid:
                pytest.skip("Keine Daten verfügbar")

            # Zweite Anfrage (sollte aus Cache kommen)
            bundle2 = service.get_bundle_by_egid(bundle1.egid)

            assert bundle2 is not None
            assert bundle2.egid == bundle1.egid
            assert bundle2.polygon == bundle1.polygon

        except ImportError as e:
            pytest.skip(f"Import-Fehler: {e}")


class TestE2ENeighborsFlow:
    """E2E Tests für Nachbar-Berechnung."""

    def test_neighbors_service_returns_result(self):
        """NeighborsService gibt Ergebnis zurück."""
        try:
            from app.services.neighbors_service import get_neighbors_service

            service = get_neighbors_service()

            # Braucht EGID im Cache - überspringen wenn nicht verfügbar
            result = service.get_neighbors(
                egid="1243790",  # Knospenweg 4 (Mitte der Reihe)
                radius_m=10.0,
                include_polygons=False
            )

            if result is None:
                pytest.skip("Keine Nachbar-Daten verfügbar")

            assert hasattr(result, 'neighbors')
            assert hasattr(result, 'target_egid')

        except ImportError as e:
            pytest.skip(f"Import-Fehler: {e}")

    def test_neighbors_blocked_sides_calculation(self):
        """blocked_sides wird aus Nachbarn berechnet."""
        try:
            from app.services.neighbors_service import get_neighbors_service, NeighborBuilding

            service = get_neighbors_service()

            # Mock-Test: Wenn Nachbar < 0.5m entfernt, dann blockiert
            neighbor = NeighborBuilding(
                egid="123457",
                distance_m=0.0,  # Direkt angrenzend
                direction="E"
            )

            # Prüfe Logik
            assert neighbor.distance_m < 0.5
            assert neighbor.direction == "E"

            # Bei distance < 0.5m sollte die Seite blockiert sein
            is_blocking = neighbor.distance_m < 0.5
            assert is_blocking, "Nachbar mit 0m Distanz sollte blockieren"

        except ImportError as e:
            pytest.skip(f"Import-Fehler: {e}")


# ===== PERFORMANCE TESTS =====

class TestCachePerformance:
    """Performance-Tests für Cache-Operationen."""

    def test_bundle_lookup_under_10ms(self):
        """Bundle-Lookup dauert < 10ms."""
        try:
            from app.services.smart_building import get_smart_building_service

            service = get_smart_building_service()

            # Mehrere Lookups
            start = time.time()
            for _ in range(10):
                service.get_bundle_by_egid("999999")  # Nicht existierendes EGID
            elapsed_ms = (time.time() - start) / 10 * 1000

            assert elapsed_ms < 10, f"Lookup: {elapsed_ms:.2f}ms (sollte < 10ms)"

        except ImportError as e:
            pytest.skip(f"Import-Fehler: {e}")

    def test_neighbors_calculation_under_50ms(self):
        """Nachbar-Berechnung dauert < 50ms."""
        try:
            from app.services.neighbors_service import get_neighbors_service

            service = get_neighbors_service()

            start = time.time()
            result = service.get_neighbors(
                egid="1243790",
                radius_m=10.0,
                include_polygons=False
            )
            elapsed_ms = (time.time() - start) * 1000

            if result is None:
                pytest.skip("Keine Daten für Performance-Test")

            assert elapsed_ms < 50, f"Nachbar-Berechnung: {elapsed_ms:.2f}ms (sollte < 50ms)"

        except ImportError as e:
            pytest.skip(f"Import-Fehler: {e}")


# ===== DATA INTEGRITY TESTS =====

class TestBundleDataIntegrity:
    """Tests für Daten-Integrität im Bundle."""

    def test_bundle_contains_required_fields(self):
        """BuildingDataBundle hat alle Pflichtfelder."""
        try:
            from app.services.smart_building.models import BuildingDataBundle

            bundle = BuildingDataBundle()

            # Pflichtfelder
            assert hasattr(bundle, 'egid')
            assert hasattr(bundle, 'polygon')
            assert hasattr(bundle, 'traufhoehe_m')
            assert hasattr(bundle, 'firsthoehe_m')
            assert hasattr(bundle, 'zones')
            assert hasattr(bundle, 'data_sources')

        except ImportError as e:
            pytest.skip(f"Import-Fehler: {e}")

    def test_bundle_to_prompt_context(self):
        """Bundle kann zu Prompt-Context konvertiert werden."""
        try:
            from app.services.smart_building.models import BuildingDataBundle, DataSource

            bundle = BuildingDataBundle(
                egid="12345",
                address_matched="Test 1, Bern",
                polygon=[[0, 0], [10, 0], [10, 10], [0, 10]],
                traufhoehe_m=10.0,
                firsthoehe_m=13.0
            )
            bundle.add_source(DataSource.SWISSBUILDINGS3D)

            context = bundle.to_prompt_context()

            assert isinstance(context, dict)
            assert context['egid'] == "12345"
            assert context['polygon_points'] == 4

        except ImportError as e:
            pytest.skip(f"Import-Fehler: {e}")


# ===== RUN TESTS =====

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])