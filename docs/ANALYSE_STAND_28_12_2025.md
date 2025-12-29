# Analyse: Aktuelle Datenlage und Workflow
**Stand: 28.12.2025**

## 1. Übersicht der implementierten Services

### Datenquellen (Backend)

| Service | Datei | Quelle | Daten |
|---------|-------|--------|-------|
| **SwisstopoService** | `swisstopo.py` | api3.geo.admin.ch | Geocoding, GWR-Daten, Gebäude-Identify |
| **GeodiensteService** | `geodienste.py` | geodienste.ch | Gebäudegeometrie (Polygon) |
| **TerrainService** | `terrain.py` | api3.geo.admin.ch | Geländehöhe (m ü.M.) |
| **HeightDB** | `height_db.py` | swissBUILDINGS3D (lokal) | Trauf-/First-/Gebäudehöhe |
| **RoofService** | `roof.py` | Berechnet | Dachneigung, Dachform, Ausrichtung |
| **OrthofotoService** | `orthofoto.py` | wms.geo.admin.ch | Luftbilder (Base64) |
| **BuildingContextService** | `building_context.py` | Claude API | Zonen-Analyse |
| **BuildingHintsService** | `building_hints.py` | Statisch | Bekannte Gebäude |

---

## 2. Verfügbare Daten pro Gebäude

### 2.1 Basis-Daten (immer verfügbar)

| Feld | Quelle | Beispiel Bundeshaus |
|------|--------|---------------------|
| Adresse | swisstopo Geocoding | Bundesplatz 3, 3011 Bern |
| Koordinaten (LV95) | swisstopo | E=2600450, N=1199830 |
| EGID | swisstopo/GWR | 2242547 |
| Geschosse | GWR (gastw) | 4 |
| Gebäudekategorie | GWR (gkat) | 1040 |
| Gebäudefläche | GWR (garea) | ~4200 m² |
| Baujahr | GWR (gbauj) | 1902 |

### 2.2 Geometrie-Daten

| Feld | Quelle | Beispiel |
|------|--------|----------|
| Polygon | geodienste.ch WFS | 26 Punkte |
| Seitenlängen | Berechnet aus Polygon | [45.2, 38.7, 32.1, ...] |
| Umfang | Berechnet | 285.4 m |
| Fläche (Polygon) | Berechnet | ~4200 m² |

### 2.3 Höhen-Daten

| Feld | Quelle | Beispiel Bundeshaus | Status |
|------|--------|---------------------|--------|
| Traufhöhe | swissBUILDINGS3D | 14.53 m | ✅ Verfügbar |
| Firsthöhe | swissBUILDINGS3D | 62.57 m | ✅ Verfügbar |
| Gebäudehöhe | swissBUILDINGS3D | 62.57 m | ✅ Verfügbar |
| **Terrain-Höhe** | swissALTI3D | 543.1 m ü.M. | ✅ **Angezeigt in Frontend** |
| Terrain min/max | swissALTI3D Profil | - | ⚠️ Geplant (4-Eckpunkte) |

### 2.4 Dach-Daten (Option C - Heuristisch)

| Feld | Quelle | Beispiel EFH | Status |
|------|--------|--------------|--------|
| Dachneigung | Berechnet | 31° | ✅ Berechnet + **Angezeigt** |
| Dachform | Klassifiziert | Satteldach | ✅ Berechnet + **Angezeigt** |
| Dachausrichtung | Aus Polygon | O-W | ✅ Berechnet + **Angezeigt** |
| First-Azimut | Berechnet | 90° | ✅ Berechnet |
| Dachfläche | Geschätzt | 153.9 m² | ✅ Berechnet + **Angezeigt** |
| **Anzeige im Frontend** | - | - | ✅ **Implementiert (29.12.2025)** |

### 2.5 Zonen-Daten (Komplexe Gebäude)

| Feld | Quelle | Beispiel Bundeshaus |
|------|--------|---------------------|
| Anzahl Zonen | Claude-Analyse | 3 |
| Zone 1 | Arkaden | 6m, typ=arkade |
| Zone 2 | Hauptgebäude | 25m, typ=hauptgebaeude |
| Zone 3 | Kuppel | 64m, typ=kuppel, sonderkonstruktion=true |
| Orthofoto-Analyse | Claude Vision | roof_features, courtyards, etc. |

---

## 3. Vergleich: test_improved_prompts.py vs. building_hints.py

### Münsterplatz 1 (Berner Münster)

| Aspekt | test_improved_prompts.py | building_hints.py | Match |
|--------|--------------------------|-------------------|-------|
| Pattern | `"Münsterplatz" in address` | `r"Münsterplatz\s*1"` | ✅ (strenger) |
| EGID | Nicht geprüft | 1230337 | ✅ Hinzugefügt |
| Name | Berner Münster (Gotische Kathedrale) | Identisch | ✅ |
| Hints | Identischer Text | Identisch | ✅ |
| Zonen | 3 (Kirchenschiff, Seitenkapellen, Turm) | Identisch | ✅ |
| Orthofoto | Nicht spezifiziert | `requires_orthofoto: True` | ✅ Hinzugefügt |

