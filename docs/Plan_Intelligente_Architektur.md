# Plan: Intelligente Architektur für Gerüstplanung

**Datum:** 29.12.2025
**Status:** Planung

---

## Übersicht: Der neue Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 1: GRUNDDATEN                                            │
│  ─────────────────────                                          │
│  Eingabe: "Bundeshaus" oder "Bundesplatz 3, 3011 Bern"          │
│                                                                  │
│  1. Smarte Suche:                                               │
│     - Prüfe ob "Bundeshaus" bekannt → Alias auflösen            │
│     - Oder: Geocoding via swisstopo                             │
│                                                                  │
│  2. Cache-Check:                                                 │
│     - Gebäude-Daten bereits vorhanden? → Aus DB laden           │
│     - SVGs bereits generiert? → Aus DB laden                    │
│                                                                  │
│  3. Grundriss-SVG anzeigen (für Fassadenauswahl)                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 2: FASSADENAUSWAHL                                       │
│  ─────────────────────────                                      │
│  Input: Grundriss-SVG mit allen Fassaden                        │
│                                                                  │
│  1. Umgebung anzeigen:                                          │
│     - Angrenzende Gebäude (grau dargestellt)                    │
│     - Blockierte Fassaden markiert (rot)                        │
│     - Freie Fassaden auswählbar (grün)                          │
│                                                                  │
│  2. Rundungen erkennen:                                         │
│     - Z.B. Bundeshaus: Rundung an Nordfassade                   │
│     - Spezielles Gerüstsystem für Rundungen                     │
│                                                                  │
│  3. User wählt Fassaden zum Einrüsten                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 3: DETAILPLANUNG                                         │
│  ─────────────────────                                          │
│  Input: Gewählte Fassaden + Terrain-Daten                       │
│                                                                  │
│  1. Pro Fassade:                                                 │
│     - Höhe (Trauf/First) pro Seite                              │
│     - Terrain-Gefälle                                           │
│     - Fenster/Türen/Balkone (falls verfügbar)                   │
│                                                                  │
│  2. Spezialelemente:                                            │
│     - Treppengerüst                                             │
│     - Bauaufzug                                                  │
│     - Kamin-Gerüst                                               │
│     - Solarpanel-Montage (Dachgerüst)                           │
│                                                                  │
│  3. NPK 114 Ausmass + Materialschätzung                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 1. Smarte Suche und Datenhaltung

### 1.1 Aktuelle Situation

```python
# Aktuell: building_context.py
building_contexts (SQLite)
├── egid (PRIMARY KEY)
├── adresse
├── context_json (Zonen, Höhen)
├── source (auto|claude|manual)
└── ...

# Problem:
# - Suche nur über EGID
# - Kein Alias-Mapping ("Bundeshaus" → Adresse)
# - SVGs werden nicht persistent gespeichert
```

### 1.2 Neue Architektur: Erweiterte Datenbank

```sql
-- Erweiterte Tabellen für building_contexts.db

-- 1. Gebäude-Stammdaten (erweitert)
CREATE TABLE IF NOT EXISTS buildings (
    egid TEXT PRIMARY KEY,
    adresse TEXT NOT NULL,
    plz INTEGER,
    ort TEXT,
    -- Neue Felder für smarte Suche:
    name TEXT,                    -- "Bundeshaus", "Berner Münster"
    aliases TEXT,                 -- JSON: ["Parlamentsgebäude", "Swiss Parliament"]
    keywords TEXT,                -- Volltextsuche: "parlament bern kuppel"
    -- Koordinaten für Geo-Suche:
    lv95_e REAL,
    lv95_n REAL,
    -- Metadaten:
    is_landmark INTEGER DEFAULT 0,  -- 1 = bekanntes Gebäude
    created_at TEXT,
    updated_at TEXT
);

-- 2. Volltext-Index für smarte Suche
CREATE VIRTUAL TABLE IF NOT EXISTS buildings_fts USING fts5(
    name, aliases, keywords, adresse, ort,
    content=buildings,
    content_rowid=rowid
);

-- 3. SVG-Cache (persistent)
CREATE TABLE IF NOT EXISTS svg_cache (
    id TEXT PRIMARY KEY,          -- hash(egid + svg_type + version)
    egid TEXT NOT NULL,
    svg_type TEXT NOT NULL,       -- "grundriss", "ansicht", "schnitt", "uebersicht"
    svg_content TEXT NOT NULL,    -- Base64 oder direkt SVG
    version TEXT DEFAULT '1.0',   -- Für Cache-Invalidierung
    generated_by TEXT,            -- "auto" | "claude_api" | "claude_ai"
    created_at TEXT,
    FOREIGN KEY (egid) REFERENCES buildings(egid)
);

-- 4. Umgebungsdaten-Cache
CREATE TABLE IF NOT EXISTS building_environment (
    egid TEXT PRIMARY KEY,
    surrounding_buildings TEXT,   -- JSON Array
    blocked_facades TEXT,         -- JSON Array [0, 2, 5]
    terrain_data TEXT,            -- JSON: {min, max, slope, corners}
    curves TEXT,                  -- JSON: Rundungen
    updated_at TEXT,
    FOREIGN KEY (egid) REFERENCES buildings(egid)
);
```

