# Claude Code Tasks: geodaten-ch Qualitätsverbesserungen

> **Projekt:** geodaten-ch (C:\Users\vonro\projects\geodaten-ch)
> **Erstellt:** 30.12.2025
> **Priorität:** P0-Fixes zuerst, dann P1-Verbesserungen
> **Kontext:** Basierend auf Qualitätsanalyse der SVG-Pipeline

---

## Projektübersicht

geodaten-ch ist eine FastAPI-Anwendung, die Schweizer Geodaten für Gerüstplanung sammelt und strukturierte Prompts für SVG-Generierung erstellt.

### Relevante Dateien

```
geodaten-ch/
├── app/
│   ├── services/
│   │   ├── smart_building/
│   │   │   ├── service.py          # SmartBuildingService Hauptlogik
│   │   │   ├── known_buildings.py  # Manuell definierte Gebäudedaten
│   │   │   ├── models.py           # Pydantic Models
│   │   │   └── zones.py            # Zonen-Analyse Logik
│   │   ├── swisstopo.py            # swisstopo API Client
│   │   └── roof.py                 # Dach-Analyse
│   └── api/
│       └── routes/
│           └── buildings.py        # API Endpoints
├── CLAUDE.md                       # Projekt-Dokumentation
└── README.md
```

---

## TASK 1: Einsteinhaus Zone korrigieren (P0)

### Problem

Die Zonenhöhe für das Einsteinhaus ist falsch definiert:
- **API-Daten:** Traufe 22.3m, First 26.2m
- **Aktuelle Zone:** 12.0m - 16.0m (FALSCH!)
- **Auswirkung:** SVG zeigt falsches Gebäude mit nur ~16m Höhe

### Lösung

Öffne `app/services/smart_building/known_buildings.py` und korrigiere den Eintrag für das Einsteinhaus.

### Suchkriterium

Suche nach `Kramgasse 49` oder `Einsteinhaus` oder EGID `1230455`.

### Änderung

```python
# VORHER (FALSCH):
"zones": [
    {"name": "Hauptgebäude", "type": "hauptgebaeude", "traufe": 12.0, "first": 16.0}
]

# NACHHER (KORREKT):
"zones": [
    {"name": "Hauptgebäude", "type": "hauptgebaeude", "traufe": 22.0, "first": 26.0}
]
```

### Validierung

Nach der Änderung sollte `max(zone.first) ≈ API-First (26.2m)` sein.

---

## TASK 2: Kunstmuseum Override hinzufügen (P0)

### Problem

Die swissBUILDINGS3D API liefert für das Kunstmuseum Bern komplett falsche Höhendaten:
- **API-Daten:** Traufe 6.7m, First 7.9m (misst nur Nebengebäude!)
- **Realität:** Altbau 15-18m, Neubau 12-15m, Erweiterung 8-10m
- **Auswirkung:** SVG zeigt ein 8m hohes Gebäude statt 18m

### Lösung

Falls das Kunstmuseum noch nicht in `known_buildings.py` existiert, füge es hinzu. Falls es existiert, ergänze das `height_override` Flag.

### Neuer/Aktualisierter Eintrag

```python
# In KNOWN_BUILDINGS dict hinzufügen/aktualisieren:

"KUNSTMUSEUM_BERN": {
    "egid": None,  # Falls EGID bekannt, hier eintragen
    "addresses": ["Hodlerstrasse 8, 3011 Bern", "Hodlerstrasse 8", "Kunstmuseum Bern"],
    "building_name": "Kunstmuseum Bern",
    "building_type": "Museum",
    "architectural_style": "Neoklassizismus / Moderne Erweiterungen",
    "construction_year": 1879,
    "building_shape": "Komplex mit mehreren Baukörpern",
    "building_shape_description": "Der Museumskomplex besteht aus dem historischen Altbau (1879), dem Stettler-Bau (1936) und modernen Erweiterungen. Die Gebäudeteile haben unterschiedliche Höhen.",
    "special_features": ["Historischer Altbau", "Stettler-Erweiterung", "Moderne Anbauten", "Innenhof"],
    
    # KRITISCH: Override für falsche API-Höhen
    "height_override": {
        "enabled": True,
        "reason": "swissBUILDINGS3D misst nur Nebengebäude (7.9m statt 18m)",
        "traufe_override": 15.0,
        "first_override": 18.0
    },
    
    "svg_hints": {
        "grundriss": "Mehrere Baukörper zeigen. Altbau prominent, Erweiterungen als Anbauten.",
        "ansicht": "3 unterschiedliche Gebäudehöhen beachten: Altbau (18m), Stettler (15m), Erweiterung (10m)",
        "schnitt": "Verschiedene Raumhöhen der Museumssäle zeigen."
    },
    "zones": [
        {
            "name": "Altbau (Hauptgebäude)",
            "type": "hauptgebaeude",
            "traufe": 15.0,
            "first": 18.0,
            "sonderkonstruktion": False
        },
        {
            "name": "Stettler-Bau",
            "type": "hauptgebaeude",
            "traufe": 12.0,
            "first": 15.0,
            "sonderkonstruktion": False
        },
        {
            "name": "Moderne Erweiterung",
            "type": "anbau",
            "traufe": 8.0,
            "first": 10.0,
            "sonderkonstruktion": False
        }
    ],
    "complexity": "complex"
}
```

