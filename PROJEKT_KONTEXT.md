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

### Roadmap

1. **Naechster Schritt:** Dokumentation korrigieren (Haiku->Sonnet)
2. **Geplant:** ML Learning System fuer automatische Zonen-Erkennung
3. **Langfristig:** DXF/IFC-Export fuer 3D-Modellierung

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
