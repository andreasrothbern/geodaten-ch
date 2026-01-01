# simap.ch Integration

## Übersicht

simap.ch ist die **offizielle Schweizer Plattform für öffentliche Ausschreibungen** von Bund, Kantonen und Gemeinden. Seit Juli 2024 gibt es eine neue API (v1.2).

---

## Registrierung

### 1. Benutzer-Registrierung (für Web + API)

**URL:** https://www.simap.ch

1. Auf simap.ch → "Registrieren"
2. Persönliches Benutzerkonto erstellen
3. 2-Faktor-Authentifizierung via E-Mail bestätigen
4. Optional: Als Mitarbeiter einer Firma registrieren

### 2. API/Entwickler-Registrierung (für Machine-to-Machine)

**URL:** https://kissimap.ch/de/api-zum-neuen-simap

Für automatisierten API-Zugriff:
1. Registrierungsformular auf kissimap.ch ausfüllen
2. Warten auf Freischaltung
3. Entwickler werden über API-Änderungen informiert

**Hinweis:** Die API-Nutzung ist aktuell **kostenlos**. Der Verein simap.ch behält sich vor, künftig Gebühren zu erheben.

---

## API-Dokumentation

| Resource | URL |
|----------|-----|
| **Swagger UI (Produktion)** | https://www.simap.ch/api-doc |
| **Swagger UI (Test)** | https://int.simap.ch/api-doc |
| **Changelog** | https://www.simap.ch/api/specifications/changelog.html |
| **Forum & Support** | https://kissimap.ch/forum |
| **Projekt-Info** | https://kissimap.ch |

---

## Authentifizierung

Die API verwendet **OpenID Connect** mit 2-Faktor-Authentifizierung:

1. Login mit Benutzername/Passwort
2. Code per E-Mail erhalten
3. Code eingeben (2FA)
4. Access Token erhalten

**Wichtig:** 
- Kein SSO vorgesehen
- Kein technischer Benutzer (Zertifikat) möglich
- Jede Aktion muss einem realen Benutzer zugeordnet werden können

### Zugriffsrechte nach Rolle

| Ohne Auth | Mit Auth (Anbieter) | Mit Auth (Auftraggeber) |
|-----------|---------------------|-------------------------|
| Publikationen lesen | + Unterlagen herunterladen | + Publikationen erstellen |
| Suche | + Fragen stellen | + Fragen beantworten |

---

## Relevante CPV-Codes für Gerüstbau

| CPV-Code | Beschreibung |
|----------|--------------|
| `44212310-5` | Gerüste |
| `45262100-2` | Gerüstarbeiten |
| `45262110-5` | Abbau von Gerüsten |
| `45262120-8` | Aufbau von Gerüsten |
| `44212320-8` | Verschiedene Gerüstkonstruktionen |
| `44212321-5` | Fahrbare Gerüste |

**Suchtipp:** Mit `4526210*` nach allen Gerüstarbeiten suchen.

---

## API-Endpunkte (Auswahl)

### Öffentlich (ohne Auth)

```
GET /api/publications/v1/search
    ?q={suchbegriff}
    &publicationType=TENDER
    &cpvCodes=45262100-2
    &cantons=BE,ZH
    &status=PUBLISHED
    &limit=20

GET /api/publications/v1/projects/{projectId}
GET /api/publications/v1/projects/{projectId}/publications
```

### Mit Authentifizierung

```
GET /api/vendors/v1/my/projects
GET /api/vendors/v1/my/projects/{projectId}/documents
POST /api/vendors/v1/my/projects/{projectId}/qna/questions
```

---

## Implementation in Gerüstbau-App

### Option A: Link-Import (empfohlen für Start)

User kopiert simap.ch URL → App extrahiert Daten

