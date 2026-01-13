# Bekannte Bugs

> **NEU 13.01.2026:** `building_3d.db` wurde auf DuckDB migriert → `building_3d.duckdb`
> Historische Bug-Referenzen auf `building_3d.db` beziehen sich auf die neue DuckDB-Datei.

## Offene Bugs

### BUG-017: Fassaden bei Knospenweg 1 falsch dargestellt

**Status:** 🔴 Offen (erkannt 11.01.2026)

**Problem:**
Bei Knospenweg 1, Bern werden die Fassaden falsch dargestellt:
1. **Halbe Fassade:** Eine Fassade erscheint nur halb/abgeschnitten
2. **Falsche Blockierung:** Fassaden werden als blockiert angezeigt, obwohl sie frei sind
3. **Traufhöhe 0.0m:** Die Traufhöhe wird als 0.0m angezeigt (sollte ~5.5m sein)

**Screenshot:** `2026-01-11 19_11_47-Task-Manager.png`

**Betroffene Adresse:**
- Knospenweg 1, Bern (EGID 1243787)

**Vermutete Ursache:**
- Polygon-Vereinfachung (Douglas-Peucker) schneidet Fassade falsch ab
- blocked_facades Berechnung verwendet falsches EGID (siehe BUG-015)
- Höhendaten werden nicht korrekt zugeordnet

**Betroffene Dateien:**
- `backend/app/services/facade_service.py`
- `backend/app/routers/geruestbau.py` - blocked_facades Endpunkt

---

### BUG-020: Bekannte Gebäude bekommen falsche Zonen (GEFIXT)

**Status:** ✅ Gefixt am 12.01.2026

**Problem:**
Das Bundeshaus bekam Kirchen-Zonen ("Seitenschiffe", "Kirchenschiff", "Turm") statt
der korrekten Zonen ("Arkaden", "Hauptgebäude", "Kuppel") aus known_buildings.py.

**Ursache:**
Zwei Fehler:
1. **EGID-Typ:** `get_known_building()` erwartete String-EGID, aber bekam Integer
2. **Reihenfolge:** `_create_default_zone()` wurde VOR `_collect_research_data()` aufgerufen

Die Zonen wurden erstellt BEVOR `_known_zones` aus `known_buildings.py` geladen wurde.

**Fixes:**
1. `known_buildings.py:601-604` - EGID zu String konvertieren vor Lookup
2. `service.py:488-493` - Research VOR Zonen-Erstellung aufrufen

**Betroffene Dateien:**
- `backend/app/services/smart_building/known_buildings.py`
- `backend/app/services/smart_building/service.py`

**Test:**
```bash
curl "http://localhost:8000/api/v1/smart-building/data?address=Bundesplatz%203,%20Bern&include_zones=true"
# → Zonen: Arkaden, Hauptgebäude, Kuppel
```

---

### BUG-021: 3D-Layer Attribute werden nicht gespeichert (GEFIXT)

**Status:** ✅ Gefixt am 12.01.2026

**Problem:**
Bei 3D-Layer Import (on-demand für komplexe Gebäude) wurden wichtige Attribute nicht gespeichert:

| Tabelle | Felder | Status vor Fix |
|---------|--------|----------------|
| building_walls | z_min, z_max | NULL |
| building_roofs | dach_min, dach_max | NULL |
| buildings_3d | has_3d_layers | 0 (nicht gesetzt) |

**Beispiel Bundeshaus (vor Fix):**
```sql
SELECT z_min, z_max FROM building_walls WHERE egid='2242547';
-- z_min=NULL, z_max=NULL

SELECT dach_min, dach_max FROM building_roofs WHERE egid='2242547';
-- dach_min=NULL, dach_max=NULL

SELECT has_3d_layers FROM buildings_3d WHERE egid=2242547;
-- has_3d_layers=0
```

**Ursache:**
Mehrere Fehler in `roof_3d_service.py` und `layer_fetcher.py`:

1. **Wall-Layer**: INSERT ohne z_min/z_max, und falsches Attribut (`DACH_MIN` statt `GESAMTHOEHE`)
2. **Roof-Layer**: INSERT ohne dach_min/dach_max (nur Geometrie gespeichert)
3. **Flag**: `has_3d_layers` wurde nach dem Import nicht auf 1 gesetzt

