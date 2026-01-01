"""
URL-Import Service für Ausschreibungen
======================================

Importiert Ausschreibungsdaten von simap.ch URLs.

Verwendung:
    from app.services.geruestbau.url_importer import UrlImporter

    importer = UrlImporter()
    result = await importer.import_from_url(url)

Stand: 31.12.2025
"""

import re
import logging
from typing import Optional, Dict, Any
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
    """Service für den Import von Ausschreibungen via URL"""

    # simap.ch project-detail URL pattern
    SIMAP_PATTERN = re.compile(
        r'simap\.ch/(?:de|fr|it)/project-detail/([a-f0-9-]+)',
        re.IGNORECASE
    )

    # Date pattern for Swiss format (DD.MM.YYYY)
    DATE_PATTERN = re.compile(r'(\d{1,2})\.(\d{1,2})\.(\d{4})')

    def __init__(self):
        self._client = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Lazy-load HTTP client"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
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

    def _convert_date(self, date_str: str) -> Optional[str]:
        """Konvertiert Schweizer Datum (DD.MM.YYYY) zu ISO (YYYY-MM-DD)"""
        match = self.DATE_PATTERN.search(date_str)
        if match:
            day, month, year = match.groups()
            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        return None

    def _extract_procedure(self, text: str) -> Optional[str]:
        """Erkennt Vergabeverfahren aus Text"""
        text_lower = text.lower()
        if 'offenes verfahren' in text_lower or 'procédure ouverte' in text_lower:
            return 'open'
        elif 'selektives verfahren' in text_lower or 'procédure sélective' in text_lower:
            return 'selective'
        elif 'einladungsverfahren' in text_lower or 'procédure sur invitation' in text_lower:
            return 'invitation'
        elif 'freihändiges verfahren' in text_lower or 'procédure de gré à gré' in text_lower:
            return 'negotiated'
        return None

    async def import_from_url(self, url: str) -> UrlImportResult:
        """
        Importiert Ausschreibungsdaten von einer URL.

        Unterstützte URLs:
        - simap.ch Projekt-Details

        Args:
            url: Die URL zum Importieren

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

        # UUID should be 36 characters (32 hex + 4 hyphens)
        if len(project_id) < 36:
            logger.warning(f"Project ID too short: '{project_id}' (expected 36 chars UUID)")
            return UrlImportResult(
                success=False,
                error=f"Projekt-ID unvollständig ({len(project_id)} Zeichen). Bitte vollständige URL kopieren."
            )

        try:
            return await self._import_from_simap(url, project_id)
        except Exception as e:
            logger.exception(f"Fehler beim Import von {url}: {e}")
            return UrlImportResult(
                success=False,
                error=f"Fehler beim Abrufen der Daten: {str(e)}"
            )

    async def _import_from_simap(self, url: str, project_id: str) -> UrlImportResult:
        """Importiert von simap.ch via offizielle API"""
        client = await self._get_client()

        # Use official simap.ch API instead of HTML scraping
        api_url = f"https://www.simap.ch/api/publications/v2/project/{project_id}/project-header"

        logger.info(f"Fetching simap.ch API: {api_url}")

        try:
            response = await client.get(
                api_url,
                headers={
                    'Accept': 'application/json',
                    'Accept-Language': 'de',
                }
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.warning(f"simap.ch API returned HTTP {e.response.status_code} for project {project_id}")
            return UrlImportResult(
                success=False,
                error=f"simap.ch API Fehler (HTTP {e.response.status_code}). Projekt-ID: {project_id}"
            )
        except httpx.RequestError as e:
            logger.warning(f"simap.ch API request failed: {e}")
            return UrlImportResult(
                success=False,
                error="simap.ch API ist nicht erreichbar."
            )

        # Parse JSON response
        try:
            data = response.json()
            logger.debug(f"simap.ch API response: {data}")
        except Exception as e:
            logger.error(f"Failed to parse simap.ch API response: {e}")
            return UrlImportResult(
                success=False,
                error="Ungültige Antwort von simap.ch API"
            )

        # Initialize result
        result = UrlImportResult(source_id=project_id)

        # Extract data from API response
        # The structure has nested multilingual fields

        # Helper to get first non-null language value
        def get_multilingual(obj: dict) -> Optional[str]:
            if not isinstance(obj, dict):
                return str(obj) if obj else None
            # Prefer German, then French, Italian, English
            for lang in ['de', 'fr', 'it', 'en']:
                if obj.get(lang):
                    return obj[lang]
            return None

        # Project title is in latestPublication.title (multilingual)
        latest_pub = data.get('latestPublication') or {}
        title_obj = latest_pub.get('title') or data.get('title') or {}
        result.project_name = (
            get_multilingual(title_obj) or
            data.get('projectTitle') or
            data.get('publicationTitle') or
            data.get('name')
        )

        # Client/Auftraggeber
        procuring_entity = data.get('procuringEntity') or data.get('client') or {}
        if isinstance(procuring_entity, dict):
            result.client_name = procuring_entity.get('name') or procuring_entity.get('organizationName')
        elif isinstance(procuring_entity, str):
            result.client_name = procuring_entity

        # Address - try various fields
        location = data.get('location') or data.get('address') or data.get('deliveryLocation') or {}
        if isinstance(location, dict):
            parts = []
            if location.get('street'):
                parts.append(location['street'])
            if location.get('houseNumber'):
                parts[-1] = f"{parts[-1]} {location['houseNumber']}" if parts else location['houseNumber']
            if location.get('postalCode') or location.get('city'):
                parts.append(f"{location.get('postalCode', '')} {location.get('city', '')}".strip())
            result.address = ', '.join(parts) if parts else None
        elif isinstance(location, str):
            result.address = location

        # If no structured address, look for text fields
        if not result.address:
            result.address = data.get('deliveryAddress') or data.get('locationDescription')

        # Deadline - check latestPublication.dates first
        pub_dates = latest_pub.get('dates') or {}
        deadline = (
            pub_dates.get('offerDeadline') or
            data.get('submissionDeadline') or
            data.get('deadline') or
            data.get('tenderDeadline')
        )
        if deadline:
            # API might return ISO format or Swiss format
            if isinstance(deadline, str):
                if 'T' in deadline:  # ISO format (2026-01-26T16:30:00+01:00)
                    result.submission_deadline = deadline.split('T')[0]
                else:
                    result.submission_deadline = self._convert_date(deadline)

        # Procedure type - processType is at root level
        procedure = data.get('processType') or data.get('procedureType') or data.get('procedure')
        if procedure:
            # Map API values to our internal values
            procedure_map = {
                'open': 'open',
                'selective': 'selective',
                'invitation': 'invitation',
                'negotiated': 'negotiated',
            }
            result.procedure = procedure_map.get(procedure.lower()) or self._extract_procedure(str(procedure))

        # Description
        result.description = (
            data.get('description') or
            data.get('shortDescription') or
            data.get('summary')
        )
        if result.description and len(result.description) > 500:
            result.description = result.description[:500] + '...'

        # Tender number - projectNumber is at root level
        result.tender_number = (
            data.get('projectNumber') or
            data.get('referenceNumber') or
            latest_pub.get('publicationNumber')
        )

        # Project dates
        execution = data.get('executionPeriod') or {}
        if isinstance(execution, dict):
            if execution.get('startDate'):
                result.project_start = execution['startDate'].split('T')[0] if 'T' in execution['startDate'] else self._convert_date(execution['startDate'])
            if execution.get('endDate'):
                result.project_end = execution['endDate'].split('T')[0] if 'T' in execution['endDate'] else self._convert_date(execution['endDate'])

        # Calculate confidence
        confidence_score = 0.0
        if result.project_name:
            confidence_score += 0.3
        if result.address:
            confidence_score += 0.3
        if result.client_name:
            confidence_score += 0.2
        if result.submission_deadline:
            confidence_score += 0.1
        if result.procedure:
            confidence_score += 0.1

        result.confidence = min(confidence_score, 1.0)
        result.success = result.project_name is not None

        if not result.success:
            logger.warning(f"No project_name found in simap.ch API response for {project_id}")
            result.error = "Projektdaten konnten nicht aus simap.ch extrahiert werden."

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
