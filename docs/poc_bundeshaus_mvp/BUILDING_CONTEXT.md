# BUILDING_CONTEXT.md - Gebäude-Kontext-System

> **Version:** 1.0
> **Datum:** 24.12.2025

## Problem

Schweizer Geodaten liefern für komplexe Gebäude unzureichende Informationen:

| Datenquelle | Was sie liefert | Was fehlt |
|-------------|-----------------|-----------|
| geodienste.ch | 1 Polygon (Grundriss) | Keine Gebäudeteil-Trennung |
| swissBUILDINGS3D | 1 globale Höhe | Keine Höhen pro Gebäudeteil |
| GWR | Kategorie, Geschosse | Keine Geometrie-Details |

**Beispiel Bundeshaus:**
- geodienste.ch: 1 komplexes Polygon
- swissBUILDINGS3D: 14.5m Traufhöhe (= Arkaden!)
- Realität: Arkaden 14m, Parlament 25m, Türme 36m, Kuppel 64m

---

## Lösung: Building Context System

Ein System, das:
1. **Automatisch** einfache Gebäude erkennt (rechteckig, eine Höhe)
2. **Bei Bedarf** komplexe Gebäude mit Claude analysiert
3. **Speichert** den Kontext für Wiederverwendung
4. **Ermöglicht** manuelle Korrekturen

---

## Architektur

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    BUILDING CONTEXT SYSTEM                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  LAYER 1: DATA AGGREGATION                                        │ │
│  │                                                                   │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │ │
│  │  │ Polygon     │  │ Höhendaten  │  │ GWR         │               │ │
│  │  │ (WFS)       │  │ (3D/ALTI)   │  │ (Kategorie) │               │ │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘               │ │
│  │         │                │                │                       │ │
│  │         └────────────────┼────────────────┘                       │ │
│  │                          ▼                                        │ │
│  │              ┌───────────────────────┐                           │ │
│  │              │   RAW BUILDING DATA   │                           │ │
│  │              └───────────┬───────────┘                           │ │
│  └──────────────────────────┼────────────────────────────────────────┘ │
│                             │                                          │
│                             ▼                                          │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  LAYER 2: COMPLEXITY DETECTION                                    │ │
│  │                                                                   │ │
│  │  Kriterien für "komplex":                                        │ │
│  │  • Polygon hat >8 Ecken                                          │ │
│  │  • Grundfläche >500m²                                            │ │
│  │  • Gebäudekategorie: Kirche, öffentlich, Industrie               │ │
│  │  • Einbuchtungen/Ausbuchtungen im Polygon                        │ │
│  │  • Bekannte Adresse (Bundeshaus, Münster, etc.)                  │ │
│  │                                                                   │ │
│  │  ┌─────────────────┐     ┌─────────────────┐                     │ │
│  │  │ EINFACH         │     │ KOMPLEX         │                     │ │
│  │  │ → 1 Zone        │     │ → Analyse nötig │                     │ │
│  │  │ → Auto-Context  │     │ → Claude/Manual │                     │ │
│  │  └────────┬────────┘     └────────┬────────┘                     │ │
│  └───────────┼───────────────────────┼───────────────────────────────┘ │
│              │                       │                                 │
│              ▼                       ▼                                 │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  LAYER 3: CONTEXT CREATION                                        │ │
│  │                                                                   │ │
│  │  Option A: AUTO (einfache Gebäude)                               │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │ • 1 Zone = gesamtes Polygon                                 │ │ │
│  │  │ • Höhe aus swissBUILDINGS3D                                 │ │ │
│  │  │ • Typ = "hauptgebaeude"                                     │ │ │
│  │  │ • Confidence = 1.0                                          │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  │                                                                   │ │
│  │  Option B: CLAUDE (komplexe Gebäude)                             │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │ Input:                                                      │ │ │
│  │  │ • Polygon-Koordinaten                                       │ │ │
│  │  │ • Verfügbare Höhendaten                                     │ │ │
│  │  │ • Gebäudekategorie                                          │ │ │
│  │  │ • Optional: Orthofoto (Base64)                              │ │ │
│  │  │                                                              │ │ │
│  │  │ Output:                                                      │ │ │
│  │  │ • Zonen mit Polygon-Punkt-Indizes                           │ │ │
│  │  │ • Geschätzte Höhen pro Zone                                 │ │ │
│  │  │ • Typ pro Zone                                              │ │ │
│  │  │ • Confidence Score                                          │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  │                                                                   │ │
│  │  Option C: MANUAL (User-Eingabe)                                 │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │ • User zeichnet Zonen im Frontend                           │ │ │
│  │  │ • User gibt Höhen ein                                       │ │ │
│  │  │ • User wählt Typen                                          │ │ │
│  │  │ • Confidence = 1.0 (validated)                              │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                             │                                          │
│                             ▼                                          │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  LAYER 4: STORAGE                                                 │ │
│  │                                                                   │ │
│  │  SQLite: building_contexts.db                                    │ │
│  │                                                                   │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │ building_contexts                                           │ │ │
│  │  │ ─────────────────────────────────────────────────────────── │ │ │
│  │  │ egid            TEXT PRIMARY KEY                            │ │ │
│  │  │ context_json    TEXT (JSON)                                 │ │ │
│  │  │ source          TEXT (auto|claude|manual)                   │ │ │
│  │  │ confidence      REAL                                        │ │ │
│  │  │ validated       INTEGER (0|1)                               │ │ │
│  │  │ created_at      TEXT                                        │ │ │
│  │  │ updated_at      TEXT                                        │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                             │                                          │
│                             ▼                                          │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  LAYER 5: CONSUMPTION                                             │ │
│  │                                                                   │ │
│  │  SVG-Generator                                                    │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │ IF context.zones.length > 1:                                │ │ │
│  │  │   → Zonen separat zeichnen                                  │ │ │
│  │  │   → Farbcodierung nach Typ                                  │ │ │
│  │  │   → Höhen pro Zone                                          │ │ │
│  │  │ ELSE:                                                        │ │ │
│  │  │   → Einfache Darstellung                                    │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  │                                                                   │ │
│  │  Gerüst-Berechnung                                               │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │ FOR each zone in context.zones:                             │ │ │
│  │  │   IF zone.beruesten:                                        │ │ │
│  │  │     → NPK 114 Ausmass mit zone.hoehe_m                      │ │ │
│  │  │     → Material-Berechnung                                   │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Datenmodell

