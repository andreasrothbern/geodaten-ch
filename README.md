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
POST /api/v1/heights/fetch-on-demand      # On-Demand Höhenabruf
GET  /api/v1/heights/stats                # Datenbank-Statistiken
```

### Dokumentation
- Swagger UI: https://acceptable-trust-production.up.railway.app/docs
- ReDoc: https://acceptable-trust-production.up.railway.app/redoc

## 3D-Daten

### swisstopo 3D Viewer
Gebäude in 3D ansehen:
https://map.geo.admin.ch/?topic=ech&lang=de&bgLayer=ch.swisstopo.pixelkarte-farbe&layers=ch.swisstopo.swissbuildings3d&3d=true

### 3D Tiles Endpoint
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
│   │   │   └── height_fetcher.py  # On-Demand Import
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

## Geplante Erweiterungen

### SUVA Gerüst-Kategorien

Für präzise Gerüstplanung nach SUVA-Normen:

| Arbeitstyp | Benötigte Daten | Status |
|------------|-----------------|--------|
| Fassade komplett | Gesamthöhe, Umfang | Vorhanden |
| Malerarbeiten | Fassadenfläche pro Seite | Vorhanden |
| Dachuntersicht | Traufhöhe, Dachüberstand | Geplant (3D Tiles) |
| Dacharbeiten | Dachhöhe, Neigung, First | Geplant (3D Tiles) |

### 3D Tiles Integration

Extraktion detaillierter Gebäudemasse aus 3D Tiles:
- Traufhöhe vs. Firsthöhe
- Dachform und Neigung
- Dachüberstand
- Fassadenflächen nach Himmelsrichtung

## Datenquellen & Lizenzen

- **swisstopo**: [Open Government Data](https://www.swisstopo.admin.ch/de/geodata.html)
- **BFS GWR**: [Gebäude- und Wohnungsregister](https://www.housing-stat.ch/)
- **geodienste.ch**: [Amtliche Vermessung](https://geodienste.ch/)

## Deployment

Gehostet auf [Railway.app](https://railway.app):
- Backend: https://acceptable-trust-production.up.railway.app
- Frontend: https://cooperative-commitment-production.up.railway.app