### Rathausgasse 2 (St. Peter & Paul)

| Aspekt | test_improved_prompts.py | building_hints.py | Match |
|--------|--------------------------|-------------------|-------|
| Pattern | `"Rathausgasse" in address and "2" in address` | `r"Rathausgasse\s*2"` | ✅ |
| EGID | Nicht geprüft | 191821074 | ✅ Hinzugefügt |
| Hints | Identisch | Identisch | ✅ |

### Bundesplatz 3 (Bundeshaus)

| Aspekt | test_improved_prompts.py | building_hints.py | Match |
|--------|--------------------------|-------------------|-------|
| Pattern | `"Bundesplatz" in address` | `r"Bundesplatz\s*3"` | ✅ |
| EGID | 2242547 | 2242547 | ✅ |
| Hints | Identisch | Identisch | ✅ |

**Fazit:** Alle Daten wurden korrekt übertragen, mit zusätzlichen Verbesserungen (EGID-Lookup, Orthofoto-Flag).

---

## 4. Fehlende Daten / Nicht angezeigte Daten

### 4.1 Terrain-Höhe (Hanglage-Erkennung)

**Status:** ✅ Implementiert, ✅ **Angezeigt (29.12.2025)**

```python
# Backend: terrain.py
height = await terrain_service.get_height(e, n)
# -> 543.1 (m ü.M.)

# Im Scaffolding-Response:
response["address"]["terrain"] = {
    "terrain_height_m": 543.1,
    "min_terrain_m": ...,
    "max_terrain_m": ...,
    "terrain_slope_m": ...  # Hanglage-Erkennung
}
```

**Implementiert:**
- ✅ Terrain-Höhe im Frontend angezeigt (Adresse-Sektion)
- ✅ Hanglage-Warnung bei >1m Differenz
- ✅ An Claude-API übergeben für komplexe Gebäude
- ⚠️ Terrain-Profil um 4 Eckpunkte: Geplant

### 4.2 Dach-Daten (Neigung, Form, Ausrichtung)

**Status:** ✅ Berechnet (roof.py), ✅ **Angezeigt (29.12.2025)**

```python
# Backend: roof.py
roof_data = roof_service.calculate(...)
# -> RoofData(
#      roof_type=SATTELDACH,
#      roof_angle_deg=31.0,
#      roof_orientation="O-W",
#      ...
#    )

# Im Scaffolding-Response:
response["roof"] = roof_data.to_dict()
```

**Implementiert:**
- ✅ Dachform mit Icon im Frontend
- ✅ Dachneigung in Grad
- ✅ First-Ausrichtung (O-W, N-S)
- ✅ Dachfläche in m²
- ✅ Konfidenz-Anzeige (bei <50% gelbe Warnung)
- ✅ An Claude-Prompt übergeben

---

## 5. Beispiel-Gebäude für Hanglage

### Potentielle Test-Adressen (Bern)

| Adresse | Erwartete Hanglage | Bemerkung |
|---------|-------------------|-----------|
| Münsterplattform 1, 3011 Bern | Stark (Aare-Hang) | Neben Münster |
| Junkerngasse 47, 3011 Bern | Mittel | Altstadt-Hang |
| Schänzlistrasse 5, 3013 Bern | Mittel | Länggasse-Hang |
| Neubrückstrasse 10, 3012 Bern | Stark | Lorraine-Hang |
| Dalmaziquai 12, 3005 Bern | Stark | Marzili-Hang |

### Potentielle Test-Adressen (Schweiz)

| Adresse | Erwartete Hanglage | Bemerkung |
|---------|-------------------|-----------|
| Seestrasse 100, 8002 Zürich | Mittel | Zürichberg |
| Via Centrale 1, 6900 Lugano | Stark | Tessin-Hang |
| Rue du Petit-Chêne 18, 1003 Lausanne | Stark | Lausanne-Hang |
| Spalenvorstadt 2, 4051 Basel | Flach | Referenz |

---

## 6. Workflow-Analyse: Gerüstbauer-Projektleiter

### Aktueller Flow (Was funktioniert)

```
1. Adresse eingeben
   ↓
2. Gebäude-Daten abrufen
   - Polygon ✅
   - Höhen (Traufe/First) ✅
   - GWR-Daten ✅
   ↓
3. Komplexität erkennen
   - Einfach → Auto-Context
   - Komplex → Claude-Analyse (mit Orthofoto)
   ↓
4. Gerüstfläche berechnen (NPK 114)
   - Fassadenflächen ✅
   - Ecken-Zuschläge ✅
   ↓
5. Material schätzen (Layher Blitz 70)
   - Rahmen, Riegel, Beläge ✅
   ↓
6. SVG-Visualisierung
   - Grundriss ✅
   - Schnitt ✅ (Professional Mode)
   - Ansicht ✅ (Professional Mode)
```

### Fehlende Workflow-Schritte