**Layer-Attribute in swissBUILDINGS3D:**
- **Wall-Layer**: `GELAENDEPUNKT` (Terrain), `GESAMTHOEHE` (Höhe) → z_max = GELAENDEPUNKT + GESAMTHOEHE
- **Roof_solid-Layer**: `DACH_MIN` (Traufe ü.M.), `DACH_MAX` (First ü.M.)

**Fixes in `roof_3d_service.py`:**
1. Zeile 470-478: Wall-Attribute als `wall_props` extrahieren
2. Zeile 480-487: Roof-Attribute als `roof_props` extrahieren
3. Zeile 502-514: Roof INSERT mit dach_min/dach_max erweitert
4. Zeile 510-522: Wall INSERT mit z_min/z_max erweitert
5. Zeile 524-526: `has_3d_layers = 1` UPDATE hinzugefügt

**Fix in `layer_fetcher.py`:**
- Zeile 214-224: z_max aus `GELAENDEPUNKT + GESAMTHOEHE` berechnen

**Ergebnis nach Fix (Bundeshaus):**

| Tabelle | Feld | Wert |
|---------|------|------|
| building_walls | z_min | 541.29m |
| building_walls | z_max | 603.86m |
| building_roofs | dach_min | 569.75m |
| building_roofs | dach_max | 571.05m |
| buildings_3d | has_3d_layers | 1 |

**Test:**
```bash
cd backend
python -c "
from app.services.roof_3d_service import get_roof_3d_service
result = get_roof_3d_service().fetch_all_layers_on_demand('2242547')
print('Layers:', result['loaded_layers'])
print('Wall:', result.get('wall_props'))
print('Roof:', result.get('roof_props'))
"
# → Layers: ['Roof_solid', 'Roof', 'Wall']
# → Wall: {'z_min': 541.29, 'z_max': 603.86}
# → Roof: {'dach_min': 569.75, 'dach_max': 571.05, ...}
```

**Hinweis Floor-Layer:**
Der Floor-Layer Import ist deaktiviert wegen `fiona.errors.UnsupportedGeometryTypeError: 2147483648`.
Der Floor-Layer verwendet einen 3D-Geometrie-Typ, den Fiona nicht unterstützt.
Die Daten sind redundant zum Building_solid Layer.

**Deaktiviert in:** `layer_fetcher.py:225-247`

---

### BUG-019: NaN-EGID verursacht Parsing-Fehler (GEFIXT)

**Status:** ✅ Gefixt am 12.01.2026

**Problem:**
Bei manchen Gebäuden im GDB ist EGID als `float('nan')` gespeichert statt als Integer.
Der Code versuchte `int(nan)` aufzurufen, was fehlschlug:
```
[BUG-015] Kein Polygon-Match für (2600683.0, 1199480.0). Fallback auf nächstes Zentrum: EGID nan (dist=30.0m)
ERROR:root:Error parsing GDB for polygon: cannot convert float NaN to integer
```

**Ursache:**
- GDB speichert EGID als `float` (nicht `int`)
- Gebäude ohne EGID haben den Wert `nan`
- `if egid` ist `True` für NaN (NaN ist truthy in Python!)
- `int(nan)` wirft ValueError

**Fix:**
```python
# Vor der int-Konvertierung NaN prüfen
import math
if egid is not None and isinstance(egid, float) and math.isnan(egid):
    egid = None
```

**Betroffene Datei:**
- `backend/app/services/swissbuildings3d_fetcher.py:1015-1019` - `parse_gdb_for_building_polygon()`

---

### BUG-018: Multi-Adress-Auflösung gibt falsche EGIDs (GEFIXT)

**Status:** ✅ Gefixt am 12.01.2026 03:15

**Problem:**
Bei Multi-Adress-Auflösung (z.B. "Knospenweg 1-9, Bern") bekamen alle Adressen
die gleiche EGID statt unterschiedliche EGIDs für jedes Gebäude.

