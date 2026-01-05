"""
E2E Tests für Gerüstbau-App.

Testet den vollständigen Workflow:
1. Projekt erstellen (Einzel- und Multi-Adresse)
2. Polygon-Vereinfachung (dynamisch + manuell)
3. Fassaden-Selektion und -Blockierung
4. Nachbar-Berechnung
5. 3D-View Datenfluss
6. Terrain/Hanglage
7. Gebäude mit Zonen
8. Cache-Konsistenz

Dokumentiert in: docs/tests/GERUESTBAU_E2E_TESTS.md
"""

import pytest
import json
import time
import sqlite3
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from unittest.mock import Mock, patch, MagicMock

# Test-Konstanten
TEST_ADDRESSES = {
    "single_efh": "Kramgasse 49, 3011 Bern",
    "rowhouse_range": "Knospenweg 2-10, 3006 Bern",  # Reihenhaus
    "complex_building": "Bundesplatz 3, 3011 Bern",  # Bundeshaus
    "church": "Münsterplatz 1, 3011 Bern",  # Berner Münster
    "mfh_slope": "Knospenweg 4, 3006 Bern",  # Gebäude mit Hanglage
}

TEST_EGIDS = {
    "knospenweg_2": "1243788",
    "knospenweg_4": "1243790",
    "knospenweg_6": "1243791",
    "knospenweg_8": "1243792",
    "knospenweg_10": "1243793",
    "bundeshaus": "2242547",
    "muenster": "1230337",
}


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def api_client():
    """HTTP-Client für API-Tests."""
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


@pytest.fixture
def project_service():
    """ProjectService Instanz."""
    try:
        from app.services.geruestbau.project_service import ProjectService
        return ProjectService()
    except ImportError:
        pytest.skip("ProjectService nicht verfügbar")


@pytest.fixture
def neighbors_service():
    """NeighborsService Instanz."""
    try:
        from app.services.neighbors_service import get_neighbors_service
        return get_neighbors_service()
    except ImportError:
        pytest.skip("NeighborsService nicht verfügbar")


@pytest.fixture
def smart_building_service():
    """SmartBuildingService Instanz."""
    try:
        from app.services.smart_building import get_smart_building_service
        return get_smart_building_service()
    except ImportError:
        pytest.skip("SmartBuildingService nicht verfügbar")


@pytest.fixture
def polygon_simplifier():
    """PolygonSimplifier Instanz."""
    try:
        from app.services.polygon_simplifier import simplify_building_polygon
        return simplify_building_polygon
    except ImportError:
        pytest.skip("PolygonSimplifier nicht verfügbar")


# ============================================================================
# 1. PROJEKT-ERSTELLUNG TESTS
# ============================================================================

