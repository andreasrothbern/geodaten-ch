# PROJEKT_KONTEXT.md

> **Gerüstplanung Schweiz - Projekt-Überblick**
> Diese Datei ist für Claude.ai und Claude Code gedacht, um bei Session-Wechseln den aktuellen Stand zu kennen.

---

## Aktuelles Projekt

**Anwendung:** Geodaten Schweiz - Gerüstbau-Modul
**Status:** Produktiv auf Railway.app
**Version:** 3.0 (SmartBuildingService)

**App-URLs:**
- Frontend: https://cooperative-commitment-production.up.railway.app/
- Backend API: https://acceptable-trust-production.up.railway.app/
- Beispiel: `?address=Bundesplatz%203,%203011%20Bern`

---

## Aktueller Stand (30.12.2025)

### ✅ Was funktioniert

| Feature | Status | Details |
|---------|--------|---------|
| SmartBuildingService | ✅ | 10-Schritte Pipeline |
| SVG-Generierung | ✅ | Claude Sonnet API |
| Batch-Test 10 Gebäude | ✅ | 100% Erkennungsrate, 299ms avg |
| known_buildings.py | ✅ | Bundeshaus, Münster, St. Peter, Zytglogge |
| On-Demand Höhendaten | ✅ | STAC API für alle CH-Gebäude |
| Bundle-Cache | ✅ | 24h TTL in SQLite |
| SVG-Cache | ✅ | Versioniert, invalidierbar |

### 🔴 Bekannte Bugs

| Bug | Datei | Priorität | Status |
|-----|-------|-----------|--------|
| Einsteinhaus Zone 16m statt 26m | `known_buildings.py` | P1 | 🔴 Offen |
| Kunstmuseum API-Höhe 7.9m falsch | swissBUILDINGS3D | P2 | 🟡 API-Problem |
| Bundeshaus U-Form fehlt | Prompt | P3 | 🟢 Nice-to-have |

### 🔨 In Arbeit

- [ ] Recherche-Optimierung: Validierung Zone vs. API-Höhen
- [ ] Dokumentation: formatting.md Rules erstellen

---

## Datenfluss

```
Adresse eingeben
      │
      ▼
SmartBuildingService (10 Schritte)
├── 1. Geocoding (swisstopo)
├── 2. GWR-Daten (Geschosse, Fläche)
├── 3. Höhendaten (swissBUILDINGS3D)
├── 4. Terrain (swissALTI3D)
├── 5. Polygon (geodienste.ch)
├── 6. Dach-Analyse
├── 7. Gebäude-Recherche (Claude Sonnet)
├── 8. Zonen-Analyse (bei komplexen)
├── 9. Zugangspunkte (SUVA)
└── 10. Qualitätsbewertung
      │
      ▼
BuildingDataBundle (24h gecacht)
      │
      ├──► Frontend-Anzeige
      └──► SVG-Generierung (Claude API)
```

---

## Roadmap

### Diese Woche (KW1 2025)

- [ ] Einsteinhaus-Zone korrigieren (5 Min)
- [ ] formatting.md Rules erstellen
- [ ] Höhen-Validierung implementieren

### Nächste Woche (KW2 2025)

- [ ] Polygon-Form-Analyse (U/L/H erkennen)
- [ ] Ehrenhof-Daten für Bundeshaus
- [ ] PROJEKT_KONTEXT.md automatisch aktualisieren

### Später (Q1 2025)

- [ ] ML Learning System
- [ ] DXF/IFC-Export
- [ ] Sonnendach-Import (BFE-Daten)

---

## Architektur-Entscheidungen

| Datum | Entscheidung | Grund |
|-------|--------------|-------|
| 29.12.2025 | SmartBuildingService statt separate Services | Einheitlicher Cache, weniger API-Calls |
| 30.12.2025 | known_buildings.py für bekannte Gebäude | Performance + Kosten sparen |
| 30.12.2025 | Claude Sonnet statt Haiku für Recherche | Bessere Qualität bei Zonen-Erkennung |
| 30.12.2025 | ASCII statt UTF-8 in Prompts | Encoding-Probleme vermeiden |

---

## Letzte Änderungen

| Datum | Änderung |
|-------|----------|
| 30.12.2025 | Batch-Test: 10/10 Gebäude erkannt (299ms avg) |
| 30.12.2025 | known_buildings.py: 5 Gebäude mit korrekten Zonen |
| 30.12.2025 | SVG-Analyse: Claude.ai vs. API Vergleich |
| 30.12.2025 | Dokumentation: Rules-Dateien erstellt |
| 29.12.2025 | SmartBuildingService als zentraler Datensammler |
| 29.12.2025 | Frontend ruft /api/v1/smart-building/data direkt |
| 28.12.2025 | Claude API SVG-Generierung mit Zonen |
| 28.12.2025 | Terrain-Integration (swissALTI3D) |

---

## Performance-Metriken

| Metrik | Wert | Datum |
|--------|------|-------|
| Batch-Test (10 Gebäude) | 2'986ms total | 30.12.2025 |
| Durchschnitt pro Gebäude | 299ms | 30.12.2025 |
| Erkennungsrate | 100% (10/10) | 30.12.2025 |
| SVG-Generierung | ~2-5s (Claude API) | 30.12.2025 |

---

## Für Claude.ai / Claude Code

Bei Code-Fragen oder Analysen:
- **Technische Details:** Siehe `CLAUDE.md`
- **Rules:** Siehe `.claude/rules/`
- **API-Endpunkte:** Siehe `CLAUDE.md` → "API-Endpunkte"
- **Bugs:** Siehe oben → "Bekannte Bugs"

### Wichtige Dateien

```
backend/app/services/smart_building/
├── service.py               # Orchestrierung (10 Schritte)
├── known_buildings.py       # Bekannte Gebäude mit Zonen
├── prompt_generator.py      # SVG-Prompt Aufbau
└── research_integration.py  # Kirchen-Zonen Integration
```

### Quick-Fixes

**Einsteinhaus Zone korrigieren:**
```python
# In known_buildings.py, Zone ändern:
"traufe": 22.0,  # war 12.0
"first": 26.0,   # war 16.0
```

---

*Letzte Aktualisierung: 30.12.2025*