**Beispiel (vor Fix):**
```
Knospenweg 1: EGID 1243787
Knospenweg 3: EGID 1243787 (FALSCH - sollte 1243789 sein)
Knospenweg 5: EGID 1243787 (FALSCH - sollte 1243791 sein)
Knospenweg 7: EGID 1243787 (FALSCH - sollte 1243793 sein)
Knospenweg 9: EGID 1243787 (FALSCH - sollte 1243795 sein)
```

**Ursache:**
`building_3d_service.get_by_coordinates()` verwendete `ORDER BY dist_sq LIMIT 1`
und gab einfach das **nächste Gebäude nach Zentrum-Distanz** zurück - OHNE
Point-in-Polygon Check! Bei teilweise gefüllter DB (nur 1 Gebäude) wurde
dieses für alle Koordinaten zurückgegeben.

**Fix:**
`get_by_coordinates()` in `building_3d_service.py` angepasst:
1. Alle Kandidaten im Radius laden (nicht nur LIMIT 1)
2. Point-in-Polygon Check für jeden Kandidaten
3. Bei Match → Gebäude zurückgeben
4. Bei keinem Match → None (damit Stufe 2/3 das GDB parst)

**Betroffene Datei:**
- `backend/app/services/building_3d_service.py:321-420` - `get_by_coordinates()`

**Test:**
```bash
curl "http://localhost:8000/api/v1/geruestbau/address/resolve?address=Knospenweg%201-9,%20Bern"
# → 5 verschiedene EGIDs: 1243787, 1243789, 1243791, 1243793, 1243795
```

---

### BUG-016: Dach-Orientierung bei Reihenhäusern inkonsistent

**Status:** 🟡 Wartet auf 3D-Layer-Migration (erkannt 11.01.2026)

**Problem:**
Bei Reihenhäusern (z.B. Knospenweg 2-10, Bern) wechselt die Dach-Orientierung
zwischen benachbarten Gebäuden, obwohl alle Dächer gleich ausgerichtet sein sollten.

**Beispiel Knospenweg:**
```
EGID 1243788: Azimut=173° → N-S (First Ost-West)
EGID 1243790: Azimut=265° → O-W (First Nord-Süd)
EGID 1243792: Azimut=355° → N-S (First Ost-West)
EGID 1243794: Azimut=265° → O-W (First Nord-Süd)
```

**Ursache:**
Aktuell wird eine **Fallback-Heuristik** verwendet (längste Polygon-Seite),
weil die echten 3D-Layer-Daten (`has_3d_layers=0`) noch nicht extrahiert sind.

**Lösung:**
Die korrekte Dach-Orientierung sollte aus den **swissBUILDINGS3D 3D-Layern** kommen:
- `building_roofs.roof_orientation` - aus DACH-Layer Geometrie berechnet
- `building_roofs.roof_form` - Satteldach, Walmdach, etc.

**Aktueller Stand:**
```sql
SELECT has_3d_layers, roof_orientation FROM buildings_3d WHERE egid=1243790;
-- has_3d_layers=0, roof_orientation=NULL → 3D-Layer noch nicht extrahiert
```

**Nächste Schritte:**
1. 3D-Layer-Migration für Knospenweg-Tile durchführen
2. `roof_orientation` aus DACH-Layer Geometrie extrahieren
3. Frontend: `roof_orientation` aus API verwenden statt Heuristik

**Betroffene Dateien:**
- `geruestbau-app/src/features/scaffold-configurator/components/threeDView/ScaffoldScene.tsx:17-47`
  - `calculatePolygonRoofOrientation()` - NUR als Fallback wenn keine DB-Daten
- `backend/app/services/roof.py` - Sollte DB-Wert priorisieren
- `backend/app/services/layer_extractor.py` - 3D-Layer Extraktion

---

### BUG-015: EGID-Zuordnung bei Koordinaten-Lookup fehlerhaft

**Status:** ✅ Gefixt am 11.01.2026 19:45

**Problem:**
Bei der Koordinaten-basierten Gebäudesuche wurde das Gebäude mit dem
**nächsten Zentrum** zur Geocoding-Koordinate gesucht. Aber die Geocoding-Koordinate
zeigt auf den **Hauseingang**, nicht aufs Gebäudezentrum. Bei Reihenhäusern liegt
der Hauseingang oft näher am Nachbar-Zentrum!

