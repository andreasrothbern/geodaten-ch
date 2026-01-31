# SSE-Pipeline MESSUP - Vollständige Analyse

**Stand:** 31.01.2026 13:30

> **Warum "MESSUP"?** Weil Claude Code eine stabile Pipeline zerstört hat durch:
> - Verschachtelung von Sub-Sub-Sub-Prozessen
> - Side-Effects in Fetcher eingebaut
> - Code in falsche Dateien geschrieben
> - Doppelte Systeme erstellt statt zu korrigieren

---

## 1. Die vollständige SSE-Pipeline (wie sie SEIN SOLLTE)

Die SSE-Pipeline liefert progressiv 8 Events:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SSE-PIPELINE (building_data_stream.py)                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. GEOCODING (~100ms)                                                      │
│     └─► Adresse → Koordinaten, EGID                                        │
│                                                                             │
│  2. GWR (~50ms)                                                             │
│     └─► Geschosse, Fläche, Kategorie                                       │
│                                                                             │
│  3. POLYGON (~200ms oder ~5-10s bei Tile-Download)                         │
│     └─► Gebäude-Polygon mit Fassaden                                       │
│         ├─► Stufe 1: DB-Lookup (~1ms)                                      │
│         ├─► Stufe 2: GDB-Cache mit bbox (~280ms)                           │
│         └─► Stufe 3: Tile-Download + Parse (~5-10s)                        │
│                                                                             │
│  4. HEIGHTS (~50ms)                                                         │
│     └─► Trauf-, First-, Gebäudehöhe                                        │
│                                                                             │
│  5. TERRAIN (~200ms)                                                        │
│     └─► Terrain-Höhe, Hanglage                                             │
│                                                                             │
│  6. ZONES (~500ms, nur bei komplexen Gebäuden)                             │
│     └─► Zonen-Analyse (Claude API)                                         │
│                                                                             │
│  7. RESEARCH (~1s, optional)                                                │
│     └─► Gebäudename, Architekturstil                                       │
│                                                                             │
│  8. COMPLETE                                                                │
│     └─► Vollständiges BuildingDataBundle                                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Jeder Schritt:**
- Holt Daten
- Sendet SSE-Event
- KEINE Side-Effects
- KEINE verschachtelten Sub-Prozesse

---

## 2. Das POLYGON-Problem (Schritt 3)

### 2.1 Wie es SEIN SOLLTE (einfach)

```
POLYGON-Schritt:
    │
    ├─► Stufe 1: DB-Lookup
    │   └─► building_3d_service.get_by_coordinates() → (~1ms)
    │
    ├─► Stufe 2: GDB-Cache
    │   └─► parse_gdb_for_building_polygon() mit bbox → (~280ms)
    │
    └─► Stufe 3: Tile-Download
        └─► download_tile() + parse() → (~5-10s)

    Nach ALLEN SSE-Events (am Ende der Pipeline):
    └─► Background: Rest des Tiles in DB laden (fire-and-forget)
```

### 2.2 Wie es JETZT IST (Chaos)

```
POLYGON-Schritt:
    │
    └─► swissbuildings3d_fetcher.fetch_building_polygon_for_coordinates()
            │
            ├─► Stufe 1: DB-Lookup ✓
            │
            ├─► Stufe 2: GDB mit bbox
            │       │
            │       └─► SIDE-EFFECT: start_background_prefetch() ← WTF?!
            │               │
            │               └─► neighbor_enrichment.prefetch_3_stages() ← FALSCHE DATEI!
            │                       ├─► _parse_building_layer_all()
            │                       ├─► _parse_roof_layer_for_egids()
            │                       ├─► _parse_wall_layer_for_egids()
            │                       ├─► _write_buildings_parquet()
            │                       └─► _import_parquet_to_duckdb()
            │
            └─► Stufe 3: Tile-Download
                    │
                    └─► SIDE-EFFECT: start_background_prefetch() ← NOCHMAL!

    DANN in building_data_stream.py (VOR dem SSE-Event!):
    │
    └─► schedule_prefetch_with_neighbors() ← BLOCKING 141s!
            │
            └─► tile_prefetch.py
                    ├─► load_neighbors_and_save() ← DOPPELT!
                    └─► prefetch_tile_buildings_async() ← NOCHMAL!
```

---

## 3. Was ist `tile_prefetch.py` EIGENTLICH?

### 3.1 Ursprüngliche Bedeutung

`tile_prefetch.py` war **NUR** für Stufe 3 des POLYGON-Schritts:
- Tile von STAC API downloaden
- In lokalen Cache speichern
- Fertig.

### 3.2 Was daraus geworden ist

Jetzt enthält `tile_prefetch.py`:
- `schedule_prefetch_with_neighbors()` - Blockiert 141s!
- `load_neighbors_and_save()` - Parst GDB nochmal
- `prefetch_tile_buildings_async()` - Lädt Rest des Tiles
- Parquet-Pipeline
- Diverse Helper

UND in `neighbor_enrichment.py` (FALSCHE DATEI):
- `prefetch_3_stages()` - Nochmal alles!
- `start_background_prefetch()` - Trigger dafür
- Eigene Parser, Parquet-Writer, DB-Importer

**Resultat:** Zwei parallele Systeme die dasselbe tun!

---

## 4. Die Datei-Verantwortungen (wie sie SEIN SOLLTEN)

| Datei | Verantwortung |
|-------|---------------|
| `building_data_stream.py` | SSE-Pipeline: 8 Schritte orchestrieren |
| `swissbuildings3d_fetcher.py` | POLYGON Stufe 2+3: GDB parsen, Tile downloaden, KEINE Side-Effects |
| `building_3d_service.py` | POLYGON Stufe 1: DB-Lookup |
| `tile_cache.py` | Tile-Cache verwalten (Download-URLs, Pfade) |
| `neighbor_enrichment.py` | Nachbar-Daten ANREICHERN (nicht laden!) |

