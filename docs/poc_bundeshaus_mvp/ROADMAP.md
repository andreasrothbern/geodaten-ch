# ROADMAP.md - Entwicklungsplan Geodaten Schweiz

> **Version:** 2.0
> **Datum:** 24.12.2025

## Vision

Eine Hybrid-Lösung für professionelle Gerüstplanung in der Schweiz:
- **Präzise Geodaten** aus offiziellen Schweizer Quellen
- **Intelligente Gebäude-Analyse** mit Claude AI
- **Professionelle Planungsunterlagen** (SVG, DXF, PDF)
- **Vollständiger Workflow** von Ausschreibung bis Abrechnung

---

## Aktueller Stand

### Was funktioniert ✅
- Adresssuche → Gebäudedaten (GWR)
- Grundriss aus geodienste.ch WFS
- Höhen aus swissBUILDINGS3D (On-Demand)
- Basis-SVG (Grundriss, Schnitt, Ansicht)
- NPK 114 Ausmass-Berechnung
- Material-Schätzung (Layher Blitz 70)

### Was fehlt ❌
- Höhenzonen für komplexe Gebäude
- Terrain-Daten für Hanglagen
- Professionelle SVG-Grafiken
- Ständer, Verankerungen, Zugänge in Grafiken
- DXF/PDF Export

---

## Ziel-Architektur

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         GEODATEN-CH ARCHITEKTUR                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  DATENQUELLEN (extern)                                            │ │
│  │  ─────────────────────────────────────────────────────────────── │ │
│  │  • swisstopo API (GWR, Geocoding)                                │ │
│  │  • geodienste.ch WFS (Gebäudepolygone)                           │ │
│  │  • swissBUILDINGS3D (Höhendaten)                                 │ │
│  │  • swissALTI3D (Terrain) [NEU]                                   │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                              ▼                                         │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  BACKEND (FastAPI)                                                │ │
│  │  ─────────────────────────────────────────────────────────────── │ │
│  │                                                                   │ │
│  │  Services:                                                        │ │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                 │ │
│  │  │ Geodaten    │ │ Kontext     │ │ Berechnung  │                 │ │
│  │  │ Aggregator  │ │ Analyzer    │ │ Engine      │                 │ │
│  │  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘                 │ │
│  │         │               │               │                         │ │
│  │  ┌──────▼───────────────▼───────────────▼──────┐                 │ │
│  │  │              BUILDING CONTEXT                │ ◄── Claude API │ │
│  │  │  (Zonen, Höhen, Typen, Terrain)             │                 │ │
│  │  └──────────────────────┬──────────────────────┘                 │ │
│  │                         │                                         │ │
│  │  ┌──────────────────────▼──────────────────────┐                 │ │
│  │  │              SVG/DXF/PDF GENERATOR          │                 │ │
│  │  │  (Grundriss, Schnitt, Ansicht)              │                 │ │
│  │  └─────────────────────────────────────────────┘                 │ │
│  │                                                                   │ │
│  │  Datenbanken:                                                     │ │
│  │  • building_heights.db (Höhen)                                   │ │
│  │  • building_contexts.db (Zonen) [NEU]                            │ │
│  │  • layher_catalog.db (Material)                                  │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                              ▼                                         │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  FRONTEND (React)                                                 │ │
│  │  ─────────────────────────────────────────────────────────────── │ │
│  │  • Adresssuche                                                   │ │
│  │  • Zonen-Editor [NEU]                                            │ │
│  │  • Interaktive SVGs                                              │ │
│  │  • Export-Funktionen                                              │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Geodaten & SVG Verbesserung

**Ziel:** Professionelle Planungsunterlagen auch für komplexe Gebäude

**Zeitrahmen:** 6-8 Wochen

### 1.1 Building Context System (Priorität: HOCH)

Das Kernstück für professionelle Grafiken.

**Problem:** 1 Polygon + 1 Höhe reicht nicht für komplexe Gebäude.

**Lösung:** Zonen-System mit automatischer/manueller Analyse.

| Task | Beschreibung | Aufwand |
|------|--------------|---------|
| 1.1.1 | Datenmodell `BuildingContext` | 1 Tag |
| 1.1.2 | SQLite Schema `building_contexts` | 0.5 Tag |
| 1.1.3 | Komplexitäts-Erkennung | 1 Tag |
| 1.1.4 | Auto-Context für einfache Gebäude | 1 Tag |
| 1.1.5 | Claude API Integration | 2 Tage |
| 1.1.6 | Analyse-Prompt optimieren | 1 Tag |
| 1.1.7 | API Endpunkte (GET/POST/PUT) | 1 Tag |
| 1.1.8 | Tests | 1 Tag |

**Dokumentation:** `docs/BUILDING_CONTEXT.md`

### 1.2 swissALTI3D Integration (Priorität: MITTEL)

