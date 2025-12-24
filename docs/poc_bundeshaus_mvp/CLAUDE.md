# CLAUDE.md - Projekt-Kontext für Claude Code

> **Letzte Aktualisierung:** 24.12.2025
> **Version:** 2.0

## Projekt: Geodaten Schweiz - Gerüstbau-Modul

Dieses Projekt bietet eine API und Web-App für Schweizer Geodaten mit Fokus auf professionelle Gerüstplanung.

**Live-Deployment:**
- Frontend: https://cooperative-commitment-production.up.railway.app
- Backend: https://acceptable-trust-production.up.railway.app
- API Docs: https://acceptable-trust-production.up.railway.app/docs

**Repository:** https://github.com/andreasrothbern/geodaten-ch/

---

## Aktuelle Architektur

```
geodaten-ch/
├── backend/                 # FastAPI + Python 3.11
│   ├── app/
│   │   ├── main.py         # API Endpunkte
│   │   ├── models/         # Pydantic Schemas
│   │   │   └── schemas.py
│   │   ├── services/       # Business Logic
│   │   │   ├── swisstopo.py      # swisstopo API (GWR, Geocoding)
│   │   │   ├── geodienste.py     # geodienste.ch WFS (Gebäudegeometrie)
│   │   │   ├── height_db.py      # Höhendatenbank Service
│   │   │   ├── height_fetcher.py # STAC On-Demand Import
│   │   │   ├── tiles3d_fetcher.py
│   │   │   ├── npk114_calculator.py  # NPK 114 Ausmass
│   │   │   ├── layher_catalog.py     # Material-Schätzung
│   │   │   └── cache.py
│   │   └── data/
│   │       └── building_heights.db   # SQLite (im Railway Volume)
│   └── scripts/
│       └── import_building_heights.py
│
├── frontend/               # React + Vite + TypeScript + Tailwind
│   └── src/
│       ├── App.tsx
│       └── components/
│           ├── SearchForm.tsx
│           ├── BuildingCard.tsx
│           ├── ScaffoldingCard.tsx
│           └── ApiStatus.tsx
│
└── docs/                   # Dokumentation
    ├── CLAUDE.md           # Diese Datei
    ├── ROADMAP.md          # Entwicklungsplan
    └── SVG_SPEC.md         # SVG-Spezifikation
```

---

## Integrierte Datenquellen

| Quelle | Daten | Genauigkeit | Status |
|--------|-------|-------------|--------|
| **GWR (BFS)** | EGID, Adresse, Geschosse, Kategorie, Baujahr | Amtlich | ✅ Live-API |
| **geodienste.ch WFS** | Gebäudegrundriss (1 Polygon) | ±10cm (AV) | ✅ Live-API |
| **swissBUILDINGS3D** | Trauf-/Firsthöhe (global) | ±50cm | ✅ DB + On-Demand |
| **swisstopo Geocoding** | Adress-Koordinaten | ±1m | ✅ Live-API |
| **swissALTI3D** | Geländehöhe (Terrain) | ±10cm | 🔜 Geplant |

---

## Aktueller Stand vs. Ziel

### Feature-Vergleich

| Feature | App (aktuell) | Ziel (professionell) |
|---------|---------------|----------------------|
| **Gebäudegeometrie** | 1 Polygon aus geodienste.ch | Mehrere Polygone pro Gebäudeteil |
| **Höhendaten** | 1 globale Höhe (SwissBuildings3D) | Höhenzonen pro Gebäudeteil |
| **Semantische Elemente** | ❌ Keine | ✅ Kuppel, Türme, Arkaden, Ehrenhof |
| **Gerüstzonen** | Rechteck um Polygon | Separate Zonen pro Fassade/Höhe |
| **Ständerpositionen** | ❌ Keine | ✅ Punkte alle 2.5-3m |
| **Verankerungen** | Nur an Polygon-Ecken | An Fassade alle 4m horiz./vert. |
| **Zugänge (Treppen)** | ❌ Keine | ✅ Markierungen mit Bezeichnung |
| **Masslinien** | Nur Umfang/Fläche | Mit Pfeilen, Beschriftung |
| **Lagenbeschriftung** | Nur im Schnitt | ✅ In Ansicht nummeriert |
| **Gebäudebeschriftung** | Nur Adresse | Zonen-Namen (BH West, etc.) |
| **Dachform Ansicht** | Einfaches Dreieck | Detailliert (Giebel, Kuppel) |
| **Material-Details** | ❌ Keine | Säulen, Beläge, Farben |
| **Terrain/Hanglage** | ❌ Horizontal | ✅ Gefälle pro Fassade |

### Daten-Lücken

Die grössten Lücken sind:

1. **Höhenzonen-Daten**
   - Problem: SwissBuildings3D liefert oft nur 1 globale Höhe
   - Beispiel Bundeshaus: 14.5m (Arkaden) statt 25m (Parlament)
   - Lösung: Gebäude-Kontext-System mit Claude-Analyse

2. **Gebäudeteil-Erkennung**
   - Problem: Nur 1 Polygon, keine Semantik
   - Ziel: Segmente mit Typ (hauptgebaeude, turm, anbau, arkade)
   - Lösung: Claude analysiert Polygon + Orthofoto

3. **Terrain-Daten**
   - Problem: Keine Geländehöhen für Hanglagen
   - Ziel: Gerüsthöhe pro Fassade bei Gefälle
   - Lösung: swissALTI3D Integration

---

