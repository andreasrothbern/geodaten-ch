# Bekannte Bugs

## Offene Bugs

*(Keine offenen Bugs)*

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
