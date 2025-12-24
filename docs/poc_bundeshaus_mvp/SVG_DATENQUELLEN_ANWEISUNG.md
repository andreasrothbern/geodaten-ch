# SVG-GENERIERUNG: DATENQUELLEN UND DATENFLUSS
# =============================================
# Anweisungen für Claude IDE
# Erstellt: 24.12.2025

## Übersicht Datenfluss

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           USER INPUT                                     │
│                    Adresse: "Bundesplatz 3, 3011 Bern"                  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  1. SWISSTOPO GEOKODIERUNG                                              │
│     Endpoint: api.geo.admin.ch/rest/services/api/SearchServer           │
│     Output: Koordinaten (LV95), EGID                                    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
┌──────────────────────┐ ┌──────────────────┐ ┌──────────────────────────┐
│ 2. GEODIENSTE.CH WFS │ │ 3. SWISSTOPO GWR │ │ 4. SWISSBUILDINGS3D      │
│    Gebäudepolygon    │ │    Gebäudedaten  │ │    Höhendaten            │
│    → douglas_peucker │ │    (EGID-basiert)│ │    (EGID oder Koordinate)│
└──────────────────────┘ └──────────────────┘ └──────────────────────────┘
                    │               │               │
                    └───────────────┼───────────────┘
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  5. DATEN-AGGREGATION (Backend: scaffolding endpoint)                   │
│     Kombiniert: Polygon + Gebäudedaten + Höhen                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
            ┌────────────┐  ┌────────────┐  ┌────────────┐
            │ SVG        │  │ SVG        │  │ SVG        │
            │ GRUNDRISS  │  │ ANSICHT    │  │ SCHNITT    │
            └────────────┘  └────────────┘  └────────────┘
```

---

## 1. GEOKODIERUNG (Adresse → Koordinaten + EGID)

### API-Endpoint
```
GET https://api.geo.admin.ch/rest/services/api/SearchServer
    ?searchText={adresse}
    &type=locations
    &origins=address
    &sr=2056
```

### Response verwenden
```python
# Aus der API-Response extrahieren:
result = response["results"][0]["attrs"]

koordinaten = {
    "x": result["x"],          # LV95 Ost (z.B. 2600000)
    "y": result["y"],          # LV95 Nord (z.B. 1200000)
}
egid = result.get("egid")      # Falls vorhanden
```

### Verwendung für SVGs
- `koordinaten` → Für swissBUILDINGS3D Lookup (falls kein EGID)
- `egid` → Für GWR und Höhen-Lookup

---

## 2. GEBÄUDEPOLYGON (geodienste.ch WFS)

### API-Endpoint
```
GET https://geodienste.ch/db/av/deu
    ?SERVICE=WFS
    &VERSION=2.0.0
    &REQUEST=GetFeature
    &TYPENAME=bodenbedeckung_projected
    &SRSNAME=EPSG:2056
    &BBOX={x-50},{y-50},{x+50},{y+50}
    &OUTPUTFORMAT=application/json
```

### Response verwenden
```python
# GeoJSON Feature mit Polygon
feature = response["features"][0]
polygon_raw = feature["geometry"]["coordinates"][0]

# Konvertieren zu Liste von Punkten
polygon = [{"x": p[0], "y": p[1]} for p in polygon_raw]
```

### Douglas-Peucker anwenden
```python
# WICHTIG: Polygon vereinfachen vor SVG-Generierung!
from services.geodienste import simplify_polygon

polygon_simplified = simplify_polygon(
    polygon,
    epsilon=0.3,              # Anpassen je nach Gebäudegrösse
    angle_tolerance=8.0,
    min_side_length=1.0
)
```

### Output für SVG-Grundriss
```python
grundriss_polygon = polygon_simplified
# Liste von {"x": float, "y": float} in Metern (LV95)
```

---

## 3. GEBÄUDEDATEN (swisstopo GWR)

### API-Endpoint
```
GET https://api.geo.admin.ch/rest/services/api/MapServer/find
    ?layer=ch.bfs.gebaeude_wohnungs_register
    &searchField=egid
    &searchText={egid}
    &returnGeometry=false