### 1.3 Smarte Suche API

```python
# Neue Funktion in building_context.py oder eigene search.py

async def smart_search(query: str, limit: int = 10) -> List[SearchResult]:
    """
    Smarte Suche nach Gebäuden.

    Reihenfolge:
    1. Exakte Alias-Matches ("Bundeshaus" → EGID)
    2. Volltext-Suche (FTS5)
    3. Fallback: Geocoding via swisstopo

    Returns:
        Liste von SearchResult mit egid, adresse, name, score
    """
    results = []

    # 1. Alias-Match prüfen
    alias_match = search_by_alias(query)
    if alias_match:
        results.append(SearchResult(
            egid=alias_match.egid,
            adresse=alias_match.adresse,
            name=alias_match.name,
            score=1.0,
            source="alias"
        ))

    # 2. FTS-Suche
    fts_results = search_fts(query)
    for r in fts_results:
        if r.egid not in [x.egid for x in results]:
            results.append(r)

    # 3. Geocoding-Fallback (nur wenn keine DB-Treffer)
    if not results:
        geo = await swisstopo_geocode(query)
        if geo:
            results.append(SearchResult(
                egid=None,  # Noch nicht bekannt
                adresse=geo.matched_address,
                name=None,
                score=geo.confidence,
                source="geocoding",
                coordinates=(geo.lv95_e, geo.lv95_n)
            ))

    return results[:limit]
```

### 1.4 API-Endpoints für Suche

```python
# GET /api/v1/search?q=Bundeshaus
{
    "results": [
        {
            "egid": "2242547",
            "adresse": "Bundesplatz 3, 3011 Bern",
            "name": "Bundeshaus",
            "score": 1.0,
            "source": "alias",
            "has_cached_data": true,
            "has_cached_svgs": ["grundriss", "ansicht"]
        }
    ],
    "query": "Bundeshaus",
    "total": 1
}

# GET /api/v1/search/suggestions?q=Bund
# Für Autocomplete
{
    "suggestions": [
        {"text": "Bundeshaus", "type": "name"},
        {"text": "Bundesplatz 3, 3011 Bern", "type": "adresse"},
        {"text": "Bündnerstrasse 10, 8006 Zürich", "type": "adresse"}
    ]
}
```

---

## 2. SVG-Caching Strategie

### 2.1 Cache-Key Berechnung

```python
def get_svg_cache_key(
    egid: str,
    svg_type: str,
    version: str = "2.0",
    selected_facades: Optional[List[int]] = None
) -> str:
    """
    Generiert einen eindeutigen Cache-Key für SVGs.

    Der Key ändert sich bei:
    - Anderen EGID
    - Anderen SVG-Typ
    - Neuer Version (z.B. Prompt-Änderung)
    - Anderen ausgewählten Fassaden (für Gerüst-SVG)
    """
    components = [egid, svg_type, version]
    if selected_facades:
        facades_str = "-".join(map(str, sorted(selected_facades)))
        components.append(f"facades:{facades_str}")

    return hashlib.sha256("|".join(components).encode()).hexdigest()[:16]
```

### 2.2 SVG-Typen