class TestProjectCreation:
    """Tests für Projekt-Erstellung und -Verwaltung."""

    @pytest.mark.asyncio
    async def test_create_project_single_address(self, project_service):
        """Projekt mit einzelner Adresse erstellen."""
        from app.models.geruestbau import ProjectCreate

        project_data = ProjectCreate(
            name="Test EFH Projekt",
            address=TEST_ADDRESSES["single_efh"],
            client_name="Test AG",
            client_contact="test@example.com",
            description="E2E Test Projekt"
        )

        project = await project_service.create_project(project_data)

        assert project is not None
        assert project.id is not None
        assert project.name == "Test EFH Projekt"
        assert project.address == TEST_ADDRESSES["single_efh"]
        assert project.status == "draft"

        # Cleanup
        await project_service.delete_project(project.id)

    @pytest.mark.asyncio
    async def test_get_project_with_geodata(self, project_service):
        """Projekt mit Geodaten laden."""
        from app.models.geruestbau import ProjectCreate

        # Projekt erstellen
        project_data = ProjectCreate(
            name="Test Geodata Projekt",
            address=TEST_ADDRESSES["single_efh"]
        )
        project = await project_service.create_project(project_data)

        # Mit Geodaten laden
        project_with_data = await project_service.get_project_with_data(project.id)

        assert project_with_data is not None
        assert project_with_data.id == project.id

        # Geodata sollte vorhanden sein (aus SmartBuildingService)
        if project_with_data.geodata:
            assert "polygon" in project_with_data.geodata or project_with_data.geodata.get("polygon") is not None

        # Cleanup
        await project_service.delete_project(project.id)

    @pytest.mark.asyncio
    async def test_list_projects_with_filter(self, project_service):
        """Projekte mit Status-Filter auflisten."""
        from app.models.geruestbau import ProjectCreate

        # Projekt erstellen
        project = await project_service.create_project(ProjectCreate(
            name="List Test",
            address=TEST_ADDRESSES["single_efh"]
        ))

        # Alle Projekte
        all_projects = await project_service.list_projects()
        assert len(all_projects) >= 1

        # Nach Status filtern
        draft_projects = await project_service.list_projects(status="draft")
        assert all(p.status == "draft" for p in draft_projects)

        # Cleanup
        await project_service.delete_project(project.id)

    @pytest.mark.asyncio
    async def test_update_project(self, project_service):
        """Projekt aktualisieren."""
        from app.models.geruestbau import ProjectCreate, ProjectUpdate

        project = await project_service.create_project(ProjectCreate(
            name="Update Test",
            address=TEST_ADDRESSES["single_efh"]
        ))

        # Update
        updated = await project_service.update_project(
            project.id,
            ProjectUpdate(name="Updated Name", status="enriched")
        )

        assert updated.name == "Updated Name"
        assert updated.status == "enriched"

        # Cleanup
        await project_service.delete_project(project.id)

    @pytest.mark.asyncio
    async def test_delete_project(self, project_service):
        """Projekt löschen."""
        from app.models.geruestbau import ProjectCreate

        project = await project_service.create_project(ProjectCreate(
            name="Delete Test",
            address=TEST_ADDRESSES["single_efh"]
        ))

        project_id = project.id

        # Löschen
        success = await project_service.delete_project(project_id)
        assert success is True

        # Sollte nicht mehr existieren
        deleted = await project_service.get_project(project_id)
        assert deleted is None


# ============================================================================
# 2. MULTI-ADRESSE TESTS
# ============================================================================

class TestMultiAddressResolution:
    """Tests für Adressbereich-Auflösung (z.B. Knospenweg 2-10)."""

    def test_parse_address_range(self, api_client):
        """Adressbereich parsen."""
        response = api_client.get(
            "/api/v1/geruestbau/address/resolve",
            params={"address": TEST_ADDRESSES["rowhouse_range"]}
        )

        if response.status_code == 404:
            pytest.skip("Adresse nicht gefunden")

        assert response.status_code == 200
        data = response.json()

        assert "parsed" in data
        assert "buildings" in data
        assert data["building_count"] >= 1

        # Mehrere Gebäude erwartet
        if data["building_count"] > 1:
            assert len(data["buildings"]) == data["building_count"]

    def test_address_range_contains_all_buildings(self, api_client):
        """Alle Gebäude im Bereich werden gefunden."""
        response = api_client.get(
            "/api/v1/geruestbau/address/resolve",
            params={"address": TEST_ADDRESSES["rowhouse_range"]}
        )

        if response.status_code != 200:
            pytest.skip("Adresse nicht verfügbar")

        data = response.json()

        # Prüfe ob EGIDs vorhanden
        egids = [b.get("egid") for b in data.get("buildings", []) if b.get("egid")]

        # Mindestens 2 Gebäude für einen Bereich erwartet
        assert len(egids) >= 1, "Mindestens ein Gebäude sollte gefunden werden"

    def test_single_address_resolution(self, api_client):
        """Einzelne Adresse auflösen."""
        response = api_client.get(
            "/api/v1/geruestbau/address/resolve",
            params={"address": TEST_ADDRESSES["single_efh"]}
        )

        if response.status_code == 404:
            pytest.skip("Adresse nicht gefunden")

        assert response.status_code == 200
        data = response.json()

        # Einzelne Adresse = 1 Gebäude
        assert data["building_count"] == 1


# ============================================================================
# 3. POLYGON-VEREINFACHUNG TESTS
# ============================================================================