```

### Alternative: Koordinaten-basiert
```
GET https://api.geo.admin.ch/rest/services/api/MapServer/identify
    ?geometry={x},{y}
    &geometryType=esriGeometryPoint
    &layers=all:ch.bfs.gebaeude_wohnungs_register
    &sr=2056
    &tolerance=10
```

### Response verwenden
```python
attrs = response["results"][0]["attributes"]

gebaeude_data = {
    "egid": attrs.get("egid"),
    "strasse": attrs.get("strname_deinr"),
    "plz": attrs.get("dplz4"),
    "ort": attrs.get("dplzname"),
    "baujahr": attrs.get("gbauj"),
    "geschosse": attrs.get("gastw"),           # WICHTIG für Höhenschätzung!
    "gebaeudekategorie": attrs.get("gkat"),    # 1021=EFH, 1025=MFH, etc.
    "grundflaeche": attrs.get("garea"),        # m²
}
```

### Höhenschätzung aus Geschossen (Fallback)
```python
def schaetze_hoehe_aus_geschossen(geschosse: int, kategorie: int) -> float:
    """Fallback wenn keine swissBUILDINGS3D Daten"""
    GESCHOSS_HOEHE = 3.0  # Meter
    
    if geschosse:
        return geschosse * GESCHOSS_HOEHE
    
    # Fallback nach Kategorie
    if kategorie == 1021:  # EFH
        return 7.5
    elif kategorie in [1025, 1030]:  # MFH
        return 12.0
    else:
        return 10.0
```

---

## 4. HÖHENDATEN (swissBUILDINGS3D)

### Primär: EGID-Lookup (building_heights_detailed)
```python
# Falls ihr eine lokale DB/Cache habt:
def get_height_by_egid(egid: int) -> dict:
    """Lookup in swissBUILDINGS3D Daten"""
    # Query eure Datenquelle
    result = db.query(
        "SELECT hoehe_traufe, hoehe_first FROM building_heights WHERE egid = ?",
        [egid]
    )
    if result:
        return {
            "hoehe_traufe": result["hoehe_traufe"],
            "hoehe_first": result["hoehe_first"],
            "quelle": "swissBUILDINGS3D_EGID"
        }
    return None
```

### Sekundär: Koordinaten-Lookup (±25m Toleranz)
```python
def get_height_by_coordinates(x: float, y: float, tolerance: float = 25.0) -> dict:
    """Suche nächstes Gebäude in swissBUILDINGS3D"""
    result = db.query("""
        SELECT hoehe_traufe, hoehe_first,
               ST_Distance(geom, ST_MakePoint(?, ?)) as dist
        FROM building_heights
        WHERE ST_DWithin(geom, ST_MakePoint(?, ?), ?)
        ORDER BY dist
        LIMIT 1
    """, [x, y, x, y, tolerance])
    
    if result:
        return {
            "hoehe_traufe": result["hoehe_traufe"],
            "hoehe_first": result["hoehe_first"],
            "quelle": "swissBUILDINGS3D_COORD"
        }
    return None
```

### Höhen-Kaskade (implementieren!)
```python
def get_building_height(egid: int, x: float, y: float, geschosse: int, kategorie: int) -> dict:
    """
    Kaskade für Höhenbestimmung:
    1. EGID-Lookup in swissBUILDINGS3D
    2. Koordinaten-Lookup (±25m)
    3. Schätzung aus GWR-Geschossen
    4. Standard nach Kategorie
    """
    
    # 1. EGID
    if egid:
        height = get_height_by_egid(egid)
        if height:
            return height
    
    # 2. Koordinaten
    if x and y:
        height = get_height_by_coordinates(x, y)
        if height:
            return height
    
    # 3. Geschoss-Schätzung
    if geschosse:
        h = geschosse * 3.0
        return {
            "hoehe_traufe": h,
            "hoehe_first": h + 2.0,  # Annahme Satteldach
            "quelle": "GWR_GESCHOSSE"
        }
    
    # 4. Kategorie-Standard
    h = schaetze_hoehe_aus_geschossen(None, kategorie)
    return {
        "hoehe_traufe": h,
        "hoehe_first": h + 2.0,
        "quelle": "STANDARD"
    }