| Typ | Beschreibung | Cache-Dauer | Generiert von |
|-----|--------------|-------------|---------------|
| `grundriss` | Grundriss mit Polygon | Permanent | Auto-Generator |
| `grundriss_umgebung` | Grundriss + Nachbargebäude | 24h | Auto + WFS |
| `ansicht` | Frontalansicht | Permanent | Claude API |
| `schnitt` | Querschnitt | Permanent | Claude API |
| `uebersicht` | Site-Overview | 24h | Claude API |
| `geruest_grundriss` | Mit Gerüst-Elementen | Session | Auto-Generator |

### 2.3 Cache-Invalidierung

```python
def should_invalidate_svg_cache(
    egid: str,
    svg_type: str,
    current_version: str
) -> bool:
    """
    Prüft ob Cache invalidiert werden soll.

    Gründe für Invalidierung:
    1. Version geändert (Prompt/Generator Update)
    2. Höhendaten aktualisiert
    3. Manuell durch User
    """
    cached = get_cached_svg(egid, svg_type)
    if not cached:
        return True

    if cached.version != current_version:
        return True

    # Prüfe ob Höhendaten neuer als Cache
    building_updated = get_building_updated_at(egid)
    if building_updated and building_updated > cached.created_at:
        return True

    return False
```

---

## 3. Umgebungsdaten und Hanglage

### 3.1 Umgebungs-Service

```python
# Neue Datei: backend/app/services/environment.py

class BuildingEnvironmentService:
    """Service für Umgebungsdaten eines Gebäudes"""

    async def get_environment(
        self,
        center_e: float,
        center_n: float,
        main_egid: str,
        radius_m: float = 50
    ) -> BuildingEnvironment:
        """
        Holt Umgebungsdaten für ein Gebäude.

        1. Alle Gebäude im Umkreis via geodienste.ch WFS
        2. Filtert Hauptgebäude heraus
        3. Berechnet Abstände zu Nachbargebäuden
        4. Identifiziert blockierte Fassaden
        """
        # 1. Alle Gebäude im Umkreis
        all_buildings = await self._get_buildings_in_radius(
            center_e, center_n, radius_m
        )

        # 2. Hauptgebäude separieren
        main_building = None
        surrounding = []
        for b in all_buildings:
            if str(b.egid) == str(main_egid):
                main_building = b
            else:
                surrounding.append(b)

        if not main_building:
            raise ValueError(f"Hauptgebäude {main_egid} nicht gefunden")

        # 3. Abstände berechnen
        for neighbor in surrounding:
            neighbor.distance_m = self._calculate_min_distance(
                main_building.polygon, neighbor.polygon
            )
            neighbor.direction = self._get_direction(
                main_building.polygon, neighbor.polygon
            )

        # 4. Blockierte Fassaden identifizieren
        blocked = self._identify_blocked_facades(
            main_building, surrounding,
            min_clearance_m=2.0  # Mindestabstand für Gerüst
        )

        return BuildingEnvironment(
            main_building=main_building,
            surrounding_buildings=surrounding,
            blocked_facades=blocked
        )

    def _identify_blocked_facades(
        self,
        main: BuildingGeometry,
        neighbors: List[BuildingGeometry],
        min_clearance_m: float
    ) -> List[int]:
        """
        Identifiziert Fassaden die nicht eingerüstet werden können.

        Kriterien:
        - Abstand zu Nachbar < min_clearance_m
        - Nachbar direkt an Fassade angrenzend
        """
        blocked = []

        for i, side in enumerate(main.sides):
            start = (side['start']['x'], side['start']['y'])
            end = (side['end']['x'], side['end']['y'])

            for neighbor in neighbors:
                # Mindestabstand zur Fassade berechnen
                dist = self._point_to_line_distance(
                    neighbor.polygon, start, end
                )
                if dist < min_clearance_m:
                    blocked.append(i)
                    break

        return blocked
```

### 3.2 Hanglage-Integration

