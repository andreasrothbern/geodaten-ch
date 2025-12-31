"""Tests für URL-Importer Service."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.geruestbau.url_importer import (
    UrlImporter,
    UrlImportResult,
    get_url_importer,
)


class TestUrlImporter:
    """Test-Klasse für UrlImporter Service."""

    def setup_method(self):
        """Setup für jeden Test."""
        self.importer = UrlImporter()

    def test_is_simap_url_valid(self):
        """Gültige simap.ch URLs erkennen."""
        valid_urls = [
            "https://simap.ch/de/project-detail/abc123",
            "https://www.simap.ch/de/project-detail/abc123",
            "http://simap.ch/fr/project-detail/abc123",
            "https://SIMAP.CH/de/project-detail/abc123",
        ]
        for url in valid_urls:
            assert self.importer._is_simap_url(url), f"Should recognize {url}"

    def test_is_simap_url_invalid(self):
        """Ungültige URLs erkennen."""
        invalid_urls = [
            "https://google.com",
            "https://example.ch/project",
            "not-a-url",
            "",
        ]
        for url in invalid_urls:
            assert not self.importer._is_simap_url(url), f"Should reject {url}"

    def test_extract_project_id_valid(self):
        """Projekt-ID aus URL extrahieren."""
        test_cases = [
            (
                "https://simap.ch/de/project-detail/7bcbe557-5b96-4b74-8fa6-9067363aa4ca",
                "7bcbe557-5b96-4b74-8fa6-9067363aa4ca"
            ),
            (
                "https://www.simap.ch/fr/project-detail/abc12345-def6-7890-ghij-klmnopqrstuv",
                "abc12345-def6-7890-ghij-klmnopqrstuv"
            ),
        ]
        for url, expected_id in test_cases:
            result = self.importer._extract_project_id(url)
            assert result == expected_id, f"Expected {expected_id} from {url}"

    def test_extract_project_id_invalid(self):
        """Ungültige URLs ohne Projekt-ID."""
        invalid_urls = [
            "https://simap.ch/de/search",
            "https://simap.ch",
            "https://google.com/project-detail/123",
        ]
        for url in invalid_urls:
            result = self.importer._extract_project_id(url)
            assert result is None, f"Should return None for {url}"

    def test_convert_date_swiss_format(self):
        """Schweizer Datum zu ISO konvertieren."""
        test_cases = [
            ("15.03.2025", "2025-03-15"),
            ("1.1.2025", "2025-01-01"),
            ("31.12.2024", "2024-12-31"),
            ("Frist: 15.03.2025", "2025-03-15"),  # Date in text
        ]
        for input_date, expected in test_cases:
            result = self.importer._convert_date(input_date)
            assert result == expected, f"Expected {expected} from {input_date}"

    def test_convert_date_invalid(self):
        """Ungültige Daten."""
        invalid_dates = [
            "2025-03-15",  # Already ISO
            "March 15, 2025",  # English format
            "no date here",
            "",
        ]
        for date_str in invalid_dates:
            result = self.importer._convert_date(date_str)
            assert result is None, f"Should return None for {date_str}"

    def test_extract_procedure(self):
        """Vergabeverfahren erkennen."""
        test_cases = [
            ("Offenes Verfahren", "open"),
            ("offenes verfahren gemäss...", "open"),
            ("Procédure ouverte", "open"),
            ("Selektives Verfahren", "selective"),
            ("Einladungsverfahren", "invitation"),
            ("Freihändiges Verfahren", "negotiated"),
            ("Procédure de gré à gré", "negotiated"),
        ]
        for text, expected in test_cases:
            result = self.importer._extract_procedure(text)
            assert result == expected, f"Expected {expected} from '{text}'"

    def test_extract_procedure_unknown(self):
        """Unbekanntes Verfahren."""
        result = self.importer._extract_procedure("Sonstiges Verfahren")
        assert result is None

    @pytest.mark.asyncio
    async def test_import_non_simap_url(self):
        """Nicht-simap.ch URL ablehnen."""
        result = await self.importer.import_from_url("https://google.com")
        assert result.success is False
        assert "simap.ch" in result.error.lower()

    @pytest.mark.asyncio
    async def test_import_invalid_simap_url(self):
        """Ungültige simap.ch URL (keine Projekt-ID)."""
        result = await self.importer.import_from_url("https://simap.ch/de/search")
        assert result.success is False
        assert "Projekt-ID" in result.error

    @pytest.mark.asyncio
    async def test_import_from_simap_success(self):
        """Erfolgreicher Import von simap.ch (gemockt)."""
        # Mock HTML response
        mock_html = """
        <html>
        <body>
            <h1>Gerüstarbeiten Schulhaus</h1>
            <dl>
                <dt>Auftraggeber</dt>
                <dd>Stadt Bern</dd>
                <dt>Eingabefrist</dt>
                <dd>15.03.2025</dd>
                <dt>Adresse</dt>
                <dd>Länggassstrasse 40, 3012 Bern</dd>
                <dt>Vergabeverfahren</dt>
                <dd>Offenes Verfahren</dd>
            </dl>
        </body>
        </html>
        """

        mock_response = MagicMock()
        mock_response.text = mock_html
        mock_response.raise_for_status = MagicMock()

        with patch.object(self.importer, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            result = await self.importer.import_from_url(
                "https://simap.ch/de/project-detail/test-123-uuid"
            )

            assert result.success is True
            assert result.project_name == "Gerüstarbeiten Schulhaus"
            assert result.client_name == "Stadt Bern"
            assert result.submission_deadline == "2025-03-15"
            assert result.address == "Länggassstrasse 40, 3012 Bern"
            assert result.procedure == "open"
            assert result.source_id == "test-123-uuid"
            assert result.confidence > 0.5


class TestUrlImportResult:
    """Tests für UrlImportResult Dataclass."""

    def test_to_dict_success(self):
        """Erfolgreiche Response serialisieren."""
        result = UrlImportResult(
            success=True,
            confidence=0.85,
            source_id="abc123",
            project_name="Test Projekt",
            address="Teststrasse 1, 3000 Bern",
        )
        data = result.to_dict()

        assert data["success"] is True
        assert data["confidence"] == 0.85
        assert data["source_id"] == "abc123"
        assert data["data"]["project_name"] == "Test Projekt"
        assert data["data"]["address"] == "Teststrasse 1, 3000 Bern"

    def test_to_dict_failure(self):
        """Fehler-Response serialisieren."""
        result = UrlImportResult(
            success=False,
            error="Test error message"
        )
        data = result.to_dict()

        assert data["success"] is False
        assert data["error"] == "Test error message"
        assert data["data"] is None


class TestGetUrlImporter:
    """Tests für Singleton-Factory."""

    def test_get_url_importer_singleton(self):
        """Singleton-Instanz zurückgeben."""
        importer1 = get_url_importer()
        importer2 = get_url_importer()
        assert importer1 is importer2
