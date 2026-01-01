"""
Universal URL-Importer für Gerüstbau-Ausschreibungen.

Unterstützte Quellen:
- simap.ch (offizielle Schweizer Ausschreibungen)
- tender24.ch
- baublatt.ch
- Gemeinde-Websites
- Beliebige URLs (generische Extraktion)

WICHTIG: simap.ch nutzt JavaScript, aber wir können dennoch Daten extrahieren:
1. Versuche zuerst die simap.ch API v1
2. Falls API fehlschlägt, parse das HTML mit BeautifulSoup

Stand: 01.01.2026
"""

import httpx
import re
import logging
from bs4 import BeautifulSoup
from dataclasses import dataclass, field
from typing import Optional, List, Tuple, Dict, Any
from enum import Enum
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class SourceType(Enum):
    """Erkannte Quellen-Typen."""
    SIMAP = "simap"
    TENDER24 = "tender24"
    BAUBLATT = "baublatt"
    INTELLITENDER = "intellitender"
    GEMEINDE = "gemeinde"
    UNKNOWN = "unknown"


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

    # Zusätzliche Felder
    location_city: Optional[str] = None
    location_canton: Optional[str] = None
    location_plz: Optional[str] = None
    cpv_codes: List[str] = field(default_factory=list)
    is_awarded: bool = False
    awarded_to: Optional[str] = None
    extraction_notes: List[str] = field(default_factory=list)

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
                "location_city": self.location_city,
                "location_canton": self.location_canton,
                "location_plz": self.location_plz,
                "cpv_codes": self.cpv_codes,
                "is_awarded": self.is_awarded,
                "awarded_to": self.awarded_to,
                "extraction_notes": self.extraction_notes,
            } if self.success else None
        }


