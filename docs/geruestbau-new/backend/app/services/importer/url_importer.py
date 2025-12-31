"""
Universal URL-Importer für Gerüstbau-Ausschreibungen.

Unterstützte Quellen:
- simap.ch (offizielle Schweizer Ausschreibungen)
- tender24.ch
- baublatt.ch
- Gemeinde-Websites
- Beliebige URLs (generische Extraktion)
"""

import httpx
import re
import json
from bs4 import BeautifulSoup
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Tuple
from enum import Enum
from urllib.parse import urlparse, unquote
import logging

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
class ExtractedProject:
    """Aus URL extrahierte Projektdaten."""
    
    # Quelle
    source: SourceType
    source_url: str
    source_id: Optional[str] = None
    
    # Hauptdaten
    title: str = ""
    description: Optional[str] = None
    
    # Adresse (für Geodaten-Anreicherung)
    address: Optional[str] = None
    location_city: Optional[str] = None
    location_canton: Optional[str] = None
    location_plz: Optional[str] = None
    
    # Auftraggeber
    client_name: Optional[str] = None
    client_contact: Optional[str] = None
    
    # Termine
    submission_deadline: Optional[str] = None
    execution_start: Optional[str] = None
    execution_end: Optional[str] = None
    publication_date: Optional[str] = None
    
    # Verfahren
    procedure_type: Optional[str] = None
    contract_type: Optional[str] = None
    cpv_codes: List[str] = field(default_factory=list)
    project_number: Optional[str] = None
    
    # Wert
    estimated_value: Optional[str] = None
    
    # Zuschlag (falls bereits vergeben)
    awarded_to: Optional[str] = None
    awarded_value: Optional[str] = None
    award_reason: Optional[str] = None
    
    # Flags
    is_awarded: bool = False
    requires_login: bool = False
    
    # Debug
    extraction_notes: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Konvertiert zu Dictionary."""
        data = asdict(self)
        data['source'] = self.source.value
        return data


class URLImporter:
    """Universal URL-Importer für Ausschreibungen."""
    
    # URL-Pattern für Quellen-Erkennung
    SOURCE_PATTERNS = {
        SourceType.SIMAP: [
            r'simap\.ch/de/project-detail/([a-f0-9-]+)',
            r'simap\.ch/.*projectId=([a-f0-9-]+)',
            r'simap\.ch/de/publication-detail/([a-f0-9-]+)',
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
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "de-CH,de;q=0.9,en;q=0.8",
            },
            follow_redirects=True
        )
    
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
            # Könnte Gemeinde oder Kanton sein
            for canton in self.CANTONS:
                if canton.lower() in domain:
                    return SourceType.GEMEINDE, None
            return SourceType.GEMEINDE, None
        
        return SourceType.UNKNOWN, None
    
    async def import_from_url(self, url: str) -> ExtractedProject:
        """
        Hauptmethode: Importiert Projektdaten aus URL.
        
        Args:
            url: Die zu parsende URL
            
        Returns:
            ExtractedProject mit allen gefundenen Daten
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
            logger.error(f"Import failed for {url}: {e}")
            return ExtractedProject(
                source=source,
                source_url=url,
                source_id=source_id,
                title="Import fehlgeschlagen",
                extraction_notes=[f"Fehler: {str(e)}"]
            )
    
    async def _try_simap_api(self, project_id: str) -> Optional[ExtractedProject]:
        """
        Versucht Daten über die simap.ch API zu laden.
        
        Die API ist öffentlich für Lesezugriffe.
        """
        api_url = f"https://www.simap.ch/api/publications/v1/projects/{project_id}"
        
        try:
            response = await self.client.get(
                api_url,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "GeruestbauApp/1.0 (https://geodaten-ch.railway.app)"
                }
            )
            
            if response.status_code != 200:
                logger.debug(f"simap.ch API returned {response.status_code}")
                return None
            
            data = response.json()
            
            # API-Daten parsen
            project = ExtractedProject(
                source=SourceType.SIMAP,
                source_url=f"https://www.simap.ch/de/project-detail/{project_id}",
                source_id=project_id,
                title=data.get('title', 'Unbekanntes Projekt')
            )
            
            # Mapping der API-Felder
            project.description = data.get('description') or data.get('shortDescription')
            project.client_name = data.get('procuringEntity', {}).get('name')
            project.client_contact = data.get('procuringEntity', {}).get('contactPoint', {}).get('name')
            
            # Termine
            project.submission_deadline = data.get('submissionDeadline')
            project.publication_date = data.get('publicationDate')
            
            # Ausführungsort
            locations = data.get('executionLocations', [])
            if locations:
                loc = locations[0]
                parts = []
                if loc.get('street'):
                    parts.append(loc['street'])
                if loc.get('zipCode') and loc.get('city'):
                    parts.append(f"{loc['zipCode']} {loc['city']}")
                project.address = ", ".join(parts) if parts else None
                project.location_city = loc.get('city')
                project.location_plz = loc.get('zipCode')
                project.location_canton = loc.get('canton')
            
            # Verfahren
            project.procedure_type = data.get('procedureType')
            project.contract_type = data.get('contractType')
            project.project_number = data.get('projectNumber')
            
            # CPV-Codes
            cpv_list = data.get('cpvCodes', [])
            project.cpv_codes = [c.get('code', '') for c in cpv_list if c.get('code')]
            
            # Wert
            estimated = data.get('estimatedValue', {})
            if estimated:
                project.estimated_value = estimated.get('text') or f"CHF {estimated.get('amount', '')}"
            
            # Zuschlag
            award = data.get('award', {})
            if award:
                project.is_awarded = True
                project.awarded_to = award.get('awardedTo', {}).get('name')
                project.awarded_value = award.get('value', {}).get('text')
                project.award_reason = award.get('awardCriteria')
            
            project.extraction_notes.append("Loaded via simap.ch API")
            
            return project
            
        except Exception as e:
            logger.debug(f"simap.ch API failed: {e}")
            return None
    
    async def _import_simap_fallback(self, url: str, project_id: str) -> ExtractedProject:
        """Importiert von simap.ch."""
        
        # Versuche zuerst die API
        api_result = await self._try_simap_api(project_id)
        if api_result:
            return api_result
        
        # Fallback: Web-Scraping
        try:
            response = await self.client.get(url)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                return ExtractedProject(
                    source=SourceType.SIMAP,
                    source_url=url,
                    source_id=project_id,
                    title="simap.ch - Zugriff verweigert",
                    requires_login=True,
                    extraction_notes=[
                        "simap.ch blockiert automatisierte Zugriffe.",
                        "Bitte öffne die Seite im Browser und kopiere die Daten manuell,",
                        "oder nutze die simap.ch API nach Registrierung."
                    ]
                )
            raise
        except Exception as e:
            return ExtractedProject(
                source=SourceType.SIMAP,
                source_url=url,
                source_id=project_id,
                title="Import fehlgeschlagen",
                extraction_notes=[f"Fehler: {str(e)}"]
            )
        
        response  # Wird unten weiterverarbeitet
        
        # Cookie-Check Redirect?
        if 'cookie-check' in response.url.path.lower():
            return ExtractedProject(
                source=SourceType.SIMAP,
                source_url=url,
                source_id=project_id,
                title="simap.ch - Cookie erforderlich",
                requires_login=True,
                extraction_notes=["simap.ch erfordert Cookie-Akzeptanz. Bitte Seite im Browser öffnen."]
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
        
        project = ExtractedProject(
            source=SourceType.SIMAP,
            source_url=url,
            source_id=project_id,
            title=title or "Unbekanntes Projekt"
        )
        
        # Details parsen
        details = self._parse_simap_details(soup)
        
        # Mapping zu Projekt-Feldern
        project.description = details.get('beschreibung') or details.get('gegenstand')
        project.client_name = details.get('auftraggeber') or details.get('beschaffungsstelle')
        project.submission_deadline = details.get('eingabefrist') or details.get('eingabetermin')
        project.procedure_type = details.get('verfahrensart')
        project.contract_type = details.get('auftragsart')
        project.publication_date = details.get('publikationsdatum')
        project.project_number = details.get('projekt_nr') or details.get('projektnummer')
        
        # Ort/Adresse
        project.location_city = details.get('ort') or details.get('realisierungsort')
        project.location_canton = details.get('kanton')
        project.address = self._extract_address_from_simap(soup, details)
        
        # PLZ extrahieren
        if project.address:
            plz_match = re.search(r'\b(\d{4})\b', project.address)
            if plz_match:
                project.location_plz = plz_match.group(1)
        
        # CPV-Codes
        project.cpv_codes = details.get('cpv_codes', [])
        
        # Zuschlag-Info
        if details.get('zuschlag') or details.get('zuschlagsempfänger'):
            project.is_awarded = True
            project.awarded_to = details.get('zuschlag') or details.get('zuschlagsempfänger')
            project.awarded_value = details.get('zuschlagspreis') or details.get('preis')
            project.award_reason = details.get('begründung')
        
        # Wert
        project.estimated_value = details.get('auftragswert') or details.get('schätzung')
        
        # Ausführungszeit
        project.execution_start = details.get('ausführung_von') or details.get('beginn')
        project.execution_end = details.get('ausführung_bis') or details.get('ende')
        
        project.extraction_notes.append(f"Parsed {len(details)} fields from simap.ch")
        
        return project
    
    def _parse_simap_details(self, soup: BeautifulSoup) -> dict:
        """Parst die Detailtabelle von simap.ch."""
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
        """Extrahiert vollständige Adresse aus simap.ch Seite."""
        
        # Versuche strukturierte Daten
        ort = details.get('ort', '')
        
        # Suche im gesamten Text nach Adress-Mustern
        text = soup.get_text()
        
        # Pattern: Strasse Nr, PLZ Ort
        full_address_pattern = r'([A-ZÄÖÜa-zäöü][a-zäöü]+(?:strasse|weg|platz|gasse|allee|rain|matte)\s+\d+[a-z]?)\s*,?\s*(\d{4})\s+([A-ZÄÖÜa-zäöü][a-zäöüéèà]+(?:\s+[A-ZÄÖÜa-zäöü][a-zäöüéèà]+)?)'
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
            # Extrahiere PLZ wenn vorhanden
            plz_in_ort = re.search(r'(\d{4})', ort)
            if plz_in_ort:
                return ort
            return ort
        
        return None
    
    async def _import_tender24(self, url: str, project_id: str) -> ExtractedProject:
        """Importiert von tender24.ch."""
        
        response = await self.client.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        title = self._extract_text(soup, 'h1') or self._extract_text(soup, '.title')
        
        project = ExtractedProject(
            source=SourceType.TENDER24,
            source_url=url,
            source_id=project_id,
            title=title or "tender24.ch Projekt"
        )
        
        # tender24 hat ähnliche Struktur
        details = self._parse_generic_details(soup)
        
        project.description = details.get('beschreibung')
        project.client_name = details.get('auftraggeber')
        project.submission_deadline = details.get('eingabefrist')
        project.address = self._extract_swiss_address(soup.get_text())
        
        # CPV-Codes
        cpv_pattern = r'\b(\d{8})-?(\d)?\b'
        cpv_matches = re.findall(cpv_pattern, soup.get_text())
        project.cpv_codes = list(set(f"{m[0]}-{m[1]}" if m[1] else m[0] for m in cpv_matches))
        
        project.extraction_notes.append("Parsed from tender24.ch")
        
        return project
    
    async def _import_baublatt(self, url: str, project_id: str) -> ExtractedProject:
        """Importiert von baublatt.ch."""
        
        response = await self.client.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        title = self._extract_text(soup, 'h1') or self._extract_text(soup, '.entry-title')
        
        project = ExtractedProject(
            source=SourceType.BAUBLATT,
            source_url=url,
            source_id=project_id,
            title=title or "baublatt.ch Projekt"
        )
        
        # Artikel-Text als Beschreibung
        article = soup.find('article') or soup.find('.entry-content')
        if article:
            project.description = article.get_text(' ', strip=True)[:500]
        
        project.address = self._extract_swiss_address(soup.get_text())
        
        project.extraction_notes.append("Parsed from baublatt.ch")
        
        return project
    
    async def _import_generic(self, url: str, source: SourceType) -> ExtractedProject:
        """Generischer Import für unbekannte Quellen."""
        
        response = await self.client.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Titel
        title = self._extract_text(soup, 'h1')
        if not title:
            title = self._extract_text(soup, 'title')
            if title:
                # Domain aus Titel entfernen
                title = re.sub(r'\s*[-|]\s*[^-|]+$', '', title).strip()
        
        project = ExtractedProject(
            source=source,
            source_url=url,
            title=title or "Importiertes Projekt"
        )
        
        # Meta-Description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            project.description = meta_desc.get('content', '')[:500]
        
        # Adresse extrahieren
        project.address = self._extract_swiss_address(soup.get_text())
        
        # Generische Details
        details = self._parse_generic_details(soup)
        project.client_name = details.get('auftraggeber') or details.get('herausgeber')
        project.submission_deadline = details.get('frist') or details.get('termin')
        
        project.extraction_notes.append(f"Generic extraction from {urlparse(url).netloc}")
        
        return project
    
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
    
    def _extract_swiss_address(self, text: str) -> Optional[str]:
        """Extrahiert Schweizer Adresse aus beliebigem Text."""
        
        # Bereinige Text
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
    
    async def close(self):
        """Schliesst den HTTP-Client."""
        await self.client.aclose()


# Singleton-Instanz
url_importer = URLImporter()
