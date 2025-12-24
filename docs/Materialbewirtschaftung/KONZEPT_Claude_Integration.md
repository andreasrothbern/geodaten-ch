# Konzept: Materialbewirtschaftung mit Claude AI Integration

## Executive Summary

Dieses Konzept beschreibt die Integration von Claude AI für die automatisierte Gerüst-Materialbewirtschaftung bei Lawil Gerüstbau AG. Ziel ist es, aus Gebäudedaten (via Geodaten-API) automatisch NPK 114-konforme Ausmassberechnungen und Materiallisten zu generieren.

---

## 1. Architektur-Entscheidung: Claude API vs Claude Web

### Option A: Claude API (Empfohlen)

```
┌─────────────────────────────────────────────────────────────────┐
│                        Lawil Web-App                            │
├─────────────────────────────────────────────────────────────────┤
│  Frontend (React)                                               │
│  ├── Adresseingabe                                              │
│  ├── Gebäudedaten-Anzeige (ScaffoldingCard)                     │
│  ├── Gerüst-Konfigurator (NEU)                                  │
│  └── Materiallisten-Export (NEU)                                │
├─────────────────────────────────────────────────────────────────┤
│  Backend (FastAPI)                                              │
│  ├── /api/v1/scaffolding (bestehend)                            │
│  ├── /api/v1/material-calculation (NEU)                         │
│  │   └── Ruft Claude API auf mit:                               │
│  │       - Gebäudedaten (aus geodaten-ch API)                   │
│  │       - Layher-Katalog (strukturierte Daten)                 │
│  │       - NPK 114 Regeln (System-Prompt)                       │
│  └── /api/v1/layher-catalog (NEU)                               │
├─────────────────────────────────────────────────────────────────┤
│  Datenbanken                                                    │
│  ├── building_heights.db (bestehend)                            │
│  ├── layher_catalog.db (NEU - Materialkatalog)                  │
│  └── calculations_cache.db (NEU - gespeicherte Berechnungen)    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │      Claude API (Anthropic)   │
              │  Model: claude-sonnet-4-20250514       │
              │  Mit strukturiertem System-   │
              │  Prompt für NPK 114/Layher    │
              └───────────────────────────────┘
```

**Vorteile Claude API:**
- Vollständige Kontrolle über Prompts und Kontext
- Integration in bestehende Lawil-App
- Automatisierte Workflows möglich
- Kosteneffizient bei hohem Volumen
- Strukturierte Outputs (JSON)
- Caching von Berechnungen
- Offline-fähig für Katalogdaten

**Nachteile:**
- Entwicklungsaufwand für Integration
- API-Kosten (ca. CHF 0.003-0.015 pro Berechnung)

### Option B: Claude Web mit Projekt-Kontext

```
┌─────────────────────────────────────────────────────────────────┐
│  Claude.ai (Web)                                                │
│  └── Projekt "Lawil Materialbewirtschaftung"                    │
│      ├── Kontext-Dokumente:                                     │
│      │   ├── NPK_114_Regeln.md                                  │
│      │   ├── Layher_Blitz70_Katalog.md                          │
│      │   ├── Layher_Allround_Katalog.md                         │
│      │   └── SUVA_Richtlinien.md                                │
│      └── Manueller Workflow:                                    │
│          1. User kopiert Gebäudedaten aus App                   │
│          2. Claude generiert Materialliste                      │
│          3. User kopiert Ergebnis zurück                        │
└─────────────────────────────────────────────────────────────────┘
```

**Vorteile Claude Web:**
- Kein Entwicklungsaufwand
- Sofort einsetzbar
- Kostenlos (Pro-Abo vorausgesetzt)
- Flexibel für Sonderfälle

**Nachteile:**
- Manueller Copy-Paste Workflow
- Keine Automatisierung
- Inkonsistente Outputs
- Nicht skalierbar

### Empfehlung: Hybrid-Ansatz

**Phase 1 (Sofort):** Claude Web für Prototyping und Validierung
**Phase 2 (2-4 Wochen):** Claude API Integration in bestehende App

---

## 2. Erweiterung der Gebäudedaten-API

### Aktuelle Daten (geodaten-ch API)

