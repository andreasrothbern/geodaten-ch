# geodaten-ch API Refactoring: swissBUILDINGS3D Integration

## Version 1.0 | 31. Dezember 2025

---

## 1. Problem-Analyse

### 1.1 Aktueller Zustand (FEHLERHAFT)

Die geodaten-ch API holt aktuell Gebäudedaten aus dem **GWR-Layer** (`ch.bfs.gebaeude_wohnungs_register`), der nur:

```
✗ Punkt-Koordinaten (kein Polygon)
✗ Keine 3D-Geometrie
✗ Keine Dachform
✗ Keine exakten Höhen (nur Geschosszahl)
```

**Workaround bisher:** Manuelle Höhendaten in `known_buildings.py` für bekannte Gebäude.

### 1.2 Was wir brauchen

**swissBUILDINGS3D 3.0 Beta** liefert:

```
✓ 3D-Gebäudevolumen (LOD2)
✓ Exakte Trauf- und Firsthöhe
✓ Dachgeometrie (Flächen, Neigung, Ausrichtung)
✓ Gebäude-Polygon (Grundriss)
✓ EGID-Verknüpfung (in vielen Kantonen)
```

### 1.3 Verfügbarkeit nach Kanton (Stand Nov 2025)

| Kanton | EGID integriert | Status |
|--------|-----------------|--------|
| AI, AR, GL, TG | ✅ Ja | Seit Dez 2022 |
| BL, BS | ✅ Ja | Seit Dez 2023 |
| BE, JU | ✅ Ja | Seit Juni 2024 |
| SG, SZ | ✅ Ja | Seit Nov 2024 |
| LU, SO | ✅ Ja | Seit Nov 2025 |
| FR, NE, SH | ✅ Ja | Seit Juni 2025 |
| Übrige | ⚠️ Nur Geometrie | Kein EGID |

**Wichtig für Bern:** ✅ EGID verfügbar seit Juni 2024

---

## 2. Neue Datenquellen-Architektur

### 2.1 Ziel-Architektur

```
┌─────────────────────────────────────────────────────────────────┐
│                     NEUE DATENQUELLEN                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  PRIMÄR: swissBUILDINGS3D 3.0 Beta                      │   │
│  │  ─────────────────────────────────────────────────────  │   │
│  │  • 3D-Geometrie (Volumen, Dach, Fassaden)               │   │
│  │  • Exakte Höhen (Traufe, First)                         │   │
│  │  • Gebäude-Polygon                                      │   │
│  │  • EGID (wo verfügbar)                                  │   │
│  │                                                         │   │
│  │  Zugriff: 3D Tiles API oder Kachel-Download             │   │
│  │  URL: https://3d.geo.admin.ch/ch.swisstopo.swissbuildings3d.3d/v1/tileset.json │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                      │
│                          ▼                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  ERGÄNZEND: Sonnendach.ch (für Dach-Details)            │   │
│  │  ─────────────────────────────────────────────────────  │   │
│  │  • Exakte Dachflächen-Polygone                          │   │
│  │  • Neigung pro Dachfläche                               │   │
│  │  • Ausrichtung (Azimut)                                 │   │
│  │  • Eignung für Solar (als Qualitätsindikator)           │   │
│  │                                                         │   │
│  │  Zugriff: WMS Feature Info                              │   │
│  │  Layer: ch.bfe.solarenergie-eignung-daecher             │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                      │
│                          ▼                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  ERGÄNZEND: GWR (für Attribute)                         │   │
│  │  ─────────────────────────────────────────────────────  │   │
│  │  • EGID (Identifikator)                                 │   │
│  │  • Baujahr                                              │   │
│  │  • Gebäudekategorie                                     │   │
│  │  • Anzahl Wohnungen                                     │   │
│  │  • Heizungsart                                          │   │
│  │                                                         │   │
│  │  Zugriff: swisstopo REST API (Find by EGID)             │   │
│  │  Layer: ch.bfs.gebaeude_wohnungs_register               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                      │
│                          ▼                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  ERGÄNZEND: swissALTI3D (für Terrain)                   │   │
│  │  ─────────────────────────────────────────────────────  │   │
│  │  • Geländehöhe an Gebäudeecken                          │   │
│  │  • Berechnung Gefälle pro Fassade                       │   │
│  │                                                         │   │
│  │  Zugriff: swisstopo Height API                          │   │
│  │  Endpoint: /rest/services/height                        │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Datenfluss

```
Adresse eingeben
      │
      ▼