### Zusätzlich: Service-Logik für height_override

In `app/services/smart_building/service.py` muss die `height_override` Logik implementiert werden, falls noch nicht vorhanden:

```python
# In der Methode, die Höhendaten zusammenführt:

def _merge_height_data(self, api_heights: dict, known_building: dict) -> dict:
    """Führt API-Höhen mit known_building Daten zusammen."""
    
    # Prüfe auf height_override
    if known_building and known_building.get("height_override", {}).get("enabled"):
        override = known_building["height_override"]
        return {
            "traufhoehe_m": override.get("traufe_override"),
            "firsthoehe_m": override.get("first_override"),
            "height_source": "manual_override",
            "height_warning": override.get("reason")
        }
    
    # Sonst API-Daten verwenden
    return {
        "traufhoehe_m": api_heights.get("traufhoehe_m"),
        "firsthoehe_m": api_heights.get("firsthoehe_m"),
        "height_source": "swissBUILDINGS3D",
        "height_warning": None
    }
```

---

## TASK 3: Höhen-Validierung implementieren (P1)

### Problem

Es gibt keine automatische Prüfung, ob Zonenhöhen mit API-Höhen konsistent sind. Dies führt zu unentdeckten Datenfehlern wie beim Einsteinhaus.

### Lösung

Implementiere eine Validierungsfunktion in `app/services/smart_building/service.py` oder `zones.py`.

### Implementation

```python
# Neue Datei oder in bestehende einfügen:
# app/services/smart_building/validation.py

from typing import List, Optional
from dataclasses import dataclass

@dataclass
class HeightValidationResult:
    is_valid: bool
    warnings: List[str]
    errors: List[str]

def validate_zone_heights(
    api_traufe: float,
    api_first: float,
    zones: List[dict],
    tolerance_percent: float = 50.0
) -> HeightValidationResult:
    """
    Validiert Zonenhöhen gegen API-Höhen.
    
    Regeln:
    1. Keine Zone sollte > 150% des API-First sein (außer Türme)
    2. Mindestens eine Zone sollte nahe der API-Traufe sein
    3. Zone < API-Traufe ist ein Fehler (außer bei Arkaden/Anbauten)
    
    Args:
        api_traufe: Traufhöhe aus swissBUILDINGS3D
        api_first: Firsthöhe aus swissBUILDINGS3D
        zones: Liste der Zonen mit 'name', 'type', 'traufe', 'first'
        tolerance_percent: Toleranz für Abweichungen (default 50%)
    
    Returns:
        HeightValidationResult mit Warnings und Errors
    """
    warnings = []
    errors = []
    
    if not zones:
        return HeightValidationResult(True, [], [])
    
    max_zone_height = max(z.get("first", 0) for z in zones)
    min_zone_height = min(z.get("traufe", float("inf")) for z in zones)
    
    # Regel 1: Zone deutlich höher als API-First
    if max_zone_height > api_first * 1.5:
        # Erlaubt für Türme und Kuppeln
        high_zones = [z for z in zones if z.get("first", 0) > api_first * 1.5]
        for zone in high_zones:
            if zone.get("type") not in ["turm", "kuppel"]:
                warnings.append(
                    f"Zone '{zone['name']}' ({zone['first']}m) überschreitet API-First "
                    f"({api_first}m) um >50% - ist das ein Turm/Kuppel?"
                )
    
    # Regel 2: Hauptgebäude-Zone sollte nahe API-Traufe sein
    hauptgebaeude_zones = [z for z in zones if z.get("type") == "hauptgebaeude"]
    if hauptgebaeude_zones:
        closest_to_api = min(
            hauptgebaeude_zones,
            key=lambda z: abs(z.get("first", 0) - api_first)
        )
        deviation = abs(closest_to_api.get("first", 0) - api_first) / api_first * 100
        if deviation > tolerance_percent:
            warnings.append(
                f"Hauptgebäude-Zone '{closest_to_api['name']}' weicht {deviation:.0f}% "
                f"von API-First ab - Daten prüfen!"
            )
    
    # Regel 3: Zone niedriger als API-Traufe (Fehler!)
    for zone in zones:
        if zone.get("type") in ["hauptgebaeude"]:
            if zone.get("first", 0) < api_traufe * 0.8:
                errors.append(
                    f"FEHLER: Zone '{zone['name']}' ({zone['first']}m) ist niedriger "
                    f"als API-Traufe ({api_traufe}m) - Zone-Daten korrigieren!"
                )
    
    is_valid = len(errors) == 0
    return HeightValidationResult(is_valid, warnings, errors)
```