```typescript
interface ScaffoldingData {
  dimensions: {
    perimeter_m: number           // Gesamtumfang
    height_estimated_m: number    // Geschätzte Höhe
    height_measured_m: number     // Gemessene Höhe (swissBUILDINGS3D)
    floors: number
  }
  sides: ScaffoldingSide[]        // Einzelne Fassadenseiten
  building: {
    footprint_area_m2: number
    bounding_box: { width_m, depth_m }
  }
}
```

### Benötigte Erweiterungen

```typescript
interface ExtendedScaffoldingData extends ScaffoldingData {
  // NEU: Detaillierte Höhenangaben
  heights: {
    traufhoehe_m: number          // Höhe bis Dachkante
    firsthoehe_m: number          // Höhe bis Dachspitze
    giebelhoehe_m: number         // Giebelhöhe (First - Traufe)
    source: 'measured' | 'estimated' | 'manual'
  }

  // NEU: Dachform-Erkennung
  roof: {
    type: 'flat' | 'gable' | 'hip' | 'mansard' | 'shed'
    slope_degrees: number         // Dachneigung
    orientation: 'NS' | 'EW'      // Firstrichtung
  }

  // NEU: Pro-Fassade Daten
  facades: FacadeData[]

  // NEU: Terrain-Informationen
  terrain: {
    slope_percent: number
    access_side: 'N' | 'E' | 'S' | 'W'
    obstacles: string[]
  }
}

interface FacadeData {
  index: number
  direction: 'N' | 'NE' | 'E' | 'SE' | 'S' | 'SW' | 'W' | 'NW'
  length_m: number

  // Höhen pro Fassade (wichtig für Giebel!)
  height_traufe_m: number         // Traufhöhe dieser Seite
  height_first_m: number | null   // Firsthöhe (nur bei Giebelseiten)
  height_average_m: number        // Mittlere Höhe (für Ausmass)

  // Gerüst-Anforderungen
  is_gable: boolean               // Ist Giebelseite?
  scaffold_type: 'facade' | 'gable' | 'roof_catch'

  // Hindernisse
  obstacles: {
    type: 'window' | 'door' | 'balcony' | 'garage'
    position_m: number
    width_m: number
  }[]
}
```

### Datenquellen für Erweiterungen

| Datenfeld | Quelle | Zuverlässigkeit |
|-----------|--------|-----------------|
| Traufhöhe | swissBUILDINGS3D | Hoch (gemessen) |
| Firsthöhe | swissBUILDINGS3D | Hoch (gemessen) |
| Dachform | swissBUILDINGS3D Attribut | Mittel |
| Dachneigung | Berechnung aus First/Traufe | Mittel |
| Fassadenlängen | WFS Gebäudepolygon | Hoch |
| Terrain | DHM25/swissALTI3D | Hoch |

### API-Erweiterung Implementation

```python
# backend/app/services/building_analysis.py

async def analyze_building_for_scaffolding(egid: int) -> ExtendedScaffoldingData:
    """
    Erweiterte Gebäudeanalyse für Gerüstplanung
    """
    # 1. Basis-Daten holen (bestehend)
    base_data = await get_scaffolding_data_by_egid(egid)

    # 2. swissBUILDINGS3D Höhen abrufen
    heights = await fetch_building_heights_3d(egid)
    # Returns: {traufhoehe: 6.5, firsthoehe: 10.2, dachform: 'GABLE'}

    # 3. Dachform analysieren
    roof = analyze_roof_type(heights, base_data.building.bounding_box)

    # 4. Fassaden mit individuellen Höhen berechnen
    facades = calculate_facade_heights(
        sides=base_data.sides,
        traufhoehe=heights['traufhoehe'],
        firsthoehe=heights['firsthoehe'],
        roof_orientation=roof['orientation']
    )

    return ExtendedScaffoldingData(
        **base_data.dict(),
        heights=heights,
        roof=roof,
        facades=facades
    )
```

---

## 3. Layher-Materialkatalog Datenbank

### Datenbankschema