```

---

## 5. FASSADEN AUS POLYGON ABLEITEN

```python
def polygon_zu_fassaden(polygon: list[dict]) -> list[dict]:
    """
    Wandelt Polygon-Punkte in Fassaden-Segmente um.
    
    Input: [{"x": 0, "y": 0}, {"x": 12, "y": 0}, {"x": 12, "y": 10}, ...]
    Output: Liste von Fassaden mit Länge, Ausrichtung, Start/End
    """
    import math
    
    fassaden = []
    n = len(polygon)
    
    for i in range(n):
        p1 = polygon[i]
        p2 = polygon[(i + 1) % n]
        
        # Länge berechnen
        dx = p2["x"] - p1["x"]
        dy = p2["y"] - p1["y"]
        laenge = math.sqrt(dx*dx + dy*dy)
        
        # Ausrichtung (0° = Ost, 90° = Nord)
        winkel = math.degrees(math.atan2(dy, dx))
        
        # Himmelsrichtung ableiten
        if -45 <= winkel < 45:
            richtung = "Ost"
        elif 45 <= winkel < 135:
            richtung = "Nord"
        elif winkel >= 135 or winkel < -135:
            richtung = "West"
        else:
            richtung = "Süd"
        
        fassaden.append({
            "id": f"F{i+1}",
            "name": f"Fassade {richtung}",
            "start": p1,
            "end": p2,
            "laenge": round(laenge, 2),
            "winkel": round(winkel, 1),
            "richtung": richtung,
            "selected": False  # User wählt später aus
        })
    
    return fassaden
```

---

## 6. DATEN FÜR SVG-GENERIERUNG ZUSAMMENSTELLEN

### Aggregierter Datensatz (Backend liefert an Frontend)

```python
def get_svg_data(address: str) -> dict:
    """
    Hauptfunktion: Sammelt alle Daten für SVG-Generierung.
    Wird vom /api/v1/scaffolding Endpoint aufgerufen.
    """
    
    # 1. Geokodierung
    geo = geocode_address(address)
    x, y = geo["x"], geo["y"]
    egid = geo.get("egid")
    
    # 2. Polygon holen und vereinfachen
    polygon_raw = get_building_polygon(x, y)
    polygon = simplify_polygon(polygon_raw, epsilon=0.3)
    
    # 3. Gebäudedaten
    gwr = get_gwr_data(egid) if egid else get_gwr_by_coords(x, y)
    
    # 4. Höhen
    heights = get_building_height(
        egid=egid,
        x=x, y=y,
        geschosse=gwr.get("geschosse"),
        kategorie=gwr.get("gebaeudekategorie")
    )
    
    # 5. Fassaden ableiten
    fassaden = polygon_zu_fassaden(polygon)
    
    # 6. Bounding Box für SVG-Skalierung
    xs = [p["x"] for p in polygon]
    ys = [p["y"] for p in polygon]
    bbox = {
        "min_x": min(xs),
        "max_x": max(xs),
        "min_y": min(ys),
        "max_y": max(ys),
        "width": max(xs) - min(xs),
        "height": max(ys) - min(ys)
    }
    
    # RETURN: Alles was SVG-Generator braucht
    return {
        "adresse": address,
        "koordinaten": {"x": x, "y": y},
        "egid": egid,
        
        # Für GRUNDRISS
        "polygon": polygon,
        "fassaden": fassaden,
        "bbox": bbox,
        
        # Für ANSICHT und SCHNITT
        "hoehe_traufe": heights["hoehe_traufe"],
        "hoehe_first": heights.get("hoehe_first"),
        "hoehe_quelle": heights["quelle"],
        
        # Gebäudedaten
        "gebaeude": {
            "baujahr": gwr.get("baujahr"),
            "geschosse": gwr.get("geschosse"),
            "grundflaeche": gwr.get("grundflaeche"),
            "kategorie": gwr.get("gebaeudekategorie")
        },
        
        # Gerüst-Defaults (User kann ändern)
        "geruest_defaults": {
            "system": "layher_blitz_70",
            "lastklasse": 3,
            "breitenklasse": "W09",
            "abstand_fassade": 0.30,
            "gangbreite": 0.70
        }
    }