**Beispiel Knospenweg, Bern (vor Fix):**
```
Geocoding "Knospenweg 4": E=2596299.06, N=1199805.22 (Hauseingang)

Gebäude-Zentren in building_3d.db:
  EGID 1243790: E=2596300.3, N=1199805.4  ← Knospenweg 4 (1.3m entfernt)
  EGID 1243792: E=2596299.7, N=1199812.8  ← Knospenweg 6 (7.6m entfernt)
  EGID 1243794: E=2596299.0, N=1199820.1  ← Knospenweg 8 (14.9m entfernt)

ALT: Nächstes Zentrum → EGID 1243790 (zufällig korrekt für Nr. 4)
ABER: Bei Nr. 6 war Zentrum von Nr. 8 näher als von Nr. 6 selbst!
```

**Fix:**
Statt nur nach nächstem Zentrum zu suchen, wird jetzt **Point-in-Polygon** geprüft:

1. Alle Kandidaten im Suchradius laden (mit Polygon)
2. Für jeden: Liegt die Geocoding-Koordinate **im Gebäudepolygon**?
3. Falls Match: Diese EGID zurückgeben (korrekt!)
4. Falls kein Match: Fallback auf nächstes Zentrum (mit Warnung)

**Geänderte Datei:**
- `backend/app/services/address_parser.py:26-128` - `_lookup_egid_by_coordinates()`
  - Neue Hilfsfunktion `_point_in_polygon()` (Ray-Casting, keine Dependencies)
  - Point-in-Polygon Check vor Zentrum-Fallback

**Test:**
```bash
# Multi-Adresse auflösen
curl "http://localhost:8000/api/v1/geruestbau/address/resolve?address=Knospenweg%204-8,%20Bern"
# → Jetzt sollten 3 verschiedene EGIDs zurückkommen
```

---

---

## Optimierungen

### OPT-001: egid_tile_index entfernt (07.01.2026)

**Status:** ✅ Implementiert

**Problem:**
`tile_prefetch.py` rief für jedes Gebäude `register_egid()` auf, was 7197 einzelne
DB-Transaktionen in `tiles.db/egid_tile_index` verursachte (~58s Overhead pro Tile!).

**Lösung:**
- `egid_tile_index` ist redundant seit `building_3d.db` existiert
- `building_3d.db` hat bereits `center_e`, `center_n` für Koordinaten-Lookups
- `address_parser.py` nutzt jetzt `building_3d.db` statt `tiles.db`

**Performance:**
```
VORHER:  158.9s (22ms/Gebäude)
NACHHER:  82.5s (11.5ms/Gebäude)
SPEEDUP:  1.9x (48% schneller!)
```

**Geänderte Dateien:**
- `tile_prefetch.py` - `register_egid()` Aufruf entfernt
- `address_parser.py` - Nutzt `building_3d.db` statt `tiles.db`
- `tile_cache.py` - Funktionen deprecated/umgeleitet
- `swissbuildings3d_fetcher.py` - `_register_egids_from_tile()` Aufrufe entfernt

---

### OPT-002: Direktes Fiona-Reading (08.01.2026)

**Status:** ✅ Implementiert

**Problem:**
GDB-Parsing mit geopandas war langsam (82.5s für 7197 Gebäude = 11.5ms/Gebäude).
geopandas lädt das gesamte GDB in einen GeoDataFrame, bevor iteriert wird.

**Lösung:**
Direktes Fiona-Reading ohne geopandas:
```python
# Vorher (langsam):
gdf = gpd.read_file(gdb_path, layer=layer)
for _, row in gdf.iterrows():
    geom = row['geometry']

# Nachher (schneller):
with fiona.open(gdb_path, layer=layer) as src:
    for feature in src:
        geom = shape(feature['geometry'])
```

**Vorteile:**
- Kein Memory-Overhead durch GeoDataFrame
- Streaming-Iteration statt vollständiges Laden
- Nur shapely + fiona benötigt, kein geopandas