Terrain-Daten für Hanglagen.

| Task | Beschreibung | Aufwand |
|------|--------------|---------|
| 1.2.1 | STAC API Client | 1 Tag |
| 1.2.2 | GeoTIFF Parser (rasterio) | 1 Tag |
| 1.2.3 | Terrain-Höhe pro Koordinate | 0.5 Tag |
| 1.2.4 | Terrain-Profil für Polygon-Ecken | 0.5 Tag |
| 1.2.5 | Caching-Strategie | 1 Tag |
| 1.2.6 | API Endpunkt `/api/v1/terrain` | 0.5 Tag |

### 1.3 Professionelle SVG-Generierung (Priorität: HOCH)

Druckfähige Planungsunterlagen.

**Dokumentation:** `docs/SVG_SPEC.md`

| Task | Beschreibung | Aufwand |
|------|--------------|---------|
| 1.3.1 | SVG-Templates mit Struktur | 2 Tage |
| 1.3.2 | Zonen-Darstellung (farbcodiert) | 1 Tag |
| 1.3.3 | Ständer-Positionen berechnen | 1 Tag |
| 1.3.4 | Verankerungs-Raster (4m × 4m) | 1 Tag |
| 1.3.5 | Zugänge markieren | 0.5 Tag |
| 1.3.6 | Masslinien mit Pfeilen | 1 Tag |
| 1.3.7 | Lagen-Beschriftung (Ansicht) | 0.5 Tag |
| 1.3.8 | Nordpfeil, Legende, Massstab | 1 Tag |
| 1.3.9 | Terrain-Profil im Schnitt | 1 Tag |

### 1.4 Export-Funktionen (Priorität: MITTEL)

| Task | Beschreibung | Aufwand |
|------|--------------|---------|
| 1.4.1 | PDF-Export (CairoSVG) | 1 Tag |
| 1.4.2 | DXF-Export (ezdxf) | 2 Tage |
| 1.4.3 | Layer-Struktur für DXF | 0.5 Tag |

### 1.5 Frontend Zonen-Editor (Priorität: HOCH)

| Task | Beschreibung | Aufwand |
|------|--------------|---------|
| 1.5.1 | Zonen-Overlay auf Grundriss | 1 Tag |
| 1.5.2 | Zonen-Panel (Liste) | 1 Tag |
| 1.5.3 | Höhen-Editor pro Zone | 0.5 Tag |
| 1.5.4 | "Analysieren" Button | 0.5 Tag |
| 1.5.5 | "Bestätigen" Workflow | 0.5 Tag |

---

## Phase 2: Claude Integration

**Ziel:** Claude kann Ausschreibungen interpretieren und Offerten erstellen

**Zeitrahmen:** 3-4 Wochen

### 2.1 MCP-Server

Model Context Protocol für Claude Desktop/API.

| Task | Beschreibung | Aufwand |
|------|--------------|---------|
| 2.1.1 | MCP Server Grundstruktur | 1 Tag |
| 2.1.2 | Tool: `get_building_data` | 0.5 Tag |
| 2.1.3 | Tool: `get_building_context` | 0.5 Tag |
| 2.1.4 | Tool: `calculate_scaffolding` | 0.5 Tag |
| 2.1.5 | Tool: `get_svg_*` | 1 Tag |
| 2.1.6 | Resource: Layher Katalog | 0.5 Tag |
| 2.1.7 | Resource: NPK 114 Regeln | 0.5 Tag |
| 2.1.8 | Deployment | 1 Tag |

### 2.2 Claude-Projekt Setup

| Task | Beschreibung | Aufwand |
|------|--------------|---------|
| 2.2.1 | Projekt-Kontext (KONTEXT.md) | 1 Tag |
| 2.2.2 | Offerten-Vorlage | 0.5 Tag |
| 2.2.3 | Beispiel-Workflows | 0.5 Tag |
| 2.2.4 | MCP-Verbindung testen | 0.5 Tag |

### 2.3 Offerten-Workflow

| Task | Beschreibung | Aufwand |
|------|--------------|---------|
| 2.3.1 | Ausschreibungs-Parser | 2 Tage |
| 2.3.2 | Offerten-Generator | 2 Tage |
| 2.3.3 | DOCX-Export | 1 Tag |
| 2.3.4 | End-to-End Tests | 1 Tag |

---

## Phase 3: Projektverwaltung

**Ziel:** Vollständiger Workflow von Ausschreibung bis Abrechnung

**Zeitrahmen:** 6-8 Wochen

### 3.1 Datenbank-Erweiterung

| Task | Beschreibung | Aufwand |
|------|--------------|---------|
| 3.1.1 | PostgreSQL Setup | 1 Tag |
| 3.1.2 | Schema: Projekte | 1 Tag |
| 3.1.3 | Schema: Kunden | 0.5 Tag |
| 3.1.4 | Schema: Dokumente | 0.5 Tag |
| 3.1.5 | Schema: Material | 1 Tag |
| 3.1.6 | Schema: Personal | 0.5 Tag |

