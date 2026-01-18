# Analyse: Ganzheitliche 3D-Rekonstruktion

**Stand:** 15.01.2026 23:55

> **UPDATE 15.01.2026 23:55:** `building_roofs` ist jetzt implementiert!
> Die echte 3D-Dachgeometrie wird aus der DB geladen und im 3D-View gerendert.

## Hintergrund

Beim Matching von Fassaden zu Wand-Polygonen haben wir festgestellt, dass einige
Polygone kleine Höhen haben (~3m), die wahrscheinlich **Eingangsbereiche, Vorsprünge
oder Fensterbrüstungen** sind - nicht die Hauptwände.

**Frage:** Sollten wir zuerst das gesamte Gebäude aus den verfügbaren 3D-Daten
rekonstruieren, um ein ganzheitliches Verständnis zu bekommen?

---

## Verfügbare Daten in building_3d.duckdb

### 1. buildings_3d (Haupttabelle)

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `egid` | INTEGER | Gebäude-ID |
| `polygon` | JSON | 2D-Grundriss als Koordinaten-Array |
| `traufhoehe_m` | FLOAT | Traufhöhe (DACH_MIN - GELAENDE) |
| `firsthoehe_m` | FLOAT | Firsthöhe (DACH_MAX - GELAENDE) |
| `roof_form` | TEXT | Dachform (satteldach, flachdach, etc.) |
| `roof_orientation` | TEXT | First-Richtung (N-S, O-W, etc.) |
| `center_e`, `center_n` | FLOAT | Gebäudezentrum LV95 |

### 2. building_walls (Wand-Geometrie)

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `gebaeudeeinheit` | TEXT | Eindeutige ID |
| `egid` | INTEGER | Referenz zu buildings_3d |
| `z_min` | FLOAT | Niedrigste z-Koordinate (m ü.M.) |
| `z_max` | FLOAT | Höchste z-Koordinate (m ü.M.) |
| `geometry_wkb` | BLOB | **MultiPolygonZ** als WKB |

**Aktuell genutzt:** `coords_3d` (JSON aus WKB konvertiert) → 19 Polygone

### 3. building_roofs (Dach-Geometrie)

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `gebaeudeeinheit` | TEXT | Eindeutige ID |
| `egid` | INTEGER | Referenz zu buildings_3d |
| `dach_min` | FLOAT | Traufe (m ü.M.) |
| `dach_max` | FLOAT | First (m ü.M.) |
| `roof_form` | TEXT | Dachform aus Geometrie-Analyse |
| `roof_angle_deg` | FLOAT | Dachneigung in Grad |
| `roof_orientation` | TEXT | First-Richtung |
| `geometry_wkb` | BLOB | **MultiPolygonZ** als WKB |

### 4. building_floors (Boden-Geometrie)

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `gebaeudeeinheit` | TEXT | Eindeutige ID |
| `egid` | INTEGER | Referenz zu buildings_3d |
| `gelaendepunkt` | FLOAT | Terrain-Höhe (m ü.M.) |
| `geometry_wkb` | BLOB | Grundfläche als WKB |

---

## Aktueller Ansatz: 2D-Matching