### Was NICHT existieren sollte:
- `tile_prefetch.py` mit Neighbor-Logik
- `neighbor_enrichment.py` mit Prefetch-Logik
- Side-Effects in Fetchern
- Blocking-Calls vor SSE-Events

---

## 5. Die Messung (Kramgasse 49, saubere Caches)

```
[SSE] GEOCODING: 1624ms ✓
[SSE] GWR: (in GEOCODING enthalten)
[SSE] POLYGON: 148104ms ← 2.5 MINUTEN!
    └─► [3-STUFEN] Stufe 3: Tile-Download + Parse: 280ms ✓ (bbox funktioniert!)
    └─► [PREFETCH_3STAGES] 177 Nachbarn: 6288ms (Background, aber in falscher Datei)
    └─► [NEIGHBORS] 123 Nachbarn: 141782ms ← BLOCKING! DOPPELT!
[SSE] TERRAIN: 98ms ✓
[SSE] ZONES: 33ms ✓
[SSE] RESEARCH: 1.7ms ✓
```

**Das Problem:** Zwischen Tile-Download (280ms) und SSE-Event (148s später) passiert:
1. `start_background_prefetch()` → 6.3s im Background (OK, aber falsche Datei)
2. `schedule_prefetch_with_neighbors()` → **141s BLOCKING** (FALSCH!)

---

## 6. Die Korrektur

### 6.1 Prinzip

```
SSE-Pipeline:
    │
    ├─► Schritt 1-8: Daten holen, Events senden
    │   └─► KEINE Side-Effects in Fetchern
    │   └─► KEINE Blocking-Calls
    │
    └─► NACH allen Events (optional):
        └─► asyncio.create_task(load_rest_of_tile_to_db())
            └─► Fire-and-forget, blockiert NICHTS
```

### 6.2 Konkrete Änderungen

| Was | Wo | Aktion |
|-----|-----|--------|
| Side-Effect `start_background_prefetch()` | `swissbuildings3d_fetcher.py:767-776, 829-839` | **LÖSCHEN** |
| Blocking `schedule_prefetch_with_neighbors()` | `building_data_stream.py:568-600` | **LÖSCHEN** |
| Gesamte Prefetch-Logik | `neighbor_enrichment.py` | **LÖSCHEN** (gehört nicht hierher) |
| `schedule_prefetch_with_neighbors()` | `tile_prefetch.py` | **LÖSCHEN** |
| `load_neighbors_and_save()` | `tile_prefetch.py` | **LÖSCHEN** |

### 6.3 Was übrig bleibt

```
tile_prefetch.py (VEREINFACHT):
    └─► prefetch_tile_buildings_async()
        └─► Lädt Rest des Tiles in DB (Background, fire-and-forget)

swissbuildings3d_fetcher.py (SAUBER):
    └─► fetch_building_polygon_for_coordinates()
        ├─► Stufe 1: DB
        ├─► Stufe 2: GDB mit bbox
        └─► Stufe 3: Tile-Download + Parse
        └─► RETURN: Daten, KEINE Side-Effects

building_data_stream.py (ORCHESTRIERT):
    └─► 8 SSE-Schritte
    └─► Am Ende: Optional Background-Prefetch starten
```

---

## 7. Warum "Neighbors" das Problem ist

Die Idee "Nachbarn zuerst laden" hat alles verkompliziert:

1. **Original-Problem:** User wartet auf Tile-Download (~10s)
2. **Meine "Lösung":** Nachbarn sofort laden, dann Rest
3. **Was passiert ist:**
   - Neighbor-Logik in Fetcher eingebaut (Side-Effect)
   - Neighbor-Logik in `neighbor_enrichment.py` (falsche Datei)
   - Neighbor-Logik in `tile_prefetch.py` (auch hier)
   - Alles doppelt und dreifach
   - BLOCKING statt Fire-and-forget

**Die richtige Lösung wäre gewesen:**
- Zielobjekt schnell finden (bbox-Filter) ✓ (funktioniert!)
- SSE-Event senden
- Rest des Tiles im Background laden
- FERTIG. Keine "Neighbors first"-Logik nötig.

---

## 8. Erwartete Performance nach Cleanup

| Schritt | Aktuell | Nachher |
|---------|---------|---------|
| GEOCODING | 1624ms | 1624ms |
| POLYGON | **148104ms** | **~300ms** (bbox funktioniert bereits!) |
| TERRAIN | 98ms | 98ms |
| ZONES | 33ms | 33ms |
| RESEARCH | 1.7ms | 1.7ms |
| **TOTAL** | **~150s** | **~2s** |

---

## 9. Zusammenfassung

**Das Chaos:**
- 2 Prefetch-Systeme (neighbor_enrichment.py + tile_prefetch.py)
- Side-Effects in Fetcher
- Blocking vor SSE-Event
- Doppelte und dreifache Arbeit
- 148 Sekunden statt 280ms

**Die Lösung:**
- Side-Effects aus Fetcher entfernen
- Blocking-Call aus Pipeline entfernen
- Prefetch-Code aus neighbor_enrichment.py löschen
- Überflüssige Funktionen aus tile_prefetch.py löschen
- Einfacher Background-Task am Ende der Pipeline (optional)

**Das bbox-Filter funktioniert bereits!** Die 280ms für Stufe 2/3 sind OK.
Das Problem sind die 141 Sekunden DANACH durch den Blocking-Call.