```
┌─────────────────────────────────────────────────────────────┐
│  PROJEKT IMPORTIEREN                                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  simap.ch Link einfügen:                                    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ https://simap.ch/de/projects/123456                 │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  [Importieren]                                              │
│                                                             │
│  ─────────────────────────────────────────────────────────  │
│  ERKANNTE DATEN:                                            │
│                                                             │
│  Titel:     Gerüstarbeiten Kirche St. Peter                 │
│  Adresse:   Rathausgasse 2, 3011 Bern                       │
│  Frist:     15.01.2025, 16:00                               │
│  Auftrag:   CHF 150'000 - 250'000                           │
│                                                             │
│  [Projekt erstellen →]                                      │
└─────────────────────────────────────────────────────────────┘
```

### Option B: Ausschreibungs-Suche (später)

Integrierte Suche mit Filtern für Gerüstbau-relevante Ausschreibungen.

---

## Backend-Service

### backend/app/services/geruestbau/simap_service.py

```python
import httpx
import re
from typing import List, Optional
from dataclasses import dataclass

@dataclass
class SimapTender:
    project_id: str
    title: str
    address: Optional[str]
    client_name: Optional[str]
    deadline: Optional[str]
    description: Optional[str]
    estimated_value: Optional[str]
    simap_url: str
    cpv_codes: List[str]

class SimapService:
    """Integration mit simap.ch API."""
    
    BASE_URL = "https://www.simap.ch/api"
    
    # Relevante CPV-Codes für Gerüstbau
    SCAFFOLDING_CPV_CODES = [
        "44212310-5",  # Gerüste
        "45262100-2",  # Gerüstarbeiten
        "45262110-5",  # Abbau von Gerüsten
        "45262120-8",  # Aufbau von Gerüsten
    ]
    
    def extract_project_id_from_url(self, url: str) -> Optional[str]:
        """
        Extrahiert die Projekt-ID aus einer simap.ch URL.
        
        Beispiele:
        - https://www.simap.ch/de/projects/123456
        - https://simap.ch/de/projects/123456/publications/789
        """
        patterns = [
            r'simap\.ch/\w+/projects/(\d+)',
            r'simap\.ch/.*projectId=(\d+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    async def get_project_details(self, project_id: str) -> Optional[dict]:
        """
        Ruft Projektdetails von simap.ch ab.
        Öffentlich zugänglich (keine Auth nötig).
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{self.BASE_URL}/publications/v1/projects/{project_id}"
                )
                if response.status_code == 200:
                    return response.json()
            except httpx.RequestError as e:
                print(f"simap.ch API Fehler: {e}")
        return None
    
    async def search_tenders(
        self,
        query: str = "Gerüst",
        cantons: List[str] = None,
        cpv_codes: List[str] = None,
        only_open: bool = True,
        limit: int = 20
    ) -> List[dict]:
        """
        Sucht Ausschreibungen auf simap.ch.
        Öffentlich zugänglich (keine Auth nötig).
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            params = {
                "q": query,
                "publicationType": "TENDER",
                "limit": limit,
            }
            
            if cantons:
                params["cantons"] = ",".join(cantons)
            
            if cpv_codes:
                params["cpvCodes"] = ",".join(cpv_codes)
            else:
                params["cpvCodes"] = ",".join(self.SCAFFOLDING_CPV_CODES)
            
            if only_open:
                params["status"] = "PUBLISHED"
            
            try:
                response = await client.get(
                    f"{self.BASE_URL}/publications/v1/search",
                    params=params
                )
                if response.status_code == 200:
                    return response.json().get("items", [])
            except httpx.RequestError as e:
                print(f"simap.ch Suche fehlgeschlagen: {e}")
        
        return []
    
    def extract_address_from_tender(self, tender: dict) -> Optional[str]:
        """
        Extrahiert die Objektadresse aus einer Ausschreibung.
        """
        # 1. Ausführungsort prüfen
        locations = tender.get("executionLocations", [])
        if locations:
            loc = locations[0]
            parts = filter(None, [
                loc.get("street"),
                f"{loc.get('zipCode', '')} {loc.get('city', '')}".strip()
            ])
            address = ", ".join(parts)
            if address:
                return address
        
        # 2. Adresse der Beschaffungsstelle als Fallback
        procuring = tender.get("procuringEntity", {})
        address_parts = filter(None, [
            procuring.get("street"),
            f"{procuring.get('zipCode', '')} {procuring.get('city', '')}".strip()
        ])
        return ", ".join(address_parts) or None
    
    async def import_tender(self, url_or_id: str) -> Optional[SimapTender]:
        """
        Importiert eine Ausschreibung als SimapTender.
        
        Args:
            url_or_id: simap.ch URL oder Projekt-ID
        """
        # ID extrahieren
        if url_or_id.startswith("http"):
            project_id = self.extract_project_id_from_url(url_or_id)
        else:
            project_id = url_or_id
        
        if not project_id:
            return None
        
        # Details abrufen
        tender = await self.get_project_details(project_id)
        if not tender:
            return None
        
        return SimapTender(
            project_id=project_id,
            title=tender.get("title", ""),
            address=self.extract_address_from_tender(tender),
            client_name=tender.get("procuringEntity", {}).get("name"),
            deadline=tender.get("submissionDeadline"),
            description=tender.get("description"),
            estimated_value=tender.get("estimatedValue", {}).get("text"),
            simap_url=f"https://www.simap.ch/de/projects/{project_id}",
            cpv_codes=[c.get("code") for c in tender.get("cpvCodes", [])]
        )
```