### BuildingContext (Haupt-Struktur)

```python
from pydantic import BaseModel
from typing import Literal, Optional
from datetime import datetime

class BuildingZone(BaseModel):
    """Eine Höhenzone innerhalb eines Gebäudes"""
    
    # Identifikation
    id: str                                    # "zone_1", "zone_2"
    name: str                                  # "Hauptgebäude", "Westturm"
    type: Literal[
        "hauptgebaeude",
        "anbau",
        "turm",
        "kuppel",
        "arkade",
        "vordach",
        "treppenhaus",
        "garage",
        "unknown"
    ]
    
    # Geometrie-Referenz
    # Option A: Indizes der Punkte im Hauptpolygon
    polygon_point_indices: list[int] | None    # [0, 1, 2, 3]
    
    # Option B: Eigenes Sub-Polygon (für komplexe Fälle)
    sub_polygon: list[tuple[float, float]] | None  # [(e, n), ...]
    
    # Höhendaten
    traufhoehe_m: float | None                 # Traufhöhe (wenn bekannt)
    firsthoehe_m: float | None                 # Firsthöhe (wenn bekannt)
    gebaeudehoehe_m: float                     # Effektive Höhe für Berechnung
    
    # Terrain (für Hanglagen)
    terrain_hoehe_m: float | None              # Mittlere Geländehöhe
    terrain_min_m: float | None                # Tiefster Punkt
    terrain_max_m: float | None                # Höchster Punkt
    
    # Gerüst-Relevanz
    fassaden_ids: list[str]                    # ["N", "E", "S"]
    beruesten: bool = True                     # Soll eingerüstet werden?
    sonderkonstruktion: bool = False           # Spezialgerüst nötig?
    
    # Metadaten
    confidence: float                          # 0.0 - 1.0
    notes: str | None                          # Freitext


class BuildingContext(BaseModel):
    """Vollständiger Kontext für ein Gebäude"""
    
    # Identifikation
    egid: str
    adresse: str | None
    
    # Zonen
    zones: list[BuildingZone]
    
    # Beziehungen
    zone_adjacency: dict[str, list[str]] | None  # {"zone_1": ["zone_2"]}
    
    # Gebäude-Eigenschaften (aggregiert)
    complexity: Literal["simple", "moderate", "complex"]
    has_height_variations: bool
    has_setbacks: bool                         # Rücksprünge
    has_towers: bool
    has_annexes: bool                          # Anbauten
    has_special_features: bool                 # Kuppeln, Arkaden, etc.
    
    # Terrain
    terrain_slope_percent: float | None        # Gefälle
    terrain_aspect: str | None                 # "N", "NE", etc.
    
    # Quelle und Qualität
    source: Literal["auto", "claude", "manual"]
    confidence: float                          # Gesamt-Confidence
    validated_by_user: bool
    reasoning: str | None                      # Begründung (von Claude)
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
```

