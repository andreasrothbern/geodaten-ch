# Layher Blitz Gerüst System - Technisches Abstract

> **Stand:** 28.01.2026
> **Quelle:** Layher Blitz Gerüst Katalog & Preisliste 2025/2026
> **Zweck:** Datenbasis für 3D-basierte Gerüstplanung

---

## 1. Systemübersicht

### 1.1 Gerüsttypen und Zulassungen

| System | Breite | Material | Max. Lastklasse | Zulassung |
|--------|--------|----------|-----------------|-----------|
| Blitz 70 | 0,73 m | Stahl | LK 4 | Z-8.1-16.2 |
| Blitz 70 | 0,73 m | Aluminium | LK 3 | Z-8.1-844 |
| Blitz 100 | 1,09 m | Stahl | LK 6 | Z-8.1-840 |

### 1.2 Lastklassen nach DIN EN 12811

| Lastklasse | zul. Flächenlast | Typische Anwendung |
|------------|------------------|-------------------|
| LK 2 | 1,5 kN/m² | Inspektionsgerüste |
| LK 3 | 2,0 kN/m² | Malerarbeiten |
| LK 4 | 3,0 kN/m² | Putzarbeiten |
| LK 5 | 4,5 kN/m² | Maurerarbeiten |
| LK 6 | 6,0 kN/m² | Schwere Maurerarbeiten |

---

## 2. Grundelemente (6 Hauptkomponenten)

### 2.1 Stellrahmen (Blitz Stellrahmen LW)

**Standardrahmen:**
- Höhe: **2,00 m** (Regelhöhe)
- Breiten: **0,73 m** oder **1,09 m**
- Geländerkästchen: 2 (nur außen) oder 4 (innen + außen)

**Ausgleichsrahmen (Höhenanpassung):**

| Höhe | Breite 0,73 m | Breite 1,09 m | Verwendung |
|------|---------------|---------------|------------|
| 0,66 m | ✓ | ✓ | Kleine Anpassung |
| 1,00 m | ✓ (mit Geländerkästchen) | ✓ | Mittlere Anpassung |
| 1,50 m | ✓ (mit Geländerkästchen) | ✓ (mit 2 Geländerkästchen) | Große Anpassung |

**Wichtig für 3D-Berechnung:**
- Aufbau beginnt immer am **höchsten Geländepunkt**
- Rohrverbinder oben für Weiterbau
- Knotenblech für Diagonalen/Konsolen/Anker

### 2.2 Fußspindeln (Höhennivellierung)

| Typ | Art.-Nr. | Länge | Max. Spindelweg | Gewicht | Einsatz |
|-----|----------|-------|-----------------|---------|---------|
| Fußspindel 60 | 4001.060 | 0,56 m | **41 cm** | 3,6 kg | Standard |
| Fußspindel 80 (verstärkt) | 4002.080 | 0,73 m | **55 cm** | 4,9 kg | Erhöhte Last |
| Fußspindel 110 (verstärkt) | 4002.110 | 1,10 m | **79 cm** | 6,5 kg | Große Differenz |
| Fußspindel 150 (verstärkt) | 4002.130 | 1,50 m | **82 cm** | 10,0 kg | Sehr große Differenz |
| Schwenkbare Fußspindel 60 | 4003.000 | 0,58 m | **32 cm** | 6,1 kg | Geneigte Untergründe |

**Technische Daten:**
- Rundgewinde Außendurchmesser: **38 mm**
- Flügelaußenmaß Spindelmutter: **205 mm**
- Fußplatte: **150 × 150 mm**
- Ausgleichsplatte (4000.400): Neigungsbereich **0–16%** (≈ 0–9°)

**Für 3D-Terrain-Berechnung:**
```
Max. Höhenausgleich pro Stiel:
- Mit Fußspindel 60:   41 cm
- Mit Fußspindel 80:   55 cm
- Mit Fußspindel 110:  79 cm
- Mit Fußspindel 150:  82 cm
- Mit Ausgleichsrahmen 0,66 m + Spindel 80: 121 cm
- Mit Ausgleichsrahmen 1,00 m + Spindel 80: 155 cm
- Mit Ausgleichsrahmen 1,50 m + Spindel 80: 205 cm
```

### 2.3 Gerüstböden

**Standard-Bodenbreiten:**

| Bodenbreite | Verwendung |
|-------------|------------|
| 0,19 m | Ausgleichsboden |
| 0,32 m | Ausgleichsboden, Einzelbelag |
| 0,50 m | Stalu-Boden für 1,09 m Gerüst (2 Stk) |
| 0,61 m | Hauptbelag (Standard) |

