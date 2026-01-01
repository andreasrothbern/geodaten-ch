# Gerüstbau-App: Multi-Objekt & Areal-Workflow

## Version 1.0 | 31. Dezember 2025

---

## 1. Problem-Analyse

### Reale Ausschreibungs-Szenarien

| Szenario | Beispiel | Herausforderung |
|----------|----------|-----------------|
| **Neubau** | FORUM UZH, Rämistrasse 80 | Gebäude existiert noch nicht in Geodaten |
| **Multi-Objekt** | Kantonsschule Luzern, Alpenquai 46-50 | Mehrere Gebäude in einer Ausschreibung |
| **Areal** | Wässerwies Areal, 22'500m² | Grosses Areal mit mehreren Bauten |
| **Sanierung** | Sichtbetonfassaden-Sanierung | Bestehendes Gebäude, aber nur Teilfassaden |

### Was wir zusätzlich brauchen

1. **Projekt ≠ Gebäude** - Ein Projekt kann mehrere Objekte umfassen
2. **Areal-Definition** - Polygon um alle relevanten Gebäude
3. **Umgebungs-Kontext** - Nachbarn, Zufahrt, Platzverhältnisse
4. **Neubau-Support** - Manuelle Gebäudedefinition wenn keine Geodaten

---

## 2. Neues Datenmodell

### Hierarchie

```
PROJECT (Projekt/Ausschreibung)
  │
  ├── SITE (Areal/Bauperimeter)
  │     ├── polygon: Areal-Grenze
  │     ├── address: Hauptadresse
  │     └── access_points: Zufahrten
  │
  ├── BUILDINGS[] (Objekte)
  │     ├── BUILDING 1 (aus Geodaten oder manuell)
  │     ├── BUILDING 2
  │     └── ...
  │
  ├── CONTEXT (Umgebung)
  │     ├── neighbors[]: Nachbargebäude (auto aus Geodaten)
  │     ├── streets[]: Angrenzende Strassen
  │     └── obstacles[]: Hindernisse (Bäume, Leitungen, etc.)
  │
  └── SCAFFOLDS[] (Gerüst-Konfigurationen)
        ├── SCAFFOLD für Building 1, Fassade N
        ├── SCAFFOLD für Building 1, Fassade S
        └── ...
```

### TypeScript Interfaces

```typescript
interface Project {
  id: string;
  name: string;                    // "FORUM UZH Werkgruppe 5B"
  reference: string;               // "#26124"
  client: Client;
  status: ProjectStatus;
  
  site: Site;                      // Areal
  buildings: Building[];           // Objekte (1-n)
  context: SiteContext;            // Umgebung
  scaffolds: ScaffoldConfig[];     // Gerüste
  
  // Ausschreibungs-Metadaten
  tender?: {
    source: 'simap' | 'manual' | 'email';
    deadline: Date;
    bkp_codes: string[];           // ["212", "226.0"]
    execution_period: DateRange;
  };
}

interface Site {
  polygon: Coordinate[];           // Areal-Grenze (LV95)
  address: string;                 // Hauptadresse
  area_m2: number;
  
  access_points: AccessPoint[];    // Zufahrten
  storage_areas: StorageArea[];    // Lagerflächen
  crane_positions?: Coordinate[];  // Kran-Standorte
}

interface Building {
  id: string;
  source: 'geodata' | 'manual' | 'planned';  // Datenquelle
  
  // Aus Geodaten (wenn vorhanden)
  egid?: string;
  address?: string;
  
  // Immer vorhanden (manuell oder aus Geodaten)
  polygon: Coordinate[];
  heights: {
    terrain_m: number;
    trauf_m: number;
    first_m: number;
    source: 'swissbuildings3d' | 'estimated' | 'manual' | 'plans';
  };
  
  // Für Neubauten
  planned_data?: {
    floors_above: number;
    floors_below: number;
    gf_m2: number;                 // Geschossfläche
    gv_m3: number;                 // Gebäudevolumen
    completion_date?: Date;
  };
  
  facades: Facade[];
}

interface SiteContext {
  // Automatisch aus Geodaten geladen
  neighbor_buildings: NeighborBuilding[];
  streets: Street[];
  parcels: Parcel[];
  
  // Manuell ergänzt
  obstacles: Obstacle[];           // Bäume, Leitungen, etc.
  restrictions: Restriction[];     // Sperrflächen, Schutzgebiete
}

interface NeighborBuilding {
  egid?: string;
  polygon: Coordinate[];
  height_m: number;
  distance_m: number;              // Abstand zum nächsten Projekt-Gebäude
  direction: 'N' | 'NO' | 'O' | 'SO' | 'S' | 'SW' | 'W' | 'NW';
}

interface AccessPoint {
  position: Coordinate;
  type: 'truck' | 'crane' | 'pedestrian';
  street_name: string;
  width_m?: number;
  height_limit_m?: number;
  weight_limit_t?: number;
}
```