### Beispiel: Einfaches Gebäude (EFH)

```json
{
  "egid": "1234567",
  "adresse": "Musterstrasse 10, 3000 Bern",
  "zones": [
    {
      "id": "zone_1",
      "name": "Hauptgebäude",
      "type": "hauptgebaeude",
      "polygon_point_indices": [0, 1, 2, 3],
      "sub_polygon": null,
      "traufhoehe_m": 6.5,
      "firsthoehe_m": 9.0,
      "gebaeudehoehe_m": 9.0,
      "terrain_hoehe_m": 520.0,
      "terrain_min_m": 520.0,
      "terrain_max_m": 520.0,
      "fassaden_ids": ["N", "E", "S", "W"],
      "beruesten": true,
      "sonderkonstruktion": false,
      "confidence": 1.0,
      "notes": null
    }
  ],
  "zone_adjacency": null,
  "complexity": "simple",
  "has_height_variations": false,
  "has_setbacks": false,
  "has_towers": false,
  "has_annexes": false,
  "has_special_features": false,
  "terrain_slope_percent": 0.0,
  "terrain_aspect": null,
  "source": "auto",
  "confidence": 1.0,
  "validated_by_user": false,
  "reasoning": null,
  "created_at": "2025-12-24T10:00:00Z",
  "updated_at": "2025-12-24T10:00:00Z"
}
```

### Beispiel: Komplexes Gebäude (Bundeshaus)