┌─────────────────┐
│ 1. Geocoding    │  swisstopo SearchServer
│    Adresse→LV95 │  → Koordinaten + EGID (wenn im Result)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 2. Building 3D  │  swissBUILDINGS3D 3D Tiles
│    Geometrie    │  → Polygon, Höhen, Dachform
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 3. Dach-Details │  Sonnendach.ch WMS
│    (optional)   │  → Dachflächen, Neigung
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 4. GWR Attribute│  GWR via swisstopo
│    (optional)   │  → Baujahr, Kategorie, etc.
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 5. Terrain      │  swissALTI3D Height API
│    Gefälle      │  → Höhe pro Ecke → Gefälle
└────────┬────────┘
         │
         ▼
    BuildingBundle
    (vollständig)
```

---

## 3. Altlasten prüfen (NICHT automatisch löschen!)

### 3.1 Zu prüfende Dateien/Module

> ⚠️ **WICHTIG:** Diese Dateien nicht automatisch löschen! Zuerst prüfen ob sie noch gebraucht werden.

```
⚠️ PRÜFEN (nicht automatisch löschen!):

src/
├── services/
│   ├── gwr_madd_service.py     # Prüfen: Wird direkter GWR XML-Zugriff noch benötigt?
│   └── geodienste_wfs.py       # Prüfen: Soll WFS nochmal versucht werden oder aufgeben?
├── tests/
│   ├── test_gwr_madd.py        # Entfernen wenn Service entfernt wird
│   └── test_geodienste_wfs.py  # Entfernen wenn Service entfernt wird
```

### 3.2 BEHALTEN: known_buildings.py

```
✅ BEHALTEN (wichtig!):

src/
├── known_buildings.py          # NICHT LÖSCHEN!
                                # Enthält:
                                # - Zusätzliche Gebäude-Informationen für Prompts
                                # - Architektonische Details (Baustil, Besonderheiten)
                                # - Zonen-Definitionen für komplexe Gebäude
                                # - Angedacht für ML-Training
                                # 
                                # Die Höhendaten werden durch swissBUILDINGS3D ersetzt,
                                # aber die qualitativen Informationen bleiben wertvoll!
```

**Hinweis zu known_buildings.py:**
- Die **Höhendaten** (trauf_height, first_height) werden durch swissBUILDINGS3D obsolet
- Die **qualitativen Daten** (Baustil, Zonen, architektonische Merkmale) bleiben wichtig
- Angedacht für **ML-Training** zur automatischen Gebäudeklassifikation
- SVG-Prompts basieren teilweise auf diesen Daten

### 3.3 Zu prüfende API-Endpunkte

```
⚠️ PRÜFEN (nicht automatisch entfernen!):

/api/v1/gwr/madd/{egid}         # Prüfen: Wird noch benötigt?
/api/v1/geodienste/wfs          # Prüfen: WFS nochmal versuchen oder aufgeben?
/api/v1/building/known/{name}   # BEHALTEN: Lookup in known_buildings.py bleibt nützlich
```

### 3.4 Entscheidungsmatrix

| Modul | Status | Entscheidung nötig |
|-------|--------|-------------------|
| `known_buildings.py` | ✅ Behalten | Höhen ersetzen, Rest behalten |
| `gwr_madd_service.py` | ⚠️ Prüfen | Wird direkter XML-Zugriff noch gebraucht? |
| `geodienste_wfs.py` | ⚠️ Prüfen | WFS hat nie funktioniert - nochmal versuchen oder aufgeben? |

### 3.5 Hintergrund: SVG-Qualität

Die SVG-Generierung hat bisher nicht die gewünschte Qualität erreicht:
- Einmal erfolgreich generiert, dann bei Aufräumarbeiten verloren gegangen
- `known_buildings.py` enthält wichtige Kontext-Informationen für bessere Prompts
- Mit echten 3D-Daten aus swissBUILDINGS3D sollte die Qualität steigen

---

## 4. Was wird BEHALTEN

### 4.1 Weiterhin benötigte Services

```
✅ BEHALTEN:

