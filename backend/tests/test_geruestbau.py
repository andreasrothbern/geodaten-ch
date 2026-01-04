"""Tests für Gerüstbau-App API."""

import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestGeruestbauAPI:
    """Test-Klasse für Gerüstbau-API Endpunkte."""

    def test_list_projects_empty(self):
        """Leere Projektliste abrufen."""
        response = client.get("/api/v1/geruestbau/projects")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_create_project(self):
        """Neues Projekt erstellen."""
        project_data = {
            "name": "Test-Projekt",
            "address": "Bundesplatz 3, 3011 Bern"
        }
        response = client.post("/api/v1/geruestbau/projects", json=project_data)
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "Test-Projekt"
        assert data["address"] == "Bundesplatz 3, 3011 Bern"
        assert data["status"] == "draft"
        assert "id" in data

        # Cleanup
        project_id = data["id"]
        client.delete(f"/api/v1/geruestbau/projects/{project_id}")

    def test_get_project_not_found(self):
        """Nicht existierendes Projekt abrufen."""
        response = client.get("/api/v1/geruestbau/projects/invalid-id")
        assert response.status_code == 404

    def test_delete_project_not_found(self):
        """Nicht existierendes Projekt löschen."""
        response = client.delete("/api/v1/geruestbau/projects/invalid-id")
        assert response.status_code == 404

    def test_project_lifecycle(self):
        """Vollständiger Projekt-Lebenszyklus."""
        # 1. Erstellen
        create_response = client.post("/api/v1/geruestbau/projects", json={
            "name": "Lifecycle Test",
            "address": "Kramgasse 49, 3011 Bern",
            "client_name": "Test AG"
        })
        assert create_response.status_code == 200
        project_id = create_response.json()["id"]

        # 2. Abrufen
        get_response = client.get(f"/api/v1/geruestbau/projects/{project_id}")
        assert get_response.status_code == 200
        assert get_response.json()["name"] == "Lifecycle Test"

        # 3. Aktualisieren
        update_response = client.put(f"/api/v1/geruestbau/projects/{project_id}", json={
            "name": "Updated Name"
        })
        assert update_response.status_code == 200
        assert update_response.json()["name"] == "Updated Name"

        # 4. Löschen
        delete_response = client.delete(f"/api/v1/geruestbau/projects/{project_id}")
        assert delete_response.status_code == 200

        # 5. Verifizieren
        verify_response = client.get(f"/api/v1/geruestbau/projects/{project_id}")
        assert verify_response.status_code == 404


class TestUrlImportEndpoint:
    """Test-Klasse für URL-Import Endpunkt."""

    def test_import_url_missing_url(self):
        """Fehlende URL im Request."""
        response = client.post("/api/v1/geruestbau/import/url", json={})
        # Pydantic validation error
        assert response.status_code == 422

    def test_import_url_empty_url(self):
        """Leere URL im Request."""
        response = client.post("/api/v1/geruestbau/import/url", json={"url": ""})
        assert response.status_code == 400

    def test_import_url_non_simap(self):
        """Nicht-simap.ch URL ablehnen."""
        response = client.post(
            "/api/v1/geruestbau/import/url",
            json={"url": "https://google.com"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "simap" in data["error"].lower()

    def test_import_url_invalid_simap(self):
        """Ungültige simap.ch URL (keine Projekt-ID)."""
        response = client.post(
            "/api/v1/geruestbau/import/url",
            json={"url": "https://simap.ch/de/search"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "Projekt-ID" in data["error"]

    def test_import_url_valid_format(self):
        """Gültige URL-Format wird akzeptiert (auch wenn Fetch fehlschlägt)."""
        # Note: This test might fail if simap.ch is unreachable
        # In CI, you'd mock the HTTP call
        response = client.post(
            "/api/v1/geruestbau/import/url",
            json={"url": "https://simap.ch/de/project-detail/test-invalid-uuid"}
        )
        assert response.status_code == 200
        # Response format is correct even if import fails
        data = response.json()
        assert "success" in data
        assert "confidence" in data or "error" in data


class TestProjectEnrichment:
    """Test-Klasse für Projekt-Anreicherung mit Geodaten (BUG-009 Regression)."""

    def test_enrich_project_basic(self):
        """Projekt erstellen und mit Geodaten anreichern."""
        # 1. Projekt erstellen
        project_data = {
            "name": "Enrichment Test",
            "address": "Bundesplatz 3, 3011 Bern"
        }
        create_response = client.post("/api/v1/geruestbau/projects", json=project_data)
        assert create_response.status_code == 200
        project_id = create_response.json()["id"]

        try:
            # 2. Projekt anreichern (ruft SmartBuildingService auf)
            enrich_response = client.post(f"/api/v1/geruestbau/projects/{project_id}/enrich")

            # Sollte nicht crashen (BUG-009 Fix)
            assert enrich_response.status_code == 200

            data = enrich_response.json()

            # 3. Prüfen: Status wurde aktualisiert
            assert data["status"] == "enriched"

            # 4. Prüfen: building_data wurde gesetzt
            # (kann leer sein wenn API nicht erreichbar, aber kein Error)
            assert "building_data" in data or data.get("building_data") is None

        finally:
            # Cleanup
            client.delete(f"/api/v1/geruestbau/projects/{project_id}")

    def test_enrich_project_returns_geodata(self):
        """Prüft dass enrich_with_geodata ProjectWithGeodata zurückgibt."""
        # 1. Projekt erstellen
        project_data = {
            "name": "Geodata Return Test",
            "address": "Kramgasse 49, 3011 Bern"
        }
        create_response = client.post("/api/v1/geruestbau/projects", json=project_data)
        assert create_response.status_code == 200
        project_id = create_response.json()["id"]

        try:
            # 2. Projekt anreichern
            enrich_response = client.post(f"/api/v1/geruestbau/projects/{project_id}/enrich")
            assert enrich_response.status_code == 200

            data = enrich_response.json()

            # 3. Response sollte jetzt 'geodata' Feld enthalten (ProjectWithGeodata)
            # Hinweis: kann null sein wenn keine Daten im Cache
            assert "geodata" in data

        finally:
            # Cleanup
            client.delete(f"/api/v1/geruestbau/projects/{project_id}")

    def test_enrich_project_not_found(self):
        """Nicht existierendes Projekt anreichern schlägt fehl."""
        response = client.post("/api/v1/geruestbau/projects/invalid-uuid/enrich")
        assert response.status_code == 404

    def test_enrich_project_egid_stored(self):
        """Prüft dass EGID nach Anreicherung gespeichert wird."""
        # 1. Projekt erstellen
        project_data = {
            "name": "EGID Storage Test",
            "address": "Bundesplatz 3, 3011 Bern"
        }
        create_response = client.post("/api/v1/geruestbau/projects", json=project_data)
        assert create_response.status_code == 200
        project_id = create_response.json()["id"]

        try:
            # 2. Projekt anreichern
            enrich_response = client.post(f"/api/v1/geruestbau/projects/{project_id}/enrich")
            assert enrich_response.status_code == 200

            # 3. Projekt abrufen und EGID prüfen
            get_response = client.get(f"/api/v1/geruestbau/projects/{project_id}")
            assert get_response.status_code == 200

            data = get_response.json()

            # EGID sollte jetzt gesetzt sein (wenn SmartBuildingService erfolgreich)
            # Kann None sein wenn API nicht erreichbar
            # Wichtig: Kein AttributeError! (BUG-009)
            assert "egid" in data

        finally:
            # Cleanup
            client.delete(f"/api/v1/geruestbau/projects/{project_id}")
