# Gerüst-Konfigurator: Feature-Spezifikation

## Version 1.0 | 31. Dezember 2025

---

## 1. Übersicht

### 1.1 Zweck
Der Gerüst-Konfigurator ermöglicht Gerüstbauern, basierend auf den ausgewählten Fassaden ein vollständiges Gerüst zu konfigurieren. Der Workflow führt von der Grundkonfiguration über den interaktiven Editor bis zur 3D-Vorschau.

### 1.2 Einordnung im Gesamtflow
```
[Import] → [Geodaten] → [Fassaden-Auswahl] → [GERÜST-KONFIGURATOR] → [Materialliste] → [Export/Offerte]
                                                      ↑
                                              DIESES FEATURE
```

### 1.3 Referenz-Mockup
- **Datei:** `/mockups/scaffold_complete.html`
- **Status:** Vollständig, getestet, interaktiv

---

## 2. Datenmodell

### 2.1 Input (von Fassaden-Auswahl)

```typescript
interface ProjectInput {
  project_id: string;
  building: {
    egid: string;
    address: string;
    name: string;
    polygon: [number, number][];  // LV95 Koordinaten
    trauf_height_m: number;       // z.B. 16.2
    first_height_m: number;       // z.B. 18.5
  };
  selected_facades: SelectedFacade[];
}

interface SelectedFacade {
  id: string;                     // z.B. 'north', 'east', 'south', 'west'
  direction: 'N' | 'NE' | 'E' | 'SE' | 'S' | 'SW' | 'W' | 'NW';
  length_m: number;               // z.B. 24.5
  height_m: number;               // Bis Traufe
  slope_percent: number;          // Gefälle, z.B. 1.2
  photo_url?: string;             // Primary Foto
  detected_features?: DetectedFeature[];  // Aus Foto-Analyse
}

interface DetectedFeature {
  type: 'window' | 'door' | 'balcony' | 'obstacle' | 'recess';
  position: { x: number; y: number };
  size: { width: number; height: number };
}
```

### 2.2 Scaffold Configuration (Hauptdatenmodell)

```typescript
interface ScaffoldConfiguration {
  project_id: string;
  created_at: string;
  updated_at: string;
  
  // Globale Einstellungen (Übersicht)
  settings: {
    work_type: 'facade' | 'roof' | 'full';
    system: 'layher_blitz' | 'layher_allround';
    field_width_m: 2.57 | 3.07;
    level_height_m: 2.0;
    bay_width_m: 0.73 | 1.09;
    safety_net: boolean;
    weather_cover: boolean;
  };
  
  // Elemente (Fassaden + Ecken)
  elements: ScaffoldElement[];
  
  // Berechnete Werte
  totals: {
    scaffold_area_m2: number;
    facade_count: number;
    corner_count: number;
    max_height_m: number;
    perimeter_m: number;
    estimated_weight_kg: number;
  };
}

type ScaffoldElement = ScaffoldFacade | ScaffoldCorner;

interface ScaffoldFacade {
  type: 'facade';
  id: string;                     // z.B. 'north'
  facade_ref: string;             // Referenz zu SelectedFacade
  name: string;                   // z.B. 'Nord'
  direction: string;
  
  // Dimensionen
  length_m: number;
  target_height_m: number;        // Abhängig von work_type
  slope_percent: number;
  
  // Berechnet
  fields: number;                 // Math.ceil(length / field_width)
  levels: number;                 // Math.ceil(height / level_height)
  
  // Modifikationen (Editor)
  modifications: {
    removed_cells: Set<string>;   // "field-level" Keys, z.B. "3-5"
    lift_position: number | null; // Field-Index
    stairs_position: number | null;
  };
  
  // Farbe für UI
  color: string;                  // z.B. '#ef4444'
}

interface ScaffoldCorner {
  type: 'corner';
  id: string;                     // z.B. 'corner-ne'
  name: string;                   // z.B. 'Ecke NO'
  connects: [string, string];     // IDs der verbundenen Fassaden
  
  // Automatisch berechnet
  corner_posts: number;           // Immer 4
  diagonals: number;              // Basierend auf Höhe
  enabled: boolean;
}
```

### 2.3 Output (für Materialliste/Export)

