# Geodaten Schweiz - Gerüstbau-Modul

API und Web-App für Schweizer Geodaten mit Fokus auf Gerüstbau-Berechnungen.

**Live Demo:** https://cooperative-commitment-production.up.railway.app

## Integrierte Datenquellen

| Quelle | Daten | Genauigkeit | Status |
|--------|-------|-------------|--------|
| **GWR (BFS)** | EGID, Adresse, Geschosse, Kategorie, Baujahr | Amtlich, aktuell | Live-API |
| **geodienste.ch WFS** | Gebäudegrundriss (Polygon) | ±10cm (AV-Daten) | Live-API |
| **swissBUILDINGS3D 3.0** | Gemessene Gebäudehöhe | ±50cm (Photogrammetrie) | DB + On-Demand |
| **swisstopo Geocoding** | Adress-Koordinaten | ±1m | Live-API |

## Höhendaten-Verfügbarkeit

### Lokal importiert (sofort verfügbar)
- Kanton Bern: 365'790 Gebäude
- Kanton Solothurn: 234'879 Gebäude
- **Total: ~600'000 Gebäude**

### On-Demand abrufbar
Kantone mit EGID-Support: AG, AI, AR, BE, BL, BS, FR, GL, JU, LU, NE, SG, SH, SO, SZ, TG + Stadt Zürich

## Höhen-Lookup-Strategie

Die Höhenabfrage erfolgt in einer Fallback-Kette:

```
┌─────────────────────────────────────────────────────────────┐
│                    LOOKUP STRATEGIE                         │
├─────────────────────────────────────────────────────────────┤
│  1. EGID-Lookup (building_heights_detailed)                 │
│     → Trauf-/Firsthöhe aus swissBUILDINGS3D per EGID       │
│     ↓ falls nicht gefunden                                  │
│  2. EGID-Legacy (building_heights)                          │
│     → Gesamthöhe aus swissBUILDINGS3D per EGID             │
│     ↓ falls nicht gefunden                                  │
│  3. Koordinaten-Lookup (building_heights_by_coord)          │
│     → Höhe per LV95-Koordinaten (±25m Toleranz)            │
│     → Für Gebäude ohne EGID in swissBUILDINGS3D            │
│     ↓ falls nicht gefunden                                  │
│  4. Geschätzt aus GWR-Daten                                 │
│     → Geschosse × Geschosshöhe + Dachhöhe                  │
│     ↓ falls keine Geschossdaten                             │
│  5. Standard nach Kategorie                                 │
│     → EFH: 8m, MFH: 12m, etc.                              │
└─────────────────────────────────────────────────────────────┘
```

**Warum Koordinaten-Lookup?**
- swissBUILDINGS3D enthält nicht bei allen Gebäuden eine EGID
- Ältere Tiles (vor 2022) haben oft nur UUID, keine EGID
- Der Koordinaten-Lookup findet das nächstgelegene Gebäude geometrisch

## Datengenauigkeit

| Messwert | Quelle | Genauigkeit |
|----------|--------|-------------|
| Gebäudehöhe (gemessen) | swissBUILDINGS3D | ±0.5m |
| Gebäudehöhe (geschätzt) | Geschosse × 3.2m | ±2-3m |
| Fassadenlänge | AV-Grundriss | ±10cm |
| Grundfläche | AV-Grundriss | ±0.1m² |
| Koordinaten | LV95 | ±1m |

## API-Endpunkte

### Hauptfunktionen
```
GET  /api/v1/lookup?address=...           # Adresse -> Gebäudedaten
GET  /api/v1/scaffolding?address=...      # Gerüstbau-Daten
POST /api/v1/heights/fetch-on-demand      # On-Demand Höhenabruf (EGID-basiert)
GET  /api/v1/heights/3d-tiles?lat=...&lon=...  # 3D Tiles Höhe (koordinatenbasiert)
GET  /api/v1/heights/stats                # Datenbank-Statistiken
```

### Dokumentation
- Swagger UI: https://acceptable-trust-production.up.railway.app/docs
- ReDoc: https://acceptable-trust-production.up.railway.app/redoc

## 3D-Daten

### swisstopo 3D Viewer
Gebäude in 3D ansehen:
https://map.geo.admin.ch/?topic=ech&lang=de&bgLayer=ch.swisstopo.pixelkarte-farbe&layers=ch.swisstopo.swissbuildings3d&3d=true

### 3D Tiles API (koordinatenbasiert)

Höhenabfrage ohne EGID - direkt per Koordinaten:

```bash
# WGS84 Koordinaten
curl "https://acceptable-trust-production.up.railway.app/api/v1/heights/3d-tiles?lat=46.3131&lon=8.4476"

# LV95 Koordinaten
curl "https://acceptable-trust-production.up.railway.app/api/v1/heights/3d-tiles-lv95?e=2679000&n=1247000"
```

**Beispiel-Antwort:**
```json
{
  "status": "success",
  "height_m": 7.92,
  "building": {
    "uuid": "4BDE20B9-4EB0-4D3F-A67A-1D1336CF9497",
    "objektart": "Gebaeude Einzelhaus",
    "distance_m": 5.5
  }
}
```

**Hinweis:** Die 3D Tiles-Abdeckung ist lückenhaft. Städtische Zentren (Bern, Zürich, Basel) sind teilweise nicht abgedeckt. Für diese Gebiete den EGID-basierten On-Demand-Abruf verwenden.

### 3D Tiles Datenquelle
```
https://3d.geo.admin.ch/ch.swisstopo.swissbuildings3d.3d/v1/tileset.json
```

## Architektur

```
geodaten-ch/
├── backend/                 # FastAPI + Python 3.11
│   ├── app/
│   │   ├── main.py         # API Endpunkte
│   │   ├── models/         # Pydantic Schemas
│   │   ├── services/       # Business Logic
│   │   │   ├── swisstopo.py
│   │   │   ├── geodienste.py
│   │   │   ├── height_db.py
│   │   │   ├── height_fetcher.py   # STAC On-Demand Import
│   │   │   └── tiles3d_fetcher.py  # 3D Tiles koordinatenbasiert
│   │   └── data/
│   │       └── building_heights.db
│   └── scripts/
│       └── import_building_heights.py
│
├── frontend/               # React + Vite + TypeScript + Tailwind
│   └── src/
│       ├── App.tsx
│       └── components/
│           ├── SearchForm.tsx
│           ├── BuildingCard.tsx
│           └── ScaffoldingCard.tsx
│
└── Deployed on Railway.app
```

## Lokale Entwicklung

```bash
# Backend
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

## SVG-Visualisierung

Die App generiert technische SVG-Zeichnungen:
- **Grundriss**: Gebäudepolygon mit Gerüstzone, Fassaden-Labels, Verankerungspunkte
- **Ansicht**: Fassadenansicht mit Höhenkoten, Gerüstlagen, Dachform
- **Schnitt**: Querschnitt durch Gebäude mit Gerüst beidseitig

### Aktueller Stand vs. Ziel

| Feature | Aktuell | Ziel (professionell) |
|---------|---------|----------------------|
| Gebäudegeometrie | 1 Polygon | Mehrere Zonen |
| Höhendaten | 1 globale Höhe | Pro Fassade |
| Gerüstzonen | Bounding Box | Pro Fassade |
| Ständerpositionen | ❌ | Alle 2.5-3m |
| Verankerungen | Nur Ecken | Alle 4m h/v |
| Zugänge | ❌ | Markierungen |
| Titelblock/Fusszeile | ✅ Optional | ✅ |

**Referenz-SVGs:** `lawil/claude_ai_bundeshaus/` enthält handgefertigte Beispiele (Bundeshaus Bern)

### SVG API-Endpunkte

```
GET  /api/v1/visualize/cross-section?address=...   # Schnittansicht
GET  /api/v1/visualize/elevation?address=...       # Fassadenansicht
POST /api/v1/visualize/floor-plan                  # Grundriss (mit Polygon-Daten)
```

**Parameter:**
- `width`, `height`: SVG-Grösse (Default: 700x480)
- `professional`: Mit Schraffur-Patterns (true/false)
- `compact`: Minimale Darstellung für Fassaden-Auswahl

## Geplante Erweiterungen

### SUVA Gerüst-Kategorien

Für präzise Gerüstplanung nach SUVA-Normen:

| Arbeitstyp | Benötigte Daten | Status |
|------------|-----------------|--------|
| Fassade komplett | Gesamthöhe, Umfang | Vorhanden |
| Malerarbeiten | Fassadenfläche pro Seite | Vorhanden |
| Dachuntersicht | Traufhöhe, Dachüberstand | Geplant |
| Dacharbeiten | Dachhöhe, Neigung, First | Geplant |

### SVG-Verbesserungen (Priorität)

| Feature | Beschreibung | Status |
|---------|--------------|--------|
| Höhenzonen-UI | Manuelle Höhe pro Fassade | Geplant |
| Ständerpositionen | Punkte alle 2.5-3m (Feldlänge) | Geplant |
| Verankerungsraster | Linien alle 4m horizontal/vertikal | Geplant |
| Zugangsmarkierungen | Gelbe Rechtecke mit Z1-Z4 Label | Geplant |
| Gerüst-Details (Ansicht) | Ständer, Riegel, Beläge separat | Geplant |

### 3D Tiles Integration

| Feature | Status |
|---------|--------|
| Koordinatenbasierte Höhenabfrage | Implementiert |
| Gebäude-Metadaten (UUID, Objektart) | Implementiert |
| Traufhöhe vs. Firsthöhe | Geplant |
| Dachform und Neigung | Geplant |
| Dachüberstand | Geplant |

**Hinweis:** 3D Tiles-Abdeckung ist regional begrenzt (~87'000 Tiles). Urbane Zentren sind oft nicht abgedeckt.

## Datenquellen & Lizenzen

- **swisstopo**: [Open Government Data](https://www.swisstopo.admin.ch/de/geodata.html)
- **BFS GWR**: [Gebäude- und Wohnungsregister](https://www.housing-stat.ch/)
- **geodienste.ch**: [Amtliche Vermessung](https://geodienste.ch/)

## Deployment

Gehostet auf [Railway.app](https://railway.app):
- Backend: https://acceptable-trust-production.up.railway.app
- Frontend: https://cooperative-commitment-production.up.railway.app

### Railway Volume (Persistente Daten)

Die Höhendatenbank (`building_heights.db`) wird in einem Railway Volume gespeichert,
damit die on-demand importierten Gebäudehöhen bei Deployments erhalten bleiben.

**Volume einrichten (einmalig):**
```bash
# Railway CLI installieren (falls nicht vorhanden)
npm install -g @railway/cli