### Integration in SmartBuildingService

```python
# In service.py, nach dem Laden der Zonen:

from .validation import validate_zone_heights, HeightValidationResult

class SmartBuildingService:
    
    def _process_building(self, address: str) -> BuildingBundle:
        # ... bestehender Code ...
        
        # Nach Zonen-Laden:
        if bundle.zones and bundle.traufhoehe_m and bundle.firsthoehe_m:
            validation = validate_zone_heights(
                api_traufe=bundle.traufhoehe_m,
                api_first=bundle.firsthoehe_m,
                zones=bundle.zones
            )
            
            # Warnings zum Bundle hinzufügen
            bundle.validation_warnings = validation.warnings
            bundle.validation_errors = validation.errors
            
            if validation.errors:
                logger.warning(f"Validierungsfehler für {address}: {validation.errors}")
        
        return bundle
```

---

## TASK 4: height_source Flag für Debugging (P1)

### Problem

Es ist nicht nachvollziehbar, woher die Höhendaten stammen (API, Cache, Schätzung, Override).

### Lösung

Füge ein `height_source` Feld zum BuildingBundle Model hinzu.

### Änderung in models.py

```python
# In app/services/smart_building/models.py

from enum import Enum

class HeightSource(str, Enum):
    SWISS_BUILDINGS_3D = "swissBUILDINGS3D"
    SWISS_BUILDINGS_3D_CACHE = "swissBUILDINGS3D_cache"
    GWR_ESTIMATED = "gwr_estimated"
    MANUAL_OVERRIDE = "manual_override"
    KNOWN_BUILDINGS = "known_buildings"
    UNKNOWN = "unknown"

class BuildingBundle(BaseModel):
    # ... bestehende Felder ...
    
    # Neue Felder für Höhen-Tracking
    height_source: Optional[HeightSource] = HeightSource.UNKNOWN
    height_warning: Optional[str] = None
    validation_warnings: List[str] = []
    validation_errors: List[str] = []
```

### Nutzung im Prompt

```python
# In der Prompt-Generierung:

if bundle.height_source == HeightSource.MANUAL_OVERRIDE:
    prompt += f"\n> ⚠️ HINWEIS: Höhendaten manuell überschrieben. Grund: {bundle.height_warning}"
elif bundle.height_source == HeightSource.GWR_ESTIMATED:
    prompt += f"\n> ⚠️ HINWEIS: Höhen geschätzt aus GWR-Geschosszahl (weniger genau)"
```

---

## TASK 5: Polygon-Form-Analyse (P2)

### Problem

Das Polygon hat viele Punkte, aber keine semantische Erkennung für U-Form, L-Form, etc. Die Form kommt aktuell nur aus `known_buildings.py`.

### Lösung

Implementiere eine einfache Konvexitäts-Analyse.

### Implementation

```python
# Neue Datei: app/services/smart_building/polygon_analysis.py

from typing import List, Tuple
from shapely.geometry import Polygon as ShapelyPolygon
from shapely.ops import unary_union

def analyze_building_shape(polygon_coords: List[Tuple[float, float]]) -> dict:
    """
    Analysiert die Grundrissform eines Gebäudes.
    
    Args:
        polygon_coords: Liste von (x, y) Koordinaten
    
    Returns:
        dict mit shape, concavity_ratio, description
    """
    if len(polygon_coords) < 4:
        return {"shape": "unknown", "concavity_ratio": 1.0, "description": "Zu wenige Punkte"}
    
    # Shapely Polygon erstellen
    poly = ShapelyPolygon(polygon_coords)
    if not poly.is_valid:
        poly = poly.buffer(0)  # Fix self-intersections
    
    # Convex Hull berechnen
    convex_hull = poly.convex_hull
    
    # Konvexitäts-Verhältnis
    concavity_ratio = poly.area / convex_hull.area if convex_hull.area > 0 else 1.0
    
    # Form bestimmen
    if concavity_ratio > 0.95:
        shape = "rechteckig"
        description = "Einfacher rechteckiger Grundriss"
    elif concavity_ratio > 0.85:
        shape = "L-Form"
        description = "L-förmiger Grundriss mit einer Einbuchtung"
    elif concavity_ratio > 0.70:
        shape = "U-Form"
        description = "U-förmiger Grundriss mit Innenhof/Ehrenhof"
    elif concavity_ratio > 0.55:
        shape = "H-Form"
        description = "H-förmiger Grundriss mit zwei Innenhöfen"
    else:
        shape = "komplex"
        description = "Komplexer Grundriss mit mehreren Einbuchtungen"
    
    # Bounding Box Aspektverhältnis
    minx, miny, maxx, maxy = poly.bounds
    width = maxx - minx
    height = maxy - miny
    aspect_ratio = max(width, height) / min(width, height) if min(width, height) > 0 else 1.0
    
    return {
        "shape": shape,
        "concavity_ratio": round(concavity_ratio, 3),
        "description": description,
        "bounding_box": {
            "width_m": round(width, 1),
            "height_m": round(height, 1),
            "aspect_ratio": round(aspect_ratio, 2)
        },
        "polygon_points": len(polygon_coords)
    }
```