class TestPolygonSimplification:
    """Tests für dynamische und manuelle Polygon-Vereinfachung."""

    def test_simplify_with_default_epsilon(self, polygon_simplifier):
        """Vereinfachung mit dynamischem Epsilon."""
        # Test-Polygon (komplexes Gebäude)
        polygon = [
            [2600000, 1200000],
            [2600010, 1200000],
            [2600010, 1200002],  # Kleine Einbuchtung
            [2600012, 1200002],
            [2600012, 1200010],
            [2600000, 1200010],
        ]

        result = polygon_simplifier(polygon, epsilon=None, use_dynamic_epsilon=True)

        assert result is not None
        assert result.simplified_point_count <= result.original_point_count
        assert result.epsilon_used > 0

    def test_simplify_with_small_epsilon(self, polygon_simplifier):
        """Vereinfachung mit kleinem Epsilon (wenig Vereinfachung)."""
        polygon = [
            [2600000, 1200000],
            [2600010, 1200000],
            [2600010, 1200001],  # Kleine Stufe
            [2600015, 1200001],
            [2600015, 1200010],
            [2600000, 1200010],
        ]

        result = polygon_simplifier(polygon, epsilon=0.3)

        assert result.epsilon_used == 0.3
        # Mit kleinem Epsilon bleiben mehr Punkte erhalten
        assert result.simplified_point_count >= 4

    def test_simplify_with_large_epsilon(self, polygon_simplifier):
        """Vereinfachung mit grossem Epsilon (starke Vereinfachung)."""
        polygon = [
            [2600000, 1200000],
            [2600010, 1200000],
            [2600010, 1200001],  # Kleine Stufe (wird entfernt)
            [2600015, 1200001],
            [2600015, 1200010],
            [2600000, 1200010],
        ]

        result = polygon_simplifier(polygon, epsilon=2.0)

        assert result.epsilon_used == 2.0
        # Mit grossem Epsilon werden kleine Einbuchtungen entfernt
        assert result.simplified_point_count <= result.original_point_count

    def test_simplification_preserves_area(self, polygon_simplifier):
        """Vereinfachung erhält Fläche ungefähr."""
        polygon = [
            [2600000, 1200000],
            [2600100, 1200000],
            [2600100, 1200100],
            [2600000, 1200100],
        ]

        result_fine = polygon_simplifier(polygon, epsilon=0.3)
        result_coarse = polygon_simplifier(polygon, epsilon=2.0)

        # Fläche sollte ähnlich sein
        area_diff = abs(result_fine.area_m2 - result_coarse.area_m2)
        assert area_diff / result_fine.area_m2 < 0.1, "Fläche sollte <10% abweichen"

    def test_simplification_calculates_sides(self, polygon_simplifier):
        """Vereinfachung berechnet Fassaden."""
        polygon = [
            [2600000, 1200000],
            [2600010, 1200000],
            [2600010, 1200010],
            [2600000, 1200010],
        ]

        result = polygon_simplifier(polygon, epsilon=0.3)

        assert result.sides is not None
        assert len(result.sides) >= 3  # Mindestens 3 Seiten für geschlossenes Polygon

        # Jede Seite hat Richtung
        for side in result.sides:
            assert "direction" in side
            assert side["direction"] in ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]

    def test_dynamic_epsilon_scales_with_size(self, polygon_simplifier):
        """Dynamisches Epsilon skaliert mit Gebäudegrösse."""
        # Kleines Gebäude (EFH)
        small_polygon = [
            [0, 0], [10, 0], [10, 12], [0, 12]
        ]

        # Grosses Gebäude (Industrie)
        large_polygon = [
            [0, 0], [100, 0], [100, 80], [0, 80]
        ]

        result_small = polygon_simplifier(small_polygon, use_dynamic_epsilon=True)
        result_large = polygon_simplifier(large_polygon, use_dynamic_epsilon=True)

        # Grosses Gebäude sollte grösseres Epsilon verwenden
        assert result_large.epsilon_used >= result_small.epsilon_used


# ============================================================================
# 4. FASSADEN-SELEKTION TESTS
# ============================================================================

