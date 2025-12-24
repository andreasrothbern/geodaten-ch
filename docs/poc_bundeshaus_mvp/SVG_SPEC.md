# SVG_SPEC.md - Spezifikation für professionelle Gerüstbau-Grafiken

> **Version:** 1.0
> **Datum:** 24.12.2025

## Übersicht

Diese Spezifikation definiert die Anforderungen für professionelle SVG-Grafiken
zur Gerüstplanung. Die Grafiken müssen druckfähig, massstabsgetreu und für
Baustellen-Dokumentation geeignet sein.

---

## 1. Grundriss (Draufsicht)

### 1.1 Erforderliche Elemente

```
┌─────────────────────────────────────────────────────────────────────────┐
│  GRUNDRISS - Bundeshaus Bern                           M 1:200          │
│                                                                         │
│                              N                                          │
│                              ↑                                          │
│                                                                         │
│         ┌──────────────────────────────────────────┐                   │
│         │░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│                   │
│         │░  ┌─────┐              ┌─────┐         ░│ ← Gerüstzone      │
│         │░  │TURM │    KUPPEL    │TURM │         ░│   (schraffiert)   │
│    ←────│░  │ W   │      ◯       │ E   │         ░│                   │
│   12.5m │░  └──┬──┘              └──┬──┘         ░│                   │
│         │░░░░░░│░░░░░░░░░░░░░░░░░░░░│░░░░░░░░░░░░│                   │
│         ├──────┴────────────────────┴─────────────┤                   │
│         │                                         │                    │
│    ←────│           PARLAMENTSGEBÄUDE             │────→ 45.0m        │
│   18.0m │             (Zone P)                    │                    │
│         │    •    •    •    •    •    •    •      │ ← Ständer         │
│         │                                         │                    │
│         ├─────────────────────────────────────────┤                   │
│         │░░░░░░░░░░░░ ARKADEN ░░░░░░░░░░░░░░░░░░░│ ← Zone A          │
│         │░░░░░░░░░░░░ (Zone A) ░░░░░░░░░░░░░░░░░░│   (andere Höhe)   │
│         └─────────────────────────────────────────┘                   │
│                                                                         │
│         │←──────────── 65.0m ────────────────────→│                   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ LEGENDE                                                          │   │
│  │ ░░░ Gerüstfläche    • Ständer    ──── Gebäude    Z1 Zugang      │   │
│  │ ═══ Terrain         ○ Verankerung  - - Fassadengrenze           │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────┐                                                           │
│  │ 0  5 10m│  Massstab                                                 │
│  └─────────┘                                                           │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Datenstruktur (Input)

```typescript
interface GrundrissInput {
  // Gebäude-Grunddaten
  egid: string;
  adresse: string;
  
  // Zonen (aus BuildingContext)
  zones: BuildingZone[];
  
  // Geometrie
  polygon: Coordinate[];           // Hauptpolygon
  sub_polygons?: SubPolygon[];     // Für komplexe Gebäude
  
  // Gerüst-Konfiguration
  scaffolding: {
    fassaden: string[];            // Welche Fassaden einrüsten
    abstand_m: number;             // Fassadenabstand (0.3m)
    feldlaenge_m: number;          // Ständerabstand
  };
  
  // Darstellungsoptionen
  options: {
    scale: number;                 // 100, 200, 500
    show_dimensions: boolean;
    show_north_arrow: boolean;
    show_legend: boolean;
    show_scaffolding: boolean;
    show_anchors: boolean;
    zone_colors: boolean;
  };
}

interface BuildingZone {
  id: string;
  name: string;
  type: "hauptgebaeude" | "turm" | "anbau" | "arkade" | "kuppel";
  polygon_points: Coordinate[];
  hoehe_m: number;
  fassaden: string[];
  color?: string;                  // Für Zonen-Darstellung
}