### Dependencies

```bash
pip install shapely --break-system-packages
```

---

## TASK 6: Testfälle für Validierung

### Testdatei erstellen

```python
# tests/test_height_validation.py

import pytest
from app.services.smart_building.validation import validate_zone_heights

class TestHeightValidation:
    
    def test_valid_bundeshaus(self):
        """Bundeshaus: Zonen korrekt, Kuppel über First erlaubt"""
        result = validate_zone_heights(
            api_traufe=53.2,
            api_first=62.6,
            zones=[
                {"name": "Arkaden", "type": "arkade", "traufe": 6.0, "first": 6.0},
                {"name": "Hauptgebäude", "type": "hauptgebaeude", "traufe": 25.0, "first": 30.0},
                {"name": "Kuppel", "type": "kuppel", "traufe": 30.0, "first": 64.0}
            ]
        )
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_invalid_einsteinhaus_old(self):
        """Einsteinhaus mit falschen Zone-Daten sollte Fehler werfen"""
        result = validate_zone_heights(
            api_traufe=22.3,
            api_first=26.2,
            zones=[
                {"name": "Hauptgebäude", "type": "hauptgebaeude", "traufe": 12.0, "first": 16.0}
            ]
        )
        assert not result.is_valid
        assert any("niedriger" in e for e in result.errors)
    
    def test_valid_einsteinhaus_fixed(self):
        """Einsteinhaus mit korrigierten Zone-Daten"""
        result = validate_zone_heights(
            api_traufe=22.3,
            api_first=26.2,
            zones=[
                {"name": "Hauptgebäude", "type": "hauptgebaeude", "traufe": 22.0, "first": 26.0}
            ]
        )
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_warning_zone_much_higher_than_api(self):
        """Warnung wenn Zone deutlich höher als API (kein Turm)"""
        result = validate_zone_heights(
            api_traufe=15.0,
            api_first=18.0,
            zones=[
                {"name": "Hauptgebäude", "type": "hauptgebaeude", "traufe": 15.0, "first": 30.0}
            ]
        )
        assert result.is_valid  # Nur Warnung, kein Fehler
        assert len(result.warnings) > 0
```

---

## Zusammenfassung: Reihenfolge der Umsetzung

| # | Task | Priorität | Aufwand | Datei(en) |
|---|------|-----------|---------|-----------|
| 1 | Einsteinhaus Zone korrigieren | P0 | 5 Min | `known_buildings.py` |
| 2 | Kunstmuseum Override | P0 | 15 Min | `known_buildings.py`, `service.py` |
| 3 | Höhen-Validierung | P1 | 2 Std | Neue `validation.py`, `service.py` |
| 4 | height_source Flag | P1 | 1 Std | `models.py`, `service.py` |
| 5 | Polygon-Form-Analyse | P2 | 3 Std | Neue `polygon_analysis.py` |
| 6 | Testfälle | P1 | 1 Std | `tests/test_height_validation.py` |

---

## Hinweise für Claude Code

1. **Vor Änderungen:** Lies zuerst `CLAUDE.md` im Projektroot für Projektkontext
2. **Backup:** Erstelle vor Änderungen an `known_buildings.py` eine Kopie
3. **Tests:** Führe nach P0-Fixes die bestehenden Tests aus (`pytest`)
4. **Logging:** Nutze das bestehende Logger-Setup (`from app.core.logging import logger`)

---

*Dokumentation erstellt: 30.12.2025*
*Für: Claude Code in C:\Users\vonro\projects\geodaten-ch*