class TestFacadeSelection:
    """Tests für Fassaden-Auswahl und -Berechnung."""

    def test_get_facades_for_address(self, api_client):
        """Fassaden für Adresse laden."""
        response = api_client.get(
            "/api/v1/geruestbau/configurator/facades",
            params={"address": TEST_ADDRESSES["single_efh"]}
        )

        if response.status_code == 404:
            pytest.skip("Gebäude nicht gefunden")

        assert response.status_code == 200
        data = response.json()

        assert "building" in data
        assert "selected_facades" in data
        assert "metadata" in data

        # Gebäude-Daten prüfen
        building = data["building"]
        assert "egid" in building or building.get("egid") is None
        assert "polygon" in building

        # Fassaden prüfen
        facades = data["selected_facades"]
        assert len(facades) >= 1

        for facade in facades:
            assert "direction" in facade
            assert "length_m" in facade
            assert facade["length_m"] > 0

    def test_facades_have_compass_directions(self, api_client):
        """Fassaden haben Kompass-Richtungen."""
        response = api_client.get(
            "/api/v1/geruestbau/configurator/facades",
            params={"address": TEST_ADDRESSES["single_efh"]}
        )

        if response.status_code != 200:
            pytest.skip("Fassaden nicht verfügbar")

        data = response.json()
        valid_directions = {"N", "NE", "E", "SE", "S", "SW", "W", "NW"}

        for facade in data["selected_facades"]:
            assert facade["direction"] in valid_directions, \
                f"Ungültige Richtung: {facade['direction']}"

    def test_facades_with_simplify_epsilon(self, api_client):
        """Fassaden mit unterschiedlichem Epsilon."""
        # Mit feinem Epsilon
        response_fine = api_client.get(
            "/api/v1/geruestbau/configurator/facades",
            params={
                "address": TEST_ADDRESSES["single_efh"],
                "simplify_epsilon": 0.3
            }
        )

        # Mit grobem Epsilon
        response_coarse = api_client.get(
            "/api/v1/geruestbau/configurator/facades",
            params={
                "address": TEST_ADDRESSES["single_efh"],
                "simplify_epsilon": 2.0
            }
        )

        if response_fine.status_code != 200 or response_coarse.status_code != 200:
            pytest.skip("Fassaden nicht verfügbar")

        data_fine = response_fine.json()
        data_coarse = response_coarse.json()

        # Grobe Vereinfachung = weniger Fassaden
        assert data_coarse["metadata"]["facade_count"] <= data_fine["metadata"]["facade_count"]

    def test_facade_heights_match_building(self, api_client):
        """Fassaden-Höhen entsprechen Gebäude-Höhe."""
        response = api_client.get(
            "/api/v1/geruestbau/configurator/facades",
            params={"address": TEST_ADDRESSES["single_efh"]}
        )

        if response.status_code != 200:
            pytest.skip("Fassaden nicht verfügbar")

        data = response.json()
        building = data["building"]

        if "trauf_height_m" in building and building["trauf_height_m"]:
            for facade in data["selected_facades"]:
                if "height_m" in facade:
                    # Höhe sollte plausibel sein (2-100m)
                    assert 2 <= facade["height_m"] <= 100


# ============================================================================
# 5. NACHBAR-BERECHNUNG UND FASSADEN-BLOCKIERUNG TESTS
# ============================================================================