## Höhen-Lookup-Strategie (aktuell)

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
│     ↓ falls nicht gefunden                                  │
│  4. Geschätzt aus GWR-Daten                                 │
│     → Geschosse × 3.2m + Dachhöhe                          │
│     ↓ falls keine Geschossdaten                             │
│  5. Standard nach Kategorie                                 │
│     → EFH: 8m, MFH: 12m, etc.                              │
└─────────────────────────────────────────────────────────────┘
```

---

## API-Endpunkte (aktuell)

### Hauptfunktionen
```
GET  /api/v1/lookup?address=...           # Adresse → Gebäudedaten
GET  /api/v1/scaffolding?address=...      # Gerüstbau-Daten
POST /api/v1/heights/fetch-on-demand      # On-Demand Höhenabruf
GET  /api/v1/heights/stats                # DB-Statistiken
```

### Geplante Erweiterungen
```
# Terrain (Phase 1)
GET  /api/v1/terrain?e=...&n=...          # Geländehöhe
GET  /api/v1/terrain/profile?coords=...   # Mehrere Punkte

# Gebäude-Kontext (Phase 2)
GET  /api/v1/building/context/{egid}      # Kontext abrufen
POST /api/v1/building/context/{egid}/analyze  # Claude-Analyse
PUT  /api/v1/building/context/{egid}      # Manuell bearbeiten

# Export (Phase 1)
GET  /api/v1/export/svg/grundriss/{egid}  # SVG Grundriss
GET  /api/v1/export/svg/schnitt/{egid}    # SVG Schnitt
GET  /api/v1/export/svg/ansicht/{egid}    # SVG Fassadenansicht
GET  /api/v1/export/dxf/{egid}            # CAD Export
GET  /api/v1/export/pdf/{egid}            # PDF Planungsblatt
```

---

## NPK 114 Konstanten

Ausmass-Berechnung gemäss NPK 114 D/2012:

```python
# Zuschläge
FASSADENABSTAND_LF = 0.30        # m - Abstand Gebäude zu Gerüst
GERUESTGANGBREITE_LG = 0.70      # m - für W09
STIRNSEITIGER_ABSCHLUSS_LS = 1.00 # m - beidseitig
HOEHENZUSCHLAG = 1.00            # m - über Arbeitshöhe

# Mindestmasse
MIN_AUSMASSLAENGE = 2.5          # m
MIN_AUSMASSHOEHE = 4.0           # m

# Formeln
# LA = LS + L + LS (beidseitiger Abschluss)
# HA = H + Höhenzuschlag
# A = LA × HA
```

---

## Layher Blitz 70 System

### Feldlängen (m)
`3.07, 2.57, 2.07, 1.57, 1.09, 0.73`

### Rahmenhöhen (m)
`2.00, 1.50, 1.00, 0.50`

### Richtwerte
| Parameter | Wert |
|-----------|------|
| Gewicht | 18–22 kg/m² |
| Lastklasse | 3 (200 kg/m²) |
| Breitenklasse | W09 (0.90 m) |
| Verankerung | alle 4m horiz., alle 4m vert. |
| Ständerabstand | 2.5–3.07m |

---

## Douglas-Peucker Parameter

Polygon-Vereinfachung für Fassadensegmente:

```python
SIMPLIFY_EPSILON = 0.3           # Meter - Toleranz
COLLINEAR_ANGLE_TOLERANCE = 8.0  # Grad
MIN_SIDE_LENGTH = 1.0            # Meter
```

---

## Deployment

**Plattform:** Railway.app

**Railway Volume:** `/app/data` für persistente SQLite-Datenbanken

**Persistente Daten:**
- `building_heights.db` - swissBUILDINGS3D Höhen
- `building_contexts.db` - Gebäude-Kontexte (geplant)
- `layher_catalog.db` - Gerüst-Materialkatalog

---

## Lokale Entwicklung

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

- API Docs: http://localhost:8000/docs
- Frontend: http://localhost:3000

---

## Wichtige Hinweise für Claude

### Bei SVG-Generierung
- Aktuelle SVGs sind funktional aber nicht professionell
- Siehe `SVG_SPEC.md` für Ziel-Spezifikation
- Benötigt Gebäude-Kontext für Zonen/Höhen

### Bei Berechnungen
- ALLE Zahlen aus Datenquellen, NICHT erfinden
- NPK 114 Regeln strikt einhalten
- Bei Unsicherheit: Nachfragen oder konservativ schätzen

### Bei komplexen Gebäuden
- 1 Polygon ≠ 1 Höhe (Bundeshaus-Problem)
- Gebäude-Kontext-System nutzen
- User-Validierung einplanen

---

## Status-Übersicht

### Fertig ✅
- [x] Backend + Frontend Deployment
- [x] swissBUILDINGS3D On-Demand Import
- [x] Railway Volume für Persistenz
- [x] Basis-SVG (Schnitt, Ansicht, Grundriss)
- [x] Fassaden-Auswahl mit interaktivem Grundriss
- [x] NPK 114 Ausmass-Berechnung
- [x] Material-Schätzung (Layher Blitz 70)
- [x] Douglas-Peucker Polygon-Vereinfachung
- [x] URL-Parameter für Adresse

### In Arbeit 🔨
- [ ] Professionelle SVG-Grafiken
- [ ] Gebäude-Kontext-System

### Geplant 🔜
- [ ] swissALTI3D (Terrain)
- [ ] Fassaden-Höhen bei Hanglagen
- [ ] DXF-Export
- [ ] MCP-Server für Claude-Integration
- [ ] Projektverwaltung (Offerte → Auftrag)