```python
# Erweiterung in terrain.py

async def get_terrain_for_building(
    polygon: List[Tuple[float, float]]
) -> TerrainData:
    """
    Holt vollständige Terrain-Daten für ein Gebäude.

    Returns:
        TerrainData mit:
        - corner_heights: Höhe an jeder Polygon-Ecke
        - min/max/slope: Statistiken
        - facade_profiles: Gefälle pro Fassade
        - classification: "eben" | "leichte_hanglage" | "hanglage" | "steilhang"
    """
    terrain_service = get_terrain_service()

    # Eckhöhen
    corner_heights = []
    for i, (e, n) in enumerate(polygon):
        h = await terrain_service.get_height(e, n)
        corner_heights.append({
            "index": i,
            "e": e, "n": n,
            "height_m": h
        })

    heights = [c["height_m"] for c in corner_heights if c["height_m"]]
    if not heights:
        return None

    min_h = min(heights)
    max_h = max(heights)
    slope = max_h - min_h

    # Klassifizierung
    if slope < 0.5:
        classification = "eben"
    elif slope < 2.0:
        classification = "leichte_hanglage"
    elif slope < 5.0:
        classification = "hanglage"
    else:
        classification = "steilhang"

    # Gefälle pro Fassade
    facade_profiles = []
    for i in range(len(polygon)):
        j = (i + 1) % len(polygon)
        h_start = corner_heights[i]["height_m"]
        h_end = corner_heights[j]["height_m"]
        if h_start and h_end:
            facade_profiles.append({
                "facade_index": i,
                "start_height_m": h_start,
                "end_height_m": h_end,
                "slope_m": h_end - h_start
            })

    return TerrainData(
        corner_heights=corner_heights,
        min_height_m=min_h,
        max_height_m=max_h,
        slope_m=slope,
        classification=classification,
        facade_profiles=facade_profiles,
        reference_height_m=min_h  # Tiefster Punkt als Referenz
    )
```

### 3.3 SVG mit Hanglage

```python
# Prompt-Erweiterung für Ansicht-SVG

TERRAIN_PROMPT_SECTION = """
## Terrain-Darstellung (WICHTIG!)

Das Gebäude steht auf einem **geneigten Terrain**:

| Ecke | Höhe (m ü.M.) | Differenz zu Referenz |
|------|---------------|----------------------|
{corner_table}

**Klassifikation:** {classification}
**Maximales Gefälle:** {slope_m:.1f}m über {distance_m:.1f}m Gebäudebreite

### SVG-Anweisung:
1. Terrain-Linie ist NICHT horizontal!
2. Zeichne Terrain als Polygon mit absteigender/aufsteigender Linie
3. Gebäude steht auf diesem geneigten Terrain
4. Tiefster Punkt = Referenz 0.00m
5. Höchster Punkt = +{slope_m:.1f}m

### ASCII-Skizze (Ansicht von {view_direction}):
```
{ascii_sketch}
```
"""
```

---

## 4. Rundungserkennung

### 4.1 Algorithmus

```python
# In geodienste.py

def detect_curves(
    polygon: List[Tuple[float, float]],
    angle_threshold_deg: float = 25.0,
    min_consecutive: int = 3,
    min_total_angle_deg: float = 45.0
) -> List[CurveSegment]:
    """
    Erkennt Rundungen (Kurven) in einem Polygon.

    Algorithmus:
    1. Berechne Winkeländerung zwischen aufeinanderfolgenden Segmenten
    2. Finde Sequenzen mit kleinen, konsistenten Winkeländerungen
    3. Alle Winkel in gleicher Richtung (alle links oder alle rechts)
    4. Gesamtwinkel > min_total_angle_deg

    Args:
        polygon: Polygon-Koordinaten
        angle_threshold_deg: Max. Winkel pro Segment für Kurve
        min_consecutive: Min. Anzahl aufeinanderfolgende Punkte
        min_total_angle_deg: Min. Gesamtwinkel der Kurve

    Returns:
        Liste von CurveSegment mit start_idx, end_idx, radius, direction
    """
    curves = []
    n = len(polygon)

    # Winkeländerungen berechnen
    angles = []
    for i in range(n):
        p1 = polygon[i]
        p2 = polygon[(i + 1) % n]
        p3 = polygon[(i + 2) % n]

        angle = calculate_angle_change(p1, p2, p3)
        angles.append(angle)

    # Kurven-Sequenzen finden
    i = 0
    while i < n:
        # Suche Sequenz mit kleinen Winkeln in gleicher Richtung
        sequence_start = i
        sequence_angles = []
        direction = None

        while i < n + sequence_start:
            idx = i % n
            angle = angles[idx]

            # Prüfe ob Winkel klein genug
            if abs(angle) > angle_threshold_deg:
                break

            # Prüfe Richtung (alle links oder alle rechts)
            if direction is None:
                direction = "left" if angle > 0 else "right"
            elif (direction == "left" and angle < 0) or \
                 (direction == "right" and angle > 0):
                break

            sequence_angles.append(angle)
            i += 1

        # Prüfe ob Sequenz lang genug und Gesamtwinkel gross genug
        if len(sequence_angles) >= min_consecutive:
            total_angle = sum(sequence_angles)
            if abs(total_angle) >= min_total_angle_deg:
                # Radius schätzen
                arc_length = calculate_arc_length(polygon, sequence_start, i-1)
                radius = arc_length / (abs(total_angle) * math.pi / 180)

                curves.append(CurveSegment(
                    start_idx=sequence_start % n,
                    end_idx=(i - 1) % n,
                    num_points=len(sequence_angles),
                    total_angle_deg=total_angle,
                    direction=direction,
                    radius_m=radius
                ))

        i = max(i, sequence_start + 1)

    return curves
```

