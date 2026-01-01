# Universal URL-Importer für Gerüstbau-App

## Übersicht

Ein nutzerfreundlicher Importer, der Projektdaten aus verschiedenen Ausschreibungsquellen extrahiert.

---

## 1. Unterstützte Quellen

### Primär: simap.ch (Offizielle Schweizer Plattform)

**Suchlink mit Gerüstbau-Filter:**
```
https://www.simap.ch/de?cpvCodes=["44212310","45262100"]&newestPubTypes=["tender"]&orderAddressCountryOnlySwitzerland=true
```

**Projekt-Detail-URL Format:**
```
https://www.simap.ch/de/project-detail/{uuid}
```

**Beispiel:**
```
https://www.simap.ch/de/project-detail/7bcbe557-5b96-4b74-8fa6-9067363aa4ca
```

### Sekundär: Weitere Ausschreibungsplattformen

| Plattform | URL | Beschreibung |
|-----------|-----|--------------|
| **tender24.ch** | https://www.tender24.ch | Private Ausschreibungsplattform |
| **bauaushang.ch** | https://www.bauaushang.ch | Bauausschreibungen |
| **competition.swiss** | https://www.competition.swiss | Wettbewerbe/Studienaufträge |
| **baublatt.ch** | https://www.baublatt.ch/ausschreibungen | Baubranche News + Ausschreibungen |
| **intelliTender** | https://www.intellitender.ch | Ausschreibungs-Aggregator |

### Tertiär: Direkte Quellen

- Gemeinde-Websites (z.B. `bern.ch/ausschreibungen`)
- Kantonale Amtsblätter
- Bauaushänge (Foto → OCR)
- E-Mail-Weiterleitungen

---

## 2. User Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PROJEKT IMPORTIEREN                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Ausschreibungen finden:                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ 🔗 simap.ch Gerüstbau-Ausschreibungen öffnen                        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  Link einfügen (simap.ch, tender24, Gemeinde-Website, etc.):               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ https://www.simap.ch/de/project-detail/7bcbe557-5b96-4b74-8fa...   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  [🔍 Daten extrahieren]                                                     │
│                                                                             │
│  ═══════════════════════════════════════════════════════════════════════   │
│                                                                             │
│  📋 ERKANNTE DATEN:                                          Quelle: simap │
│                                                                             │
│  Titel         [Gerüstarbeiten Sanierung Schulhaus Länggasse    ] ✏️       │
│  Adresse       [Länggassstrasse 40, 3012 Bern                   ] ✅ erkannt│
│  Auftraggeber  [Stadt Bern, Hochbauamt                          ] ✏️       │
│  Frist         [15.02.2025, 16:00                               ] ✏️       │
│  Verfahren     [Offenes Verfahren                               ]          │
│  Geschätzt     [CHF 80'000 - 120'000                            ]          │
│                                                                             │
│  📎 Dokumente: Login auf simap.ch erforderlich                             │
│     [→ Auf simap.ch öffnen und Dokumente herunterladen]                    │
│                                                                             │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  [Verwerfen]                    [✅ Projekt erstellen & Geodaten laden]    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Technische Implementierung

### Backend URL-Parser Service