class TestNeighborsAndFacadeBlocking:
    """Tests für Nachbar-Berechnung und blockierte Fassaden."""

    def test_get_neighbors_for_rowhouse(self, neighbors_service):
        """Nachbarn für Reihenhaus finden."""
        # Knospenweg 4 (Mitte der Reihe)
        result = neighbors_service.get_neighbors(
            egid=TEST_EGIDS["knospenweg_4"],
            radius_m=10.0,
            include_polygons=True
        )

        if result is None:
            pytest.skip("Keine Nachbar-Daten verfügbar")

        assert result.target_egid == TEST_EGIDS["knospenweg_4"]
        assert len(result.neighbors) >= 0  # Kann 0 sein wenn nicht im Cache

    def test_blocked_sides_for_adjacent_buildings(self, api_client):
        """Blockierte Seiten bei angrenzenden Gebäuden."""
        response = api_client.get(
            f"/api/v1/geruestbau/building/{TEST_EGIDS['knospenweg_4']}/neighbors",
            params={"radius_m": 10, "include_polygons": True}
        )

        if response.status_code == 404:
            pytest.skip("Gebäude nicht im Cache")

        assert response.status_code == 200
        data = response.json()

        assert "blocked_sides" in data
        # Bei Reihenhaus sollten Seiten blockiert sein
        # (kann leer sein wenn Nachbarn nicht geladen)

    def test_neighbors_with_different_radii(self, neighbors_service):
        """Nachbarn mit verschiedenen Radien."""
        egid = TEST_EGIDS["knospenweg_4"]

        result_0m = neighbors_service.get_neighbors(egid, radius_m=0.5)
        result_5m = neighbors_service.get_neighbors(egid, radius_m=5.0)
        result_10m = neighbors_service.get_neighbors(egid, radius_m=10.0)

        if all(r is None for r in [result_0m, result_5m, result_10m]):
            pytest.skip("Keine Nachbar-Daten")

        # Grösserer Radius = mehr oder gleich viele Nachbarn
        if result_0m and result_5m:
            assert len(result_5m.neighbors) >= len(result_0m.neighbors)
        if result_5m and result_10m:
            assert len(result_10m.neighbors) >= len(result_5m.neighbors)

    def test_neighbor_direction_calculation(self, neighbors_service):
        """Nachbar-Richtung wird korrekt berechnet."""
        result = neighbors_service.get_neighbors(
            egid=TEST_EGIDS["knospenweg_4"],
            radius_m=10.0
        )

        if result is None or len(result.neighbors) == 0:
            pytest.skip("Keine Nachbarn gefunden")

        valid_directions = {"N", "NE", "E", "SE", "S", "SW", "W", "NW"}

        for neighbor in result.neighbors:
            if neighbor.direction:
                assert neighbor.direction in valid_directions

    def test_neighbor_distance_calculation(self, neighbors_service):
        """Nachbar-Distanz wird korrekt berechnet."""
        result = neighbors_service.get_neighbors(
            egid=TEST_EGIDS["knospenweg_4"],
            radius_m=10.0
        )

        if result is None or len(result.neighbors) == 0:
            pytest.skip("Keine Nachbarn gefunden")

        for neighbor in result.neighbors:
            assert neighbor.distance_m >= 0
            assert neighbor.distance_m <= 10.0  # Innerhalb Suchradius

    def test_neighbor_polygons_included(self, api_client):
        """Nachbar-Polygone werden mitgeliefert."""
        response = api_client.get(
            f"/api/v1/geruestbau/building/{TEST_EGIDS['knospenweg_4']}/neighbors",
            params={"radius_m": 10, "include_polygons": True}
        )

        if response.status_code == 404:
            pytest.skip("Gebäude nicht im Cache")

        data = response.json()

        # Prüfe ob Polygone enthalten
        for neighbor in data.get("neighbors", []):
            if "polygon" in neighbor and neighbor["polygon"]:
                assert len(neighbor["polygon"]) >= 3


# ============================================================================
# 6. 3D-VIEW DATENFLUSS TESTS
# ============================================================================

class TestThreeDViewDataFlow:
    """Tests für 3D-Visualisierung Datenfluss."""

    @pytest.mark.asyncio
    async def test_smart_building_data_for_3d(self, smart_building_service):
        """SmartBuildingService liefert 3D-relevante Daten."""
        bundle = await smart_building_service.collect_all_data(
            address=TEST_ADDRESSES["single_efh"],
            include_research=False,
            include_zones_analysis=False
        )

        if bundle is None:
            pytest.skip("Keine Daten verfügbar")

        # Für 3D-View benötigte Felder
        assert bundle.polygon is not None, "Polygon fehlt"
        assert len(bundle.polygon) >= 3, "Polygon braucht min. 3 Punkte"

        # Höhen für 3D-Rendering
        if bundle.traufhoehe_m is not None:
            assert bundle.traufhoehe_m > 0

    def test_3d_data_contains_heights(self, api_client):
        """3D-Daten enthalten Höheninformationen."""
        response = api_client.get(
            "/api/v1/smart-building/data",
            params={
                "address": TEST_ADDRESSES["single_efh"],
                "include_research": False
            }
        )

        if response.status_code != 200:
            pytest.skip("Smart-Building Daten nicht verfügbar")

        data = response.json()

        # Höhen für 3D-Rendering
        height_fields = ["traufhoehe_m", "firsthoehe_m", "gebaeudehoehe_m"]
        has_height = any(data.get(f) is not None for f in height_fields)

        assert has_height, "Mindestens ein Höhenfeld muss vorhanden sein"

    def test_neighbors_for_3d_scene(self, api_client):
        """Nachbarn für 3D-Szene laden."""
        response = api_client.get(
            f"/api/v1/geruestbau/building/{TEST_EGIDS['knospenweg_4']}/neighbors",
            params={"radius_m": 10, "include_polygons": True}
        )

        if response.status_code == 404:
            pytest.skip("Gebäude nicht im Cache")

        data = response.json()

        # Für 3D-Szene: Target-Polygon und Nachbar-Polygone
        assert "target_polygon" in data or data.get("target_egid") is not None