### 4.2 Datenstruktur

```python
@dataclass
class CurveSegment:
    """Eine erkannte Rundung im Polygon"""
    start_idx: int          # Index des ersten Punktes
    end_idx: int            # Index des letzten Punktes
    num_points: int         # Anzahl Punkte in der Kurve
    total_angle_deg: float  # Gesamtwinkel der Kurve
    direction: str          # "left" oder "right" (konvex/konkav)
    radius_m: float         # Geschätzter Radius
```

### 4.3 Integration in Grundriss-SVG

```python
# Prompt für Grundriss mit Rundungen

CURVES_SECTION = """
## Erkannte Rundungen

| Bereich | Start-Idx | End-Idx | Winkel | Radius | Richtung |
|---------|-----------|---------|--------|--------|----------|
{curves_table}

### Darstellung im SVG:
1. Rundungen als Bézier-Kurven (nicht als Polygonsegmente!)
2. Markiere Rundungsbereich mit gestrichelter Linie
3. Beschriftung: "Rundung R={radius}m"

### Gerüst-Hinweis:
Rundungen werden mit **Winkelkupplungen** eingerüstet.
- Layher Blitz 70: Winkelkupplung bis 90°
- Feldlängen: 0.73m, 1.09m für enge Radien
"""
```

---

## 5. Implementierungsschritte

### Phase 1: Datenbank-Erweiterung (Priorität: Hoch)

1. **Migrations-Script erstellen**
   - Neue Tabellen: `buildings`, `buildings_fts`, `svg_cache`, `building_environment`
   - Daten aus `building_contexts` migrieren

2. **Search-Service implementieren**
   - `smart_search()` Funktion
   - FTS5-Integration
   - API-Endpoint `/api/v1/search`

3. **SVG-Cache-Service**
   - `get_cached_svg()`, `set_cached_svg()`
   - Cache-Invalidierung

### Phase 2: Umgebungsdaten (Priorität: Hoch)

4. **Environment-Service**
   - `get_surrounding_buildings()`
   - `identify_blocked_facades()`
   - Speicherung in `building_environment`

5. **Grundriss-SVG erweitern**
   - Nachbargebäude anzeigen (grau)
   - Blockierte Fassaden markieren (rot)

### Phase 3: Terrain/Hanglage (Priorität: Mittel)

6. **Terrain-Service erweitern**
   - `get_terrain_for_building()`
   - Gefälle pro Fassade

7. **SVG-Prompts anpassen**
   - Geneigte Terrain-Linie
   - Höhenkoten an Ecken

### Phase 4: Rundungserkennung (Priorität: Mittel)

8. **Kurven-Detection**
   - `detect_curves()` implementieren
   - In `BuildingGeometry` integrieren

9. **Grundriss-SVG mit Kurven**
   - Bézier-Kurven statt Polygonsegmente
   - Rundungen beschriften

### Phase 5: Frontend (Priorität: Niedrig)

10. **Smarte Suche im Frontend**
    - Autocomplete mit Suggestions
    - Name + Adresse anzeigen

11. **Fassadenauswahl-UI**
    - Interaktiver Grundriss
    - Fassaden anklickbar
    - Blockierte Fassaden ausgegraut

---

## 6. API-Übersicht (Neu)