```typescript
interface ScaffoldOutput {
  configuration: ScaffoldConfiguration;
  
  // Pro Element aufgeschlüsselt
  element_details: ElementDetail[];
  
  // Für 3D-Visualisierung
  geometry: {
    building_outline: [number, number][];
    scaffold_segments: ScaffoldSegment[];
    roof_outline?: [number, number][];
  };
}

interface ElementDetail {
  element_id: string;
  type: 'facade' | 'corner';
  active_fields: number;
  removed_fields: number;
  area_m2: number;
  has_lift: boolean;
  has_stairs: boolean;
}

interface ScaffoldSegment {
  facade_id: string;
  start_point: [number, number, number];  // x, y, z
  end_point: [number, number, number];
  height_m: number;
  fields: number;
  levels: number;
}
```

---

## 3. UI-Komponenten

### 3.1 Komponenten-Hierarchie

```
<ScaffoldConfigurator>
├── <Header>
│   └── Projekt-Name, Navigation
│
├── <MainTabs>
│   ├── [Übersicht] [Editor] [3D-Ansicht]
│   └── Tab-State Management
│
├── <OverviewPanel>                    // Tab 1
│   ├── <ProjectHeader>
│   │   ├── Adresse, Name
│   │   └── <MiniFloorPlan>            // SVG mit markierten Fassaden
│   │
│   ├── <WorkTypeSelector>
│   │   └── [Fassade] [Dacharbeiten] [Komplett]
│   │
│   ├── <SystemSelector>
│   │   ├── [Layher Blitz] [Layher Allround]
│   │   └── <BayWidthSelector>
│   │       └── [W09 (0.73m)] [W13 (1.09m)]
│   │
│   ├── <SummaryStats>                 // Gradient-Box
│   │   └── Fläche, Fassaden, Ecken, Lagen, Höhe, Gewicht
│   │
│   ├── <FacadeCards>
│   │   └── Grid mit allen Elementen (klickbar → Editor)
│   │
│   └── <GlobalOptions>
│       ├── [✓] Schutznetz
│       └── [ ] Wetterschutz/Plane
│
├── <EditorPanel>                      // Tab 2
│   ├── <FacadeCarousel>
│   │   ├── <CarouselArrow left>
│   │   ├── <CarouselItem side>        // Vorherige
│   │   ├── <CarouselItem center>      // Aktive (gross)
│   │   ├── <CarouselItem side>        // Nächste
│   │   ├── <CarouselArrow right>
│   │   └── <CarouselDots>
│   │
│   ├── <Toolbar>
│   │   ├── [Auswählen] [Feld±] [Reihe±] [Schicht±] [Lift] [Treppe]
│   │   └── <ToolHint>
│   │
│   ├── <EditorCanvas>
│   │   ├── <CornerInfo>               // Wenn Ecke ausgewählt
│   │   └── <ScaffoldGrid>             // Wenn Fassade ausgewählt
│   │       └── <ResponsiveSVG>
│   │           ├── Dach (wenn roof/full)
│   │           ├── Gebäude-Outline
│   │           ├── Höhen-/Breiten-Marker
│   │           ├── Gerüst-Zellen (klickbar)
│   │           ├── Lift/Treppe Overlays
│   │           ├── Gefälle-Indikator
│   │           └── Boden
│   │
│   ├── <EditorStats>
│   │   └── [Felder] [Entfernt] [m²] [Extras]
│   │
│   └── <EditorLegend>
│
└── <ThreeDPanel>                      // Tab 3
    ├── <ThreeDViewer>
    │   ├── 3D-Szene (IFC.js/xeokit)
    │   ├── <ViewControls>             // Drehen, Zoom, Reset
    │   ├── <ViewSelector>             // Iso, N, O, S, W, Draufsicht
    │   ├── <Compass>
    │   └── <InfoBadge>
    │
    ├── <LibraryNote>                  // Implementierungshinweis
    │
    ├── <EnvironmentInfo>
    │   └── Strasse, Nachbarn, Depot
    │
    └── <SummaryCard>
        └── Zusammenfassung + Warnungen
```

### 3.2 Responsive Breakpoints

| Breakpoint | Verhalten |
|------------|-----------|
| **Mobile** (<640px) | Karussell: 3 Items, SVG skaliert auf Breite, Pinch-to-Zoom |
| **Tablet** (640-1024px) | Grössere Zellen, mehr Beschriftungen |
| **Desktop** (>1024px) | Volle Details, 2-Spalten-Layout möglich |

---

## 4. Benutzer-Interaktionen

### 4.1 Übersicht-Tab