**Performance:** ✅ Gemessen am 08.01.2026
```
VORHER:  82.5s (11.5ms/Gebäude) - geopandas
NACHHER: 70.0s (9.8ms/Gebäude)  - fiona_direct
SPEEDUP: 1.17x (15% schneller)
```

**Gesamt-Performance nach OPT-001 + OPT-002:**
```
ORIGINAL:     158.9s (22.0ms/Gebäude)
NACH OPT-001:  82.5s (11.5ms/Gebäude)  1.9x
NACH OPT-002:  70.0s (9.8ms/Gebäude)   2.2x (gesamt)
```

**Geänderte Datei:**
- `tile_prefetch.py` - `_parse_all_buildings_from_gdb()` neu implementiert

**Performance-Logging:**
Die neue Implementierung loggt automatisch:
```
[PREFETCH] GDB-Parsing: 7197 Gebäude | 45000ms (6.3ms/Gebäude) | Methode: fiona_direct
```

---

## Geplante Optimierungen

### TODO: Weitere GDB Parsing Optimierungen

**Status:** 📋 Geplant (nach OPT-002 Messung)

| Option | Beschreibung | Status | Anwendung |
|--------|--------------|--------|-----------|
| **A) Parallel-Parsing** | multiprocessing.Pool | 📋 Geplant | Batch-Import |
| **B) Direktes Fiona** | Ohne geopandas | ✅ OPT-002 | Alle |
| **C) Vorberechnung** | Alle Gebäude beim Download | 📋 Geplant | Nur Batch-Import |

**Option A - Details:**
Parallelisierung mit multiprocessing für Batch-Imports.
⚠️ Achtung: Fiona-Features sind nicht picklable, müsste Koordinaten serialisieren.
→ Svoll kombiniert mit Option C bei Massenimport.

**Option C - Analyse (08.01.2026):**

Bei User-Requests ist Vorberechnung NICHT sinnvoll:
```
MIT Vorberechnung:  5-10s (Download) + 70s (Parsing) = ~80s Wartezeit
OHNE (aktuell):     5-10s (Download) + 0.5s (1 Geb.) = ~10s Wartezeit
```
→ User Experience würde sich verschlechtern!

**Sinnvoll NUR bei Batch-Import** (z.B. `scripts/import_tiles.py`):
- Kein User wartet → Zeit spielt keine Rolle
- Alle Tiles auf einmal importieren
- Kombinierbar mit Option A (Parallel-Parsing)

**Kleine Optimierungen (optional):**
- **C1:** Paralleles Parsing während ZIP-Entpackung (~1-2s Gewinn)
- **C2:** Prefetch mit höherer Priorität (schnellere Cache-Füllung)

> Siehe `docs/architecture/BATCH_IMPORT.md` für vollständige Dokumentation des Import-Prozesses.

---

## Gefixte Bugs

### BUG-014: Neighbors-API liest aus falscher DB (GEFIXT)

**Status:** ✅ Gefixt am 07.01.2026

**Problem:**
Die Neighbors-API suchte nur in `smart_building_cache`, aber via `tile_prefetch`
werden ALLE Gebäude eines Tiles in `building_3d.db` gespeichert.

**Fix:**
- **Nachbarn:** Direkt aus `building_3d.db` mit koordinaten-basierter Suche
- **Zielgebäude:** building_3d.db zuerst, dann smart_building_cache als Fallback
  (für den Fall dass das Bundle existiert bevor prefetch läuft)

**Geänderte Datei:**
`backend/app/services/neighbors_service.py`

### BUG-013: Zonen nicht an 3D-Viewer übertragen (GEFIXT)

**Status:** ✅ Gefixt am 05.01.2026

**Problem:**
`convertGeodataToConfiguratorFormat()` in `ConfiguratorPage.tsx` übertrug keine
Zonen-Daten an den 3D-Viewer.

**Fix:**
Zonen, building_name, complexity und research_source werden jetzt korrekt
in das `BuildingConfig` Objekt kopiert.

**Betroffene Datei:**
`geruestbau-app/src/pages/ConfiguratorPage.tsx:340-380`