| Endpoint | Methode | Beschreibung |
|----------|---------|--------------|
| `/api/v1/search` | GET | Smarte Suche (Name/Alias/Adresse) |
| `/api/v1/search/suggestions` | GET | Autocomplete-Vorschläge |
| `/api/v1/building/{egid}/environment` | GET | Umgebungsdaten |
| `/api/v1/building/{egid}/terrain` | GET | Terrain-Daten |
| `/api/v1/building/{egid}/curves` | GET | Erkannte Rundungen |
| `/api/v1/building/{egid}/svg/{type}` | GET | SVG aus Cache oder generieren |
| `/api/v1/building/{egid}/facades/select` | POST | Fassaden für Gerüst auswählen |

---

## 7. Bekannte Gebäude (Initial-Daten)

```python
# Initiale Seed-Daten für bekannte Gebäude

LANDMARK_BUILDINGS = [
    {
        "egid": "2242547",
        "name": "Bundeshaus",
        "aliases": ["Parlamentsgebäude", "Swiss Parliament", "Bundeshaus Bern"],
        "adresse": "Bundesplatz 3, 3011 Bern",
        "keywords": "parlament bundesversammlung kuppel regierung",
        "is_landmark": True
    },
    {
        "egid": "1230337",
        "name": "Berner Münster",
        "aliases": ["Münster Bern", "Cathedral Bern"],
        "adresse": "Münsterplatz 1, 3011 Bern",
        "keywords": "kirche kathedrale gotik turm",
        "is_landmark": True
    },
    {
        "egid": "191821074",
        "name": "Kirche St. Peter und Paul",
        "aliases": ["St. Peter und Paul Bern"],
        "adresse": "Rathausgasse 2, 3011 Bern",
        "keywords": "kirche katholisch doppelturm",
        "is_landmark": True
    },
    # ... weitere bekannte Gebäude
]
```

---

## 8. Verbesserte SVG-Prompts (aus Claude.ai Analyse)

Basierend auf: `docs/Verbessertes_Prompt_Schnitt_Ansicht.md`

### 8.1 RECHERCHE-ANWEISUNG für Claude

Bei bekannten/komplexen Gebäuden soll Claude zuerst recherchieren:

```markdown
## RECHERCHE-ANWEISUNG

> **WICHTIG:** Falls Gebäudename, Gebäudetyp oder Baustil mit "RECHERCHIEREN" markiert:
> 1. Suche das Gebäude anhand Adresse/EGID/Koordinaten
> 2. Identifiziere den korrekten Gebäudenamen
> 3. Bestimme Gebäudetyp (Kirche, Rathaus, Wohnhaus, etc.)
> 4. Bestimme Baustil (Neugotik, Barock, Klassizismus, Modern, etc.)
> 5. Ermittle charakteristische Architekturmerkmale (Fensterformen, Portal, Türme)
> 6. Kläre Turmkonfiguration (Anzahl, Position, Form) falls vorhanden
> 7. Validiere die angegebenen Höhenzonen gegen recherchierte Informationen
>
> **Erst danach mit der SVG-Erstellung beginnen.**
```

### 8.2 Unterschied Fassade vs. Schnitt (KRITISCH!)

```
FASSADENANSICHT                    GEBÄUDESCHNITT
================                    ===============
Blick von AUSSEN                   Blick in SCHNITTEBENE

    ┌─────────┐                        ┌─────────┐
    │░░░░░░░░░│ ← Fassade             │█│     │█│ ← Schnittfläche
    │░░░░░░░░░│   (alles sichtbar      │ │     │ │   (dicht schraffiert)
    │░░░░░░░░░│    von aussen)         │ │     │ │
    └─────────┘                        │ │     │ │ ← Innenraum (LEER!)
                                       └─┴─────┴─┘

░░░ = lockere Schraffur            █ = dichte Schnitt-Schraffur
      (Aussenfläche)                   (geschnittenes Mauerwerk)
                                     = weiss (Innenraum)
```

### 8.3 Zwei Schraffur-Patterns

```xml
<defs>
  <!-- Lockere Schraffur für Aussenflächen (Fassade) -->
  <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
    <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
  </pattern>

  <!-- Dichte Schraffur für Schnittflächen (geschnittenes Mauerwerk) -->
  <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
    <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
  </pattern>
</defs>
```

| Element | Fill |
|---------|------|
| Gebäude-Aussenfläche | `url(#hatch)` - lockere Schraffur |
| Schnittfläche (Mauerwerk) | `url(#cut-hatch)` - dichte Schraffur |
| Innenraum | `#FFFFFF` (weiss, leer) |