```sql
-- layher_catalog.db

-- Gerüstsysteme
CREATE TABLE systems (
    id TEXT PRIMARY KEY,           -- 'blitz70', 'allround'
    name TEXT,                     -- 'Layher Blitz 70 Stahl'
    field_lengths TEXT,            -- JSON: [3.07, 2.57, 2.07, 1.57, 1.09, 0.73]
    frame_heights TEXT,            -- JSON: [2.00, 1.50, 1.00, 0.50]
    deck_width_m REAL,             -- 0.32
    max_load_class INTEGER         -- 6
);

-- Materialien
CREATE TABLE materials (
    article_number TEXT PRIMARY KEY,
    system_id TEXT REFERENCES systems(id),
    category TEXT,                 -- 'frame', 'ledger', 'deck', 'diagonal', 'base'
    name_de TEXT,
    name_fr TEXT,
    length_m REAL,
    height_m REAL,
    width_m REAL,
    weight_kg REAL,
    load_class INTEGER,
    notes TEXT
);

-- Richtwerte pro 100m² (für Schätzungen)
CREATE TABLE reference_values (
    system_id TEXT REFERENCES systems(id),
    material_category TEXT,
    quantity_per_100m2_min INTEGER,
    quantity_per_100m2_max INTEGER,
    notes TEXT
);

-- Beispieldaten Layher Blitz 70
INSERT INTO materials VALUES
('2622.200', 'blitz70', 'frame', 'Stellrahmen ø48.3', NULL, 2.00, NULL, 0.73, 18.5, 6, NULL),
('2622.150', 'blitz70', 'frame', 'Stellrahmen ø48.3', NULL, 1.50, NULL, 0.73, 15.0, 6, NULL),
('2622.100', 'blitz70', 'frame', 'Stellrahmen ø48.3', NULL, 1.00, NULL, 0.73, 12.0, 6, NULL),
('2626.307', 'blitz70', 'ledger', 'Doppelgeländer', NULL, 3.07, NULL, NULL, 10.5, NULL, NULL),
('2626.257', 'blitz70', 'ledger', 'Doppelgeländer', NULL, 2.57, NULL, NULL, 9.0, NULL, NULL),
('2624.307', 'blitz70', 'deck', 'Robustboden', NULL, 3.07, NULL, 0.32, 19.5, 6, 'Durchstieg'),
('2624.257', 'blitz70', 'deck', 'Robustboden', NULL, 2.57, NULL, 0.32, 16.5, 6, NULL),
('2628.307', 'blitz70', 'diagonal', 'Diagonalstrebe', NULL, 3.07, 2.00, NULL, 5.5, NULL, 'Mit Klauen'),
('2620.040', 'blitz70', 'base', 'Fussspindel', NULL, 0.40, NULL, NULL, 3.0, NULL, 'Verstellbar'),
('2620.000', 'blitz70', 'base', 'Fussplatte', NULL, NULL, NULL, 0.15, 2.5, NULL, '150x150mm');
```

### Katalog-Service

```python
# backend/app/services/layher_catalog.py

class LayherCatalogService:
    def __init__(self, db_path: str):
        self.db = sqlite3.connect(db_path)

    def get_system(self, system_id: str) -> dict:
        """Hole Systemdaten (Feldlängen, Rahmenhöhen etc.)"""
        ...

    def get_materials_by_category(self, system_id: str, category: str) -> list[dict]:
        """Alle Materialien einer Kategorie"""
        ...

    def find_optimal_field_length(self, system_id: str, required_length: float) -> float:
        """Finde beste Feldlänge für gegebene Anforderung"""
        system = self.get_system(system_id)
        field_lengths = sorted(system['field_lengths'], reverse=True)

        # Greedy: Grösste passende Länge
        for length in field_lengths:
            if length <= required_length + 0.1:  # 10cm Toleranz
                return length
        return field_lengths[-1]  # Kleinste Länge

    def calculate_frames_for_height(self, system_id: str, target_height: float) -> list[dict]:
        """Berechne optimale Rahmenkombination für Zielhöhe"""
        system = self.get_system(system_id)
        frame_heights = sorted(system['frame_heights'], reverse=True)

        result = []
        remaining = target_height

        while remaining > 0.1:
            for height in frame_heights:
                if height <= remaining + 0.1:
                    result.append({'height': height, 'quantity': 1})
                    remaining -= height
                    break
            else:
                break

        # Gruppieren
        return self._group_frames(result)
```

---

## 4. NPK 114 Berechnungsmodul

### Kernlogik