```json
{
  "egid": "1230564",
  "adresse": "Bundesplatz 3, 3011 Bern",
  "zones": [
    {
      "id": "zone_arkade",
      "name": "Arkaden",
      "type": "arkade",
      "polygon_point_indices": [0, 1, 2, 3],
      "sub_polygon": null,
      "traufhoehe_m": 14.5,
      "firsthoehe_m": null,
      "gebaeudehoehe_m": 14.5,
      "terrain_hoehe_m": 540.0,
      "fassaden_ids": ["S"],
      "beruesten": true,
      "sonderkonstruktion": false,
      "confidence": 0.9,
      "notes": "Arkaden-Bereich zur Bundesgasse"
    },
    {
      "id": "zone_parlament",
      "name": "Parlamentsgebäude",
      "type": "hauptgebaeude",
      "polygon_point_indices": [4, 5, 6, 7, 8, 9],
      "sub_polygon": null,
      "traufhoehe_m": 25.0,
      "firsthoehe_m": 28.0,
      "gebaeudehoehe_m": 25.0,
      "terrain_hoehe_m": 540.0,
      "fassaden_ids": ["N", "E", "W"],
      "beruesten": true,
      "sonderkonstruktion": false,
      "confidence": 0.85,
      "notes": "Hauptfassaden des Parlamentsgebäudes"
    },
    {
      "id": "zone_turm_w",
      "name": "Westturm",
      "type": "turm",
      "polygon_point_indices": [10, 11, 12, 13],
      "sub_polygon": null,
      "traufhoehe_m": 36.0,
      "firsthoehe_m": 38.0,
      "gebaeudehoehe_m": 36.0,
      "terrain_hoehe_m": 540.0,
      "fassaden_ids": ["N", "W"],
      "beruesten": true,
      "sonderkonstruktion": true,
      "confidence": 0.8,
      "notes": "Hoher Turm, evtl. Hängegerüst oder Fassadenlift"
    },
    {
      "id": "zone_turm_e",
      "name": "Ostturm",
      "type": "turm",
      "polygon_point_indices": [14, 15, 16, 17],
      "sub_polygon": null,
      "traufhoehe_m": 36.0,
      "firsthoehe_m": 38.0,
      "gebaeudehoehe_m": 36.0,
      "terrain_hoehe_m": 540.0,
      "fassaden_ids": ["N", "E"],
      "beruesten": true,
      "sonderkonstruktion": true,
      "confidence": 0.8,
      "notes": null
    },
    {
      "id": "zone_kuppel",
      "name": "Kuppel",
      "type": "kuppel",
      "polygon_point_indices": null,
      "sub_polygon": [[600450, 199550], [600460, 199560], [600450, 199570], [600440, 199560]],
      "traufhoehe_m": null,
      "firsthoehe_m": 64.0,
      "gebaeudehoehe_m": 64.0,
      "terrain_hoehe_m": 540.0,
      "fassaden_ids": [],
      "beruesten": false,
      "sonderkonstruktion": true,
      "confidence": 0.7,
      "notes": "Kuppel nicht mit Standgerüst einrüstbar, Spezialgerüst erforderlich"
    }
  ],
  "zone_adjacency": {
    "zone_arkade": ["zone_parlament"],
    "zone_parlament": ["zone_arkade", "zone_turm_w", "zone_turm_e", "zone_kuppel"],
    "zone_turm_w": ["zone_parlament"],
    "zone_turm_e": ["zone_parlament"],
    "zone_kuppel": ["zone_parlament"]
  },
  "complexity": "complex",
  "has_height_variations": true,
  "has_setbacks": true,
  "has_towers": true,
  "has_annexes": false,
  "has_special_features": true,
  "terrain_slope_percent": 0.5,
  "terrain_aspect": null,
  "source": "claude",
  "confidence": 0.82,
  "validated_by_user": false,
  "reasoning": "Das Bundeshaus zeigt eine komplexe Struktur mit mehreren Höhenzonen. Die Arkaden (14.5m) bilden den tiefsten Bereich. Das Hauptgebäude (25m) enthält die Parlamentssäle. Zwei symmetrische Türme (36m) flankieren das Gebäude. Die zentrale Kuppel (64m) ist das höchste Element und erfordert Speziallösungen.",
  "created_at": "2025-12-24T10:00:00Z",
  "updated_at": "2025-12-24T10:00:00Z"
}
```

---

## API-Endpunkte

### GET /api/v1/building/context/{egid}

Gibt den Kontext zurück, falls vorhanden.

**Query-Parameter:**
- `create_if_missing` (bool): Automatisch erstellen wenn nicht vorhanden
- `analyze` (bool): Claude-Analyse triggern wenn komplex

**Response:**
```json
{
  "status": "found|created|not_found",
  "context": { ... },
  "needs_validation": true
}
```

### POST /api/v1/building/context/{egid}/analyze

Triggert Claude-Analyse für komplexes Gebäude.

**Request Body:**
```json
{
  "include_orthofoto": false,
  "force_reanalyze": false
}
```