---

## 3. Erweiterter Workflow

### Übersicht

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ERWEITERTER WORKFLOW                                │
└─────────────────────────────────────────────────────────────────────────────┘

  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
  │    1     │    │    2     │    │    3     │    │    4     │    │    5     │
  │ PROJEKT  │───▶│  AREAL   │───▶│ OBJEKTE  │───▶│ FASSADEN │───▶│ GERÜST   │
  │ IMPORT   │    │ UMGEBUNG │    │ GEBÄUDE  │    │ AUSWAHL  │    │ CONFIG   │
  └──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
       │               │               │               │               │
       │               │               │               │               │
       ▼               ▼               ▼               ▼               ▼
  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
  │Ausschreib│    │ Karte +  │    │ Geodaten │    │ Pro Geb. │    │ Pro      │
  │PDF/simap │    │ Nachbarn │    │ + Manual │    │ Fassaden │    │ Fassade  │
  │ parsen   │    │ Zufahrt  │    │ Neubau   │    │ wählen   │    │ Editor   │
  └──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
                                                                       │
                                                                       ▼
                                                              ┌──────────────┐
                                                              │   6. 3D +    │
                                                              │   EXPORT     │
                                                              │              │
                                                              │ • 3D Ansicht │
                                                              │ • mit Umgeb. │
                                                              │ • PDF/IFC    │
                                                              └──────────────┘
```

---

## 4. Schritt 1: Projekt-Import (erweitert)

### Aus Ausschreibung extrahieren

```typescript
interface TenderExtraction {
  // Basis-Infos
  project_name: string;          // "FORUM UZH, BKP 212-01 Betonelemente"
  reference: string;             // "#26124"
  client: string;                // "Hochbauamt Kanton Zürich"
  
  // Adresse(n) - KANN MEHRERE SEIN
  addresses: string[];           // ["Rämistrasse 80", "Alpenquai 46-50"]
  location: {
    plz: string;
    city: string;
    canton: string;
  };
  
  // Gebäude-Infos (für Neubauten)
  building_info?: {
    floors_total: number;        // 11 Vollgeschosse
    floors_above: number;        // OG07 = 7
    floors_below: number;        // UG03 = 3
    gf_m2: number;              // 66'597 m²
    gv_m3: number;              // 320'000 m³
  };
  
  // Termine
  execution: DateRange;
  deadline: Date;
  
  // Gerüst-relevante Infos
  scaffold_hints: {
    bkp_226: boolean;            // Explizit Gerüste ausgeschrieben?
    height_mentions: string[];   // "Höhe ca. 55m"
    area_mentions: string[];     // "3'720 m² Trapezfassade"
  };
}
```

### AI-Extraktion Prompt (erweitert)

```markdown
Analysiere diese Ausschreibung und extrahiere:

1. PROJEKT-IDENTIFIKATION
   - Projektname, Referenznummer, Auftraggeber

2. STANDORT (kann mehrere Adressen haben!)
   - Alle genannten Adressen/Hausnummern
   - PLZ, Ort, Kanton
   - Parzellennummer falls vorhanden