# Login
npx @railway/cli login

# Ins Backend-Verzeichnis wechseln und Projekt verlinken
cd backend
npx @railway/cli link

# Volume erstellen mit Mount-Pfad
npx @railway/cli volume add --mount-path /app/data
```

**Gespeicherte Daten im Volume (`/app/data`):**
- `building_heights.db` - swissBUILDINGS3D Höhen (on-demand importiert)
- `layher_catalog.db` - Gerüst-Materialkatalog
- `svg_cache.db` - SVG-Visualisierungs-Cache


## Test-Adressen

### Kantone mit WFS-Unterstützung (Gerüstbau-Daten verfügbar)

| Kanton | Adresse                           | Höhendaten | WFS |
|--------|-----------------------------------|------------|-----|
| BE     | Kramgasse 49, 3011 Bern           | DB | ✅ |
| BE     | Bundesplatz 3, 3011 Bern          | DB | ✅ |
| SO     | Hauptgasse 10, 4500 Solothurn     | DB | ✅ |
| BS     | Marktplatz 10, 4051 Basel         | On-Demand | ✅ |
| FR     | Rue de Romont 10, 1700 Fribourg   | On-Demand | ✅ |
| ZH     | Bahnhofstrasse 50, 8001 Zürich    | On-Demand | ✅ |
| AG     | Bahnhofstrasse 20, 5000 Aarau     | On-Demand | ✅ |
| SG     | Marktgasse 11, 9000 St. Gallen    | On-Demand | ✅ |
| TG     | Freiestrasse 10, 8500 Frauenfeld  | On-Demand | ✅ |
| BL     | Hauptstrasse 50, 4410 Liestal     | On-Demand | ✅ |
| SH     | Vordergasse 17, 8200 Schaffhausen | On-Demand | ✅ |

### 3D Tiles API Test-Koordinaten

| Region | Koordinaten (WGS84) | Status |
|--------|---------------------|--------|
| Tessin/Graubünden | lat=46.3131, lon=8.4476 | ✅ Funktioniert |
| Wallis | lat=46.2305, lon=10.1451 | ✅ Funktioniert |
| Bern Stadt | lat=46.9466, lon=7.4448 | ❌ Keine Abdeckung |
| Zürich Stadt | lat=47.3769, lon=8.5417 | ❌ Keine Abdeckung |

```bash
# Funktionierendes Beispiel
curl "https://acceptable-trust-production.up.railway.app/api/v1/heights/3d-tiles?lat=46.3131&lon=8.4476"
```

### Kantone ohne WFS-Unterstützung

| Kanton | Grund |
|--------|-------|
| LU     | Keine geodienste.ch WFS-Daten |
| NE     | Keine geodienste.ch WFS-Daten |
| GE, VD, VS | Kantonale Geodienste nicht integriert |

### Bereits in DB importiert (sofortige Höhendaten)
- Kanton Bern (BE): ~366'000 Gebäude
- Kanton Solothurn (SO): ~235'000 Gebäude