| Aktion | Effekt |
|--------|--------|
| **Work Type wählen** | Ändert Zielhöhe (Traufe/+1m/First), berechnet Lagen neu |
| **System wählen** | Ändert Feldbreite (2.57/3.07m), berechnet Felder neu |
| **Bay Width wählen** | Speichert für Materialliste |
| **Schutznetz toggle** | Speichert global |
| **Plane toggle** | Speichert global |
| **Fassaden-Karte klicken** | Wechselt zu Editor, zeigt diese Fassade |

### 4.2 Editor-Tab

| Aktion | Effekt |
|--------|--------|
| **Karussell navigieren** | Wechselt aktives Element (zirkulär) |
| **Dot klicken** | Springt direkt zu Element |
| **Tool: Auswählen** | Zeigt Info zu Feld (später: Details-Panel) |
| **Tool: Feld ±** | Toggle einzelnes Feld removed/active |
| **Tool: Reihe ±** | Toggle ganze vertikale Reihe (alle Levels eines Fields) |
| **Tool: Schicht ±** | Toggle ganze horizontale Schicht (alle Fields eines Levels) |
| **Tool: Lift** | Platziert/entfernt Lift an Field-Position |
| **Tool: Treppe** | Platziert/entfernt Treppe an Field-Position |

### 4.3 3D-Tab

| Aktion | Effekt |
|--------|--------|
| **Drehen (Drag)** | Rotiert Szene |
| **Zoom (Pinch/Scroll)** | Zoom in/out |
| **View wählen** | Wechselt zu Ansicht (Iso, N, O, S, W, Draufsicht) |
| **Reset** | Zurück zu Default-Ansicht |

---

## 5. Berechnungslogik

### 5.1 Felder und Lagen

```typescript
function calculateFieldsAndLevels(
  facade: SelectedFacade,
  settings: ScaffoldConfiguration['settings']
): { fields: number; levels: number; target_height: number } {
  
  // Zielhöhe basierend auf Work Type
  let target_height: number;
  switch (settings.work_type) {
    case 'facade':
      target_height = facade.height_m;  // Bis Traufe
      break;
    case 'roof':
      target_height = facade.height_m + 1.0;  // +1m Absturzsicherung
      break;
    case 'full':
      target_height = facade.height_m + 2.5;  // Bis ca. First
      break;
  }
  
  // Felder: Aufrunden
  const fields = Math.ceil(facade.length_m / settings.field_width_m);
  
  // Lagen: Aufrunden + 1 für Arbeitsplatz
  const levels = Math.ceil(target_height / settings.level_height_m);
  
  return { fields, levels, target_height };
}
```

### 5.2 Fläche berechnen

```typescript
function calculateArea(
  facade: ScaffoldFacade,
  settings: ScaffoldConfiguration['settings']
): number {
  const totalCells = facade.fields * facade.levels;
  const removedCells = facade.modifications.removed_cells.size;
  const activeCells = totalCells - removedCells;
  
  const cellArea = settings.field_width_m * settings.level_height_m;
  return activeCells * cellArea;
}
```

### 5.3 Ecken-Material

```typescript
function calculateCornerMaterial(
  corner: ScaffoldCorner,
  adjacentFacades: [ScaffoldFacade, ScaffoldFacade]
): { posts: number; diagonals: number } {
  const maxLevels = Math.max(
    adjacentFacades[0].levels,
    adjacentFacades[1].levels
  );
  
  return {
    posts: 4,  // Immer 4 Eckpfosten
    diagonals: maxLevels * 2  // 2 pro Lage
  };
}
```

### 5.4 Gewicht schätzen

```typescript
function estimateWeight(config: ScaffoldConfiguration): number {
  // Grobe Schätzung: ~25-30 kg/m² Gerüstfläche
  const KG_PER_M2 = 28;
  return Math.round(config.totals.scaffold_area_m2 * KG_PER_M2);
}
```

---

## 6. SVG-Rendering (Editor)

### 6.1 Responsive Berechnung

```typescript
function calculateSvgDimensions(
  containerWidth: number,
  facade: ScaffoldFacade
): SvgDimensions {
  const marginLeft = 45;
  const marginRight = 20;
  const availableWidth = containerWidth - marginLeft - marginRight;
  
  // Zellbreite basierend auf verfügbarem Platz
  const cellWidth = Math.max(30, Math.min(50, availableWidth / facade.fields));
  const cellHeight = Math.round(cellWidth * 0.6);
  
  // SVG Dimensionen
  const svgWidth = marginLeft + (facade.fields * cellWidth) + marginRight;
  const svgHeight = calculateSvgHeight(facade.levels, cellHeight);
  
  return {
    cellWidth,
    cellHeight,
    svgWidth,
    svgHeight,
    startX: marginLeft,
    startY: svgHeight - 30  // Boden bei 30px vom unteren Rand
  };
}
```