3. GEBÄUDE-INFORMATIONEN
   - Neubau oder Bestand?
   - Anzahl Geschosse (oberirdisch/unterirdisch)
   - Geschossfläche, Gebäudevolumen
   - Gebäudetyp (Schulhaus, Universität, etc.)

4. GERÜST-RELEVANTE INFORMATIONEN
   - Erwähnte Höhen
   - Erwähnte Fassadenflächen
   - BKP 226 (Gerüste) enthalten?
   - Besondere Anforderungen (Denkmalschutz, etc.)

5. TERMINE
   - Ausführungszeitraum
   - Eingabefrist
```

---

## 5. Schritt 2: Areal & Umgebung

### UI-Konzept

```
┌─────────────────────────────────────────────────────────────────┐
│  ← Zurück         AREAL DEFINIEREN              [Weiter →]      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Projekt: FORUM UZH                                             │
│  Adresse: Rämistrasse 80, 8001 Zürich                          │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                                                         │   │
│  │              [INTERAKTIVE KARTE]                        │   │
│  │                                                         │   │
│  │     ┌─────────────────┐                                 │   │
│  │     │   Gloria-       │  ← Nachbar (auto erkannt)       │   │
│  │     │   strasse       │                                 │   │
│  │     └─────────────────┘                                 │   │
│  │            │                                            │   │
│  │    ════════╪════════  Rämistrasse                       │   │
│  │            │                                            │   │
│  │     ╔═══════════════╗  ← AREAL (editierbar)            │   │
│  │     ║               ║                                   │   │
│  │     ║  [NEUBAU]     ║  ← Geplantes Gebäude             │   │
│  │     ║   FORUM UZH   ║                                   │   │
│  │     ║               ║                                   │   │
│  │     ╚═══════════════╝                                   │   │
│  │            │                                            │   │
│  │    ════════╪════════  Freiestrasse                      │   │
│  │            │                                            │   │
│  │     ┌─────────────────┐                                 │   │
│  │     │   Bestand       │  ← Nachbar (auto erkannt)       │   │
│  │     └─────────────────┘                                 │   │
│  │                                                         │   │
│  │  [Polygon bearbeiten] [Zoom +] [Zoom -]                 │   │
│  │                                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ERKANNTE UMGEBUNG:                                             │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ ✅ 4 Nachbargebäude erkannt                             │   │
│  │ ✅ 4 angrenzende Strassen                               │   │
│  │ ⚠️ Neubau - keine Geodaten verfügbar                    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ZUFAHRTEN MARKIEREN:                                           │
│  [+ LKW-Zufahrt]  [+ Kran-Standort]  [+ Lagerplatz]            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Umgebungs-Daten laden

```typescript
async function loadSiteContext(
  center: Coordinate,
  radius_m: number = 100
): Promise<SiteContext> {
  
  // 1. Nachbargebäude aus swissBUILDINGS3D
  const neighbors = await swissBuildings3D.getInRadius(center, radius_m);
  
  // 2. Strassen aus swisstopo
  const streets = await swisstopo.getStreets(center, radius_m);
  
  // 3. Parzellen aus geodienste.ch
  const parcels = await geodienste.getParcels(center, radius_m);
  
  // 4. Höhenmodell für Terrain
  const terrain = await swissALTI3D.getTerrainMesh(center, radius_m);
  
  return {
    neighbor_buildings: neighbors.map(n => ({
      egid: n.egid,
      polygon: n.polygon,
      height_m: n.height_m,
      distance_m: calculateDistance(center, n.centroid),
      direction: calculateDirection(center, n.centroid)
    })),
    streets,
    parcels,
    terrain,
    obstacles: [],      // Manuell ergänzen
    restrictions: []    // Manuell ergänzen
  };
}
```

---

## 6. Schritt 3: Objekte/Gebäude

### Multi-Gebäude Auswahl