```python
# backend/app/services/geruestbau/url_importer.py

import httpx
import re
from bs4 import BeautifulSoup
from dataclasses import dataclass
from typing import Optional, List
from enum import Enum
from urllib.parse import urlparse, parse_qs
import json

class SourceType(Enum):
    SIMAP = "simap"
    TENDER24 = "tender24"
    BAUBLATT = "baublatt"
    INTELLITENDER = "intellitender"
    GEMEINDE = "gemeinde"
    UNKNOWN = "unknown"

@dataclass
class ExtractedProject:
    """Aus URL extrahierte Projektdaten."""
    source: SourceType
    source_url: str
    source_id: Optional[str]
    
    title: str
    description: Optional[str]
    
    # Adresse (für Geodaten-Anreicherung)
    address: Optional[str]
    location_city: Optional[str]
    location_canton: Optional[str]
    
    # Auftraggeber
    client_name: Optional[str]
    client_contact: Optional[str]
    
    # Termine
    submission_deadline: Optional[str]
    execution_start: Optional[str]
    execution_end: Optional[str]
    
    # Verfahren
    procedure_type: Optional[str]
    contract_type: Optional[str]
    cpv_codes: List[str]
    
    # Schätzung
    estimated_value: Optional[str]
    
    # Zuschlag (falls bereits vergeben)
    awarded_to: Optional[str]
    awarded_value: Optional[str]
    
    # Meta
    raw_html: Optional[str] = None


class URLImporter:
    """Universal URL-Importer für Ausschreibungen."""
    
    # URL-Pattern für Quellen-Erkennung
    SOURCE_PATTERNS = {
        SourceType.SIMAP: [
            r'simap\.ch/de/project-detail/([a-f0-9-]+)',
            r'simap\.ch/.*projectId=([a-f0-9-]+)',
        ],
        SourceType.TENDER24: [
            r'tender24\.ch/.*?/(\d+)',
        ],
        SourceType.BAUBLATT: [
            r'baublatt\.ch/ausschreibungen/(\d+)',
        ],
        SourceType.INTELLITENDER: [
            r'intellitender\.ch/.*?id=(\d+)',
        ],
    }
    
    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; GeruestbauApp/1.0)"
            },
            follow_redirects=True
        )
    
    def detect_source(self, url: str) -> tuple[SourceType, Optional[str]]:
        """Erkennt die Quelle und extrahiert die ID."""
        for source, patterns in self.SOURCE_PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    return source, match.group(1)
        
        # Fallback: Versuche Gemeinde/Kanton zu erkennen
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        swiss_domains = ['.ch', '.swiss']
        if any(domain.endswith(d) for d in swiss_domains):
            return SourceType.GEMEINDE, None
        
        return SourceType.UNKNOWN, None
    
    async def import_from_url(self, url: str) -> ExtractedProject:
        """Hauptmethode: Importiert Projektdaten aus URL."""
        
        source, source_id = self.detect_source(url)
        
        if source == SourceType.SIMAP:
            return await self._import_simap(url, source_id)
        elif source == SourceType.TENDER24:
            return await self._import_tender24(url, source_id)
        elif source == SourceType.BAUBLATT:
            return await self._import_baublatt(url, source_id)
        else:
            return await self._import_generic(url)
    
    async def _import_simap(self, url: str, project_id: str) -> ExtractedProject:
        """Importiert von simap.ch."""
        
        response = await self.client.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Titel extrahieren
        title = self._extract_text(soup, 'h1') or "Unbekanntes Projekt"
        
        # Strukturierte Daten suchen (simap hat oft JSON-LD)
        json_ld = soup.find('script', type='application/ld+json')
        structured_data = {}
        if json_ld:
            try:
                structured_data = json.loads(json_ld.string)
            except:
                pass
        
        # Projekt-Details-Tabelle parsen
        details = self._parse_simap_details(soup)
        
        # Adresse extrahieren
        address = self._extract_address_from_simap(soup, details)
        
        return ExtractedProject(
            source=SourceType.SIMAP,
            source_url=url,
            source_id=project_id,
            title=title,
            description=details.get('beschreibung'),
            address=address,
            location_city=details.get('ort'),
            location_canton=details.get('kanton'),
            client_name=details.get('auftraggeber'),
            client_contact=details.get('kontakt'),
            submission_deadline=details.get('eingabefrist'),
            execution_start=details.get('ausfuehrung_von'),
            execution_end=details.get('ausfuehrung_bis'),
            procedure_type=details.get('verfahrensart'),
            contract_type=details.get('auftragsart'),
            cpv_codes=details.get('cpv_codes', []),
            estimated_value=details.get('schaetzung'),
            awarded_to=details.get('zuschlag_an'),
            awarded_value=details.get('zuschlag_wert'),
            raw_html=response.text
        )
    
    def _parse_simap_details(self, soup: BeautifulSoup) -> dict:
        """Parst die Detailtabelle von simap.ch."""
        details = {}
        
        # Suche nach Label-Value Paaren
        # simap.ch verwendet oft <dt>/<dd> oder Tabellen
        for dt in soup.find_all('dt'):
            dd = dt.find_next_sibling('dd')
            if dd:
                key = self._normalize_key(dt.get_text(strip=True))
                value = dd.get_text(strip=True)
                if key and value:
                    details[key] = value
        
        # Alternative: Tabellen-Zeilen
        for row in soup.find_all('tr'):
            cells = row.find_all(['th', 'td'])
            if len(cells) >= 2:
                key = self._normalize_key(cells[0].get_text(strip=True))
                value = cells[1].get_text(strip=True)
                if key and value and key not in details:
                    details[key] = value
        
        # CPV-Codes extrahieren
        cpv_pattern = r'\b\d{8}-\d\b'
        text = soup.get_text()
        details['cpv_codes'] = re.findall(cpv_pattern, text)
        
        return details
    
    def _normalize_key(self, key: str) -> str:
        """Normalisiert Feldnamen."""
        key = key.lower().strip()
        key = re.sub(r'[:\s]+', '_', key)
        key = re.sub(r'[^a-z0-9_äöü]', '', key)
        
        # Mapping zu Standard-Keys
        mappings = {
            'auftraggeber': 'auftraggeber',
            'beschaffungsstelle': 'auftraggeber',
            'verfahrensart': 'verfahrensart',
            'auftragsart': 'auftragsart',
            'eingabefrist': 'eingabefrist',
            'eingabetermin': 'eingabefrist',
            'frist': 'eingabefrist',
            'ausführungsort': 'ort',
            'erfüllungsort': 'ort',
            'realisierungsort': 'ort',
            'kanton': 'kanton',
            'beschreibung': 'beschreibung',
            'gegenstand': 'beschreibung',
            'zuschlag': 'zuschlag_an',
            'preis': 'zuschlag_wert',
        }
        
        for pattern, normalized in mappings.items():
            if pattern in key:
                return normalized
        
        return key
    
    def _extract_address_from_simap(self, soup: BeautifulSoup, details: dict) -> Optional[str]:
        """Extrahiert vollständige Adresse."""
        
        # Versuche strukturierte Adresse
        ort = details.get('ort', '')
        
        # Suche nach PLZ + Ort Pattern
        plz_ort_pattern = r'\b(\d{4})\s+([A-ZÄÖÜa-zäöü][a-zäöü]+(?:\s+[A-ZÄÖÜa-zäöü][a-zäöü]+)*)'
        text = soup.get_text()
        matches = re.findall(plz_ort_pattern, text)
        
        if matches:
            plz, city = matches[0]
            
            # Suche Strasse in der Nähe
            street_pattern = r'([A-ZÄÖÜa-zäöü][a-zäöü]+(?:strasse|weg|platz|gasse)\s+\d+[a-z]?)'
            street_matches = re.findall(street_pattern, text, re.IGNORECASE)
            
            if street_matches:
                return f"{street_matches[0]}, {plz} {city}"
            else:
                return f"{plz} {city}"
        
        return ort if ort else None
    
    async def _import_generic(self, url: str) -> ExtractedProject:
        """Generischer Import für unbekannte Quellen."""
        
        response = await self.client.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Titel: <title> oder <h1>
        title = self._extract_text(soup, 'title') or self._extract_text(soup, 'h1') or "Importiertes Projekt"
        
        # Versuche Adresse aus gesamtem Text zu extrahieren
        address = self._extract_swiss_address(soup.get_text())
        
        return ExtractedProject(
            source=SourceType.UNKNOWN,
            source_url=url,
            source_id=None,
            title=title,
            description=self._extract_text(soup, 'meta[name="description"]', attr='content'),
            address=address,
            location_city=None,
            location_canton=None,
            client_name=None,
            client_contact=None,
            submission_deadline=None,
            execution_start=None,
            execution_end=None,
            procedure_type=None,
            contract_type=None,
            cpv_codes=[],
            estimated_value=None,
            awarded_to=None,
            awarded_value=None,
            raw_html=response.text
        )
    
    def _extract_swiss_address(self, text: str) -> Optional[str]:
        """Extrahiert Schweizer Adresse aus Text."""
        
        # Pattern: Strasse Nr, PLZ Ort
        pattern = r'([A-ZÄÖÜa-zäöü][a-zäöü]+(?:strasse|weg|platz|gasse|allee)\s+\d+[a-z]?)\s*,?\s*(\d{4})\s+([A-ZÄÖÜa-zäöü][a-zäöü]+)'
        match = re.search(pattern, text, re.IGNORECASE)
        
        if match:
            street, plz, city = match.groups()
            return f"{street}, {plz} {city}"
        
        # Fallback: Nur PLZ + Ort
        plz_pattern = r'\b(\d{4})\s+([A-ZÄÖÜa-zäöü][a-zäöü]+(?:\s+[A-ZÄÖÜa-zäöü][a-zäöü]+)?)\b'
        plz_match = re.search(plz_pattern, text)
        
        if plz_match:
            return f"{plz_match.group(1)} {plz_match.group(2)}"
        
        return None
    
    def _extract_text(self, soup: BeautifulSoup, selector: str, attr: str = None) -> Optional[str]:
        """Extrahiert Text aus Element."""
        elem = soup.select_one(selector)
        if elem:
            if attr:
                return elem.get(attr)
            return elem.get_text(strip=True)
        return None
    
    async def close(self):
        await self.client.aclose()


# Singleton
url_importer = URLImporter()
```