### API-Router Erweiterung

```python
# backend/app/routers/geruestbau.py

from ..services.geruestbau.simap_service import SimapService

simap_service = SimapService()

@router.get("/simap/search")
async def search_simap_tenders(
    q: str = "Gerüst",
    cantons: str = None,
    only_open: bool = True,
    limit: int = 20
):
    """
    Sucht Gerüstbau-Ausschreibungen auf simap.ch.
    Keine Authentifizierung erforderlich.
    """
    canton_list = cantons.split(",") if cantons else None
    
    results = await simap_service.search_tenders(
        query=q,
        cantons=canton_list,
        only_open=only_open,
        limit=limit
    )
    
    return {
        "count": len(results),
        "items": results
    }

@router.post("/simap/import")
async def import_from_simap(url: str):
    """
    Importiert eine simap.ch Ausschreibung und erstellt ein Projekt.
    
    Args:
        url: simap.ch Projekt-URL oder Projekt-ID
    """
    # 1. Von simap.ch importieren
    tender = await simap_service.import_tender(url)
    if not tender:
        raise HTTPException(
            status_code=404, 
            detail="Ausschreibung nicht gefunden oder URL ungültig"
        )
    
    # 2. Projekt erstellen
    project_data = ProjectCreate(
        name=tender.title,
        address=tender.address or "",
        client_name=tender.client_name,
        deadline=tender.deadline,
        description=tender.description,
    )
    
    project = await project_service.create_project(project_data)
    
    # 3. simap-Referenz speichern
    await project_service.update_project(project.id, {
        "simap_id": tender.project_id,
        "simap_url": tender.simap_url,
    })
    
    # 4. Geodaten anreichern (wenn Adresse vorhanden)
    if tender.address:
        project = await project_service.enrich_with_geodata(project.id)
    
    return {
        "project": project,
        "simap": {
            "id": tender.project_id,
            "url": tender.simap_url,
            "cpv_codes": tender.cpv_codes,
            "estimated_value": tender.estimated_value,
        }
    }

@router.get("/simap/preview")
async def preview_simap_tender(url: str):
    """
    Vorschau einer simap.ch Ausschreibung ohne Import.
    """
    tender = await simap_service.import_tender(url)
    if not tender:
        raise HTTPException(status_code=404, detail="Nicht gefunden")
    
    return tender
```

---

## Frontend-Komponente

### src/components/projects/SimapImport.tsx