```
┌─────────────────────────────────────────────────────────────────┐
│  ← Zurück          OBJEKTE AUSWÄHLEN            [Weiter →]      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Projekt: Kantonsschule Luzern                                  │
│  Areal: Alpenquai 46-50                                         │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                                                         │   │
│  │              [AREAL-KARTE]                              │   │
│  │                                                         │   │
│  │      ┌─────┐    ┌─────┐    ┌─────┐                     │   │
│  │      │ A   │    │ B   │    │ C   │                     │   │
│  │      │ ✅  │    │ ✅  │    │ ☐   │                     │   │
│  │      └─────┘    └─────┘    └─────┘                     │   │
│  │        46         48         50                         │   │
│  │                                                         │   │
│  │  ═══════════════════════════════════  Alpenquai        │   │
│  │                                                         │   │
│  │            ~~~~~~~~~~~~~  See                           │   │
│  │                                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  AUSGEWÄHLTE OBJEKTE (2):                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ ☑ Gebäude A - Alpenquai 46                              │   │
│  │   EGID: 12345 • 4 Geschosse • 18.5m Höhe               │   │
│  │   [Details] [Entfernen]                                 │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │ ☑ Gebäude B - Alpenquai 48                              │   │
│  │   EGID: 12346 • 5 Geschosse • 22.0m Höhe               │   │
│  │   [Details] [Entfernen]                                 │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  [+ Gebäude aus Karte wählen]                                  │
│  [+ Gebäude manuell hinzufügen]  ← Für Neubauten               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Neubau manuell definieren

```
┌─────────────────────────────────────────────────────────────────┐
│  NEUBAU DEFINIEREN                               [Speichern]    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ⚠️ Keine Geodaten verfügbar - manuelle Eingabe erforderlich   │
│                                                                 │
│  GRUNDRISS:                                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  [Polygon auf Karte zeichnen]                           │   │
│  │  oder                                                   │   │
│  │  [DXF/DWG hochladen]                                    │   │
│  │  oder                                                   │   │
│  │  Rechteck: Länge [____] m × Breite [____] m            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  HÖHEN (aus Ausschreibung/Plänen):                             │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Geschosse oberirdisch:    [7]    (OG07)                │   │
│  │  Geschosse unterirdisch:   [3]    (UG03)                │   │
│  │  Geschosshöhe:             [3.5]  m                     │   │
│  │  ─────────────────────────────────                      │   │
│  │  Traufhöhe (berechnet):    24.5 m                       │   │
│  │  Firsthöhe (geschätzt):    28.0 m                       │   │
│  │  ─────────────────────────────────                      │   │
│  │  Oder manuell: Traufe [____] m  First [____] m         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ZUSATZ-INFOS:                                                  │
│  Gebäudetyp:     [Universität/Hochschule        ▼]             │
│  GF total:       [66'597] m²                                    │
│  GV total:       [320'000] m³                                   │
│                                                                 │
│  📎 Pläne hochladen (optional):                                │
│  [+ Grundriss] [+ Schnitt] [+ Fassadenplan]                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 7. 3D-Ansicht mit Umgebung

### Konzept

```
┌─────────────────────────────────────────────────────────────────┐
│  3D-ANSICHT                                   [Export ▼]        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                                                         │   │
│  │                   [3D VIEWER]                           │   │
│  │                                                         │   │
│  │         ╱╲                                              │   │
│  │        ╱  ╲  ← Nachbar (transparent)                    │   │
│  │       ╱    ╲                                            │   │
│  │      └──────┘                                           │   │
│  │                                                         │   │
│  │     ▓▓▓▓▓▓▓▓▓▓▓▓▓                                      │   │
│  │     ▓ GERÜST    ▓  ← Projekt-Gebäude (farbig)          │   │
│  │     ▓           ▓                                       │   │
│  │     ▓▓▓▓▓▓▓▓▓▓▓▓▓                                      │   │
│  │           │                                             │   │
│  │     ══════╧══════  Strasse                              │   │
│  │       🚛            ← Zufahrt markiert                  │   │
│  │                                                         │   │
│  │  [Orbit] [Pan] [Zoom] [Reset]     [N]←Kompass           │   │
│  │                                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  LAYER:                                                         │
│  ☑ Projekt-Gebäude        ☑ Gerüst                             │
│  ☑ Nachbargebäude         ☑ Terrain                            │
│  ☑ Strassen               ☐ Parzellengrenzen                   │
│  ☑ Zufahrten/Kran         ☐ Bäume                              │
│                                                                 │
│  ANSICHTEN:                                                     │
│  [Gesamt] [Nord] [Ost] [Süd] [West] [Draufsicht] [Schnitt]    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3D-Datenquellen

| Element | Quelle | LOD |
|---------|--------|-----|
| Projekt-Gebäude | swissBUILDINGS3D oder manuell | LOD2-3 |
| Nachbargebäude | swissBUILDINGS3D | LOD1-2 (vereinfacht) |
| Terrain | swissALTI3D | 0.5m Raster |
| Strassen | swisstopo TLM | 2D + Breite |
| Gerüst | Berechnet aus Konfig | LOD3 (detailliert) |

---

## 8. Angepasstes Export-Format

### IFC mit Kontext

```typescript
interface IFCExport {
  // Projekt-Infos
  project: {
    name: string;
    reference: string;
    client: string;
  };
  
  // Site (IfcSite)
  site: {
    polygon: Coordinate[];
    terrain_mesh: TerrainMesh;
    geo_reference: {
      system: 'LV95';
      origin: Coordinate;
    };
  };
  
  // Gebäude (IfcBuilding[])
  buildings: {
    id: string;
    geometry: BuildingGeometry;
    is_project: boolean;      // true = Projekt, false = Nachbar
  }[];
  
  // Gerüste (IfcElementAssembly[])
  scaffolds: {
    building_id: string;
    facade_id: string;
    elements: ScaffoldElement[];
  }[];
  
  // Zusatz-Elemente
  context: {
    streets: StreetGeometry[];
    access_points: AccessPoint[];
    crane_positions: Coordinate[];
  };
}
```

---

## 9. Zusammenfassung der Änderungen

### Neue Konzepte

| Konzept | Beschreibung |
|---------|--------------|
| **Site/Areal** | Projekt-Perimeter mit Polygon |
| **Multi-Building** | Mehrere Gebäude pro Projekt |
| **Context** | Automatisch geladene Umgebung |
| **Neubau-Support** | Manuelle Gebäudedefinition |
| **3D mit Umgebung** | Nachbarn, Strassen, Terrain |

### Workflow-Änderungen

```
ALT:  Adresse → Gebäude → Fassaden → Gerüst → Export

NEU:  Ausschreibung → Areal → Objekte(1-n) → Fassaden → Gerüst → 3D+Kontext → Export
           │            │         │
           │            │         └── inkl. Neubau-Support
           │            └── inkl. Umgebung laden
           └── Multi-Adress-Parsing
```

### API-Erweiterungen (geodaten-ch)

```
POST /api/v1/site/context
  → Lädt Umgebung für Koordinate + Radius

POST /api/v1/building/manual
  → Erstellt manuelles Gebäude (Neubau)

GET /api/v1/neighbors?center=...&radius=...
  → Nachbargebäude für 3D-Kontext
```

---

## 10. Offene Fragen

1. **Wie detailliert soll die Umgebung sein?**
   - Nur Bounding-Boxes der Nachbarn?
   - Oder volle 3D-Geometrie?

2. **Neubau-Pläne:**
   - DXF/DWG Import implementieren?
   - Oder nur einfache Polygon-Zeichnung?

3. **Performance:**
   - Wie viele Nachbargebäude laden?
   - LOD-Stufen für weit entfernte Gebäude?

4. **Offline-Fähigkeit:**
   - Umgebungsdaten cachen?
   - Wie gross darf der Cache werden?

---

*Dokument erstellt: 31.12.2025*
*Für: Gerüstbau-App Erweiterung*
