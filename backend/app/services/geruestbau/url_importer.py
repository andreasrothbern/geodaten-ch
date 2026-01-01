"""
URL-Import Service für Ausschreibungen
======================================

Importiert Ausschreibungsdaten von simap.ch URLs via REST API.

simap.ch ist eine JavaScript SPA - HTML-Scraping funktioniert nicht.
Stattdessen nutzen wir die offizielle REST API.

API-Endpunkt:
    GET https://www.simap.ch/api/publications/v2/project/{projectId}/project-header

Verwendung:
    from app.services.geruestbau.url_importer import UrlImporter

    importer = UrlImporter()
    result = await importer.import_from_url(url)

Stand: 01.01.2026
"""

import re
import logging
from typing import Optional, Dict, Any, Union
from dataclasses import dataclass
import httpx

logger = logging.getLogger(__name__)


@dataclass
class UrlImportResult:
    """Ergebnis des URL-Imports"""
    success: bool = False
    confidence: float = 0.0
    error: Optional[str] = None
    source_id: Optional[str] = None

    # Extrahierte Daten
    project_name: Optional[str] = None
    address: Optional[str] = None
    client_name: Optional[str] = None
    client_contact: Optional[str] = None
    description: Optional[str] = None
    tender_number: Optional[str] = None
    submission_deadline: Optional[str] = None  # ISO format YYYY-MM-DD
    project_start: Optional[str] = None
    project_end: Optional[str] = None
    procedure: Optional[str] = None  # open, selective, invitation, negotiated

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu API-Response-Format"""
        return {
            "success": self.success,
            "confidence": self.confidence,
            "error": self.error,
            "source_id": self.source_id,
            "data": {
                "project_name": self.project_name,
                "address": self.address,
                "client_name": self.client_name,
                "client_contact": self.client_contact,
                "description": self.description,
                "tender_number": self.tender_number,
                "submission_deadline": self.submission_deadline,
                "project_start": self.project_start,
                "project_end": self.project_end,
                "procedure": self.procedure,
            } if self.success else None
        }


class UrlImporter:
    """
    Service für den Import von Ausschreibungen via URL.

    WICHTIG: simap.ch ist eine JavaScript SPA. HTML-Scraping funktioniert NICHT.
    Wir nutzen die offizielle simap.ch REST API.
    """

    # simap.ch project-detail URL pattern
    SIMAP_PATTERN = re.compile(
        r'simap\.ch/(?:de|fr|it)/project-detail/([a-f0-9-]+)',
        re.IGNORECASE
    )

    def __init__(self):
        self._client = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Lazy-load HTTP client"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'application/json',
                    'Accept-Language': 'de,fr,it,en',
                }
            )
        return self._client

    def _is_simap_url(self, url: str) -> bool:
        """Prüft ob URL von simap.ch ist"""
        return 'simap.ch' in url.lower()

    def _extract_project_id(self, url: str) -> Optional[str]:
        """Extrahiert Projekt-ID aus simap.ch URL"""
        match = self.SIMAP_PATTERN.search(url)
        return match.group(1) if match else None

    async def import_from_url(self, url: str) -> UrlImportResult:
        """
        Importiert Ausschreibungsdaten von einer simap.ch URL.

        Nutzt die offizielle simap.ch REST API.

        Args:
            url: Die simap.ch URL (z.B. https://www.simap.ch/de/project-detail/uuid)

        Returns:
            UrlImportResult mit extrahierten Daten
        """
        if not self._is_simap_url(url):
            return UrlImportResult(
                success=False,
                error="Nur simap.ch URLs werden unterstützt"
            )

        project_id = self._extract_project_id(url)
        if not project_id:
            return UrlImportResult(
                success=False,
                error="Ungültige simap.ch URL - keine Projekt-ID gefunden"
            )

        # Validate UUID length (36 chars: 32 hex + 4 hyphens)
        if len(project_id) < 36:
            return UrlImportResult(
                success=False,
                error=f"Projekt-ID unvollständig ({len(project_id)} Zeichen). Bitte vollständige URL kopieren."
            )

        try:
            return await self._import_from_simap_api(project_id)
        except Exception as e:
            logger.exception(f"Fehler beim Import von {url}: {e}")
            return UrlImportResult(
                success=False,
                error=f"Fehler beim Abrufen der Daten: {str(e)}"
            )

    def _get_multilingual_value(self, obj: Any) -> Optional[str]:
        """
        Extrahiert ersten nicht-leeren Wert aus mehrsprachigem Objekt.

        simap.ch API liefert Felder als {de: "...", fr: "...", it: "...", en: "..."}
        Wir bevorzugen: de > fr > it > en
        """
        if obj is None:
            return None
        if isinstance(obj, str):
            return obj if obj else None
        if isinstance(obj, dict):
            for lang in ['de', 'fr', 'it', 'en']:
                value = obj.get(lang)
                if value:
                    return value
        return None

    async def _import_from_simap_api(self, project_id: str) -> UrlImportResult:
        """
        Importiert von simap.ch via offizielle REST API.

        API-Endpunkt: GET /api/publications/v2/project/{id}/project-header
        """
        client = await self._get_client()
        api_url = f"https://www.simap.ch/api/publications/v2/project/{project_id}/project-header"

        logger.info(f"Fetching simap.ch API: {api_url}")

        try:
            response = await client.get(api_url)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.warning(f"simap.ch API returned HTTP {e.response.status_code}")
            return UrlImportResult(
                success=False,
                error=f"simap.ch API Fehler (HTTP {e.response.status_code})"
            )
        except httpx.RequestError as e:
            logger.warning(f"simap.ch API request failed: {e}")
            return UrlImportResult(
                success=False,
                error="simap.ch API nicht erreichbar"
            )

        # Parse JSON
        try:
            data = response.json()
            logger.debug(f"simap.ch API response keys: {data.keys()}")
        except Exception as e:
            logger.error(f"Failed to parse simap.ch response: {e}")
            return UrlImportResult(
                success=False,
                error="Ungültige Antwort von simap.ch"
            )

        # Initialize result
        result = UrlImportResult(source_id=project_id)

        # Extract from latestPublication (nested structure)
        latest_pub = data.get('latestPublication') or {}
        pub_dates = latest_pub.get('dates') or {}

        # Project title - in latestPublication.title (multilingual)
        title_obj = latest_pub.get('title') or {}
        result.project_name = self._get_multilingual_value(title_obj)

        # Tender/Project number
        result.tender_number = (
            data.get('projectNumber') or
            latest_pub.get('publicationNumber')
        )

        # Submission deadline
        deadline = pub_dates.get('offerDeadline')
        if deadline and isinstance(deadline, str):
            # Format: "2026-01-26T16:30:00+01:00" -> "2026-01-26"
            result.submission_deadline = deadline.split('T')[0] if 'T' in deadline else deadline

        # Procedure type
        process_type = data.get('processType')
        if process_type:
            procedure_map = {
                'open': 'open',
                'selective': 'selective',
                'invitation': 'invitation',
                'negotiated': 'negotiated',
            }
            result.procedure = procedure_map.get(process_type.lower(), process_type)

        # Note: simap.ch API does NOT provide address or client details
        # These must be entered manually or extracted from downloaded PDF

        # Calculate confidence based on available data
        confidence = 0.0
        if result.project_name:
            confidence += 0.4
        if result.tender_number:
            confidence += 0.2
        if result.submission_deadline:
            confidence += 0.2
        if result.procedure:
            confidence += 0.2

        result.confidence = min(confidence, 1.0)
        result.success = result.project_name is not None

        if not result.success:
            result.error = "Keine Projektdaten in simap.ch API gefunden"

        return result

    async def close(self):
        """Schliesst den HTTP-Client"""
        if self._client:
            await self._client.aclose()
            self._client = None


# Singleton instance
_importer_instance = None


def get_url_importer() -> UrlImporter:
    """Gibt Singleton-Instanz des UrlImporters zurück"""
    global _importer_instance
    if _importer_instance is None:
        _importer_instance = UrlImporter()
    return _importer_instance