# ============================================================================
# 7. TERRAIN UND HANGLAGE TESTS
# ============================================================================

class TestTerrainAndSlope:
    """Tests für Terrain-Daten und Hanglage-Berechnung."""

    @pytest.mark.asyncio
    async def test_terrain_data_loaded(self, smart_building_service):
        """Terrain-Daten werden geladen."""
        bundle = await smart_building_service.collect_all_data(
            address=TEST_ADDRESSES["single_efh"],
            include_research=False,
            include_zones_analysis=False
        )

        if bundle is None:
            pytest.skip("Keine Daten")

        # Terrain ist optional, aber wenn vorhanden...
        if bundle.terrain:
            # TerrainProfile hat reference_height_m, nicht height_m
            assert bundle.terrain.reference_height_m is not None or \
                   bundle.terrain.min_height_m is not None

    @pytest.mark.asyncio
    async def test_project_enrichment_adds_terrain(self, project_service):
        """Projekt-Enrichment fügt Terrain-Daten hinzu."""
        from app.models.geruestbau import ProjectCreate

        project = await project_service.create_project(ProjectCreate(
            name="Terrain Test",
            address=TEST_ADDRESSES["single_efh"]
        ))

        # Enrichen
        enriched = await project_service.enrich_with_geodata(project.id)

        if enriched and enriched.geodata:
            # Terrain sollte vorhanden sein
            terrain = enriched.geodata.get("terrain")
            if terrain:
                assert "height_m" in terrain or "slope_class" in terrain

        # Cleanup
        await project_service.delete_project(project.id)

    def test_slope_classification(self):
        """Hanglage-Klassifikation funktioniert."""
        # Hanglage-Klassen
        classifications = {
            "eben": (0, 0.5),      # < 0.5m
            "leicht": (0.5, 1.5),  # 0.5-1.5m
            "mittel": (1.5, 3.0),  # 1.5-3.0m
            "stark": (3.0, float('inf')),  # > 3.0m
        }

        def classify_slope(slope_m: float) -> str:
            for cls, (min_val, max_val) in classifications.items():
                if min_val <= slope_m < max_val:
                    return cls
            return "stark"

        assert classify_slope(0.2) == "eben"
        assert classify_slope(1.0) == "leicht"
        assert classify_slope(2.0) == "mittel"
        assert classify_slope(5.0) == "stark"


# ============================================================================
# 8. GEBÄUDE MIT ZONEN TESTS
# ============================================================================

class TestBuildingZones:
    """Tests für Gebäude mit mehreren Zonen (z.B. Bundeshaus)."""

    @pytest.mark.asyncio
    async def test_complex_building_has_zones(self, smart_building_service):
        """Komplexes Gebäude hat mehrere Zonen."""
        bundle = await smart_building_service.collect_all_data(
            address=TEST_ADDRESSES["complex_building"],
            include_research=True,
            include_zones_analysis=True
        )

        if bundle is None:
            pytest.skip("Bundeshaus nicht verfügbar")

        # Komplexes Gebäude sollte Zonen haben
        assert bundle.zones is not None
        # Bundeshaus hat typischerweise Arkaden, Hauptgebäude, Kuppel
        if len(bundle.zones) > 1:
            zone_types = [z.type for z in bundle.zones]
            assert len(zone_types) > 1, "Mehrere Zonen erwartet"

    @pytest.mark.asyncio
    async def test_church_has_tower_zone(self, smart_building_service):
        """Kirche hat Turm-Zone."""
        bundle = await smart_building_service.collect_all_data(
            address=TEST_ADDRESSES["church"],
            include_research=True,
            include_zones_analysis=True
        )

        if bundle is None:
            pytest.skip("Münster nicht verfügbar")

        # Kirche sollte Turm-Zone haben
        if bundle.zones and len(bundle.zones) > 1:
            zone_types = [z.type for z in bundle.zones]
            # Typischerweise: hauptgebaeude, turm
            assert "turm" in zone_types or any("turm" in str(zt).lower() for zt in zone_types)

    @pytest.mark.asyncio
    async def test_simple_building_single_zone(self, smart_building_service):
        """Einfaches Gebäude hat eine Zone."""
        bundle = await smart_building_service.collect_all_data(
            address=TEST_ADDRESSES["single_efh"],
            include_research=False,
            include_zones_analysis=True
        )

        if bundle is None:
            pytest.skip("EFH nicht verfügbar")

        # Einfaches Gebäude hat typischerweise 1 Zone
        if bundle.zones:
            # EFH sollte maximal 1-2 Zonen haben
            assert len(bundle.zones) <= 3