src/services/
├── swisstopo_service.py        # Geocoding, Height API → erweitern
├── cache_service.py            # Caching → bleibt
└── svg_service.py              # SVG-Generierung → bleibt
```

### 4.2 Weiterhin benötigte API-Endpunkte

```
✅ BEHALTEN:

/api/v1/geocode                 # Adresse → Koordinaten
/api/v1/building/smart          # Haupt-Endpunkt → erweitern
/api/v1/building/{egid}         # Lookup by EGID → erweitern
/api/v1/height                  # Terrain-Höhe
/api/v1/svg-prompt              # Prompt-Generierung → anpassen
```

---

## 5. Neue Implementierung

### 5.1 Neuer Service: swissbuildings3d_service.py

```python
"""
swissBUILDINGS3D 3.0 Beta Service

Lädt 3D-Gebäudedaten von swisstopo.
"""

import httpx
from typing import Optional
from pydantic import BaseModel

class Building3D(BaseModel):
    """3D-Gebäudedaten aus swissBUILDINGS3D."""
    egid: Optional[str]
    polygon: list[tuple[float, float]]  # LV95 Koordinaten
    trauf_height_m: float
    first_height_m: float
    building_height_m: float  # = first - terrain
    roof_type: str  # 'flat', 'gabled', 'hipped', 'complex'
    roof_surfaces: list[dict]  # Dachflächen mit Neigung/Azimut
    terrain_height_m: float
    lod: str  # 'LOD1' oder 'LOD2'