### 6.2 SVG Struktur

```svg
<svg viewBox="0 0 {width} {height}" preserveAspectRatio="xMidYMid meet">
  <!-- Pattern für Hintergrund-Grid -->
  <defs>
    <pattern id="grid">...</pattern>
    <linearGradient id="roofGradient">...</linearGradient>
  </defs>
  
  <!-- Layer-Reihenfolge (hinten → vorne) -->
  <g id="background">...</g>
  <g id="roof">...</g>              <!-- Wenn roof/full -->
  <g id="buildingOutline">...</g>
  <g id="heightMarkers">...</g>
  <g id="widthMarkers">...</g>
  <g id="scaffoldCells">...</g>     <!-- Klickbare Felder -->
  <g id="extras">...</g>            <!-- Lift, Treppe -->
  <g id="slopeIndicator">...</g>
  <g id="ground">...</g>
</svg>
```

### 6.3 Zell-Rendering

```typescript
function renderCell(
  field: number,
  level: number,
  dims: SvgDimensions,
  facade: ScaffoldFacade
): string {
  const x = dims.startX + (field * dims.cellWidth);
  const y = dims.startY - ((level + 1) * dims.cellHeight);
  const padding = Math.max(1, dims.cellWidth * 0.04);
  
  const key = `${field}-${level}`;
  const isRemoved = facade.modifications.removed_cells.has(key);
  
  return `
    <rect 
      x="${x + padding}" 
      y="${y + padding}" 
      width="${dims.cellWidth - padding * 2}" 
      height="${dims.cellHeight - padding * 2}"
      rx="2"
      fill="${isRemoved ? '#fecaca' : facade.color}"
      stroke="${isRemoved ? '#fca5a5' : '#b91c1c'}"
      opacity="${isRemoved ? 0.4 : 0.9}"
      class="scaffold-cell cursor-pointer"
      onclick="handleCellClick(${field}, ${level})"
    />
  `;
}
```

---

## 7. Karussell-Navigation

### 7.1 Logik

```typescript
function getVisibleElements(
  elements: ScaffoldElement[],
  currentIndex: number
): { prev: ScaffoldElement; current: ScaffoldElement; next: ScaffoldElement } {
  const total = elements.length;
  
  return {
    prev: elements[(currentIndex - 1 + total) % total],
    current: elements[currentIndex],
    next: elements[(currentIndex + 1) % total]
  };
}

function navigateCarousel(direction: -1 | 1): void {
  const total = elements.length;
  currentIndex = (currentIndex + direction + total) % total;
  renderCarousel();
  renderEditor();
}
```

### 7.2 Styling

| Position | Grösse | Opacity | Transform |
|----------|--------|---------|-----------|
| **Center** | 100% | 1.0 | scale(1.1) |
| **Side** | 85% | 0.5 | scale(0.85) |

---

## 8. 3D-Visualisierung

### 8.1 Empfohlene Library

**IFC.js / xeokit** wird empfohlen wegen:
- Nativer IFC Import/Export
- Direkte Kompatibilität mit LayPLAN
- swissBUILDINGS3D als IFC ladbar
- BIM-Standard-Unterstützung

### 8.2 Datenquellen für 3D

Die 3D-Daten sind bereits über die geodaten-ch API verfügbar:

| Daten | Quelle | Was wir bekommen |
|-------|--------|------------------|
| **Gebäude-Geometrie** | swissBUILDINGS3D | 3D-Volumen, Trauf-/Firsthöhe, LOD2 |
| **Dachgeometrie** | Sonnendach.ch | Exakte Dachflächen, Neigung, Ausrichtung |
| **Grundriss** | geodienste.ch | Polygon-Umriss |
| **Terrain** | swissALTI3D | Geländehöhe für Gefälle |

```typescript
// Bereits in geodaten-ch API verfügbar
interface BuildingBundle {
  // Von swissBUILDINGS3D
  building_polygon: [number, number][];
  traufhoehe_m: number;
  firsthoehe_m: number;
  
  // Von Sonnendach.ch
  roof_surfaces: RoofSurface[];
  
  // Von swissALTI3D
  terrain_height_m: number;
}

interface RoofSurface {
  polygon: [number, number, number][];  // 3D Koordinaten
  azimuth: number;                       // Ausrichtung
  tilt: number;                          // Neigung
  area_m2: number;
}
```

