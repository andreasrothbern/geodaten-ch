# PROJEKT_KONTEXT.md
# Gerüstplanung Schweiz - Projekt-Überblick
# ==========================================
# Diese Datei ist für Claude.ai als Project Knowledge gedacht.
# Für technische Details: siehe CLAUDE.md

## Aktuelles Projekt

**Anwendung:** Geodaten Schweiz - Gerüstbau-Modul
**Status:** Produktiv auf Railway.app

**App-URLs:**
- Frontend: https://cooperative-commitment-production.up.railway.app/
- Backend API: https://acceptable-trust-production.up.railway.app/
- Beispiel: `?address=Bundesplatz%203,%203011%20Bern`

---

## Was die App macht

Eine Web-Anwendung für Gerüstplanung in der Schweiz, die automatisch:

1. **Gebäudedaten sammelt** (Adresse, EGID, Geschosse, Baujahr)
2. **Gebäudegeometrie abruft** (Polygon aus amtlicher Vermessung)
3. **Höhendaten ermittelt** (gemessen oder geschätzt)
4. **Terrain-Höhen berechnet** (m ü.M.)
5. **SVG-Visualisierungen generiert** (Grundriss, Ansicht, Schnitt)
6. **Gerüst-Ausmass berechnet** (NPK 114 konform)
7. **Material schätzt** (Layher Blitz 70)

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
├── 7. Gebäude-Recherche (Claude)
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

## Bekanntes Problem: Höhenzonen

**Problem:** swissBUILDINGS3D liefert nur EINE globale Höhe pro Gebäude.

**Beispiel Bundeshaus:**
- swissBUILDINGS3D Traufhöhe: 14.5m (= Arkaden-Höhe!)
- Tatsächliche Parlamentsfassade: 22-25m
- Kuppel: 62m

**Lösung:** Claude-Analyse erkennt automatisch Höhenzonen bei komplexen Gebäuden.

---

## Für Claude.ai

Bei Code-Fragen oder Analysen:
- **Technische Details:** Siehe `CLAUDE.md` (1800+ Zeilen)
- **API-Endpunkte:** Siehe `CLAUDE.md` → "API-Endpunkte"
- **Datenquellen:** Siehe `CLAUDE.md` → "Integrierte Datenquellen"
- **Status/Roadmap:** Siehe `CLAUDE.md` → "Status"

Screenshots der App helfen bei der Analyse!

---

## Letzte Änderungen

| Datum | Änderung |
|-------|----------|
| 2025-12-29 | SmartBuildingService als zentraler Datensammler |
| 2025-12-29 | Frontend ruft /api/v1/smart-building/data direkt |
| 2025-12-29 | Dokumentation konsolidiert |
| 2025-12-28 | Claude API SVG-Generierung mit Zonen |
| 2025-12-28 | Terrain-Integration (swissALTI3D) |