### 3.2 Workflow-Engine

| Task | Beschreibung | Aufwand |
|------|--------------|---------|
| 3.2.1 | Status-Workflow | 2 Tage |
| 3.2.2 | Benachrichtigungen | 1 Tag |
| 3.2.3 | Dokument-Versionierung | 1 Tag |

### 3.3 Frontend-Erweiterung

| Task | Beschreibung | Aufwand |
|------|--------------|---------|
| 3.3.1 | Dashboard | 2 Tage |
| 3.3.2 | Projektliste | 1 Tag |
| 3.3.3 | Projektdetail | 2 Tage |
| 3.3.4 | Offerten-Editor | 2 Tage |
| 3.3.5 | Kalender | 2 Tage |
| 3.3.6 | Benutzer-Auth | 2 Tage |

---

## PoC: Building Context System

**Erstes Ziel:** Bundeshaus Bern korrekt darstellen

### PoC Scope

1. **Kontext-Erstellung für Bundeshaus**
   - Claude analysiert das Polygon
   - Zonen: Arkaden, Parlament, Türme, Kuppel
   - Höhen pro Zone

2. **SVG mit Zonen**
   - Grundriss mit farbcodierten Zonen
   - Schnitt mit unterschiedlichen Höhen
   - Ansicht mit korrekter Höhe pro Fassade

3. **Frontend-Anzeige**
   - Zonen-Liste anzeigen
   - Manuell korrigierbar

### PoC Nicht-Scope

- Terrain-Integration (Phase 1.2)
- DXF-Export (Phase 1.4)
- MCP-Server (Phase 2)
- Projektverwaltung (Phase 3)

### PoC Timeline

| Tag | Aufgabe |
|-----|---------|
| 1 | Datenmodell + SQLite Schema |
| 2 | Auto-Context für einfache Gebäude |
| 3 | Claude API Integration |
| 4 | Analyse-Prompt optimieren |
| 5 | API Endpunkte |
| 6 | SVG-Generator erweitern |
| 7 | Frontend Zonen-Anzeige |
| 8 | Tests + Bugfixes |

---

## Meilensteine

| Meilenstein | Datum | Kriterium |
|-------------|-------|-----------|
| **M0: PoC** | +2 Wochen | Bundeshaus mit Zonen darstellbar |
| **M1: Context System** | +4 Wochen | Beliebige Gebäude analysierbar |
| **M2: SVG 2.0** | +6 Wochen | Professionelle, druckfähige Grafiken |
| **M3: Terrain** | +8 Wochen | Hanglagen-Berechnung funktioniert |
| **M4: MCP-Server** | +10 Wochen | Claude kann Geodaten abrufen |
| **M5: Offerten** | +12 Wochen | Ausschreibung → Offerte Workflow |
| **M6: Projektverwaltung** | +18 Wochen | Vollständiger Workflow |

---

## Risiken

| Risiko | Wahrsch. | Impact | Mitigation |
|--------|----------|--------|------------|
| Claude-Analyse ungenau | Mittel | Hoch | User-Validierung, Fallback auf manuell |
| swissALTI3D Zugang | Niedrig | Mittel | Fallback auf Schätzung |
| API-Kosten Claude | Mittel | Niedrig | Caching, nur bei Bedarf |
| Komplexe Gebäude | Hoch | Mittel | Immer manuelle Korrektur ermöglichen |

---

## Technologie-Stack

| Komponente | Technologie |
|------------|-------------|
| Backend | FastAPI + Python 3.11 |
| Datenbank | SQLite (→ PostgreSQL in Phase 3) |
| Frontend | React + Vite + TypeScript + Tailwind |
| SVG | Python (svgwrite oder Template) |
| DXF | ezdxf |
| PDF | CairoSVG oder WeasyPrint |
| AI | Anthropic Claude API (Sonnet) |
| MCP | Python mcp-sdk |
| Hosting | Railway.app |

---

## Dokumentation

| Dokument | Inhalt |
|----------|--------|
| `CLAUDE.md` | Projekt-Kontext für Claude Code |
| `ROADMAP.md` | Dieser Entwicklungsplan |
| `SVG_SPEC.md` | Spezifikation für professionelle Grafiken |
| `BUILDING_CONTEXT.md` | Gebäude-Kontext-System Architektur |
| `README.md` | Projekt-Übersicht und API-Doku |

---

## Nächste Schritte

1. **Sofort:** PoC für Building Context starten
2. **Diese Woche:** Datenmodell + Claude-Integration
3. **Nächste Woche:** SVG-Generator erweitern
4. **Danach:** Frontend Zonen-Editor

---

*Letzte Aktualisierung: 24.12.2025*