```
┌─────────────────────────────────────────────────────────────────┐
│                   AKTUELLER DATENFLUSS                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Lade building_walls.coords_3d (19 Wand-Polygone)            │
│                                                                 │
│  2. Für jede Fassade (aus 2D-Grundriss):                        │
│     ├─ Finde überlappende Wand-Polygone (2D-Projektion)        │
│     ├─ Wähle Polygon mit MAX HÖHE                              │
│     └─ Verwende dessen z_max - z_min als Wandhöhe              │
│                                                                 │
│  Problem: Keine semantische Zuordnung!                          │
│  - Was ist ein Eingang vs. Hauptwand?                          │
│  - Welche Wände sind Giebel vs. Trauf?                         │
│  - Wo ist der First genau?                                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Probleme des aktuellen Ansatzes

1. **Keine Semantik:** Wir wissen nicht, ob ein 3m-Polygon ein Eingang,
   Fenster oder Vorsprung ist.

2. **Heuristiken:** MAX HEIGHT Strategie funktioniert, aber ist nicht robust.

3. **Keine First-Position:** Wir kennen die roof_orientation, aber nicht
   die genaue Position der First-Linie.

4. **Kein Dach-Kontext:** Die Dach-Geometrie wird nicht genutzt!

---

## Alternativer Ansatz: Ganzheitliche 3D-Rekonstruktion

```
┌─────────────────────────────────────────────────────────────────┐
│               GANZHEITLICHE 3D-REKONSTRUKTION                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  PHASE 1: Geometrie laden                                       │
│  ├─ building_floors.geometry_wkb → Grundfläche mit Terrain-z   │
│  ├─ building_walls.geometry_wkb  → Alle Wand-Flächen           │
│  └─ building_roofs.geometry_wkb  → Dach-Flächen                │
│                                                                 │
│  PHASE 2: 3D-Modell konstruieren                                │
│  ├─ Wände nach Orientierung gruppieren (N/S/O/W)               │
│  ├─ First-Linie aus Dach-Geometrie extrahieren                 │
│  ├─ Trauf-Linien aus Dach-Kanten ableiten                      │
│  └─ Giebel-Dreiecke identifizieren                             │
│                                                                 │
│  PHASE 3: Semantische Zuordnung                                 │
│  ├─ Hauptwände identifizieren (größte zusammenhängende Fläche) │
│  ├─ Nebenelemente klassifizieren (Eingang, Erker, Vorsprung)   │
│  ├─ Giebel-Fassaden markieren (Wände unter Dach-Schräge)       │
│  └─ Trauf-Fassaden markieren (Wände unter Dach-Kante)          │
│                                                                 │
│  PHASE 4: Gerüst-Planung                                        │
│  ├─ Pro Fassade: korrekte Höhe aus 3D-Modell                   │
│  ├─ Giebel: Zusatzgerüst für Dreieck                           │
│  ├─ Dachüberstand berücksichtigen                              │
│  └─ First-Position für Giebelgerüst-Spitze                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Vergleich der Ansätze

| Aspekt | Aktuell (2D-Matching) | 3D-Rekonstruktion |
|--------|----------------------|-------------------|
| **Komplexität** | Niedrig | Hoch |
| **Genauigkeit** | ~90% (mit MAX HEIGHT) | ~99% |
| **Robustheit** | Heuristiken-abhängig | Geometrie-basiert |
| **First-Position** | ❌ Unbekannt | ✅ Aus Dach-Geometrie |
| **Giebel-Erkennung** | ⚠️ Per Höhe geraten | ✅ Aus Dach-Form |
| **Nebenelemente** | ❌ Als Wände behandelt | ✅ Klassifiziert |
| **Aufwand** | ✅ Gering | ⚠️ Mittel-Hoch |

---

## Konkrete Analyse für Knospenweg 4

### Was wir aus den 19 Wall-Polygonen ableiten können:

```
Polygon-Höhen-Verteilung:
──────────────────────────
~3.0m (P9, P11):      ████  2 Polygone → Eingang/Vorsprung?
~6.2m (P17):          ██    1 Polygon  → Zwischenhöhe?
~9.1-9.3m (10 Stück): ██████████████████████  → TRAUF-WÄNDE
~10.7m (7 Stück):     ██████████████          → GIEBEL-WÄNDE
```

### Was die Dach-Geometrie uns sagen würde:

```
building_roofs.geometry_wkb (MultiPolygonZ):
────────────────────────────────────────────
- First-Linie: Höchste Kante des Dachs
- Trauf-Linien: Niedrigste Kanten (mit Dachrinne)
- Dachneigung: roof_angle_deg ≈ 21.7°
- First-Richtung: roof_orientation = "N-S"

Aus der Dach-Geometrie können wir DIREKT ableiten:
- Wo der First verläuft (x,y Koordinaten)
- Welche Gebäudeseiten unter der Schräge sind (Giebel)
- Welche unter der Traufe sind (Trauf-Fassaden)
```