```
❌ Hanglage-Erkennung
   - Terrain-Profil um Gebäude
   - Höhenunterschied min/max
   - Ausgleichs-Berechnung

❌ Dach-Analyse für Solar
   - Dachneigung anzeigen
   - Ausrichtung (Süd optimal)
   - Fläche pro Dachseite

❌ Zufahrt/Logistik
   - Strassenbreite
   - Kranstellplatz
   - Materialablage

❌ Nachbargebäude
   - Abstände prüfen
   - Überstand-Genehmigung

❌ Offert-Generierung
   - Positionen aus NPK 114
   - Preise aus Katalog
   - PDF-Export
```

---

## 7. Daten-Matrix: Was haben wir, was fehlt?

| Kategorie | Daten | Quelle | Implementiert | Angezeigt | Für Gerüstbau |
|-----------|-------|--------|---------------|-----------|---------------|
| **Basis** | Adresse | swisstopo | ✅ | ✅ | Info |
| | EGID | GWR | ✅ | ✅ | Referenz |
| | Koordinaten | swisstopo | ✅ | ✅ | Planung |
| **Geometrie** | Polygon | geodienste.ch | ✅ | ✅ | Fassaden |
| | Seitenlängen | Berechnet | ✅ | ✅ | Feldaufteilung |
| | Umfang | Berechnet | ✅ | ✅ | Gerüstmenge |
| **Höhen** | Traufhöhe | swissBUILDINGS3D | ✅ | ✅ | Gerüsthöhe |
| | Firsthöhe | swissBUILDINGS3D | ✅ | ✅ | Dacharbeiten |
| | **Terrain** | swissALTI3D | ✅ | ✅ | **Hanglage** |
| **Dach** | Neigung | Berechnet | ✅ | ✅ | **Solar/Dach** |
| | Form | Klassifiziert | ✅ | ✅ | **Gerüstform** |
| | Ausrichtung | Berechnet | ✅ | ✅ | **Solar** |
| **Zonen** | Komplexität | Erkannt | ✅ | ✅ | Multi-Zone |
| | Zonen-Liste | Claude | ✅ | ✅ | Teilbereiche |
| | Orthofoto-Analyse | Claude Vision | ✅ | ❌ | Innenhöfe |
| **Gerüst** | NPK-Ausmass | Berechnet | ✅ | ✅ | Offert |
| | Material | Geschätzt | ✅ | ✅ | Logistik |
| | Zugänge | SUVA-Regel | ✅ | ✅ | Sicherheit |

---

## 8. Nächste Schritte (Stand: 29.12.2025)

### ✅ Erledigt: Priorität 1 - Fehlende Anzeigen ergänzen

1. **Terrain-Höhe im Frontend anzeigen** ✅
   - Höhe m ü.M. in Adresse-Sektion
   - Hanglage-Badge bei >1m Differenz

2. **Dach-Daten im Frontend anzeigen** ✅
   - Neigung, Form, Ausrichtung
   - Icon/Symbol für Dachtyp
   - Konfidenz-Warnung bei <50%

### ✅ Erledigt: Priorität 2 - Hanglage-Erkennung

1. **Terrain-Daten an Claude-API** ✅
   - terrain_data Parameter in analyze_with_claude()
   - Hanglage-Hinweise im Prompt für komplexe Gebäude

2. **Hanglage-Warnung im Frontend** ✅
   - Orange Badge bei >1m Differenz

### ⚠️ Ausstehend: Terrain-Profil (4 Eckpunkte)

1. **Terrain-Profil implementieren**
   - 4 Eckpunkte des Polygons abfragen
   - Min/Max Höhe pro Seite berechnen
   - Genauere Hanglage-Erkennung

2. **Detaillierte Hanglage-Analyse**
   - > 3m Differenz → Ausgleichsberechnung
   - Fassaden-spezifische Gerüsthöhen

### Priorität 3: Workflow für Projektleiter

1. **Checkliste-Modus**
   - Schritt-für-Schritt Anleitung
   - Datenvollständigkeit prüfen

2. **Offert-Vorbereitung**
   - NPK-Positionen exportieren
   - Material-Liste erstellen

---

## 9. Anhang: API-Response Beispiel

```json
{
  "address": {...},
  "gwr_data": {...},
  "heights": {
    "traufhoehe_m": 14.53,
    "firsthoehe_m": 62.57,
    "source": "swissbuildings3d_detailed"
  },
  "roof": {
    "roof_type": "mansarddach",
    "roof_angle_deg": 63.4,
    "roof_orientation": "N-S",
    "confidence": 0.4
  },
  "scaffolding": {
    "total_ausmass_m2": 1850.5,
    "fassaden": [...],
    "material": {...}
  },
  "context": {
    "complexity": "complex",
    "zones": [
      {"name": "Arkaden", "type": "arkade", "gebaeudehoehe_m": 6},
      {"name": "Hauptgebäude", "type": "hauptgebaeude", "gebaeudehoehe_m": 25},
      {"name": "Kuppel", "type": "kuppel", "gebaeudehoehe_m": 64}
    ],
    "has_orthofoto_analysis": true
  }
}
```