**Feldlängen (Rastermaße):**

| Feldlänge | Typische Verwendung |
|-----------|-------------------|
| 0,73 m | Kurze Felder, Ecken |
| 1,09 m | Kurze Felder |
| 1,57 m | Mittlere Felder |
| 2,07 m | **Standard-Feldlänge** |
| 2,57 m | Lange Felder |
| 3,07 m | Sehr lange Felder |
| 4,14 m | Maximale Feldlänge |

**Lastklassen nach Bodentyp und Feldlänge:**

| Bodentyp | 0,73 m | 1,57 m | 2,07 m | 2,57 m | 3,07 m |
|----------|--------|--------|--------|--------|--------|
| U-Stahlboden LW 0,32 m | LK 6 | LK 6 | LK 6 | LK 5 | LK 4 |
| U-Stalu-Boden 0,61 m | LK 6 | LK 6 | LK 6 | LK 5 | LK 4 |
| U-Xtra-N-Boden 0,61 m | LK 3 | LK 3 | LK 3 | LK 3 | LK 3 |
| U-Robustboden 0,61 m | - | LK 3 | LK 3 | LK 3 | LK 3 |

### 2.4 Geländer (Seitenschutz)

**Dreiteiliger Seitenschutz nach Norm:**
1. **Handlauf** (Geländerholm) - Höhe: 1,00 m über Boden
2. **Zwischenholm** (Knieleiste) - Höhe: 0,50 m über Boden
3. **Bordbrett** - Höhe: 0,15 m

**Geländertypen:**

| Typ | Feldlängen | Besonderheit |
|-----|-----------|--------------|
| I-Geländer mit Drehriegel | 1,57–3,07 m | **Vorlaufend** (vor Montage nächster Lage) |
| Doppelgeländer | 1,57–4,14 m | Handlauf + Zwischenholm |
| Einzelgeländer | 0,73–3,07 m | Nur Handlauf |
| Stirngeländer | 0,73–1,09 m | Für Stirnseiten |

**Bordbretter:**
- Holz: 0,73–4,14 m Länge × 0,15 m Höhe
- Aluminium: 0,73–3,07 m Länge × 0,15 m Höhe

### 2.5 Diagonalen (Aussteifung)

| Typ | Feldlänge | Feldhöhe | Länge |
|-----|-----------|----------|-------|
| Diagonale mit Keil-Halbkupplung | 2,07 m | 2,00 m | 2,80 m |
| Diagonale mit Keil-Halbkupplung | 2,57 m | 2,00 m | 3,20 m |
| Diagonale mit Keil-Halbkupplung | 3,07 m | 2,00 m | 3,60 m |
| Diagonale mit Keil-Halbkupplung | 2,57 m | 1,50 m | 2,97 m |

**Horizontalstreben** (im Fußbereich des Diagonalfeldes):
- 2,07 m, 2,57 m, 3,07 m Feldlängen

### 2.6 Konsolen (Verbreiterung)

| Breite | Typ | Verwendung |
|--------|-----|------------|
| 0,22 m | Standard | +0,19 m Boden |
| 0,36 m | Standard/Kombi | +0,32 m Boden |
| 0,50 m | Standard | +0,50 m Boden oder 2× 0,61 m |
| 0,73 m | Standard/Verstärkt | Volle Verbreiterung |
| 1,09 m | Standard | Große Verbreiterung |

**Traufkonsole 1,00 m:** Für Spengler/Dachdecker-Arbeitsplatz

---

## 3. Arbeitstypen und Gerüstkonfiguration

### 3.1 Fassadengerüst (Standard)

**Regelabstand zur Fassade:** ≤ 0,30 m (max. Spalt zur Wand)

**Konfiguration:**
- Gerüstbreite: 0,73 m oder 1,09 m
- Feldlängen: 2,07–3,07 m (optimal)
- Lagenhöhe: 2,00 m

### 3.2 Malergerüst / Putzgerüst

**Lastklasse:** LK 3–4
**Gerüsthöhe:** Bis Traufhöhe + 1,00 m Überstand

### 3.3 Maurergerüst

**Lastklasse:** LK 5–6
**Gerüstbreite:** 1,09 m empfohlen
**Besonderheit:** Stellrahmen mit 2 Geländerkästchen für Innengeländer

### 3.4 Dachfanggerüst (Spengler/Dachdecker)