---

## Empfehlung

### Kurzfristig (Jetzt): MAX HEIGHT Strategie beibehalten

Der aktuelle Ansatz mit **Toleranz 3.0m + MAX HEIGHT** funktioniert für die
meisten Gebäude. Die Ergebnisse für Knospenweg 4 sind korrekt:

| Fassade | Gematchte Höhe | Typ |
|---------|----------------|-----|
| E | 9.26m | Trauf ✓ |
| S | 10.71m | Giebel ✓ |
| W | 9.11m | Trauf ✓ |
| N | 10.71m | Giebel ✓ |

### Mittelfristig: Dach-Geometrie für First-Position

```typescript
// Beispiel: First-Linie aus Dach-Geometrie extrahieren
const roofGeometry = await loadBuildingRoof(egid);
const ridgeLine = extractRidgeLine(roofGeometry); // Höchste Kante

// First-Position für Giebel-Gerüst
const ridgePosition = {
  start: ridgeLine.start,
  end: ridgeLine.end,
  height_m: roofGeometry.dach_max - terrainHeight
};
```

### Langfristig: Vollständige 3D-Rekonstruktion

Für komplexe Gebäude (Bundeshaus, Kirchen, L-Formen) wäre eine vollständige
3D-Rekonstruktion sinnvoll:

1. **3D-Viewer:** Echte Dach-Geometrie rendern statt Heuristik
2. **Giebel-Gerüst:** Exakte Dreieck-Form aus Dach ableiten
3. **Nebenelemente:** Eingänge, Erker automatisch erkennen und ausschließen

---

## Nächste Schritte

### Option A: Dach-Geometrie laden und nutzen ✅ IMPLEMENTIERT (15.01.2026 23:55)

1. ✅ `building_roofs` in API Response aufnehmen (wie `building_walls`)
2. ⏳ First-Linie extrahieren (höchste Kante der Dach-Geometrie)
3. ⏳ Fassaden als "Giebel" markieren wenn sie unter der Dach-Schräge liegen

**Implementiert:**
- `layer_fetcher.py:get_roofs_for_building()` - Daten aus DB laden
- `geruestbau.py` - building_roofs in API Response
- `project.ts:BuildingRoof` Interface
- `ConfiguratorPage.tsx:convertRoofData()` - coords_3d → roof_geometry_coords
- 3D-View rendert echte Dach-Geometrie aus building_roofs

### Option B: 3D-Viewer mit echter Geometrie ✅ TEILWEISE IMPLEMENTIERT

1. ✅ `building_roofs.geometry_wkb` im Frontend laden (als coords_3d)
2. ✅ Dach aus echter MultiPolygonZ Geometrie rendern
3. ⏳ Wände aus `building_walls.geometry_wkb` rendern (statt Extrusion)

### Option C: Semantische Wand-Klassifikation ⏳ OFFEN

1. Wall-Polygone nach Position und Größe gruppieren
2. Hauptwände identifizieren (größte zusammenhängende Fläche pro Seite)
3. Nebenelemente (Eingang, Erker) ausfiltern

---

## Fazit

**Die Daten sind exzellent** - und werden jetzt genutzt!

✅ **Implementiert (15.01.2026):**
- `building_roofs` wird in der API geladen und ans Frontend gesendet
- Echte 3D-Dachgeometrie wird im 3D-View gerendert
- `dach_min`/`dach_max` für korrekte Höhenberechnung

⏳ **Noch offen:**
- First-Position aus höchster Dach-Kante extrahieren
- Automatische Giebel vs. Trauf Erkennung
- Wände aus building_walls 3D-Geometrie rendern (statt Extrusion)
