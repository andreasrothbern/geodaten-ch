"""Tests für Gerüstbau-App API."""

import pytest
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