**Komponenten:**
- **Schutzgitterstütze:** 2,00 m hoch (Art.-Nr. 1748.003)
- **Seitenschutzgitter:** 2 Stück pro Feld
- **Traufkonsole 1,00 m** (Art.-Nr. 1718.100)

**Konfiguration:**
- Erhöhter Seitenschutz: 2,00 m über Arbeitsebene
- Netzschutz mit Gurtschnellverschluss möglich
- Schutzdachträger für Passantenschutz

**Für 3D-Berechnung (Spengler WorkType):**
```
Gerüsthöhe = Traufhöhe + ca. 1,00 m (bis Dachfang-Oberkante)
Am Giebel: Trapez-Form bis Firsthöhe
```

### 3.5 Brüstungsgerüst (Stellrahmen für Brüstung)

**Art.-Nr. 1773.241:** Blitz Stellrahmen LW 2,00 m für Brüstung
- Für Dachvorsprünge die ins Gerüst ragen
- Danach max. 4 Etagen mit normalen Stellrahmen

---

## 4. Verankerung

### 4.1 Ankerabstände (Regelfall)

| Richtung | Max. Abstand |
|----------|-------------|
| Horizontal | Jedes 2. Feld (ca. 4–6 m) |
| Vertikal | Jede 2. Lage (ca. 4 m) |

### 4.2 Ankertypen

| Typ | Art.-Nr. | Länge | Verwendung |
|-----|----------|-------|------------|
| Blitz Anker | 1755.069 | 0,69 m | Standard am Knotenblech |
| Gerüsthalter | 1754.020–175 | 0,20–1,75 m | V-förmig an Stielen |
| WDVS-Anker 600 | 4000.600 | 0,68 m | Bis 200 mm Isolierung |
| WDVS-Anker 800 | 4000.800 | 0,88 m | Bis 300 mm Isolierung |

### 4.3 Gerüststütze (ohne Verankerung)

**Stahl-Gerüststütze (Art.-Nr. 4032.600):**
- Teleskopierbar: 3,30–6,00 m
- Max. Standhöhe: **6,20 m**
- Auch für Dachfanggerüste (z.B. PV-Installationen)

---

## 5. Höhenberechnung für 3D-Daten

### 5.1 Lagenhöhen-Schema

```
Lage n+1:  ═══════════════════  Boden + 2,00 m
           │                 │
           │   Stellrahmen   │  2,00 m
           │     2,00 m      │
           │                 │
Lage n:    ═══════════════════  Boden
           │                 │
           │   Stellrahmen   │  2,00 m
           │     2,00 m      │
           │                 │
Lage 1:    ═══════════════════  Boden 1
           │                 │
           │   Fußspindel    │  0,30–0,80 m (variabel)
           │                 │
Terrain:   ─────────────────────
```

### 5.2 Gerüsthöhe-Berechnung

```typescript
// Formel für Anzahl der Lagen
function calculateLayers(targetHeight_m: number): LayerConfig {
  const LAYER_HEIGHT = 2.00;  // Stellrahmen-Regelhöhe
  const MIN_SPINDLE = 0.10;   // Min. Spindelauszug
  const MAX_SPINDLE = 0.55;   // Fußspindel 80 max.

  // Vollständige Lagen
  const fullLayers = Math.floor(targetHeight_m / LAYER_HEIGHT);
  const remainder = targetHeight_m % LAYER_HEIGHT;

  // Restbetrag mit Ausgleichsrahmen + Spindel abdecken
  if (remainder <= MAX_SPINDLE) {
    return { fullLayers, adjustmentFrame: null, spindleHeight: remainder };
  } else if (remainder <= 0.66 + MAX_SPINDLE) {
    return { fullLayers, adjustmentFrame: 0.66, spindleHeight: remainder - 0.66 };
  } else if (remainder <= 1.00 + MAX_SPINDLE) {
    return { fullLayers, adjustmentFrame: 1.00, spindleHeight: remainder - 1.00 };
  } else if (remainder <= 1.50 + MAX_SPINDLE) {
    return { fullLayers, adjustmentFrame: 1.50, spindleHeight: remainder - 1.50 };
  } else {
    return { fullLayers: fullLayers + 1, adjustmentFrame: null, spindleHeight: MIN_SPINDLE };
  }
}
```

### 5.3 Terrain-Ausgleich (Hanglage)

