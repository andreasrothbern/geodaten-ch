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
from bs4 import BeautifulSoup

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

        try:
            return await self._import_from_simap(url, project_id)
        except Exception as e:
            logger.exception(f"Fehler beim Import von {url}: {e}")
            return UrlImportResult(
                success=False,
                error=f"Fehler beim Abrufen der Daten: {str(e)}"
            )

    async def _import_from_simap(self, url: str, project_id: str) -> UrlImportResult:
        """Importiert von simap.ch"""
        client = await self._get_client()

        # Fetch the page
        response = await client.get(url)
        response.raise_for_status()

        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')

        # Initialize result
        result = UrlImportResult(source_id=project_id)

        # Extract title
        title_elem = soup.find('h1') or soup.find('h2', class_='project-title')
        if title_elem:
            result.project_name = title_elem.get_text(strip=True)

        # Extract data from definition lists or tables
        # simap.ch uses various HTML structures
        for dt in soup.find_all(['dt', 'th', 'label']):
            label = dt.get_text(strip=True).lower()
            # Find corresponding value
            if dt.name == 'dt':
                dd = dt.find_next_sibling('dd')
                value = dd.get_text(strip=True) if dd else None
            elif dt.name == 'th':
                td = dt.find_next_sibling('td')
                value = td.get_text(strip=True) if td else None
            else:
                # For label, look for next input or span
                next_elem = dt.find_next(['input', 'span', 'p'])
                value = next_elem.get_text(strip=True) if next_elem else None

            if not value:
                continue

            # Map to fields
            if any(k in label for k in ['auftraggeber', 'mandant', 'bauherr', 'adjudicateur']):
                result.client_name = value
            elif any(k in label for k in ['eingabefrist', 'délai', 'frist']):
                result.submission_deadline = self._convert_date(value)
            elif any(k in label for k in ['adresse', 'standort', 'ort', 'lieu']):
                result.address = value
            elif any(k in label for k in ['vergabeverfahren', 'verfahren', 'procédure']):
                result.procedure = self._extract_procedure(value)
            elif any(k in label for k in ['projektnummer', 'projekt-nr', 'numéro']):
                result.tender_number = value
            elif any(k in label for k in ['ausführungsbeginn', 'début']):
                result.project_start = self._convert_date(value)
            elif any(k in label for k in ['ausführungsende', 'fin']):
                result.project_end = self._convert_date(value)

        # Extract description from various possible elements
        desc_elem = soup.find(['article', 'div'], class_=['description', 'content', 'project-description'])
        if desc_elem:
            result.description = desc_elem.get_text(strip=True)[:500]  # Limit length

        # Try to find address in the full text if not found
        if not result.address:
            # Look for Swiss postal code pattern
            address_pattern = re.compile(
                r'([A-Za-zäöüÄÖÜéèà\s-]+\s+\d+[a-z]?\s*,?\s*\d{4}\s+[A-Za-zäöüÄÖÜéèà\s-]+)',
                re.IGNORECASE
            )
            text = soup.get_text()
            match = address_pattern.search(text)
            if match:
                result.address = match.group(1).strip()

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