interface Coordinate {
  e: number;  // LV95 Ost
  n: number;  // LV95 Nord
}
```

### 1.3 SVG-Struktur

```xml
<svg xmlns="http://www.w3.org/2000/svg" 
     viewBox="0 0 800 600"
     width="800" height="600">
  
  <!-- Definitionen -->
  <defs>
    <!-- Schraffur für Gerüstfläche -->
    <pattern id="scaffolding-hatch" patternUnits="userSpaceOnUse" 
             width="8" height="8" patternTransform="rotate(45)">
      <line x1="0" y1="0" x2="0" y2="8" 
            stroke="#4CAF50" stroke-width="1" opacity="0.3"/>
    </pattern>
    
    <!-- Pfeilspitze für Masslinien -->
    <marker id="arrow" markerWidth="10" markerHeight="7" 
            refX="9" refY="3.5" orient="auto">
      <polygon points="0 0, 10 3.5, 0 7" fill="#333"/>
    </marker>
    
    <!-- Zonen-Farben -->
    <style>
      .zone-hauptgebaeude { fill: #E3F2FD; stroke: #1976D2; }
      .zone-turm { fill: #FFF3E0; stroke: #F57C00; }
      .zone-arkade { fill: #E8F5E9; stroke: #388E3C; }
      .zone-kuppel { fill: #FCE4EC; stroke: #C2185B; }
      .zone-anbau { fill: #F3E5F5; stroke: #7B1FA2; }
      
      .building-outline { fill: none; stroke: #333; stroke-width: 2; }
      .scaffolding-area { fill: url(#scaffolding-hatch); stroke: #4CAF50; }
      .dimension-line { stroke: #666; stroke-width: 1; }
      .dimension-text { font-family: Arial; font-size: 12px; fill: #333; }
      .zone-label { font-family: Arial; font-size: 14px; font-weight: bold; }
      .anchor-point { fill: #FF5722; }
      .stand-point { fill: #333; }
    </style>
  </defs>
  
  <!-- Titel -->
  <g id="title">
    <text x="20" y="30" font-size="18" font-weight="bold">
      GRUNDRISS - Bundeshaus Bern
    </text>
    <text x="700" y="30" font-size="14">M 1:200</text>
  </g>
  
  <!-- Nordpfeil -->
  <g id="north-arrow" transform="translate(750, 80)">
    <polygon points="0,-30 -8,0 0,-10 8,0" fill="#333"/>
    <text x="0" y="15" text-anchor="middle" font-size="14">N</text>
  </g>
  
  <!-- Gebäude-Zonen -->
  <g id="building-zones">
    <path id="zone-arkade" class="zone-arkade" 
          d="M 100,400 L 500,400 L 500,450 L 100,450 Z"/>
    <path id="zone-parlament" class="zone-hauptgebaeude"
          d="M 100,200 L 500,200 L 500,400 L 100,400 Z"/>
    <path id="zone-turm-w" class="zone-turm"
          d="M 120,100 L 180,100 L 180,200 L 120,200 Z"/>
    <path id="zone-turm-e" class="zone-turm"
          d="M 420,100 L 480,100 L 480,200 L 420,200 Z"/>
    <circle id="zone-kuppel" class="zone-kuppel" cx="300" cy="150" r="40"/>
  </g>
  
  <!-- Gerüstfläche -->
  <g id="scaffolding">
    <path class="scaffolding-area"
          d="M 95,95 L 505,95 L 505,455 L 95,455 Z
             M 100,100 L 500,100 L 500,450 L 100,450 Z"/>
  </g>
  
  <!-- Ständerpositionen -->
  <g id="stands">
    <circle class="stand-point" cx="100" cy="200" r="4"/>
    <circle class="stand-point" cx="100" cy="250" r="4"/>
    <circle class="stand-point" cx="100" cy="300" r="4"/>
    <!-- ... weitere Ständer -->
  </g>
  
  <!-- Verankerungspunkte -->
  <g id="anchors">
    <circle class="anchor-point" cx="100" cy="220" r="3"/>
    <circle class="anchor-point" cx="100" cy="260" r="3"/>
    <!-- ... weitere Verankerungen -->
  </g>
  
  <!-- Zugänge -->
  <g id="access-points">
    <rect x="95" y="320" width="20" height="30" fill="#FFC107" stroke="#F57F17"/>
    <text x="85" y="340" font-size="10" fill="#333">Z1</text>
  </g>
  
  <!-- Masslinien -->
  <g id="dimensions">
    <!-- Horizontale Masse -->
    <line x1="100" y1="480" x2="500" y2="480" class="dimension-line"
          marker-start="url(#arrow)" marker-end="url(#arrow)"/>
    <text x="300" y="495" class="dimension-text" text-anchor="middle">65.0 m</text>
    
    <!-- Vertikale Masse -->
    <line x1="530" y1="200" x2="530" y2="400" class="dimension-line"
          marker-start="url(#arrow)" marker-end="url(#arrow)"/>
    <text x="545" y="300" class="dimension-text" transform="rotate(90, 545, 300)">18.0 m</text>
  </g>
  
  <!-- Zonen-Beschriftung -->
  <g id="zone-labels">
    <text x="300" y="300" class="zone-label" text-anchor="middle">
      PARLAMENT (25.0m)
    </text>
    <text x="150" y="150" class="zone-label" text-anchor="middle">
      TURM W (36.0m)
    </text>
    <text x="300" y="430" class="zone-label" text-anchor="middle">
      ARKADEN (14.5m)
    </text>
  </g>
  
  <!-- Legende -->
  <g id="legend" transform="translate(20, 520)">
    <rect x="0" y="0" width="400" height="60" fill="#f5f5f5" stroke="#ccc"/>
    <text x="10" y="20" font-size="12" font-weight="bold">LEGENDE</text>
    
    <rect x="10" y="30" width="20" height="15" fill="url(#scaffolding-hatch)"/>
    <text x="35" y="42" font-size="10">Gerüstfläche</text>
    
    <circle cx="120" cy="37" r="4" fill="#333"/>
    <text x="130" y="42" font-size="10">Ständer</text>
    
    <circle cx="200" cy="37" r="3" fill="#FF5722"/>
    <text x="210" y="42" font-size="10">Verankerung</text>
    
    <rect x="280" y="30" width="15" height="15" fill="#FFC107" stroke="#F57F17"/>
    <text x="300" y="42" font-size="10">Zugang</text>
  </g>
  
  <!-- Massstabsbalken -->
  <g id="scale-bar" transform="translate(600, 550)">
    <rect x="0" y="0" width="100" height="10" fill="#333"/>
    <rect x="50" y="0" width="50" height="10" fill="#fff" stroke="#333"/>
    <text x="0" y="25" font-size="10">0</text>
    <text x="50" y="25" font-size="10">5</text>
    <text x="100" y="25" font-size="10">10m</text>
  </g>
  
</svg>
```

---

## 2. Schnitt (Seitenansicht)

### 2.1 Erforderliche Elemente

```
┌─────────────────────────────────────────────────────────────────────────┐
│  SCHNITT A-A (Nord-Süd)                                    M 1:100      │
│                                                                         │
│                                                                         │
│                            ┌─────┐ ← First 28.0m                       │
│                           /│     │\                                     │
│                          / │     │ \                                    │
│            ┌────────────/  │     │  \────────────┐                      │
│            │           /   │TURM │   \           │ ← Traufe 25.0m      │
│     L6 ────│──────────/    │     │    \──────────│                      │
│            │         │     │     │     │         │                      │
│     L5 ────│─────────│     │     │     │─────────│                      │
│            │    ┌────┤     │     │     ├────┐    │                      │
│     L4 ────│────┤    │     │     │     │    ├────│                      │
│            │    │    │     │     │     │    │    │                      │
│     L3 ────│────┤    │     │     │     │    ├────│                      │
│            │    │    │     │     │     │    │    │                      │
│     L2 ────│────┤    │     │     │     │    ├────│ ← Lagen             │
│            │    │    │     └─────┘     │    │    │                      │
│     L1 ────│────┤    │                 │    ├────│                      │
│            │    │    │     ARKADEN     │    │    │ ← 14.5m             │
│            │    └────┴─────────────────┴────┘    │                      │
│            │         │                 │         │                      │
│    ════════╧═════════╧═════════════════╧═════════╧════════ Terrain     │
│    516.0m                                              520.0m           │
│    (Talseite)                                      (Bergseite)          │
│                                                                         │
│            │←── 4.0m ──→│                                              │
│                                                                         │
│  Höhenkoten:                                                           │
│  ▽ Terrain Tal:  516.0 m ü.M.                                          │
│  ▽ Terrain Berg: 520.0 m ü.M.                                          │
│  ▽ Traufe:       541.0 m ü.M. (= 520 + 21m Gebäudehöhe Bergseite)      │
│  ▽ First:        548.0 m ü.M.                                          │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Datenstruktur (Input)

```typescript
interface SchnittInput {
  egid: string;
  adresse: string;
  
  // Schnitt-Definition
  schnitt: {
    bezeichnung: string;           // "A-A", "B-B"
    richtung: "NS" | "EW";         // Nord-Süd oder Ost-West
    fassade: string;               // "N", "S", etc.
  };
  
  // Höhendaten pro Zone
  zones: {
    id: string;
    name: string;
    traufhoehe_m: number;
    firsthoehe_m: number;
    terrain_start_m: number;       // Terrain am Start der Zone
    terrain_end_m: number;         // Terrain am Ende
  }[];
  
  // Gerüst
  scaffolding: {
    lagen: number;                 // Anzahl Lagen
    lagenhoehe_m: number;          // 2.0m Standard
    gesamthoehe_m: number;
  };
  
  // Terrain-Profil (für Hanglagen)
  terrain_profile: {
    distance_m: number;            // Abstand vom Startpunkt
    hoehe_m: number;               // Geländehöhe
  }[];
  
  options: {
    scale: number;
    show_layers: boolean;          // Lagen-Markierung
    show_heights: boolean;         // Höhenkoten
    show_terrain: boolean;         // Terrain-Linie
    show_anchors: boolean;
  };
}
```

---

## 3. Ansicht (Fassadenansicht)

### 3.1 Erforderliche Elemente

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ANSICHT NORD - Parlamentsfassade                          M 1:100      │
│                                                                         │
│                                                                         │
│            F1      F2      F3      F4      F5      F6      F7          │
│         │←3.07→│←3.07→│←2.57→│←3.07→│←3.07→│←2.57→│←3.07→│            │
│                                                                         │
│         ┌───────────────────────────────────────────────────┐ ──L7     │
│    25m ─│═══════════════════════════════════════════════════│          │
│         ├───────────────────────────────────────────────────┤ ──L6     │
│         │  ○       ○       ○       ○       ○       ○       ○│          │
│         ├───────────────────────────────────────────────────┤ ──L5     │
│         │  │       │       │       │       │       │       ││          │
│         ├──┼───────┼───────┼───────┼───────┼───────┼───────┼┤ ──L4     │
│         │  ○       ○       ○       ○       ○       ○       ○│          │
│         ├──┼───────┼───────┼───────┼───────┼───────┼───────┼┤ ──L3     │
│         │  │       │       │       │       │       │       ││          │
│         ├──┼───────┼───────┼───────┼───────┼───────┼───────┼┤ ──L2     │
│         │  ○       ○       ○       ○       ○       ○       ○│          │
│         ├──┼───────┼───────┼───────┼───────┼───────┼───────┼┤ ──L1     │
│         │  │       │       │       │       │       │       ││          │
│    ═════╧══╧═══════╧═══════╧═══════╧═══════╧═══════╧═══════╧╧══════    │
│    Terrain                                                              │
│                                                                         │
│         │←─────────────── 21.5m (7 Felder) ───────────────→│           │
│                                                                         │
│  ○ = Verankerung (alle 4m horiz. / 4m vert.)                           │
│  │ = Ständer                                                            │
│  ═ = Belag                                                              │
│                                                                         │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │ Ausmass: 22.5m × 26.0m = 585.0 m²                              │    │
│  │ Lagen: 7 × 2.0m + 1 × 1.0m Konsole                             │    │
│  │ Felder: 7 (5× 3.07m, 2× 2.57m)                                 │    │
│  │ Verankerungen: 35 Stück                                         │    │
│  └────────────────────────────────────────────────────────────────┘    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Datenstruktur (Input)

```typescript
interface AnsichtInput {
  egid: string;
  adresse: string;
  fassade: string;                 // "N", "E", "S", "W"
  
  // Fassaden-Geometrie
  fassade_data: {
    laenge_m: number;
    hoehe_m: number;
    terrain_start_m: number;
    terrain_end_m: number;
  };
  
  // Gerüst-Konfiguration
  scaffolding: {
    // Felder
    felder: {
      id: string;                  // "F1", "F2", etc.
      laenge_m: number;            // 3.07, 2.57, etc.
      position_m: number;          // Abstand vom Start
    }[];
    
    // Lagen
    lagen: {
      nummer: number;              // 1, 2, 3, ...
      hoehe_m: number;             // Unterkante der Lage
      typ: "standard" | "konsole"; // 2.0m oder Aufsatz
    }[];
    
    // Verankerungen
    verankerungen: {
      position_x_m: number;
      position_y_m: number;
    }[];
    
    // Zugänge
    zugaenge: {
      position_m: number;
      bezeichnung: string;         // "Z1", "Z2"
    }[];
  };
  
  // Ausmass
  ausmass: {
    laenge_m: number;              // Mit Zuschlägen
    hoehe_m: number;               // Mit Zuschlägen
    flaeche_m2: number;
  };
  
  options: {
    scale: number;
    show_field_labels: boolean;
    show_layer_labels: boolean;
    show_dimensions: boolean;
    show_anchors: boolean;
    show_access: boolean;
  };
}
```

---

## 4. Farbschema

### 4.1 Zonen-Farben

| Zone-Typ | Fill | Stroke | Hex |
|----------|------|--------|-----|
| Hauptgebäude | Hellblau | Blau | #E3F2FD / #1976D2 |
| Turm | Hellorange | Orange | #FFF3E0 / #F57C00 |
| Anbau | Helllila | Lila | #F3E5F5 / #7B1FA2 |
| Arkade | Hellgrün | Grün | #E8F5E9 / #388E3C |
| Kuppel | Hellrosa | Pink | #FCE4EC / #C2185B |

### 4.2 Gerüst-Farben

| Element | Farbe | Hex |
|---------|-------|-----|
| Gerüstfläche (schraffiert) | Grün transparent | #4CAF50 @ 30% |
| Ständer | Schwarz | #333333 |
| Beläge | Braun | #8D6E63 |
| Verankerung | Orange | #FF5722 |
| Zugang | Gelb | #FFC107 |

### 4.3 Linien

| Element | Farbe | Stärke |
|---------|-------|--------|
| Gebäude-Umriss | Schwarz | 2px |
| Fassadengrenze | Grau gestrichelt | 1px |
| Masslinie | Dunkelgrau | 1px |
| Terrain | Braun | 2px |

---

## 5. Typografie

| Element | Font | Grösse | Gewicht |
|---------|------|--------|---------|
| Titel | Arial | 18px | Bold |
| Zonen-Label | Arial | 14px | Bold |
| Masse | Arial | 12px | Normal |
| Legende | Arial | 10px | Normal |
| Höhenkoten | Arial | 10px | Normal |

---

## 6. Export-Formate

### 6.1 SVG (Standard)
- Vektor-basiert
- Skalierbar ohne Qualitätsverlust
- Für Web und Druck

### 6.2 PDF
- Aus SVG generiert (WeasyPrint oder CairoSVG)
- A4 oder A3 Format
- Mit Titelblock und Projektinfos

### 6.3 DXF (CAD)
- Layer-Struktur gemäss Abschnitt 7
- Für AutoCAD, BricsCAD, etc.
- Massstab 1:1 (Meter)

---

## 7. DXF Layer-Struktur

| Layer-Name | Farbe | Inhalt |
|------------|-------|--------|
| GEBAUDE | Weiss (7) | Gebäude-Umriss |
| GEBAUDE_ZONEN | Cyan (4) | Zonen-Grenzen |
| GERUEST_UMRISS | Grün (3) | Gerüst-Aussenkante |
| GERUEST_STAENDER | Grün (3) | Ständerpositionen |
| GERUEST_BELAG | Braun (24) | Beläge |
| VERANKERUNG | Rot (1) | Verankerungspunkte |
| ZUGANG | Gelb (2) | Zugänge |
| BEMASS | Gelb (2) | Masslinien |
| TEXT | Weiss (7) | Beschriftungen |
| TERRAIN | Braun (24) | Geländelinie |

---

## 8. Generierungs-Workflow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      SVG-GENERIERUNGS-WORKFLOW                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. Daten sammeln                                                       │
│     ├─ Gebäude-Polygon (geodienste.ch)                                 │
│     ├─ Höhendaten (swissBUILDINGS3D)                                   │
│     ├─ Terrain (swissALTI3D)                                           │
│     └─ Gebäude-Kontext (DB oder Claude)                                │
│                                                                         │
│  2. Kontext prüfen                                                      │
│     ├─ IF Kontext existiert → Zonen verwenden                          │
│     ├─ ELIF komplexes Gebäude → Kontext erstellen (Claude)             │
│     └─ ELSE → Einfache Darstellung                                     │
│                                                                         │
│  3. Gerüst berechnen                                                    │
│     ├─ Felder optimieren (Layher-Längen)                               │
│     ├─ Lagen berechnen (pro Zone)                                      │
│     ├─ Verankerungen platzieren (4m × 4m Raster)                       │
│     └─ Zugänge platzieren                                              │
│                                                                         │
│  4. SVG generieren                                                      │
│     ├─ Koordinaten transformieren (LV95 → SVG)                         │
│     ├─ Zonen zeichnen (farbcodiert)                                    │
│     ├─ Gerüst zeichnen                                                 │
│     ├─ Masslinien hinzufügen                                           │
│     ├─ Beschriftungen                                                   │
│     └─ Legende und Titelblock                                          │
│                                                                         │
│  5. Export                                                              │
│     ├─ SVG (direkt)                                                    │
│     ├─ PDF (via CairoSVG)                                              │
│     └─ DXF (via ezdxf)                                                 │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 9. Qualitätskriterien

### 9.1 Muss-Kriterien
- [ ] Massstabsgetreu (1:100, 1:200, 1:500)
- [ ] Alle Masse beschriftet
- [ ] Nordpfeil vorhanden
- [ ] Legende vollständig
- [ ] Druckfähig (A4/A3)

### 9.2 Soll-Kriterien
- [ ] Zonen farbcodiert
- [ ] Ständerpositionen sichtbar
- [ ] Verankerungen markiert
- [ ] Terrain-Profil bei Hanglagen
- [ ] Höhenkoten bei Schnitt

### 9.3 Kann-Kriterien
- [ ] Materialdetails (Beläge, Säulen)
- [ ] Fotorealistische Elemente
- [ ] 3D-Ansicht