```typescript
// Spindelwahl basierend auf Höhendifferenz
function selectSpindle(heightDiff_m: number): SpindleType {
  if (heightDiff_m <= 0.41) return 'SPINDLE_60';  // 4001.060
  if (heightDiff_m <= 0.55) return 'SPINDLE_80';  // 4002.080
  if (heightDiff_m <= 0.79) return 'SPINDLE_110'; // 4002.110
  if (heightDiff_m <= 0.82) return 'SPINDLE_150'; // 4002.130
  return 'ADJUSTMENT_FRAME_REQUIRED';  // Ausgleichsrahmen nötig
}

// Ausgleichsrahmen-Wahl
function selectAdjustmentFrame(heightDiff_m: number, maxSpindle: number = 0.55): FrameType {
  const frameOptions = [0.66, 1.00, 1.50];
  for (const frame of frameOptions) {
    if (heightDiff_m <= frame + maxSpindle) {
      return { frame_m: frame, spindle_m: heightDiff_m - frame };
    }
  }
  return null; // Mehrere Ausgleichsrahmen oder Statik-Nachweis nötig
}
```

---

## 6. Feldlängen-Optimierung

### 6.1 Verfügbare Feldlängen

```typescript
const FIELD_LENGTHS_M = [0.73, 1.09, 1.57, 2.07, 2.57, 3.07, 4.14];
```

### 6.2 Optimierungsalgorithmus

```typescript
function optimizeFieldLengths(facadeLength_m: number): number[] {
  // Präferenz: Längere Felder bevorzugen (weniger Material)
  // Aber: Mindestens 2 Felder pro Fassade

  const PREFERRED_LENGTHS = [3.07, 2.57, 2.07, 1.57, 1.09, 0.73];

  // Greedy-Ansatz mit Ausgleich
  let remaining = facadeLength_m;
  const fields: number[] = [];

  while (remaining > 0.01) {
    for (const length of PREFERRED_LENGTHS) {
      if (remaining >= length || (fields.length > 0 && remaining >= 0.73)) {
        fields.push(Math.min(length, remaining));
        remaining -= length;
        break;
      }
    }
  }

  return fields;
}
```

---

## 7. Arbeitstyp-spezifische Konfiguration

### 7.1 WorkType: facade (Fassadenarbeiten)

```typescript
const FACADE_CONFIG = {
  targetHeight: 'traufhoehe_m',
  scaffoldDistance_m: 0.30,
  width_m: 0.73,
  loadClass: 4,
  sideProtection: 'DOUBLE_RAILING',  // Doppelgeländer
};
```

### 7.2 WorkType: roof (Dacharbeiten)

```typescript
const ROOF_CONFIG = {
  targetHeight: 'traufhoehe_m + 1.0',  // 1m über Traufe
  scaffoldDistance_m: 0.30,
  width_m: 0.73,
  loadClass: 3,
  sideProtection: 'PROTECTION_GRID',  // Schutzgitterstütze 2m
};
```

### 7.3 WorkType: roofer (Spengler)

```typescript
const ROOFER_CONFIG = {
  // Trauf-Fassade: Bis unter First minus 1m
  targetHeight_trauf: 'firsthoehe_m - 1.0',
  // Giebel-Fassade: Trapez bis First
  targetHeight_giebel: 'traufhoehe_m + giebel_height_m - 1.0',
  scaffoldDistance_m: 0.30,
  width_m: 0.73,
  loadClass: 3,
  sideProtection: 'PROTECTION_GRID',
  console: 'TRAUFKONSOLE_1M',  // Art.-Nr. 1718.100
};
```

---

## 8. Artikelnummern-Referenz (wichtigste)

### 8.1 Stellrahmen

| Art.-Nr. | Bezeichnung | Maße |
|----------|-------------|------|
| 1773.200 | Stellrahmen LW Stahl, 2 Geländerkästchen | 2,00 × 0,73 m |
| 1773.204 | Stellrahmen LW Stahl, 4 Geländerkästchen | 2,00 × 0,73 m |
| 1782.200 | Stellrahmen LW Stahl, 2 Geländerkästchen | 2,00 × 1,09 m |
| 1782.204 | Stellrahmen LW Stahl, 4 Geländerkästchen | 2,00 × 1,09 m |
| 1773.066 | Ausgleichsrahmen | 0,66 × 0,73 m |
| 1773.100 | Ausgleichsrahmen | 1,00 × 0,73 m |
| 1773.150 | Ausgleichsrahmen | 1,50 × 0,73 m |

### 8.2 Fußspindeln