class UrlImporter:
    """
    Universal URL-Importer für Ausschreibungen.

    Strategie für simap.ch:
    1. Versuche API v1 (liefert strukturierte JSON-Daten)
    2. Falls API fehlschlägt: Web-Scraping mit BeautifulSoup
       - Methode 1: <dt>/<dd> Paare
       - Methode 2: Tabellen-Zeilen
       - Methode 3: Label/Value Divs
    """

    # URL-Pattern für Quellen-Erkennung
    SOURCE_PATTERNS = {
        SourceType.SIMAP: [
            r'simap\.ch/(?:de|fr|it)/project-detail/([a-f0-9-]+)',
            r'simap\.ch/.*projectId=([a-f0-9-]+)',
            r'simap\.ch/(?:de|fr|it)/publication-detail/([a-f0-9-]+)',
        ],
        SourceType.TENDER24: [
            r'tender24\.ch/.*?/(\d+)',
            r'tender24\.ch/.*ausschreibung.*?(\d+)',
        ],
        SourceType.BAUBLATT: [
            r'baublatt\.ch/ausschreibungen?/(\d+)',
            r'baublatt\.ch/.*?/(\d+)',
        ],
        SourceType.INTELLITENDER: [
            r'intellitender\.ch/.*?id=(\d+)',
        ],
    }

    # Schweizer Kantone
    CANTONS = [
        'AG', 'AI', 'AR', 'BE', 'BL', 'BS', 'FR', 'GE', 'GL', 'GR',
        'JU', 'LU', 'NE', 'NW', 'OW', 'SG', 'SH', 'SO', 'SZ', 'TG',
        'TI', 'UR', 'VD', 'VS', 'ZG', 'ZH'
    ]

    def __init__(self):
        self._client = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Lazy-load HTTP client"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "de-CH,de;q=0.9,en;q=0.8",
                },
                follow_redirects=True
            )
        return self._client

    def detect_source(self, url: str) -> Tuple[SourceType, Optional[str]]:
        """Erkennt die Quelle und extrahiert die ID."""
        for source, patterns in self.SOURCE_PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, url, re.IGNORECASE)
                if match:
                    return source, match.group(1)

        # Fallback: Schweizer Domain?
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        if '.ch' in domain or '.swiss' in domain:
            for canton in self.CANTONS:
                if canton.lower() in domain:
                    return SourceType.GEMEINDE, None
            return SourceType.GEMEINDE, None

        return SourceType.UNKNOWN, None

    async def import_from_url(self, url: str) -> UrlImportResult:
        """
        Hauptmethode: Importiert Projektdaten aus URL.

        Args:
            url: Die zu parsende URL

        Returns:
            UrlImportResult mit allen gefundenen Daten
        """
        url = url.strip()
        source, source_id = self.detect_source(url)

        logger.info(f"Importing from {source.value}: {url}")

        try:
            if source == SourceType.SIMAP:
                return await self._import_simap(url, source_id)
            elif source == SourceType.TENDER24:
                return await self._import_tender24(url, source_id)
            elif source == SourceType.BAUBLATT:
                return await self._import_baublatt(url, source_id)
            else:
                return await self._import_generic(url, source)
        except Exception as e:
            logger.exception(f"Import failed for {url}: {e}")
            return UrlImportResult(
                success=False,
                source_id=source_id,
                error=f"Import fehlgeschlagen: {str(e)}",
                extraction_notes=[f"Fehler: {str(e)}"]
            )

    async def _import_simap(self, url: str, project_id: Optional[str]) -> UrlImportResult:
        """Importiert von simap.ch - versucht API, dann Web-Scraping."""

        if not project_id:
            return UrlImportResult(
                success=False,
                error="Keine Projekt-ID in URL gefunden"
            )

        # Validate UUID length (36 chars: 32 hex + 4 hyphens)
        if len(project_id) < 36:
            return UrlImportResult(
                success=False,
                error=f"Projekt-ID unvollständig ({len(project_id)} Zeichen). Bitte vollständige URL kopieren."
            )

        # Versuche zuerst die API
        api_result = await self._try_simap_api(project_id)
        if api_result and api_result.success:
            return api_result

        # Fallback: Web-Scraping
        logger.info(f"API failed, trying web scraping for {project_id}")
        return await self._scrape_simap(url, project_id)

    async def _try_simap_api(self, project_id: str) -> Optional[UrlImportResult]:
        """
        Versucht Daten über die simap.ch API v1 zu laden.
        """
        client = await self._get_client()
        api_url = f"https://www.simap.ch/api/publications/v1/projects/{project_id}"

        try:
            response = await client.get(
                api_url,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "GeruestbauApp/1.0 (https://geodaten-ch.railway.app)"
                }
            )

            if response.status_code != 200:
                logger.debug(f"simap.ch API v1 returned {response.status_code}")
                return None

            data = response.json()

            result = UrlImportResult(source_id=project_id)

            # Titel
            result.project_name = data.get('title', 'Unbekanntes Projekt')

            # Beschreibung
            result.description = data.get('description') or data.get('shortDescription')

            # Auftraggeber
            procuring = data.get('procuringEntity', {})
            result.client_name = procuring.get('name')
            result.client_contact = procuring.get('contactPoint', {}).get('name')

            # Termine
            result.submission_deadline = data.get('submissionDeadline')
            # project_start/end nicht direkt in API v1

            # Ausführungsort/Adresse
            locations = data.get('executionLocations', [])
            if locations:
                loc = locations[0]
                parts = []
                if loc.get('street'):
                    parts.append(loc['street'])
                if loc.get('zipCode') and loc.get('city'):
                    parts.append(f"{loc['zipCode']} {loc['city']}")
                result.address = ", ".join(parts) if parts else None
                result.location_city = loc.get('city')
                result.location_plz = loc.get('zipCode')
                result.location_canton = loc.get('canton')

            # Verfahren
            result.procedure = data.get('procedureType')
            result.tender_number = data.get('projectNumber')

            # CPV-Codes
            cpv_list = data.get('cpvCodes', [])
            result.cpv_codes = [c.get('code', '') for c in cpv_list if c.get('code')]

            # Zuschlag
            award = data.get('award', {})
            if award:
                result.is_awarded = True
                result.awarded_to = award.get('awardedTo', {}).get('name')

            result.extraction_notes.append("Loaded via simap.ch API v1")

            # Confidence berechnen
            confidence = 0.0
            if result.project_name:
                confidence += 0.3
            if result.address:
                confidence += 0.3
            if result.client_name:
                confidence += 0.2
            if result.submission_deadline:
                confidence += 0.1
            if result.procedure:
                confidence += 0.1

            result.confidence = min(confidence, 1.0)
            result.success = result.project_name is not None

            return result

        except Exception as e:
            logger.debug(f"simap.ch API v1 failed: {e}")
            return None

    async def _scrape_simap(self, url: str, project_id: str) -> UrlImportResult:
        """
        Scrapet simap.ch Seite mit BeautifulSoup.

        Verwendet 3 Parsing-Strategien:
        1. <dt>/<dd> Paare
        2. Tabellen-Zeilen
        3. Label/Value Divs
        """
        client = await self._get_client()

        try:
            response = await client.get(url)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                return UrlImportResult(
                    success=False,
                    source_id=project_id,
                    error="simap.ch blockiert automatisierte Zugriffe. Bitte Seite im Browser öffnen.",
                    extraction_notes=["HTTP 403 Forbidden"]
                )
            raise
        except Exception as e:
            return UrlImportResult(
                success=False,
                source_id=project_id,
                error=f"Fehler beim Abrufen: {str(e)}"
            )

        # Cookie-Check Redirect?
        if 'cookie-check' in str(response.url).lower():
            return UrlImportResult(
                success=False,
                source_id=project_id,
                error="simap.ch erfordert Cookie-Akzeptanz. Bitte Seite im Browser öffnen."
            )

        soup = BeautifulSoup(response.text, 'html.parser')

        # Titel extrahieren
        title = self._extract_text(soup, 'h1')
        if not title:
            title = self._extract_text(soup, '.project-title')
        if not title:
            title = self._extract_text(soup, 'title')
            if title:
                title = title.replace(' - simap.ch', '').strip()

        result = UrlImportResult(
            source_id=project_id,
            project_name=title or "Unbekanntes Projekt"
        )

        # Details parsen mit 3 Methoden
        details = self._parse_simap_details(soup)

        # Mapping zu Result-Feldern
        result.description = details.get('beschreibung') or details.get('gegenstand')
        result.client_name = details.get('auftraggeber') or details.get('beschaffungsstelle')
        result.submission_deadline = details.get('eingabefrist') or details.get('eingabetermin')
        result.procedure = details.get('verfahrensart')
        result.tender_number = details.get('projekt_nr') or details.get('projektnummer')

        # Ort/Adresse extrahieren
        result.location_city = details.get('ort') or details.get('realisierungsort')
        result.location_canton = details.get('kanton')
        result.address = self._extract_address_from_simap(soup, details)

        # PLZ aus Adresse extrahieren
        if result.address:
            plz_match = re.search(r'\b(\d{4})\b', result.address)
            if plz_match:
                result.location_plz = plz_match.group(1)

        # CPV-Codes
        result.cpv_codes = details.get('cpv_codes', [])

        # Zuschlag-Info
        if details.get('zuschlag') or details.get('zuschlagsempfänger'):
            result.is_awarded = True
            result.awarded_to = details.get('zuschlag') or details.get('zuschlagsempfänger')

        # Ausführungszeit
        result.project_start = details.get('ausführung_von') or details.get('beginn')
        result.project_end = details.get('ausführung_bis') or details.get('ende')

        result.extraction_notes.append(f"Parsed {len(details)} fields via web scraping")

        # Confidence berechnen
        confidence = 0.0
        if result.project_name and result.project_name != "Unbekanntes Projekt":
            confidence += 0.25
        if result.address:
            confidence += 0.25
        if result.client_name:
            confidence += 0.2
        if result.submission_deadline:
            confidence += 0.15
        if result.procedure:
            confidence += 0.15

        result.confidence = min(confidence, 1.0)
        result.success = bool(result.project_name and result.project_name != "Unbekanntes Projekt")

        if not result.success:
            result.error = "Keine Projektdaten gefunden. Möglicherweise JavaScript-Seite."

        return result

    def _parse_simap_details(self, soup: BeautifulSoup) -> dict:
        """
        Parst die Detailtabelle von simap.ch mit 3 Strategien.
        """
        details = {}

        # Methode 1: <dt>/<dd> Paare
        for dt in soup.find_all('dt'):
            dd = dt.find_next_sibling('dd')
            if dd:
                key = self._normalize_key(dt.get_text(strip=True))
                value = dd.get_text(' ', strip=True)
                if key and value:
                    details[key] = value

        # Methode 2: Tabellen-Zeilen
        for row in soup.find_all('tr'):
            cells = row.find_all(['th', 'td'])
            if len(cells) >= 2:
                key = self._normalize_key(cells[0].get_text(strip=True))
                value = cells[1].get_text(' ', strip=True)
                if key and value and key not in details:
                    details[key] = value

        # Methode 3: Label/Value divs (simap.ch neues Design)
        for label_div in soup.find_all(class_=re.compile(r'label|field-label', re.I)):
            value_div = label_div.find_next_sibling()
            if value_div:
                key = self._normalize_key(label_div.get_text(strip=True))
                value = value_div.get_text(' ', strip=True)
                if key and value and key not in details:
                    details[key] = value

        # CPV-Codes extrahieren
        cpv_pattern = r'\b(\d{8})-?(\d)?\b'
        text = soup.get_text()
        cpv_matches = re.findall(cpv_pattern, text)
        details['cpv_codes'] = list(set(f"{m[0]}-{m[1]}" if m[1] else m[0] for m in cpv_matches))

        return details

    def _normalize_key(self, key: str) -> str:
        """Normalisiert Feldnamen für einheitliches Mapping."""
        if not key:
            return ""

        key = key.lower().strip()
        key = key.rstrip(':')
        key = re.sub(r'\s+', '_', key)
        key = re.sub(r'[^a-z0-9_äöüéèà]', '', key)

        # Mapping zu Standard-Keys
        mappings = {
            'auftraggeber': ['auftraggeber', 'beschaffungsstelle', 'vergabestelle'],
            'beschreibung': ['beschreibung', 'gegenstand', 'leistung', 'kurzbeschreibung'],
            'verfahrensart': ['verfahrensart', 'verfahren'],
            'auftragsart': ['auftragsart', 'art_des_auftrags'],
            'eingabefrist': ['eingabefrist', 'eingabetermin', 'frist', 'abgabetermin'],
            'ort': ['ausführungsort', 'erfüllungsort', 'realisierungsort', 'ort', 'standort'],
            'kanton': ['kanton'],
            'zuschlag': ['zuschlag', 'zuschlagsempfänger', 'zuschlag_an'],
            'zuschlagspreis': ['zuschlagspreis', 'preis', 'auftragswert'],
            'begründung': ['begründung', 'zuschlagsgrund'],
        }

        for normalized, variants in mappings.items():
            for variant in variants:
                if variant in key:
                    return normalized

        return key

    def _extract_address_from_simap(self, soup: BeautifulSoup, details: dict) -> Optional[str]:
        """
        Extrahiert vollständige Schweizer Adresse aus simap.ch Seite.

        Sucht nach Mustern wie:
        - Strasse Nr, PLZ Ort
        - PLZ Ort
        """
        # Versuche strukturierte Daten
        ort = details.get('ort', '')

        # Suche im gesamten Text nach Adress-Mustern
        text = soup.get_text()

        # Pattern: Strasse Nr, PLZ Ort
        full_address_pattern = r'([A-ZÄÖÜa-zäöü][a-zäöü]+(?:strasse|weg|platz|gasse|allee|rain|matte|ring|ufer)\s+\d+[a-z]?)\s*,?\s*(\d{4})\s+([A-ZÄÖÜa-zäöüéèà][a-zäöüéèà]+(?:\s+[A-ZÄÖÜa-zäöüéèà][a-zäöüéèà]+)?)'
        match = re.search(full_address_pattern, text, re.IGNORECASE)

        if match:
            street, plz, city = match.groups()
            return f"{street}, {plz} {city}"

        # Fallback: PLZ + Ort
        plz_ort_pattern = r'\b(\d{4})\s+([A-ZÄÖÜ][a-zäöüéèà]+(?:\s+[A-ZÄÖÜ][a-zäöüéèà]+)?)\b'
        plz_match = re.search(plz_ort_pattern, text)

        if plz_match:
            return f"{plz_match.group(1)} {plz_match.group(2)}"

        # Letzter Fallback: Nur Ort aus Details
        if ort:
            plz_in_ort = re.search(r'(\d{4})', ort)
            if plz_in_ort:
                return ort
            return ort

        return None

    def _extract_swiss_address(self, text: str) -> Optional[str]:
        """Extrahiert Schweizer Adresse aus beliebigem Text."""
        text = ' '.join(text.split())

        # Pattern 1: Vollständige Adresse (Strasse Nr, PLZ Ort)
        full_pattern = r'([A-ZÄÖÜa-zäöü][a-zäöü]+(?:strasse|weg|platz|gasse|allee|rain|matte|ring|ufer)\s+\d+[a-z]?)\s*,?\s*(\d{4})\s+([A-ZÄÖÜa-zäöüéèà][a-zäöüéèà]+(?:\s+[a-zäöüéèà]+)?)'
        match = re.search(full_pattern, text, re.IGNORECASE)

        if match:
            street, plz, city = match.groups()
            return f"{street}, {plz} {city}"

        # Pattern 2: PLZ + Ort (ohne Strasse)
        plz_pattern = r'\b(\d{4})\s+([A-ZÄÖÜ][a-zäöüéèà]+(?:\s+[A-Za-zäöüéèà]+)?)\b'
        plz_match = re.search(plz_pattern, text)

        if plz_match:
            plz, city = plz_match.groups()
            # Validiere PLZ (Schweiz: 1000-9999)
            if 1000 <= int(plz) <= 9999:
                return f"{plz} {city}"

        return None

    def _extract_text(self, soup: BeautifulSoup, selector: str) -> Optional[str]:
        """Extrahiert Text aus Element via CSS-Selector."""
        elem = soup.select_one(selector)
        if elem:
            return elem.get_text(' ', strip=True)
        return None

    async def _import_tender24(self, url: str, project_id: Optional[str]) -> UrlImportResult:
        """Importiert von tender24.ch."""
        client = await self._get_client()
        response = await client.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')

        title = self._extract_text(soup, 'h1') or self._extract_text(soup, '.title')

        result = UrlImportResult(
            source_id=project_id,
            project_name=title or "tender24.ch Projekt"
        )

        details = self._parse_generic_details(soup)

        result.description = details.get('beschreibung')
        result.client_name = details.get('auftraggeber')
        result.submission_deadline = details.get('eingabefrist')
        result.address = self._extract_swiss_address(soup.get_text())

        # CPV-Codes
        cpv_pattern = r'\b(\d{8})-?(\d)?\b'
        cpv_matches = re.findall(cpv_pattern, soup.get_text())
        result.cpv_codes = list(set(f"{m[0]}-{m[1]}" if m[1] else m[0] for m in cpv_matches))

        result.extraction_notes.append("Parsed from tender24.ch")

        # Confidence
        confidence = 0.5 if result.project_name else 0.2
        if result.address:
            confidence += 0.3
        result.confidence = min(confidence, 1.0)
        result.success = bool(result.project_name)

        return result

    async def _import_baublatt(self, url: str, project_id: Optional[str]) -> UrlImportResult:
        """Importiert von baublatt.ch."""
        client = await self._get_client()
        response = await client.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')

        title = self._extract_text(soup, 'h1') or self._extract_text(soup, '.entry-title')

        result = UrlImportResult(
            source_id=project_id,
            project_name=title or "baublatt.ch Projekt"
        )

        # Artikel-Text als Beschreibung
        article = soup.find('article') or soup.find('.entry-content')
        if article:
            result.description = article.get_text(' ', strip=True)[:500]

        result.address = self._extract_swiss_address(soup.get_text())
        result.extraction_notes.append("Parsed from baublatt.ch")

        confidence = 0.5 if result.project_name else 0.2
        if result.address:
            confidence += 0.3
        result.confidence = min(confidence, 1.0)
        result.success = bool(result.project_name)

        return result

    async def _import_generic(self, url: str, source: SourceType) -> UrlImportResult:
        """Generischer Import für unbekannte Quellen."""
        client = await self._get_client()
        response = await client.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Titel
        title = self._extract_text(soup, 'h1')
        if not title:
            title = self._extract_text(soup, 'title')
            if title:
                # Domain aus Titel entfernen
                title = re.sub(r'\s*[-|]\s*[^-|]+$', '', title).strip()

        result = UrlImportResult(
            project_name=title or "Importiertes Projekt"
        )

        # Meta-Description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            result.description = meta_desc.get('content', '')[:500]

        # Adresse extrahieren
        result.address = self._extract_swiss_address(soup.get_text())

        # Generische Details
        details = self._parse_generic_details(soup)
        result.client_name = details.get('auftraggeber') or details.get('herausgeber')
        result.submission_deadline = details.get('frist') or details.get('termin')

        parsed = urlparse(url)
        result.extraction_notes.append(f"Generic extraction from {parsed.netloc}")

        confidence = 0.3 if result.project_name else 0.1
        if result.address:
            confidence += 0.2
        result.confidence = min(confidence, 1.0)
        result.success = bool(result.project_name)

        return result

    def _parse_generic_details(self, soup: BeautifulSoup) -> dict:
        """Parst Details aus beliebiger Seite."""
        details = {}

        # Suche nach typischen Label-Value Strukturen
        for dt in soup.find_all('dt'):
            dd = dt.find_next_sibling('dd')
            if dd:
                key = self._normalize_key(dt.get_text(strip=True))
                value = dd.get_text(' ', strip=True)
                if key and value:
                    details[key] = value

        # Tabellen
        for row in soup.find_all('tr'):
            cells = row.find_all(['th', 'td'])
            if len(cells) >= 2:
                key = self._normalize_key(cells[0].get_text(strip=True))
                value = cells[1].get_text(' ', strip=True)
                if key and value:
                    details[key] = value

        return details

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