```python
# backend/app/services/npk114_calculator.py

from dataclasses import dataclass
from typing import Literal

@dataclass
class NPK114Config:
    """NPK 114 Konfiguration"""
    fassadenabstand_m: float = 0.30          # LF
    gangbreite_m: float = 0.70               # LG (bis 0.70m)
    stirnseitiger_abschluss_m: float = 1.00  # LS = LF + LG
    hoehenzuschlag_m: float = 1.00           # Über Arbeitshöhe
    min_ausmasslaenge_m: float = 2.50        # LAmin
    min_ausmasshoehe_m: float = 4.00         # HAmin


class NPK114Calculator:
    def __init__(self, config: NPK114Config = None):
        self.config = config or NPK114Config()

    def calculate_facade_ausmass(
        self,
        facade_length_m: float,
        facade_height_m: float,
        is_gable: bool = False,
        gable_height_m: float = 0
    ) -> dict:
        """
        Berechne Ausmass für eine Fassadenseite nach NPK 114

        Args:
            facade_length_m: Fassadenlänge in Metern
            facade_height_m: Traufhöhe in Metern
            is_gable: Ist es eine Giebelseite?
            gable_height_m: Giebelhöhe (First - Traufe)

        Returns:
            dict mit LA, HA, Fläche und Details
        """
        c = self.config

        # Ausmasslänge: LA = LS + L + LS
        LA = c.stirnseitiger_abschluss_m + facade_length_m + c.stirnseitiger_abschluss_m
        LA = max(LA, c.min_ausmasslaenge_m)  # Minimum 2.5m
        LA = round(LA, 1)  # 0.1m Genauigkeit

        # Ausmasshöhe
        if is_gable:
            # Giebel: Mittlere Höhe = Traufe + (Giebelhöhe × 0.5)
            effective_height = facade_height_m + (gable_height_m * 0.5)
        else:
            effective_height = facade_height_m

        HA = effective_height + c.hoehenzuschlag_m
        HA = max(HA, c.min_ausmasshoehe_m)  # Minimum 4.0m
        HA = round(HA, 1)

        # Fläche
        area_m2 = round(LA * HA, 2)

        return {
            'facade_length_m': facade_length_m,
            'facade_height_m': facade_height_m,
            'is_gable': is_gable,
            'gable_height_m': gable_height_m,
            'ausmass_laenge_LA_m': LA,
            'ausmass_hoehe_HA_m': HA,
            'ausmass_flaeche_m2': area_m2,
            'calculation': f"LA={c.stirnseitiger_abschluss_m}+{facade_length_m}+{c.stirnseitiger_abschluss_m}={LA}m, HA={effective_height}+{c.hoehenzuschlag_m}={HA}m"
        }

    def calculate_corner_surcharge(self, height_m: float, num_corners: int = 4) -> dict:
        """
        Berechne Eckzuschläge

        Formel: A_Ecke = LS × HA (pro Ecke)
        """
        c = self.config
        HA = height_m + c.hoehenzuschlag_m
        corner_area = c.stirnseitiger_abschluss_m * HA
        total_area = corner_area * num_corners

        return {
            'corners': num_corners,
            'area_per_corner_m2': round(corner_area, 2),
            'total_corner_area_m2': round(total_area, 2)
        }

    def calculate_complete_building(self, building_data: dict) -> dict:
        """
        Vollständige Ausmassberechnung für ein Gebäude
        """
        facades = building_data['facades']
        traufhoehe = building_data['heights']['traufhoehe_m']
        giebelhoehe = building_data['heights'].get('giebelhoehe_m', 0)

        facade_results = []
        total_area = 0

        for facade in facades:
            result = self.calculate_facade_ausmass(
                facade_length_m=facade['length_m'],
                facade_height_m=facade.get('height_traufe_m', traufhoehe),
                is_gable=facade.get('is_gable', False),
                gable_height_m=giebelhoehe if facade.get('is_gable') else 0
            )
            result['direction'] = facade['direction']
            facade_results.append(result)
            total_area += result['ausmass_flaeche_m2']

        # Eckzuschläge
        corners = self.calculate_corner_surcharge(traufhoehe, num_corners=4)
        total_area += corners['total_corner_area_m2']

        return {
            'facades': facade_results,
            'corners': corners,
            'total_scaffold_area_m2': round(total_area, 2),
            'npk_config': self.config.__dict__
        }
```

---

## 5. Claude API Integration

### System-Prompt für Materialberechnung