| Art.-Nr. | Bezeichnung | Max. Weg |
|----------|-------------|----------|
| 4001.060 | Fußspindel 60 | 41 cm |
| 4002.080 | Fußspindel 80 verstärkt | 55 cm |
| 4002.110 | Fußspindel 110 verstärkt | 79 cm |
| 4002.130 | Fußspindel 150 verstärkt | 82 cm |
| 4003.000 | Schwenkbare Fußspindel 60 | 32 cm |
| 4000.400 | Ausgleichsplatte | 0–16% |

### 8.3 Seitenschutz

| Art.-Nr. | Bezeichnung |
|----------|-------------|
| 1721.xxx | I-Geländer mit Drehriegel |
| 1728.xxx | Doppelgeländer Stahl |
| 1732.xxx | Doppelgeländer Aluminium |
| 1748.003 | Schutzgitterstütze 2,00 m |
| 1718.100 | Blitz Traufkonsole 1,00 m |

### 8.4 Verankerung

| Art.-Nr. | Bezeichnung |
|----------|-------------|
| 1755.069 | Blitz Anker |
| 1754.xxx | Gerüsthalter (diverse Längen) |
| 4000.600 | WDVS-Anker 600 (bis 200 mm) |
| 4000.800 | WDVS-Anker 800 (bis 300 mm) |

---

## 9. Konstanten für die Software

```typescript
// Layher Blitz System Constants
export const LAYHER_BLITZ = {
  // Rastermaße
  FIELD_LENGTHS_M: [0.73, 1.09, 1.57, 2.07, 2.57, 3.07, 4.14],
  FRAME_WIDTHS_M: [0.73, 1.09],
  FRAME_HEIGHTS_M: [0.66, 1.00, 1.50, 2.00],

  // Fußspindeln
  SPINDLES: {
    SPINDLE_60: { artNr: '4001.060', maxHeight_m: 0.41, length_m: 0.56 },
    SPINDLE_80: { artNr: '4002.080', maxHeight_m: 0.55, length_m: 0.73 },
    SPINDLE_110: { artNr: '4002.110', maxHeight_m: 0.79, length_m: 1.10 },
    SPINDLE_150: { artNr: '4002.130', maxHeight_m: 0.82, length_m: 1.50 },
  },

  // Ausgleichsrahmen
  ADJUSTMENT_FRAMES_M: [0.66, 1.00, 1.50],

  // Abstände
  MAX_WALL_GAP_M: 0.30,
  ANCHOR_HORIZONTAL_M: 6.0,  // ca. jedes 2. Feld
  ANCHOR_VERTICAL_M: 4.0,    // ca. jede 2. Lage

  // Seitenschutz
  RAILING_HEIGHT_M: 1.00,
  KNEE_RAIL_HEIGHT_M: 0.50,
  TOE_BOARD_HEIGHT_M: 0.15,
  PROTECTION_GRID_HEIGHT_M: 2.00,

  // Max. Standhöhe ohne Verankerung
  MAX_FREESTANDING_HEIGHT_M: 6.20,
} as const;
```

---

## 10. Verwendung mit 3D-Daten

### 10.1 Input aus swissBUILDINGS3D

```typescript
interface Building3DData {
  polygon: number[][];        // 2D Grundriss-Polygon
  walls: {
    geometry: number[][];     // 3D Wall-Vertices [x, y, z]
    traufhoehe_m: number;     // Trauf-Höhe (m ü.M.)
    firsthoehe_m: number;     // First-Höhe (m ü.M.)
    terrain_z_m: number;      // Terrain am Wandfuß (m ü.M.)
    azimuth_deg: number;      // Wandausrichtung
    length_m: number;         // Wandlänge
    is_giebel: boolean;       // Giebel-Fassade?
  }[];
}
```

### 10.2 Output für Gerüstplanung

```typescript
interface ScaffoldPlan {
  facades: {
    wall_index: number;
    fields: {
      length_m: number;       // Feldlänge (aus Raster)
      start_m: number;        // Position entlang Fassade
    }[];
    layers: {
      height_m: number;       // Lagenhöhe
      frame_type: 'standard' | 'adjustment';
      frame_height_m: number;
    }[];
    spindles: {
      position_m: number;     // Position entlang Fassade
      height_m: number;       // Spindel-Auszug
      type: string;           // Art.-Nr.
    }[];
    anchors: {
      position_m: number;
      layer: number;
      type: string;
    }[];
  }[];
  totalHeight_m: number;
  totalLength_m: number;
}
```

---

## Changelog

| Datum | Änderung |
|-------|----------|
| 28.01.2026 | Initiale Version aus Layher Katalog 2025/2026 |