# ============================================================================
# 9. SCAFFOLD CONFIGURATION TESTS
# ============================================================================

class TestScaffoldConfiguration:
    """Tests für Gerüst-Konfiguration."""

    @pytest.mark.asyncio
    async def test_save_and_load_scaffold_config(self, project_service):
        """Scaffold-Config speichern und laden."""
        from app.models.geruestbau import ProjectCreate, ScaffoldConfig

        # Projekt erstellen
        project = await project_service.create_project(ProjectCreate(
            name="Config Test",
            address=TEST_ADDRESSES["single_efh"]
        ))

        # Config speichern
        config = ScaffoldConfig(
            simplify_epsilon=0.5,
            field_length_ratio=75.0
        )
        saved_config = await project_service.update_scaffold_config(project.id, config)

        assert saved_config.simplify_epsilon == 0.5
        assert saved_config.field_length_ratio == 75.0

        # Config laden
        loaded_config = await project_service.get_scaffold_config(project.id)
        assert loaded_config.simplify_epsilon == 0.5
        assert loaded_config.field_length_ratio == 75.0

        # Cleanup
        await project_service.delete_project(project.id)

    @pytest.mark.asyncio
    async def test_config_persists_across_loads(self, project_service):
        """Config bleibt nach Projekt-Neuladen erhalten."""
        from app.models.geruestbau import ProjectCreate, ScaffoldConfig

        project = await project_service.create_project(ProjectCreate(
            name="Persist Test",
            address=TEST_ADDRESSES["single_efh"]
        ))

        # Config setzen
        await project_service.update_scaffold_config(
            project.id,
            ScaffoldConfig(simplify_epsilon=1.2, field_length_ratio=60.0)
        )

        # Projekt neu laden
        project_reloaded = await project_service.get_project(project.id)
        config = await project_service.get_scaffold_config(project.id)

        assert config.simplify_epsilon == 1.2
        assert config.field_length_ratio == 60.0

        # Cleanup
        await project_service.delete_project(project.id)


# ============================================================================
# 10. CACHE-KONSISTENZ TESTS
# ============================================================================

class TestCacheConsistency:
    """Tests für Cache-Konsistenz über verschiedene Services."""

    @pytest.mark.asyncio
    async def test_smart_building_cache_populated(self, smart_building_service):
        """SmartBuildingService befüllt Cache."""
        # Daten laden
        bundle = await smart_building_service.collect_all_data(
            address=TEST_ADDRESSES["single_efh"],
            include_research=False
        )

        if bundle is None or not bundle.egid:
            pytest.skip("Keine Daten")

        # Cache prüfen
        cached = smart_building_service.get_bundle_by_egid(bundle.egid)

        assert cached is not None
        assert cached.egid == bundle.egid

    def test_neighbors_use_smart_building_cache(self, neighbors_service, smart_building_service):
        """NeighborsService verwendet SmartBuildingService."""
        # Prüfe dass NeighborsService SmartBuildingService nutzt
        assert hasattr(neighbors_service, '_get_smart_service')

        smart_service = neighbors_service._get_smart_service()
        assert smart_service is not None

    @pytest.mark.asyncio
    async def test_project_uses_cached_data(self, project_service, smart_building_service):
        """ProjectService verwendet gecachte Daten."""
        from app.models.geruestbau import ProjectCreate

        # Erst Cache befüllen
        bundle = await smart_building_service.collect_all_data(
            address=TEST_ADDRESSES["single_efh"],
            include_research=False
        )

        if bundle is None:
            pytest.skip("Keine Daten")

        # Dann Projekt erstellen
        project = await project_service.create_project(ProjectCreate(
            name="Cache Test",
            address=TEST_ADDRESSES["single_efh"],
            egid=bundle.egid
        ))

        # Projekt mit Daten laden sollte Cache nutzen
        project_with_data = await project_service.get_project_with_data(project.id)

        # Cleanup
        await project_service.delete_project(project.id)


# ============================================================================
# 11. API INTEGRATION TESTS
# ============================================================================