**Response:**
```json
{
  "status": "success",
  "context": { ... },
  "cost_estimate_usd": 0.02
}
```

### PUT /api/v1/building/context/{egid}

Aktualisiert den Kontext (manuelle Korrekturen).

**Request Body:**
```json
{
  "zones": [ ... ],
  "validated": true
}
```

### DELETE /api/v1/building/context/{egid}

Löscht den Kontext (Reset).

---

## Claude-Prompt

```python
CONTEXT_ANALYSIS_PROMPT = """
Du analysierst ein Schweizer Gebäude für die Gerüstplanung.

## Eingabedaten

### Grundriss-Polygon (LV95 Koordinaten)
```json
{polygon_json}
```

### Polygon-Eigenschaften
- Anzahl Ecken: {num_vertices}
- Grundfläche: {area_m2:.1f} m²
- Umfang: {perimeter_m:.1f} m
- Bounding Box: {bbox_width:.1f}m × {bbox_height:.1f}m

### Verfügbare Höhendaten
- Globale Traufhöhe: {traufhoehe_m} m (swissBUILDINGS3D)
- Globale Firsthöhe: {firsthoehe_m} m
- Globale Gebäudehöhe: {gebaeudehoehe_m} m

### Gebäude-Metadaten (GWR)
- EGID: {egid}
- Adresse: {adresse}
- Kategorie: {gkat} ({gkat_text})
- Geschosse: {gastw}
- Baujahr: {gbauj}
- Grundfläche (GWR): {garea} m²

{orthofoto_section}

## Deine Aufgabe

Analysiere das Gebäude und teile es in Höhenzonen auf.

### Schritt 1: Komplexität bewerten
- Ist das Polygon annähernd rechteckig? → wahrscheinlich 1 Zone
- Hat es Einbuchtungen, L-Form, U-Form? → mehrere Zonen möglich
- Ist die Gebäudekategorie speziell (Kirche, öffentlich)? → Türme/Kuppeln möglich

### Schritt 2: Zonen identifizieren
Für jede Zone bestimme:
1. **Welche Polygon-Punkte** gehören dazu (als Indizes 0, 1, 2, ...)
2. **Geschätzte Höhe** basierend auf:
   - Globale Höhe als Basis
   - Kategorie-spezifische Anpassungen
   - Proportionale Schätzung bei Anbauten
3. **Typ** der Zone

### Höhen-Schätzung Richtlinien
| Situation | Schätzung |
|-----------|-----------|
| Einfaches Gebäude | Globale Höhe verwenden |
| Anbau/Garage | 60-80% der Haupthöhe oder 3-5m |
| Turm (Kirche) | 2-3× Schiffhöhe |
| Arkaden/Laubengang | 4-5m |
| Kuppel | Firsthöhe + 50-100% |

### Schritt 3: Confidence bewerten
- 0.9-1.0: Sehr sicher (einfache Geometrie, klare Struktur)
- 0.7-0.9: Sicher (typische Struktur erkannt)
- 0.5-0.7: Unsicher (Annahmen getroffen)
- <0.5: Sehr unsicher (User-Validierung empfohlen)

## Output-Format

Antworte NUR mit validem JSON:

```json
{{
  "complexity": "simple|moderate|complex",
  "zones": [
    {{
      "id": "zone_1",
      "name": "Hauptgebäude",
      "type": "hauptgebaeude|anbau|turm|kuppel|arkade|vordach|treppenhaus|garage|unknown",
      "polygon_point_indices": [0, 1, 2, 3],
      "traufhoehe_m": 12.5,
      "firsthoehe_m": 15.0,
      "gebaeudehoehe_m": 15.0,
      "fassaden_ids": ["N", "E", "S", "W"],
      "beruesten": true,
      "sonderkonstruktion": false,
      "confidence": 0.9,
      "notes": null
    }}
  ],
  "zone_adjacency": {{
    "zone_1": ["zone_2"]
  }},
  "has_height_variations": false,
  "has_setbacks": false,
  "has_towers": false,
  "has_annexes": false,
  "has_special_features": false,
  "overall_confidence": 0.9,
  "reasoning": "Kurze Begründung der Analyse"
}}
```

## Wichtige Regeln

1. Bei einfachen rechteckigen Gebäuden: NUR 1 Zone erstellen
2. Erfinde KEINE Höhen ohne Grundlage - nutze die globale Höhe als Basis
3. Bei Unsicherheit: Weniger Zonen sind besser als falsche Zonen
4. `polygon_point_indices` müssen gültige Indizes sein (0 bis {max_index})
5. Jeder Polygon-Punkt sollte zu genau einer Zone gehören
6. `fassaden_ids` basieren auf der Ausrichtung: N, NE, E, SE, S, SW, W, NW
"""
```

