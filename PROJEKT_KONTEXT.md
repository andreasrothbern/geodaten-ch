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

## Aktueller Stand (30.12.2025)

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
| **CI/CD Pipeline** | Automatische Tests + Deployment bei Push | ❌ Fehlt |
| **Tests** | Unit + Integration Tests für Backend | ❌ Fehlt |
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

**Konzept:** [`../geruestbau_app_konzept.md`](../geruestbau_app_konzept.md)

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

| Task | Beschreibung | Priorität |
|------|--------------|-----------|
| **Projekt-Setup** | Neues Repo, Tech Stack definieren | P0 |
| **Auth/Multi-Tenant** | Benutzer-Verwaltung, Firmen-Trennung | P0 |
| **Projekt-DB Schema** | PostgreSQL + PostGIS Setup | P0 |
| **CI/CD Pipeline** | Tests + Deployment | P0 |
| **PDF Offerte** | Template-basierte PDF-Generierung | P1 |
| **Foto-Upload** | S3/MinIO Integration | P1 |
| **IFC Export** | ifcopenshell Integration | P2 |
| **LayPLAN XML** | Export für Layher Software | P2 |
| **Mobile App** | React Native iOS/Android | P3 |

**Architektur:** geodaten-ch bleibt als API-Service, die Gerüstbau-App wird ein separates Frontend mit eigener Projekt-Datenbank.

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
| 2025-12-30 | BUG-011/012 Hoehen-Validierung implementiert |
| 2025-12-30 | known_buildings.py erweitert (10 Berner Gebaeude) |
| 2025-12-30 | CURRENT_BUGS.md mit Claude.ai Analyse-Bugs |
| 2025-12-29 | SmartBuildingService als zentraler Datensammler |
| 2025-12-29 | Frontend ruft /api/v1/smart-building/data direkt |
| 2025-12-29 | Dokumentation konsolidiert |
| 2025-12-28 | Claude API SVG-Generierung mit Zonen |
| 2025-12-28 | Terrain-Integration (swissALTI3D) |