class SwissBuildings3DService:
    """Service für swissBUILDINGS3D 3.0 Beta Daten."""
    
    # 3D Tiles Endpoint
    TILES_URL = "https://3d.geo.admin.ch/ch.swisstopo.swissbuildings3d.3d/v1/tileset.json"
    
    # Identify für einzelne Gebäude (via map.geo.admin.ch API)
    IDENTIFY_URL = "https://api3.geo.admin.ch/rest/services/api/MapServer/identify"
    
    # Layer für swissBUILDINGS3D
    LAYER_ID = "ch.swisstopo.swissbuildings3d_3_0"
    
    async def get_building_by_coordinates(
        self, 
        e: float, 
        n: float,
        tolerance: float = 50.0
    ) -> Optional[Building3D]:
        """
        Holt 3D-Gebäudedaten für Koordinaten.
        
        Args:
            e: LV95 Ost-Koordinate
            n: LV95 Nord-Koordinate
            tolerance: Suchradius in Metern
        
        Returns:
            Building3D oder None wenn nicht gefunden
        """
        params = {
            "geometryType": "esriGeometryPoint",
            "geometry": f"{e},{n}",
            "geometryFormat": "geojson",
            "layers": f"all:{self.LAYER_ID}",
            "tolerance": tolerance,
            "mapExtent": f"{e-100},{n-100},{e+100},{n+100}",
            "imageDisplay": "100,100,96",
            "returnGeometry": "true",
            "sr": "2056"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(self.IDENTIFY_URL, params=params)
            response.raise_for_status()
            data = response.json()
        
        if not data.get("results"):
            return None
        
        feature = data["results"][0]
        return self._parse_building(feature)
    
    async def get_building_by_egid(self, egid: str) -> Optional[Building3D]:
        """
        Holt 3D-Gebäudedaten für EGID.
        
        Hinweis: Nicht alle Kantone haben EGID in swissBUILDINGS3D.
        Falls nicht gefunden, Fallback auf Koordinaten-Suche.
        """
        # Zuerst Koordinaten aus GWR holen
        gwr_coords = await self._get_coords_from_gwr(egid)
        if not gwr_coords:
            return None
        
        return await self.get_building_by_coordinates(
            gwr_coords['e'], 
            gwr_coords['n']
        )
    
    def _parse_building(self, feature: dict) -> Building3D:
        """Parsed swissBUILDINGS3D Feature zu Building3D."""
        props = feature.get("properties", {})
        geom = feature.get("geometry", {})
        
        # Polygon extrahieren
        polygon = []
        if geom.get("type") == "Polygon":
            polygon = [(p[0], p[1]) for p in geom["coordinates"][0]]
        
        # Höhen
        # swissBUILDINGS3D liefert absolute Höhen (m.ü.M.)
        # Wir brauchen relative Höhen (über Terrain)
        z_min = props.get("z_min", 0)
        z_max = props.get("z_max", 0)
        z_trauf = props.get("z_trauf", z_max)
        
        return Building3D(
            egid=props.get("egid"),
            polygon=polygon,
            trauf_height_m=z_trauf - z_min,
            first_height_m=z_max - z_min,
            building_height_m=z_max - z_min,
            roof_type=self._detect_roof_type(props),
            roof_surfaces=[],  # Wird später von Sonnendach.ch ergänzt
            terrain_height_m=z_min,
            lod=props.get("lod", "LOD2")
        )
    
    def _detect_roof_type(self, props: dict) -> str:
        """Erkennt Dachtyp aus Eigenschaften."""
        # TODO: Logik basierend auf Geometrie
        objektart = props.get("objektart", "")
        if "flach" in objektart.lower():
            return "flat"
        return "gabled"  # Default
```

### 5.2 Neuer Service: sonnendach_service.py

```python
"""
Sonnendach.ch Service

Lädt detaillierte Dachgeometrien.
"""

import httpx
from typing import Optional

class RoofSurface(BaseModel):
    """Eine Dachfläche."""
    polygon: list[tuple[float, float, float]]  # 3D Koordinaten
    area_m2: float
    tilt_degrees: float      # Neigung
    azimuth_degrees: float   # Ausrichtung (0=N, 90=O, 180=S, 270=W)
    eignung: str             # 'hoch', 'mittel', 'gering'


class SonnendachService:
    """Service für Sonnendach.ch Daten."""
    
    LAYER_ID = "ch.bfe.solarenergie-eignung-daecher"
    IDENTIFY_URL = "https://api3.geo.admin.ch/rest/services/api/MapServer/identify"
    
    async def get_roof_surfaces(
        self, 
        e: float, 
        n: float
    ) -> list[RoofSurface]:
        """
        Holt Dachflächen für Koordinaten.
        """
        params = {
            "geometryType": "esriGeometryPoint",
            "geometry": f"{e},{n}",
            "layers": f"all:{self.LAYER_ID}",
            "tolerance": 10,
            "mapExtent": f"{e-50},{n-50},{e+50},{n+50}",
            "imageDisplay": "100,100,96",
            "returnGeometry": "true",
            "sr": "2056"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(self.IDENTIFY_URL, params=params)
            data = response.json()
        
        surfaces = []
        for result in data.get("results", []):
            surface = self._parse_surface(result)
            if surface:
                surfaces.append(surface)
        
        return surfaces
    
    def _parse_surface(self, feature: dict) -> Optional[RoofSurface]:
        """Parsed Sonnendach Feature zu RoofSurface."""
        props = feature.get("properties", {})
        geom = feature.get("geometry", {})
        
        if not geom:
            return None
        
        return RoofSurface(
            polygon=geom.get("coordinates", [[]])[0],
            area_m2=props.get("flaeche", 0),
            tilt_degrees=props.get("neigung", 0),
            azimuth_degrees=props.get("ausrichtung", 0),
            eignung=props.get("eignung_text", "unbekannt")
        )
```

### 5.3 Aktualisierter BuildingBundle

```python
"""
Neues BuildingBundle Datenmodell.
"""

from pydantic import BaseModel
from typing import Optional

class BuildingBundle(BaseModel):
    """Vollständige Gebäudedaten aus allen Quellen."""
    
    # Identifikation
    egid: Optional[str]
    address: str
    
    # Koordinaten
    lv95_e: float
    lv95_n: float
    wgs84_lat: float
    wgs84_lon: float
    
    # 3D-Geometrie (aus swissBUILDINGS3D)
    polygon: list[tuple[float, float]]
    trauf_height_m: float
    first_height_m: float
    building_height_m: float
    roof_type: str
    lod: str
    
    # Dach-Details (aus Sonnendach.ch)
    roof_surfaces: list[dict]
    
    # Terrain (aus swissALTI3D)
    terrain_height_m: float
    slope_percent: Optional[float]  # Gefälle
    
    # GWR-Attribute (optional)
    baujahr: Optional[int]
    gebaeudekategorie: Optional[int]
    anzahl_geschosse: Optional[int]
    anzahl_wohnungen: Optional[int]
    
    # Metadaten
    data_sources: list[str]  # z.B. ['swissbuildings3d', 'sonnendach', 'gwr']
    data_quality: str  # 'high', 'medium', 'low'
```

---

## 6. Migrationsplan

### Phase 1: Vorbereitung (1-2 Stunden)

```
□ 1.1 Backup des aktuellen Codes
□ 1.2 Branch erstellen: feature/swissbuildings3d-integration
□ 1.3 Tests für neue Services schreiben (TDD)
```

### Phase 2: Neue Services implementieren (2-3 Stunden)

```
□ 2.1 swissbuildings3d_service.py erstellen
□ 2.2 sonnendach_service.py erstellen
□ 2.3 BuildingBundle aktualisieren
□ 2.4 Tests ausführen
```

### Phase 3: Integration (1-2 Stunden)

```
□ 3.1 building_service.py aktualisieren
□ 3.2 API-Endpunkte anpassen
□ 3.3 Caching für neue Daten implementieren
□ 3.4 Integrationstests
```

### Phase 4: Altlasten prüfen (1 Stunde)

```
□ 4.1 known_buildings.py: Höhendaten durch swissBUILDINGS3D ersetzen (Rest behalten!)
□ 4.2 gwr_madd_service.py: Prüfen ob noch benötigt → Entscheidung dokumentieren
□ 4.3 geodienste_wfs.py: Prüfen ob WFS nochmal versucht werden soll → Entscheidung dokumentieren
□ 4.4 Nur nach expliziter Freigabe: Alte Tests löschen
□ 4.5 Nur nach expliziter Freigabe: Alte API-Endpunkte entfernen
□ 4.6 requirements.txt aufräumen (nur ungenutzte Dependencies)
```

### Phase 5: Dokumentation (30 Min)

```
□ 5.1 README.md aktualisieren
□ 5.2 CLAUDE.md aktualisieren
□ 5.3 API-Dokumentation aktualisieren
```

### Phase 6: Deployment (30 Min)

```
□ 6.1 Staging testen
□ 6.2 Production deployment
□ 6.3 Monitoring prüfen
```

---

## 7. API-Änderungen

### 7.1 Aktualisierter /api/v1/building/smart Endpunkt

**Request:**
```json
POST /api/v1/building/smart
{
  "address": "Länggassstrasse 40, 3012 Bern"
}
```

**Response (NEU):**
```json
{
  "egid": "1234567",
  "address": "Länggassstrasse 40, 3012 Bern",
  
  "coordinates": {
    "lv95_e": 2600100.0,
    "lv95_n": 1199500.0,
    "wgs84_lat": 46.9520,
    "wgs84_lon": 7.4380
  },
  
  "geometry": {
    "polygon": [[2600090, 1199490], [2600110, 1199490], ...],
    "lod": "LOD2"
  },
  
  "heights": {
    "terrain_m": 540.5,
    "trauf_m": 16.2,
    "first_m": 18.5,
    "building_m": 18.5
  },
  
  "roof": {
    "type": "gabled",
    "surfaces": [
      {
        "area_m2": 85.3,
        "tilt_degrees": 35,
        "azimuth_degrees": 180
      },
      {
        "area_m2": 82.1,
        "tilt_degrees": 35,
        "azimuth_degrees": 0
      }
    ]
  },
  
  "attributes": {
    "baujahr": 1965,
    "kategorie": "Wohngebäude",
    "geschosse": 4,
    "wohnungen": 8
  },
  
  "metadata": {
    "sources": ["swissbuildings3d", "sonnendach", "gwr", "swissalti3d"],
    "quality": "high",
    "timestamp": "2025-12-31T10:00:00Z"
  }
}
```

---

## 8. Risiken und Fallbacks

### 8.1 swissBUILDINGS3D nicht verfügbar

**Risiko:** API temporär nicht erreichbar

**Fallback:**
```python
if not building_3d:
    # Fallback auf GWR + geschätzte Höhe
    gwr_data = await gwr_service.get_by_egid(egid)
    estimated_height = gwr_data.geschosse * 3.0  # ~3m pro Geschoss
```

### 8.2 Kanton ohne EGID-Integration

**Risiko:** EGID nicht in swissBUILDINGS3D (z.B. ZH, AG, VD)

**Fallback:**
```python
# Koordinaten-basierte Suche statt EGID
building = await swissbuildings3d.get_by_coordinates(e, n)
```

### 8.3 Sonnendach.ch ohne Daten

**Risiko:** Gebäude nicht in Sonnendach.ch (z.B. Industriebauten)

**Fallback:**
```python
if not roof_surfaces:
    # Schätze Dachform aus swissBUILDINGS3D
    roof_surfaces = estimate_roof_from_3d(building_3d)
```

---

## 9. Testfälle

### 9.1 Neue Tests

```python
# tests/test_swissbuildings3d.py

import pytest
from services.swissbuildings3d_service import SwissBuildings3DService

@pytest.mark.asyncio
async def test_get_building_bern():
    """Test: Gebäude in Bern (EGID verfügbar seit Juni 2024)."""
    service = SwissBuildings3DService()
    
    # Bundeshaus Bern
    building = await service.get_building_by_coordinates(
        e=2600423, n=1199521
    )
    
    assert building is not None
    assert building.trauf_height_m > 0
    assert building.first_height_m >= building.trauf_height_m
    assert len(building.polygon) > 3

@pytest.mark.asyncio
async def test_get_building_zurich():
    """Test: Gebäude in Zürich (EGID noch nicht verfügbar)."""
    service = SwissBuildings3DService()
    
    # ETH Hauptgebäude
    building = await service.get_building_by_coordinates(
        e=2683100, n=1248000
    )
    
    # Sollte trotzdem Geometrie liefern (ohne EGID)
    assert building is not None
    assert building.egid is None  # Noch kein EGID in ZH
    assert building.polygon is not None
```

---

## 10. Checkliste vor Merge

```
□ Alle neuen Tests grün
□ Keine Regression in bestehenden Features
□ known_buildings.py: Höhen-Felder durch swissBUILDINGS3D ersetzt (qualitative Daten behalten!)
□ Altlasten-Entscheidungen dokumentiert (was bleibt, was geht)
□ Keine Referenzen auf tatsächlich gelöschte Module
□ API-Dokumentation aktuell
□ README.md aktuell
□ CLAUDE.md aktuell
□ Staging getestet
□ Performance akzeptabel (<500ms für building/smart)
```

---

## 11. Referenzen

- [swissBUILDINGS3D 3.0 Beta Dokumentation](https://www.swisstopo.admin.ch/de/landschaftmodell-swissbuildings3d-3-0-beta)
- [swisstopo API Dokumentation](https://api3.geo.admin.ch/services/sdiservices.html)
- [3D Tiles Endpoint](https://3d.geo.admin.ch/ch.swisstopo.swissbuildings3d.3d/v1/tileset.json)
- [Sonnendach.ch](https://www.uvek-gis.admin.ch/BFE/sonnendach/)

---

*Dokument erstellt: 31.12.2025*
*Für: Claude IDE / geodaten-ch Refactoring*
*Geschätzter Aufwand: 6-8 Stunden*
