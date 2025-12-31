# PROJEKT_KONTEXT.md
# Geruestplanung Schweiz - Projekt-Ueberblick
# ==========================================
# Diese Datei ist fuer Claude.ai als Project Knowledge gedacht.
# Fuer technische Details: siehe CLAUDE.md

## Aktuelles Projekt

**Anwendung:** Geodaten Schweiz - Geruestbau-Modul
**Status:** Produktiv auf Railway.app

**App-URLs:**
- Frontend: https://cooperative-commitment-production.up.railway.app/
- Backend API: https://acceptable-trust-production.up.railway.app/
- Gerüstbau-App: https://geruestbau-app-production.up.railway.app/
- Beispiel: `?address=Bundesplatz%203,%203011%20Bern`

---

## Was die App macht

Eine Web-Anwendung fuer Geruestplanung in der Schweiz, die automatisch:

1. **Gebaeudedaten sammelt** (Adresse, EGID, Geschosse, Baujahr)
2. **Gebaeudegeometrie abruft** (Polygon aus amtlicher Vermessung)
3. **Hoehendaten ermittelt** (gemessen oder geschaetzt)
4. **Terrain-Hoehen berechnet** (m ue.M.)
5. **SVG-Visualisierungen generiert** (Grundriss, Ansicht, Schnitt)
6. **Geruest-Ausmass berechnet** (NPK 114 konform)
7. **Material schaetzt** (Layher Blitz 70)

---

## Datenfluss

```
Adresse eingeben
      |
      v
SmartBuildingService (10 Schritte)
|-- 1. Geocoding (swisstopo)
|-- 2. GWR-Daten (Geschosse, Flaeche)
|-- 3. Hoehendaten (swissBUILDINGS3D)
|-- 4. Terrain (swissALTI3D)
|-- 5. Polygon (geodienste.ch)
|-- 6. Dach-Analyse
|-- 7. Gebaeude-Recherche (Claude)
|-- 8. Zonen-Analyse (bei komplexen)
|-- 9. Zugangspunkte (SUVA)
+-- 10. Qualitaetsbewertung
      |
      v
BuildingDataBundle (24h gecacht)
      |
      |---> Frontend-Anzeige
      +---> SVG-Generierung (Claude API)
```

---

## Bekanntes Problem: Hoehenzonen

**Problem:** swissBUILDINGS3D liefert nur EINE globale Hoehe pro Gebaeude.

**Beispiel Bundeshaus:**
- swissBUILDINGS3D Traufhoehe: 14.5m (= Arkaden-Hoehe!)
- Tatsaechliche Parlamentsfassade: 22-25m
- Kuppel: 62m

**Loesung:** Claude-Analyse erkennt automatisch Hoehenzonen bei komplexen Gebaeuden.

---

## Fuer Claude.ai

Bei Code-Fragen oder Analysen:
- **Technische Details:** Siehe `CLAUDE.md` (1800+ Zeilen)
- **API-Endpunkte:** Siehe `CLAUDE.md` -> "API-Endpunkte"
- **Datenquellen:** Siehe `CLAUDE.md` -> "Integrierte Datenquellen"
- **Status/Roadmap:** Siehe `CLAUDE.md` -> "Status"

Screenshots der App helfen bei der Analyse!

---

## Aktueller Stand (31.12.2025)

### Was funktioniert

| Feature | Status |
|---------|--------|
| SmartBuildingService (10-Schritte Pipeline) | Produktiv |
| Bekannte Gebaeude (known_buildings.py) | 10+ Gebaeude |
| Hoehen-Validierung (BUG-011/012) | Implementiert |
| Claude SVG-Generierung | Sonnet 4 |
| Request-Deduplizierung | Gefixt |
| On-Demand Hoehendaten (STAC API) | Funktioniert |

### Bekannte Bugs

| Bug | Prioritaet | Status |
|-----|-----------|--------|
| BUG-004: Einsteinhaus langsam | P1 | Offen |
| BUG-006: Nur 1-2 Zonen bei Unbekannten | P2 | Offen |
| FEATURE-001: Grundrissform-Erkennung | P2 | Geplant |

**Details:** Siehe `docs/roadmap/CURRENT_BUGS.md`

---

## Offene Punkte: geodaten-ch API

### P0 - Kritisch (blockiert Weiterentwicklung)

| Task | Beschreibung | Status |
|------|--------------|--------|
| **CI/CD Pipeline** | Automatische Tests + Deployment bei Push | ✅ Implementiert |
| **Tests** | Unit + Integration Tests für Backend | ✅ Basis vorhanden |
| **Prompt-Versionierung** | SVG-Prompts versioniert speichern | ❌ Fehlt |

### P1 - Wichtig