```

---

## 7. SVG-GENERATOR AUFRUFEN

### Grundriss
```python
def generate_grundriss_svg(data: dict, selected_fassaden: list[str] = None) -> str:
    """
    Input: data von get_svg_data()
    Output: SVG-String
    """
    polygon = data["polygon"]
    fassaden = data["fassaden"]
    bbox = data["bbox"]
    
    # Massstab berechnen
    max_dim = max(bbox["width"], bbox["height"])
    scale = 600 / max_dim  # SVG soll 600px breit sein
    
    # SVG generieren...
    # (siehe bestehenden svg_generator.py Code)
```

### Ansicht (Elevation)
```python
def generate_ansicht_svg(data: dict, fassade_id: str) -> str:
    """
    Input: data + welche Fassade
    Output: SVG-String
    """
    # Fassade finden
    fassade = next(f for f in data["fassaden"] if f["id"] == fassade_id)
    
    laenge = fassade["laenge"]
    hoehe_traufe = data["hoehe_traufe"]
    hoehe_first = data.get("hoehe_first", hoehe_traufe)
    
    # Gerüst berechnen
    hoehe_ausmass = hoehe_traufe + 1.0  # NPK 114 Zuschlag
    anzahl_lagen = math.ceil(hoehe_ausmass / 2.0)
    
    # SVG generieren...
```

### Schnitt (Cross-Section)
```python
def generate_schnitt_svg(data: dict) -> str:
    """
    Input: data
    Output: SVG-String
    """
    # Gebäudebreite aus BBox oder kürzester Fassade
    breite = min(data["bbox"]["width"], data["bbox"]["height"])
    
    hoehe_traufe = data["hoehe_traufe"]
    hoehe_first = data.get("hoehe_first", hoehe_traufe)
    
    # Dachform schätzen (falls nicht vorhanden)
    if hoehe_first > hoehe_traufe:
        dachform = "satteldach"
    else:
        dachform = "flach"
    
    # SVG generieren...
```

---

## ZUSAMMENFASSUNG: Was woher kommt

| Daten | Quelle | API/Service |
|-------|--------|-------------|
| Koordinaten | swisstopo | api.geo.admin.ch SearchServer |
| EGID | swisstopo | api.geo.admin.ch SearchServer |
| Polygon | geodienste.ch | WFS bodenbedeckung |
| Geschosse, Baujahr, Fläche | swisstopo GWR | api.geo.admin.ch MapServer |
| Traufhöhe, Firsthöhe | swissBUILDINGS3D | Lokale DB oder API |
| Fassaden-Längen | **Berechnet** | Aus Polygon-Segmenten |
| Ausrichtung (N/S/O/W) | **Berechnet** | Aus Segment-Winkel |

---

## CHECKLISTE FÜR CLAUDE IDE

- [ ] `get_svg_data()` Funktion implementiert?
- [ ] Höhen-Kaskade (EGID → Koordinaten → GWR → Standard)?
- [ ] Douglas-Peucker auf Polygon angewendet?
- [ ] Fassaden aus Polygon abgeleitet?
- [ ] Bounding Box für SVG-Skalierung?
- [ ] Massstab dynamisch berechnet?