### 8.4 Szenen-Aufbau

```typescript
interface Scene3D {
  // Gebäude
  building: {
    source: 'swissBUILDINGS3D' | 'generated';
    lod: 'LOD1' | 'LOD2';
    geometry: BuildingGeometry;
  };
  
  // Gerüst (parametrisch generiert)
  scaffold: {
    segments: ScaffoldSegment[];
    corners: CornerGeometry[];
    extras: ExtraGeometry[];  // Lift, Treppe
  };
  
  // Umgebung
  environment: {
    ground: GroundPlane;
    neighbors?: BuildingGeometry[];
    streets?: StreetGeometry[];
  };
  
  // Kamera
  camera: {
    position: [number, number, number];
    target: [number, number, number];
    fov: number;
  };
}
```

### 8.5 View Presets

| View | Kamera-Position | Target |
|------|-----------------|--------|
| **Isometrisch** | [1, 1, 1] normalisiert | Gebäudemitte |
| **Nord** | [0, 1, 0] | Gebäudemitte |
| **Ost** | [1, 0, 0] | Gebäudemitte |
| **Süd** | [0, -1, 0] | Gebäudemitte |
| **West** | [-1, 0, 0] | Gebäudemitte |
| **Draufsicht** | [0, 0, 1] | Gebäudemitte |

### 8.6 Export-Formate

| Format | Library | Verwendung |
|--------|---------|------------|
| **IFC** | IFC.js | LayPLAN, BIM-Software |
| **DXF** | dxf-writer | AutoCAD, 2D-Pläne |
| **glTF** | xeokit | Web-Viewer, AR |

---

## 9. State Management

### 9.1 Zustand-Struktur (React/Zustand empfohlen)

```typescript
interface ScaffoldConfiguratorState {
  // Navigation
  currentTab: 'overview' | 'editor' | '3d';
  currentElementIndex: number;
  currentTool: Tool;
  
  // Konfiguration
  configuration: ScaffoldConfiguration;
  
  // UI
  isLoading: boolean;
  error: string | null;
  
  // Actions
  setWorkType: (type: WorkType) => void;
  setSystem: (system: ScaffoldSystem) => void;
  setBayWidth: (width: number) => void;
  toggleOption: (option: 'safety_net' | 'weather_cover') => void;
  
  navigateCarousel: (direction: -1 | 1) => void;
  jumpToElement: (index: number) => void;
  setTool: (tool: Tool) => void;
  
  toggleCell: (facadeId: string, field: number, level: number) => void;
  toggleRow: (facadeId: string, field: number) => void;
  toggleLevel: (facadeId: string, level: number) => void;
  setLift: (facadeId: string, position: number | null) => void;
  setStairs: (facadeId: string, position: number | null) => void;
  
  // Computed
  getCurrentElement: () => ScaffoldElement;
  getTotals: () => ScaffoldConfiguration['totals'];
}
```

### 9.2 Persistierung

- **LocalStorage:** Für Entwürfe während der Session
- **Backend API:** Für gespeicherte Projekte

```typescript
// Auto-Save bei Änderungen
useEffect(() => {
  const debounced = debounce(() => {
    localStorage.setItem(
      `scaffold_draft_${projectId}`,
      JSON.stringify(configuration)
    );
  }, 1000);
  
  debounced();
}, [configuration]);
```

---

## 10. API-Endpunkte

### 10.1 Konfiguration speichern

```yaml
POST /api/v1/projects/{project_id}/scaffold
Content-Type: application/json

Request:
{
  "settings": { ... },
  "elements": [ ... ]
}

Response:
{
  "id": "scaffold_123",
  "project_id": "proj_456",
  "created_at": "2025-12-31T10:00:00Z",
  "configuration": { ... },
  "totals": { ... }
}
```

### 10.2 Konfiguration laden

```yaml
GET /api/v1/projects/{project_id}/scaffold

Response:
{
  "configuration": { ... },
  "totals": { ... }
}
```

### 10.3 3D-Geometrie generieren

```yaml
POST /api/v1/projects/{project_id}/scaffold/geometry
Content-Type: application/json

Request:
{
  "format": "ifc" | "gltf",
  "include_building": true,
  "lod": "LOD2"
}

Response:
{
  "geometry_url": "https://...",
  "format": "ifc",
  "file_size_bytes": 123456
}
```

---