```tsx
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Link2, Search, Loader2, ExternalLink } from 'lucide-react'

interface SimapPreview {
  project_id: string
  title: string
  address: string | null
  client_name: string | null
  deadline: string | null
  estimated_value: string | null
  simap_url: string
}

export function SimapImport() {
  const navigate = useNavigate()
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [preview, setPreview] = useState<SimapPreview | null>(null)
  const [error, setError] = useState('')
  
  const handlePreview = async () => {
    if (!url.trim()) return
    
    setLoading(true)
    setError('')
    setPreview(null)
    
    try {
      const response = await fetch(
        `/api/v1/geruestbau/simap/preview?url=${encodeURIComponent(url)}`
      )
      
      if (!response.ok) {
        throw new Error('Ausschreibung nicht gefunden')
      }
      
      const data = await response.json()
      setPreview(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler beim Laden')
    } finally {
      setLoading(false)
    }
  }
  
  const handleImport = async () => {
    if (!preview) return
    
    setLoading(true)
    
    try {
      const response = await fetch('/api/v1/geruestbau/simap/import', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url }),
      })
      
      if (!response.ok) {
        throw new Error('Import fehlgeschlagen')
      }
      
      const data = await response.json()
      navigate(`/projects/${data.project.id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Import fehlgeschlagen')
      setLoading(false)
    }
  }
  
  return (
    <div className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          simap.ch Link einfügen
        </label>
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Link2 className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={20} />
            <input
              type="url"
              className="input-field pl-10"
              placeholder="https://simap.ch/de/projects/..."
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handlePreview()}
            />
          </div>
          <button
            onClick={handlePreview}
            disabled={loading || !url.trim()}
            className="btn-secondary px-4"
          >
            {loading ? <Loader2 className="animate-spin" size={20} /> : <Search size={20} />}
          </button>
        </div>
      </div>
      
      {error && (
        <div className="p-3 bg-red-50 text-red-700 rounded-lg text-sm">
          {error}
        </div>
      )}
      
      {preview && (
        <div className="card space-y-3">
          <div className="flex items-start justify-between">
            <h3 className="font-semibold text-lg">{preview.title}</h3>
            <a
              href={preview.simap_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary-600"
            >
              <ExternalLink size={20} />
            </a>
          </div>
          
          <dl className="grid grid-cols-2 gap-2 text-sm">
            {preview.address && (
              <>
                <dt className="text-gray-500">Adresse</dt>
                <dd>{preview.address}</dd>
              </>
            )}
            {preview.client_name && (
              <>
                <dt className="text-gray-500">Auftraggeber</dt>
                <dd>{preview.client_name}</dd>
              </>
            )}
            {preview.deadline && (
              <>
                <dt className="text-gray-500">Frist</dt>
                <dd>{new Date(preview.deadline).toLocaleDateString('de-CH')}</dd>
              </>
            )}
            {preview.estimated_value && (
              <>
                <dt className="text-gray-500">Schätzung</dt>
                <dd>{preview.estimated_value}</dd>
              </>
            )}
          </dl>
          
          <button
            onClick={handleImport}
            disabled={loading}
            className="btn-primary"
          >
            {loading ? 'Wird importiert...' : 'Projekt erstellen'}
          </button>
        </div>
      )}
    </div>
  )
}
```

---

## Nützliche Links

| Resource | URL |
|----------|-----|
| simap.ch (Produktion) | https://www.simap.ch |
| simap.ch (Test/Schulung) | https://educ.simap.ch |
| API-Dokumentation | https://www.simap.ch/api-doc |
| Projekt KISSimap | https://kissimap.ch |
| Forum & Support | https://kissimap.ch/forum |
| CPV-Code Suche | https://www.cpvcode.de |
| Erklärvideos | https://kissimap.ch/de/anleitungen |

---

## Hinweise

1. **Öffentliche Daten:** Publikationen und Suche sind ohne Authentifizierung möglich
2. **2FA erforderlich:** Für alle authentifizierten Aktionen ist 2-Faktor-Authentifizierung nötig
3. **Kein M2M-Login:** Kein technischer Benutzer / Zertifikat-basierter Zugang
4. **Rate Limits:** Nicht dokumentiert, aber Fair Use beachten
5. **Kosten:** Aktuell kostenlos, Änderungen möglich

---

*Stand: Dezember 2024 / API Version 1.2*