### 8.4 SVG-Anforderungen pro Typ

#### Grundriss (Draufsicht)
- **Perspektive:** Vogelperspektive, Blick von oben
- **Zeigt:** Gebäudeumriss, Raumaufteilung, Wandstärken
- **Gebäudeform:** Vereinfacht basierend auf Gebäudetyp
- **Gerüstzone:** Rechteckige Hülle mit 1m Abstand (KEINE Treppenstufen!)
- **Schraffur:** `url(#hatch)` für Mauern

#### Fassadenansicht (Elevation)
- **Perspektive:** Frontalansicht von AUSSEN, orthogonal
- **Zeigt:** NUR die sichtbare Aussenfläche
- **WICHTIG:**
  - Vordere Elemente VERDECKEN hintere Elemente
  - Turm verdeckt dahinterliegendes Hauptschiff
  - KEINE Innenräume sichtbar
  - KEINE Gewölbe sichtbar (nur von aussen erkennbare Dachform)
- **Schraffur:** `url(#hatch)` für alle Fassadenflächen

#### Gebäudeschnitt (Querschnitt)
- **Perspektive:** Gebäude AUFGESCHNITTEN entlang Schnittlinie A-A
- **Zeigt:** Innenräume, Konstruktion, Raumhöhen
- **WICHTIG:**
  - Geschnittene Mauern = DICHTE Schraffur `url(#cut-hatch)`
  - Innenräume = WEISS/LEER (keine Schraffur!)
  - Gewölbe, Decken, Böden sichtbar
  - Raumhöhen ablesbar
- **Schraffur:**
  - `url(#cut-hatch)` NUR für geschnittene Bauteile
  - Innenräume LEER lassen

### 8.5 Vereinfachte Polygon-Darstellung

Für komplexe Polygone (>10 Punkte):

```markdown
## Polygon-Daten

### Vereinfachte Bounding-Box
- **Länge (O-W):** ca. {width_m} m
- **Breite (N-S):** ca. {depth_m} m

### Gerüstzone
- **Abstand:** 1.0 m um Gebäude
- **Darstellung:** Vereinfachte rechteckige Hülle um Gesamtgebäude
- **NICHT:** Exakte Offset-Kontur des komplexen Polygons

### Fassaden-Referenz (nur für Grössenangaben)
- Längste Fassade: {longest_m} m
- Gesamtumfang: ca. {perimeter_m} m
- Hinweis: Bei >10 Polygon-Punkten vereinfachte Darstellung verwenden
```

---

## 9. Kosten-Optimierung

### Claude-API Calls minimieren

| Situation | Aktion |
|-----------|--------|
| Gebäude bereits analysiert | SVG/Zonen aus Cache laden |
| Einfaches Gebäude | Auto-Generator (kein Claude) |
| Neues komplexes Gebäude | 1x Claude-Analyse → Cache |
| SVG-Regenerierung | Nur bei Version-Upgrade |

### Geschätzte Kosten

| Aktion | Kosten |
|--------|--------|
| Erstanalyse (ohne Orthofoto) | ~$0.01-0.02 |
| Erstanalyse (mit Orthofoto) | ~$0.05-0.10 |
| SVG aus Cache | $0 |
| Wiederkehrender User | $0 (alles gecached) |

---

## 10. Zusammenfassung der Verbesserungen

### Aus Problem_Gerüstzone.md
- [x] Polygon-Koordinaten im Prompt (relativ oder Bounding-Box)
- [x] Rundungserkennung für Winkelkupplungen
- [x] Umgebungsdaten (blockierte Fassaden)
- [x] Hanglage-Visualisierung

### Aus Verbessertes_Prompt_Schnitt_Ansicht.md
- [x] RECHERCHE-ANWEISUNG für bekannte Gebäude
- [x] Klare Unterscheidung Fassade vs. Schnitt
- [x] Zwei Schraffur-Typen (`hatch` vs. `cut-hatch`)
- [x] Verdeckungs-Regel: Vorne verdeckt hinten
- [x] Innenräume LEER im Schnitt
- [x] Rechteckige Gerüstzone (keine Stufen)

### Smarte Architektur
- [x] Persistente Datenhaltung (SQLite)
- [x] SVG-Caching
- [x] Volltext-Suche (FTS5)
- [x] Alias-Mapping ("Bundeshaus" → EGID)