## 11. Implementierungs-Reihenfolge

### Phase 1: Grundstruktur
1. [ ] Projekt-Setup (React + TypeScript + Tailwind)
2. [ ] Routing und Tab-Navigation
3. [ ] State Management Setup (Zustand)
4. [ ] Datenmodell-Typen definieren

### Phase 2: Übersicht-Tab
5. [ ] ProjectHeader Komponente
6. [ ] MiniFloorPlan SVG
7. [ ] WorkTypeSelector
8. [ ] SystemSelector + BayWidthSelector
9. [ ] SummaryStats
10. [ ] FacadeCards
11. [ ] GlobalOptions (Schutznetz, Plane)

### Phase 3: Editor-Tab
12. [ ] FacadeCarousel Komponente
13. [ ] Toolbar mit Tool-State
14. [ ] Responsive SVG Container
15. [ ] ScaffoldGrid Rendering
16. [ ] Cell-Interaktionen (click handlers)
17. [ ] Lift/Treppe Platzierung
18. [ ] Dach-Darstellung
19. [ ] Gefälle-Indikator
20. [ ] EditorStats

### Phase 4: 3D-Tab
21. [ ] IFC.js/xeokit Integration
22. [ ] Gebäude aus swissBUILDINGS3D laden (bereits via geodaten-ch API verfügbar)
23. [ ] Dachgeometrie von Sonnendach.ch integrieren
24. [ ] Gerüst parametrisch generieren
25. [ ] Kamera-Controls
26. [ ] View-Presets
27. [ ] Environment-Info Komponente

### Phase 5: Backend
27. [ ] API-Endpunkte implementieren
28. [ ] Speicherung/Laden
29. [ ] IFC-Export generieren
30. [ ] DXF-Export generieren

### Phase 6: Polish
31. [ ] Mobile Optimierung testen
32. [ ] Performance-Optimierung
33. [ ] Error Handling
34. [ ] Loading States

---

## 12. Dateien und Struktur

```
src/
├── features/
│   └── scaffold-configurator/
│       ├── components/
│       │   ├── ScaffoldConfigurator.tsx    # Haupt-Container
│       │   ├── OverviewPanel.tsx
│       │   ├── EditorPanel.tsx
│       │   ├── ThreeDPanel.tsx
│       │   ├── FacadeCarousel.tsx
│       │   ├── ScaffoldGrid.tsx
│       │   ├── Toolbar.tsx
│       │   ├── SystemSelector.tsx
│       │   ├── WorkTypeSelector.tsx
│       │   ├── FacadeCards.tsx
│       │   ├── MiniFloorPlan.tsx
│       │   └── SummaryStats.tsx
│       │
│       ├── hooks/
│       │   ├── useScaffoldConfig.ts        # Zustand Store
│       │   ├── useCarousel.ts
│       │   ├── useSvgDimensions.ts
│       │   └── useThreeD.ts
│       │
│       ├── utils/
│       │   ├── calculations.ts             # Fläche, Felder, etc.
│       │   ├── svgRenderer.ts              # SVG Generierung
│       │   └── geometry.ts                 # 3D Geometrie
│       │
│       ├── types/
│       │   └── scaffold.types.ts
│       │
│       └── api/
│           └── scaffoldApi.ts
│
├── lib/
│   └── ifc/                                # IFC.js Setup
│       ├── viewer.ts
│       └── exporter.ts
```

---

## 13. Referenzen

### Mockups
- `/mockups/scaffold_complete.html` - Vollständiges interaktives Mockup

### Vorherige Features
- `/mockups/import_v2.html` - Import-Flow
- `/mockups/facade_selection.html` - Fassaden-Auswahl

### Externe Dokumentation
- [IFC.js Dokumentation](https://ifcjs.github.io/info/)
- [xeokit SDK](https://xeokit.io/)
- [Layher Blitz System](https://www.layher.com/)

---

## 14. Offene Fragen / Entscheidungen

| Frage | Status | Entscheidung |
|-------|--------|--------------|
| 3D Library | ⏳ Offen | IFC.js/xeokit empfohlen, finale Entscheidung nach Evaluation |
| Offline-Fähigkeit | ⏳ Offen | LocalStorage für Drafts, später PWA? |
| Mehrere Konfigurationen pro Projekt | ⏳ Offen | Vorerst eine, Versionen später |

---

*Dokument erstellt: 31.12.2025*
*Für: Claude IDE Implementation*
*Referenz-Mockup: scaffold_complete.html*