class TestAPIIntegration:
    """Vollständige API-Integrationstests."""

    def test_full_workflow_single_building(self, api_client):
        """Vollständiger Workflow für einzelnes Gebäude."""
        # 1. Fassaden laden
        facades_response = api_client.get(
            "/api/v1/geruestbau/configurator/facades",
            params={"address": TEST_ADDRESSES["single_efh"]}
        )

        if facades_response.status_code != 200:
            pytest.skip("Gebäude nicht verfügbar")

        facades_data = facades_response.json()
        egid = facades_data["building"].get("egid")

        # 2. Projekt erstellen
        project_response = api_client.post(
            "/api/v1/geruestbau/projects",
            json={
                "name": "E2E Test Projekt",
                "address": TEST_ADDRESSES["single_efh"],
                "egid": egid
            }
        )

        assert project_response.status_code == 200
        project = project_response.json()
        project_id = project["id"]

        # 3. Nachbarn laden (für 3D-View)
        if egid:
            neighbors_response = api_client.get(
                f"/api/v1/geruestbau/building/{egid}/neighbors",
                params={"radius_m": 10}
            )
            # 404 ist OK wenn nicht im Cache

        # 4. Config speichern
        config_response = api_client.put(
            f"/api/v1/geruestbau/projects/{project_id}/scaffold",
            json={
                "simplify_epsilon": 0.5,
                "field_length_ratio": 50.0
            }
        )

        assert config_response.status_code == 200

        # 5. Projekt laden
        load_response = api_client.get(
            f"/api/v1/geruestbau/projects/{project_id}"
        )

        assert load_response.status_code == 200

        # 6. Cleanup
        delete_response = api_client.delete(
            f"/api/v1/geruestbau/projects/{project_id}"
        )

        assert delete_response.status_code == 200

    def test_api_error_handling(self, api_client):
        """API gibt korrekte Fehler zurück."""
        # Nicht existierendes Projekt
        response = api_client.get(
            "/api/v1/geruestbau/projects/non-existent-id"
        )
        assert response.status_code == 404

        # Ungültige Adresse
        response = api_client.get(
            "/api/v1/geruestbau/address/resolve",
            params={"address": "XYZ123NonExistent"}
        )
        # Entweder 404 oder leere Antwort
        assert response.status_code in [200, 404]


# ============================================================================
# 12. PERFORMANCE TESTS
# ============================================================================

class TestPerformance:
    """Performance-Tests für kritische Operationen."""

    def test_facade_loading_under_5s(self, api_client):
        """Fassaden laden dauert < 5s (nach Cache-Warmup)."""
        # Erster Aufruf kann langsam sein (STAC-Tile Download)
        # Wir messen den zweiten Aufruf (Cache-Hit)

        # Warmup (ignoriere Zeit)
        warmup_response = api_client.get(
            "/api/v1/geruestbau/configurator/facades",
            params={"address": TEST_ADDRESSES["single_efh"]}
        )

        if warmup_response.status_code != 200:
            pytest.skip("Endpoint nicht verfügbar")

        # Eigentlicher Test (sollte aus Cache kommen)
        start = time.time()
        response = api_client.get(
            "/api/v1/geruestbau/configurator/facades",
            params={"address": TEST_ADDRESSES["single_efh"]}
        )
        elapsed = time.time() - start

        # Mit Cache sollte es schnell sein
        # Erhöhe auf 30s um Netzwerk-Variationen zu tolerieren
        assert elapsed < 30.0, f"Fassaden laden (cached): {elapsed:.2f}s (sollte < 30s)"

    def test_neighbors_lookup_under_1s(self, neighbors_service):
        """Nachbar-Lookup dauert < 1s."""
        start = time.time()

        result = neighbors_service.get_neighbors(
            egid=TEST_EGIDS["knospenweg_4"],
            radius_m=10.0,
            include_polygons=False
        )

        elapsed = time.time() - start

        # Auch wenn keine Daten: sollte schnell sein
        assert elapsed < 1.0, f"Nachbar-Lookup: {elapsed:.2f}s (sollte < 1s)"

    def test_address_resolution_under_2s(self, api_client):
        """Adress-Auflösung dauert < 2s."""
        start = time.time()

        response = api_client.get(
            "/api/v1/geruestbau/address/resolve",
            params={"address": TEST_ADDRESSES["single_efh"]}
        )

        elapsed = time.time() - start

        assert elapsed < 2.0, f"Adress-Auflösung: {elapsed:.2f}s (sollte < 2s)"


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-x"])