### API Router

```python
# backend/app/routers/geruestbau.py - Ergänzung

from ..services.geruestbau.url_importer import url_importer, ExtractedProject

@router.post("/import/url")
async def import_from_url(url: str) -> dict:
    """
    Importiert Projektdaten aus einer URL.
    
    Unterstützte Quellen:
    - simap.ch (offizielle Ausschreibungen)
    - tender24.ch
    - baublatt.ch
    - Gemeinde-Websites
    - Beliebige URLs (generische Extraktion)
    """
    try:
        extracted = await url_importer.import_from_url(url)
        
        return {
            "success": True,
            "source": extracted.source.value,
            "data": {
                "title": extracted.title,
                "description": extracted.description,
                "address": extracted.address,
                "location": {
                    "city": extracted.location_city,
                    "canton": extracted.location_canton,
                },
                "client": {
                    "name": extracted.client_name,
                    "contact": extracted.client_contact,
                },
                "dates": {
                    "submission_deadline": extracted.submission_deadline,
                    "execution_start": extracted.execution_start,
                    "execution_end": extracted.execution_end,
                },
                "procedure": {
                    "type": extracted.procedure_type,
                    "contract_type": extracted.contract_type,
                    "cpv_codes": extracted.cpv_codes,
                },
                "value": {
                    "estimated": extracted.estimated_value,
                    "awarded": extracted.awarded_value,
                    "awarded_to": extracted.awarded_to,
                },
            },
            "source_url": extracted.source_url,
            "source_id": extracted.source_id,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "source_url": url,
        }


@router.post("/import/url/create-project")
async def import_and_create_project(
    url: str,
    auto_enrich: bool = True
) -> dict:
    """
    Importiert von URL und erstellt direkt ein Projekt.
    Optional: Automatische Geodaten-Anreicherung.
    """
    # 1. Daten extrahieren
    extracted = await url_importer.import_from_url(url)
    
    # 2. Projekt erstellen
    project_data = ProjectCreate(
        name=extracted.title,
        address=extracted.address or "",
        client_name=extracted.client_name,
        description=extracted.description,
        deadline=extracted.submission_deadline,
    )
    
    project = await project_service.create_project(project_data)
    
    # 3. Quell-Referenz speichern
    await project_service.update_project(project.id, {
        "source_type": extracted.source.value,
        "source_url": extracted.source_url,
        "source_id": extracted.source_id,
        "cpv_codes": extracted.cpv_codes,
    })
    
    # 4. Geodaten anreichern (wenn Adresse vorhanden)
    if auto_enrich and extracted.address:
        try:
            project = await project_service.enrich_with_geodata(project.id)
        except Exception as e:
            # Fehler bei Anreicherung ist nicht kritisch
            project.enrichment_error = str(e)
    
    return {
        "project": project,
        "extracted": {
            "source": extracted.source.value,
            "source_url": extracted.source_url,
        }
    }
```