```python
# backend/app/services/claude_material_service.py

SYSTEM_PROMPT = """Du bist ein Experte für Gerüstbau-Materialbewirtschaftung in der Schweiz.

## Deine Aufgaben
1. NPK 114-konforme Ausmassberechnungen erstellen
2. Materiallisten für Layher Blitz 70 oder Allround generieren
3. Personal- und Transportbedarf berechnen
4. SUVA/BauAV-Konformität sicherstellen

## NPK 114 D/2012 Regeln
- Ausmasslänge: LA = LS + L + LS (LS = 1.0m stirnseitiger Abschluss)
- Ausmasshöhe: HA = H + 1.0m (Höhenzuschlag)
- Minimum: LAmin ≥ 2.5m, HAmin ≥ 4.0m
- Giebel: H_mittel = H_Traufe + (H_Giebel × 0.5)
- Eckzuschlag: A_Ecke = LS × HA pro Ecke
- Rundung: 0.1m Genauigkeit, kaufmännisch

## Layher Blitz 70 System
- Feldlängen: 3.07m, 2.57m, 2.07m, 1.57m, 1.09m, 0.73m
- Rahmenhöhen: 2.00m, 1.50m, 1.00m, 0.50m
- Belagbreite: 0.32m (3 Beläge = 0.96m für W09)
- Gewicht: ca. 18-22 kg/m² Gerüstfläche

## Lastklassen (EN 12811)
- Klasse 3: 200 kg/m² (Standard Fassadenarbeiten)
- Klasse 4: 300 kg/m² (Maurerarbeiten)

## Output-Format
Liefere strukturierte JSON-Antworten mit:
- ausmass: NPK 114 Berechnung
- material_list: Artikelnummern, Mengen, Gewichte
- personnel: Montage-/Demontagezeit, Mannstunden
- transport: Fahrzeugtyp, Ladungssicherung
- safety: SUVA-Hinweise, PSA-Anforderungen
"""

class ClaudeMaterialService:
    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-20250514"

    async def generate_material_list(
        self,
        building_data: dict,
        system: str = "blitz70",
        load_class: int = 3,
        width_class: str = "W09"
    ) -> dict:
        """
        Generiere vollständige Materialliste mit Claude
        """
        user_prompt = f"""
Erstelle eine vollständige Materialliste für folgendes Gebäude:

## Gebäudedaten
- Adresse: {building_data['address']['matched']}
- EGID: {building_data['gwr_data']['egid']}
- Grundfläche: {building_data['building']['footprint_area_m2']:.1f} m²
- Fassadenlänge gesamt: {building_data['dimensions']['perimeter_m']:.1f} m

## Höhen
- Traufhöhe: {building_data['heights']['traufhoehe_m']:.1f} m
- Firsthöhe: {building_data['heights']['firsthoehe_m']:.1f} m
- Giebelhöhe: {building_data['heights']['giebelhoehe_m']:.1f} m

## Dachform
- Typ: {building_data['roof']['type']}
- Neigung: {building_data['roof']['slope_degrees']}°

## Fassaden
{self._format_facades(building_data['facades'])}

## Gerüst-Anforderungen
- System: Layher {system.replace('blitz70', 'Blitz 70').replace('allround', 'Allround')}
- Lastklasse: {load_class} ({self._load_class_description(load_class)})
- Breitenklasse: {width_class}

Bitte erstelle:
1. NPK 114 Ausmassberechnung für alle Fassaden
2. Vollständige Materialliste mit Artikelnummern
3. Gewichtszusammenfassung
4. Personalbedarfsberechnung (3-Mann-Kolonne)
5. Transportempfehlung
"""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}]
        )

        return self._parse_response(response.content[0].text)

    def _format_facades(self, facades: list) -> str:
        lines = []
        for f in facades:
            gable = " (Giebel)" if f.get('is_gable') else ""
            lines.append(f"- {f['direction']}: {f['length_m']:.1f}m × {f['height_traufe_m']:.1f}m{gable}")
        return "\n".join(lines)

    def _load_class_description(self, load_class: int) -> str:
        descriptions = {
            2: "150 kg/m², Maler",
            3: "200 kg/m², Fassadenarbeiten",
            4: "300 kg/m², Maurerarbeiten",
            5: "450 kg/m², Steinarbeiten",
            6: "600 kg/m², Schwere Lasten"
        }
        return descriptions.get(load_class, "")
```

### API-Endpunkt