| Task | Beschreibung | Status |
|------|--------------|--------|
| **ML Learning System** | Feedback-Loop für SVG-Qualität | 🔜 Geplant |
| **SVG-Prompt Optimierung** | Iterative Verbesserung mit Claude | 🔄 Laufend |
| **Mehr bekannte Gebäude** | known_buildings.py erweitern | 🔄 Laufend |
| **BUG-004** | Einsteinhaus langsam (7.8s) | ❌ Offen |

### P2 - Nice to have

| Task | Beschreibung | Status |
|------|--------------|--------|
| **DXF/IFC Export** | CAD-Formate für 3D-Modellierung | 🔜 Geplant |
| **Grundrissform-Erkennung** | L/U/H-Form automatisch erkennen | 🔜 Geplant |
| **API Rate Limiting** | Schutz vor Überlastung | ❌ Fehlt |

**Details:** Siehe `docs/roadmap/CURRENT_BUGS.md` und `docs/roadmap/ML_LEARNING_SYSTEM.md`

---

## Naechstes Projekt: Geruestbau-App

**Status:** In Entwicklung auf Branch `feature/geruestbau-app`

### Dokumentation

| Dokument | Beschreibung |
|----------|--------------|
| [`CLAUDE_GERUESTBAU.md`](CLAUDE_GERUESTBAU.md) | CLAUDE.md Erweiterung für Gerüstbau-Modul |
| [`docs/geruestbau-app/GERUESTBAU_APP_SETUP.md`](docs/geruestbau-app/GERUESTBAU_APP_SETUP.md) | Vollständiges Setup-Guide für PWA |
| [`docs/geruestbau-app/QUICKSTART.md`](docs/geruestbau-app/QUICKSTART.md) | Schnellstart-Anleitung |
| [`../geruestbau_app_konzept.md`](docs/geruestbau_app_konzept.md) | Grobkonzept |

Die geodaten-ch API wird als Backend für eine vollständige Gerüstbau-App dienen.

### Module-Übersicht

| Modul | Beschreibung | geodaten-ch Integration |
|-------|--------------|------------------------|
| 1. Erfassung | PDF/Foto/simap.ch Import | - |
| 2. Geodaten | Automatische Anreicherung | ✅ SmartBuildingService |
| 3. Fotos | KI-Analyse Blickrichtung | ✅ Claude Vision |
| 4. Kontrolle | Daten-Validierung | ✅ Höhenzonen-Erkennung |
| 5. Fassaden | Interaktive Auswahl | ✅ Polygon + Zonen |
| 6. Editor | Gerüst-Konfiguration | ✅ NPK 114 Berechnung |
| 7. Material | Layher-Katalog | ✅ Materialliste |
| 8. Export | PDF/IFC/DXF/LayPLAN | 🔜 Geplant |

### Offene Punkte: Gerüstbau-App

| Task | Beschreibung | Priorität | Status |
|------|--------------|-----------|--------|
| **Projekt-Setup** | PWA im geodaten-ch Repo | P0 | ✅ Implementiert |
| **CI/CD Pipeline** | GitHub Actions für Tests + Deployment | P0 | ✅ Implementiert |
| **Auth/Multi-Tenant** | Benutzer-Verwaltung, Firmen-Trennung | P0 | ❌ Offen |
| **Projekt-DB Schema** | SQLite (später PostgreSQL) | P0 | ✅ Schema definiert |
| **PDF Offerte** | Template-basierte PDF-Generierung | P1 | ❌ Offen |
| **Foto-Upload** | S3/MinIO Integration | P1 | ❌ Offen |
| **IFC Export** | ifcopenshell Integration | P2 | ❌ Offen |
| **LayPLAN XML** | Export für Layher Software | P2 | ❌ Offen |
| **Mobile App** | PWA (kein React Native nötig) | P3 | ✅ PWA-Setup |

**Architektur:** Die Gerüstbau-App wird als PWA (`geruestbau-app/`) im geodaten-ch Repo entwickelt und nutzt die bestehende Backend-API.

**Tech Stack:**
- Frontend: React 18 + TypeScript + Vite + TailwindCSS
- State: Zustand
- PWA: vite-plugin-pwa
- Backend: Erweiterung des bestehenden FastAPI

### CI/CD Pipeline

Die GitHub Actions Pipeline (`.github/workflows/ci.yml`) testet alle 3 Komponenten parallel:

```
┌─────────────────────────────────────────────────────────────┐
│                    CI/CD PIPELINE                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Push/PR zu main                                            │
│       │                                                     │
│       ├──────────────┬──────────────┬──────────────┐       │
│       ▼              ▼              ▼              │       │
│  backend-test   frontend-test   geruestbau-test   │       │
│  (Python 3.11)  (Node 20)       (Node 20)         │       │
│  pytest         npm build       npm build+test    │       │
│       │              │              │              │       │
│       └──────────────┴──────────────┴──────────────┘       │
│                          │                                  │
│                          ▼                                  │
│                       deploy                                │
│                  (nur bei main push)                        │
│                  Railway.app Auto-Deploy                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Jobs:**

| Job | Runner | Schritte |
|-----|--------|----------|
| `backend-test` | ubuntu-latest | Python 3.11, pip install, pytest |
| `frontend-test` | ubuntu-latest | Node 20, npm ci, npm build |
| `geruestbau-test` | ubuntu-latest | Node 20, npm ci, npm build, npm test |
| `deploy` | ubuntu-latest | Railway.app (automatisch via GitHub Integration) |

### Ordnerstruktur

```
geodaten-ch/
├── .github/
│   └── workflows/
│       └── ci.yml              # CI/CD Pipeline
│
├── backend/                    # FastAPI + Python 3.11
│   ├── app/
│   │   ├── main.py
│   │   ├── models/
│   │   ├── routers/
│   │   │   └── geruestbau.py   # Gerüstbau-API Router
│   │   └── services/
│   │       ├── smart_building/
│   │       └── geruestbau/     # Gerüstbau-Service
│   └── tests/
│       └── test_geruestbau.py
│
├── frontend/                   # React + Vite (bestehend)
│   └── src/
│
├── geruestbau-app/             # Mobile-First PWA (NEU)
│   ├── src/
│   │   ├── api/                # API Client
│   │   ├── components/         # UI-Komponenten
│   │   ├── pages/              # Seiten
│   │   ├── stores/             # Zustand State
│   │   └── types/              # TypeScript Types
│   ├── package.json
│   ├── vite.config.ts
│   ├── Dockerfile
│   └── README.md
│
├── docs/
│   └── geruestbau-app/         # Setup-Guides
│
├── CLAUDE.md                   # Technische Dokumentation
├── CLAUDE_GERUESTBAU.md        # Gerüstbau-Erweiterung
└── PROJEKT_KONTEXT.md          # Projekt-Überblick
```

---

## ML Learning System (Konzept)

Ziel: Automatische Verbesserung der SVG-Qualität durch Feedback-Loop.

```
┌─────────────────────────────────────────────────────────────┐
│                    ML LEARNING SYSTEM                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. SVG generieren (Claude API)                             │
│       ↓                                                     │
│  2. User-Feedback sammeln (👍/👎, Korrekturen)              │
│       ↓                                                     │
│  3. Feedback + Prompt in DB speichern                       │
│       ↓                                                     │
│  4. Periodisch: Prompts analysieren, verbessern             │
│       ↓                                                     │
│  5. A/B Testing neuer Prompt-Versionen                      │
│       ↓                                                     │
│  6. Beste Version wird Default                              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Details:** Siehe `docs/roadmap/ML_LEARNING_SYSTEM.md`

---

## Letzte Aenderungen

| Datum | Aenderung |
|-------|----------|
| 2025-12-31 | **Gerüstbau-App**: Komplette PWA-Struktur implementiert |
| 2025-12-31 | **CI/CD**: GitHub Actions Pipeline für alle 3 Komponenten |
| 2025-12-31 | **Backend**: Gerüstbau-Router + Project-Service hinzugefügt |
| 2025-12-31 | **Tests**: test_geruestbau.py mit Projekt-Lifecycle Tests |
| 2025-12-31 | **Gerüstbau-App**: Branch `feature/geruestbau-app` erstellt |
| 2025-12-31 | **Gerüstbau-App**: PWA-Setup dokumentiert (docs/geruestbau-app/) |
| 2025-12-31 | CLAUDE_GERUESTBAU.md erstellt (CLAUDE.md Erweiterung) |
| 2025-12-31 | 4 SVG-Typen: Grundriss, Ansicht, Querschnitt, Längsschnitt |
| 2025-12-31 | SVG-Preloading für alle 4 Typen parallel |
| 2025-12-30 | BUG-011/012 Hoehen-Validierung implementiert |
| 2025-12-30 | known_buildings.py erweitert (10 Berner Gebaeude) |
| 2025-12-30 | CURRENT_BUGS.md mit Claude.ai Analyse-Bugs |
| 2025-12-29 | SmartBuildingService als zentraler Datensammler |
| 2025-12-29 | Frontend ruft /api/v1/smart-building/data direkt |
| 2025-12-29 | Dokumentation konsolidiert |
| 2025-12-28 | Claude API SVG-Generierung mit Zonen |
| 2025-12-28 | Terrain-Integration (swissALTI3D) |