---

## 4. Frontend Komponente

```tsx
// geruestbau-app/src/components/projects/URLImporter.tsx

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { 
  Link2, Search, Loader2, ExternalLink, 
  MapPin, Calendar, Building2, Check, AlertCircle 
} from 'lucide-react'

interface ExtractedData {
  success: boolean
  source: string
  data: {
    title: string
    description?: string
    address?: string
    location?: { city?: string; canton?: string }
    client?: { name?: string }
    dates?: { submission_deadline?: string }
    value?: { estimated?: string }
  }
  source_url: string
  error?: string
}

const SIMAP_SEARCH_URL = 'https://www.simap.ch/de?cpvCodes=["44212310","45262100"]&newestPubTypes=["tender"]&orderAddressCountryOnlySwitzerland=true'

export function URLImporter() {
  const navigate = useNavigate()
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [extracted, setExtracted] = useState<ExtractedData | null>(null)
  const [creating, setCreating] = useState(false)
  
  const handleExtract = async () => {
    if (!url.trim()) return
    
    setLoading(true)
    setExtracted(null)
    
    try {
      const response = await fetch(
        `/api/v1/geruestbau/import/url?url=${encodeURIComponent(url)}`
      )
      const data = await response.json()
      setExtracted(data)
    } catch (err) {
      setExtracted({
        success: false,
        source: 'error',
        data: { title: '' },
        source_url: url,
        error: 'Verbindungsfehler'
      })
    } finally {
      setLoading(false)
    }
  }
  
  const handleCreateProject = async () => {
    if (!extracted?.success) return
    
    setCreating(true)
    
    try {
      const response = await fetch(
        `/api/v1/geruestbau/import/url/create-project?url=${encodeURIComponent(url)}&auto_enrich=true`,
        { method: 'POST' }
      )
      const data = await response.json()
      navigate(`/projects/${data.project.id}`)
    } catch (err) {
      alert('Fehler beim Erstellen des Projekts')
    } finally {
      setCreating(false)
    }
  }
  
  const sourceLabels: Record<string, string> = {
    simap: 'simap.ch',
    tender24: 'tender24.ch',
    baublatt: 'baublatt.ch',
    gemeinde: 'Gemeinde-Website',
    unknown: 'Webseite',
  }
  
  return (
    <div className="space-y-4">
      {/* Quick Link zu simap.ch */}
      <a
        href={SIMAP_SEARCH_URL}
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center gap-2 p-3 bg-blue-50 text-blue-700 rounded-lg hover:bg-blue-100 transition-colors"
      >
        <Search size={20} />
        <span className="font-medium">Gerüstbau-Ausschreibungen auf simap.ch suchen</span>
        <ExternalLink size={16} className="ml-auto" />
      </a>
      
      {/* URL Input */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Link zu Ausschreibung einfügen
        </label>
        <p className="text-xs text-gray-500 mb-2">
          simap.ch, tender24.ch, Gemeinde-Websites, etc.
        </p>
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Link2 className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={20} />
            <input
              type="url"
              className="w-full pl-10 pr-4 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500"
              placeholder="https://www.simap.ch/de/project-detail/..."
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleExtract()}
            />
          </div>
          <button
            onClick={handleExtract}
            disabled={loading || !url.trim()}
            className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
          >
            {loading ? <Loader2 className="animate-spin" size={20} /> : 'Laden'}
          </button>
        </div>
      </div>
      
      {/* Error */}
      {extracted && !extracted.success && (
        <div className="p-4 bg-red-50 text-red-700 rounded-lg flex items-start gap-3">
          <AlertCircle size={20} className="flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-medium">Daten konnten nicht extrahiert werden</p>
            <p className="text-sm">{extracted.error}</p>
          </div>
        </div>
      )}
      
      {/* Extracted Data */}
      {extracted?.success && (
        <div className="border rounded-lg overflow-hidden">
          <div className="bg-gray-50 px-4 py-2 flex items-center justify-between border-b">
            <span className="text-sm font-medium text-gray-600">
              Quelle: {sourceLabels[extracted.source] || extracted.source}
            </span>
            <a
              href={extracted.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary-600 hover:underline text-sm flex items-center gap-1"
            >
              Original öffnen <ExternalLink size={14} />
            </a>
          </div>
          
          <div className="p-4 space-y-3">
            <h3 className="font-semibold text-lg">{extracted.data.title}</h3>
            
            {extracted.data.description && (
              <p className="text-gray-600 text-sm line-clamp-3">
                {extracted.data.description}
              </p>
            )}
            
            <div className="grid grid-cols-2 gap-3 text-sm">
              {extracted.data.address && (
                <div className="flex items-start gap-2">
                  <MapPin size={16} className="text-gray-400 mt-0.5" />
                  <div>
                    <p className="text-gray-500">Adresse</p>
                    <p className="font-medium">{extracted.data.address}</p>
                    <span className="inline-flex items-center gap-1 text-xs text-green-600">
                      <Check size={12} /> Geodaten verfügbar
                    </span>
                  </div>
                </div>
              )}
              
              {extracted.data.client?.name && (
                <div className="flex items-start gap-2">
                  <Building2 size={16} className="text-gray-400 mt-0.5" />
                  <div>
                    <p className="text-gray-500">Auftraggeber</p>
                    <p className="font-medium">{extracted.data.client.name}</p>
                  </div>
                </div>
              )}
              
              {extracted.data.dates?.submission_deadline && (
                <div className="flex items-start gap-2">
                  <Calendar size={16} className="text-gray-400 mt-0.5" />
                  <div>
                    <p className="text-gray-500">Eingabefrist</p>
                    <p className="font-medium">{extracted.data.dates.submission_deadline}</p>
                  </div>
                </div>
              )}
              
              {extracted.data.value?.estimated && (
                <div className="flex items-start gap-2">
                  <span className="text-gray-400 font-bold">CHF</span>
                  <div>
                    <p className="text-gray-500">Geschätzter Wert</p>
                    <p className="font-medium">{extracted.data.value.estimated}</p>
                  </div>
                </div>
              )}
            </div>
            
            {/* Hinweis Dokumente */}
            <div className="bg-amber-50 text-amber-800 p-3 rounded-lg text-sm">
              <p className="font-medium">📎 Dokumente</p>
              <p>Für Ausschreibungsunterlagen: Auf simap.ch einloggen und Dokumente herunterladen.</p>
            </div>
          </div>
          
          <div className="bg-gray-50 px-4 py-3 border-t flex justify-end gap-3">
            <button
              onClick={() => setExtracted(null)}
              className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg"
            >
              Verwerfen
            </button>
            <button
              onClick={handleCreateProject}
              disabled={creating}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 flex items-center gap-2"
            >
              {creating ? (
                <>
                  <Loader2 className="animate-spin" size={18} />
                  Wird erstellt...
                </>
              ) : (
                <>
                  <Check size={18} />
                  Projekt erstellen & Geodaten laden
                </>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
```

---

## 5. Wichtige Links zum Einbetten

### In der App anzeigen:

```tsx
const TENDER_LINKS = {
  simap: {
    name: 'simap.ch',
    description: 'Offizielle Schweizer Ausschreibungsplattform',
    searchUrl: 'https://www.simap.ch/de?cpvCodes=["44212310","45262100"]&newestPubTypes=["tender"]&orderAddressCountryOnlySwitzerland=true',
    logo: '/logos/simap.svg',
  },
  tender24: {
    name: 'tender24.ch',
    description: 'Private Ausschreibungsplattform',
    searchUrl: 'https://www.tender24.ch/Search?searchText=ger%C3%BCst',
    logo: '/logos/tender24.svg',
  },
  baublatt: {
    name: 'baublatt.ch',
    description: 'Baubranche News & Ausschreibungen',
    searchUrl: 'https://www.baublatt.ch/ausschreibungen',
    logo: '/logos/baublatt.svg',
  },
}
```

---

## 6. Dependencies

```bash
# Backend
pip install beautifulsoup4 httpx --break-system-packages
```

```json
// package.json (Frontend)
{
  "dependencies": {
    "lucide-react": "^0.263.1"
  }
}
```

---

*Stand: Dezember 2024*