---

## Komplexitäts-Erkennung

```python
def detect_complexity(polygon: list, gwr_data: dict) -> str:
    """
    Erkennt die Komplexität eines Gebäudes.
    
    Returns: "simple", "moderate", "complex"
    """
    
    num_vertices = len(polygon)
    area = calculate_area(polygon)
    bbox = calculate_bbox(polygon)
    aspect_ratio = bbox.width / bbox.height if bbox.height > 0 else 1
    
    # Kategorie-basierte Komplexität
    complex_categories = [
        1040,  # Gebäude mit Nebennutzung
        1060,  # Gebäude für Bildung/Kultur
        1080,  # Gebäude für Gesundheit
    ]
    
    # Entscheidungslogik
    is_simple = (
        num_vertices <= 6 and
        area < 300 and
        0.5 < aspect_ratio < 2.0 and
        gwr_data.get('gkat') not in complex_categories
    )
    
    is_complex = (
        num_vertices > 12 or
        area > 1000 or
        gwr_data.get('gkat') in complex_categories or
        has_concave_sections(polygon)
    )
    
    if is_simple:
        return "simple"
    elif is_complex:
        return "complex"
    else:
        return "moderate"
```

---

## Frontend-Integration

### Zonen-Editor (React Component)

```typescript
interface ZoneEditorProps {
  egid: string;
  context: BuildingContext;
  onSave: (context: BuildingContext) => void;
}

// Features:
// - Grundriss mit farbcodierten Zonen anzeigen
// - Zonen anklickbar zum Bearbeiten
// - Höhen-Slider pro Zone
// - Typ-Dropdown
// - "Analysieren" Button für Claude
// - "Bestätigen" Button für Validierung
```

### Workflow im Frontend

```
1. User gibt Adresse ein
   ↓
2. Backend liefert Gebäudedaten
   ↓
3. Frontend prüft: Kontext vorhanden?
   ├─ JA → Zonen anzeigen
   └─ NEIN → "Analysieren" Button anzeigen
              ↓
4. User klickt "Analysieren"
   ↓
5. Backend ruft Claude API auf
   ↓
6. Kontext wird angezeigt (farbcodierte Zonen)
   ↓
7. User kann korrigieren
   ↓
8. User klickt "Bestätigen"
   ↓
9. Kontext wird gespeichert (validated=true)
   ↓
10. SVG-Generierung nutzt Kontext
```

---

## Kosten-Schätzung

### Claude API
- Sonnet 4: ~$3/1M input tokens, ~$15/1M output tokens
- Pro Analyse: ~2000 input tokens, ~500 output tokens
- **Kosten pro Analyse: ~$0.01-0.02**

### Optimierungen
- Caching: Einmal analysiert = gespeichert
- Batch: Mehrere Gebäude gleichzeitig
- Einfache Gebäude: Kein Claude nötig

---

## Nächste Schritte

1. **Datenbank-Schema** erstellen
2. **Auto-Context** für einfache Gebäude
3. **Claude-Integration** für komplexe Gebäude
4. **Frontend Zonen-Editor**
5. **SVG-Generator** erweitern für Zonen