```python
# backend/app/main.py

@app.post("/api/v1/material-calculation")
async def calculate_materials(
    request: MaterialCalculationRequest,
    claude_service: ClaudeMaterialService = Depends(get_claude_service)
):
    """
    Generiere Materialliste für ein Gebäude
    """
    # 1. Erweiterte Gebäudedaten holen
    building_data = await analyze_building_for_scaffolding(request.egid)

    # 2. Manuelle Überschreibungen anwenden
    if request.manual_heights:
        building_data['heights'].update(request.manual_heights)

    # 3. Claude für Materialberechnung aufrufen
    result = await claude_service.generate_material_list(
        building_data=building_data,
        system=request.system,
        load_class=request.load_class,
        width_class=request.width_class
    )

    # 4. In Cache speichern
    await save_calculation(request.egid, result)

    return result
```

---

## 6. Frontend-Erweiterung

### Neuer Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│  1. Adresseingabe                                               │
│     [Bundesplatz 3, Bern                    ] [Suchen]          │
├─────────────────────────────────────────────────────────────────┤
│  2. Gebäudedaten (ScaffoldingCard - bestehend)                  │
│     ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐             │
│     │ 42.3 m  │ │ 380 m²  │ │ 185 m²  │ │ 3D View │             │
│     │Fassade  │ │Gerüst   │ │Grundfl. │ │         │             │
│     └─────────┘ └─────────┘ └─────────┘ └─────────┘             │
│                                                                 │
│     Höhen: Traufe 6.5m │ First 10.2m │ Giebel 3.7m             │
├─────────────────────────────────────────────────────────────────┤
│  3. Gerüst-Konfiguration (NEU)                                  │
│     System:     [Layher Blitz 70 ▼]                             │
│     Lastklasse: [3 - 200 kg/m² ▼]                               │
│     Breite:     [W09 - 0.90m ▼]                                 │
│                                                                 │
│     [✓] Alle Seiten eingerüsten                                 │
│     [ ] Nur ausgewählte Seiten: [Nord] [Ost] [Süd] [West]       │
│                                                                 │
│     [Materialliste generieren]                                  │
├─────────────────────────────────────────────────────────────────┤
│  4. Ergebnis (NEU)                                              │
│     ┌─ Ausmass NPK 114 ─────────────────────────────────────┐   │
│     │ Nordseite:  LA=14.0m × HA=7.5m = 105.00 m²            │   │
│     │ Ostseite:   LA=12.0m × HA=9.3m = 111.60 m² (Giebel)   │   │
│     │ ...                                                    │   │
│     │ Eckzuschläge: 4 × 7.50 m² = 30.00 m²                  │   │
│     │ ─────────────────────────────────────────             │   │
│     │ TOTAL: 463.20 m²                                      │   │
│     └────────────────────────────────────────────────────────┘   │
│                                                                 │
│     ┌─ Materialliste ───────────────────────────────────────┐   │
│     │ Art.Nr.    Bezeichnung              Menge    Gewicht  │   │
│     │ 2622.200   Stellrahmen 2.00m        72 Stk   1'332 kg │   │
│     │ 2626.307   Doppelgeländer 3.07m     96 Stk   1'008 kg │   │
│     │ ...                                                    │   │
│     │ ─────────────────────────────────────────             │   │
│     │ TOTAL: 487 Teile, 9'240 kg                            │   │
│     └────────────────────────────────────────────────────────┘   │
│                                                                 │
│     [PDF Export] [Excel Export] [An Lager senden]               │
└─────────────────────────────────────────────────────────────────┘
```

### React Component

```typescript
// frontend/src/components/MaterialCalculator.tsx

interface MaterialCalculatorProps {
  buildingData: ExtendedScaffoldingData
}

export function MaterialCalculator({ buildingData }: MaterialCalculatorProps) {
  const [system, setSystem] = useState<'blitz70' | 'allround'>('blitz70')
  const [loadClass, setLoadClass] = useState(3)
  const [widthClass, setWidthClass] = useState('W09')
  const [result, setResult] = useState<MaterialCalculationResult | null>(null)
  const [loading, setLoading] = useState(false)

  const handleCalculate = async () => {
    setLoading(true)
    try {
      const response = await fetch('/api/v1/material-calculation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          egid: buildingData.gwr_data.egid,
          system,
          load_class: loadClass,
          width_class: widthClass
        })
      })
      const data = await response.json()
      setResult(data)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="card space-y-6">
      <h3 className="text-lg font-semibold">Materialkalkulation</h3>

      {/* Konfiguration */}
      <div className="grid grid-cols-3 gap-4">
        <select value={system} onChange={e => setSystem(e.target.value)}>
          <option value="blitz70">Layher Blitz 70</option>
          <option value="allround">Layher Allround</option>
        </select>
        {/* ... weitere Selects */}
      </div>

      <button onClick={handleCalculate} disabled={loading}>
        {loading ? 'Berechne...' : 'Materialliste generieren'}
      </button>

      {/* Ergebnisse */}
      {result && (
        <>
          <AusmassTable data={result.ausmass} />
          <MaterialList data={result.material_list} />
          <PersonnelSummary data={result.personnel} />
          <ExportButtons result={result} />
        </>
      )}
    </div>
  )
}
```

---

## 7. Implementierungs-Roadmap

### Phase 1: Prototyping (Sofort)

1. **Claude Web Projekt einrichten**
   - Kontext-Dokumente hochladen (NPK 114, Layher-Katalog, SUVA)
   - Test-Workflows mit echten Gebäudedaten
   - Output-Format validieren

2. **Manuelle Dateneingabe**
   - Gebäudedaten aus geodaten-ch API kopieren
   - Claude generiert Materialliste
   - Ergebnisse dokumentieren

### Phase 2: Backend-Erweiterung (1-2 Wochen)

1. **Layher-Katalog DB**
   - SQLite-Schema erstellen
   - Blitz 70 Daten importieren
   - API-Endpunkt für Katalogabfrage

2. **NPK 114 Calculator**
   - Python-Modul implementieren
   - Unit-Tests schreiben
   - Integration in bestehende API

3. **Höhendaten-Erweiterung**
   - Trauf-/Firsthöhe aus swissBUILDINGS3D
   - Pro-Fassade Höhenberechnung
   - Dachform-Erkennung

### Phase 3: Claude API Integration (2-3 Wochen)

1. **Claude Service**
   - API-Key Management
   - System-Prompt optimieren
   - Response-Parsing

2. **Caching**
   - Berechnungs-Cache
   - Token-Optimierung

3. **Frontend**
   - MaterialCalculator Komponente
   - Export-Funktionen (PDF, Excel)

### Phase 4: Produktionsreife (1-2 Wochen)

1. **Testing**
   - End-to-End Tests
   - Validierung gegen reale Projekte (GL2025 Dokumentation)

2. **Deployment**
   - Railway.app Konfiguration
   - Secrets Management
   - Monitoring

---

## 8. Kosten-Schätzung

### Claude API

| Nutzung | Tokens/Anfrage | Kosten/Anfrage | Monatlich (50 Anfragen) |
|---------|----------------|----------------|-------------------------|
| Material-Berechnung | ~3000 Input + ~2000 Output | ~CHF 0.02 | CHF 1.00 |
| Komplexe Analyse | ~5000 Input + ~4000 Output | ~CHF 0.04 | CHF 2.00 |

**Geschätzte Monatskosten:** CHF 2-5 bei moderater Nutzung

### Entwicklungsaufwand

| Phase | Aufwand |
|-------|---------|
| Phase 1 (Prototyping) | 4-8 Stunden |
| Phase 2 (Backend) | 16-24 Stunden |
| Phase 3 (Claude API) | 16-24 Stunden |
| Phase 4 (Produktion) | 8-16 Stunden |
| **Total** | **44-72 Stunden** |

---

## 9. Risiken und Mitigationen

| Risiko | Wahrscheinlichkeit | Mitigation |
|--------|-------------------|------------|
| Claude API Halluzinationen | Mittel | Strukturierte Prompts, Validierung |
| swissBUILDINGS3D Datenlücken | Mittel | Fallback auf geschätzte Höhen |
| NPK 114 Fehlberechnungen | Niedrig | Unit-Tests, Vergleich mit manuellen Berechnungen |
| API-Kosten steigen | Niedrig | Caching, Token-Optimierung |

---

## 10. Nächste Schritte

1. **Heute:** Claude Web Projekt mit Kontext-Dokumenten einrichten
2. **Diese Woche:** 2-3 Test-Berechnungen mit echten Gebäudedaten
3. **Nächste Woche:** Layher-Katalog DB erstellen
4. **Folgewoche:** NPK 114 Calculator implementieren

---

*Erstellt: 21.12.2025*
*Version: 1.0*
*Autor: Claude Code für Lawil Gerüstbau AG*
