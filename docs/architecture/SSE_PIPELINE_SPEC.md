# SSE-Pipeline Spezifikation

**Stand:** 31.01.2026 16:00
**Status:** ✅ IMPLEMENTIERT
**Zweck:** Referenz für alle zukünftigen Sessions - KEIN NEU BAUEN!

---

## 1. Die komplette SSE-Pipeline

**Datei:** `building_data_stream.py`
**Klasse:** `BuildingDataStreamService`
**Methode:** `stream_building_data()` (Zeile 320-900)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SSE-PIPELINE (8 Schritte)                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  SCHRITT 1: GEOCODING (Zeile 386-469)                                      │
│  ─────────────────────────────────────                                      │
│  Funktion: smart._collect_geocoding(bundle)                                │
│  Dann:     smart._collect_gwr_data(bundle)                                 │
│  Output:   SSEEvent(StreamStep.GEOCODING, {...})                           │
│  Dauer:    ~100-200ms                                                      │
│                                                                             │
│  SCHRITT 2: GWR (Zeile 471-499)                                            │
│  ─────────────────────────────────                                          │
│  Funktion: Daten bereits in Schritt 1 gesammelt                            │
│  Output:   SSEEvent(StreamStep.GWR, {...})                                 │
│  Dauer:    0ms (nur Event senden)                                          │
│                                                                             │
│  SCHRITT 3: POLYGON (Zeile 501-629)                                        │
│  ─────────────────────────────────────                                      │
│  Funktion: smart._collect_building_3d_data(bundle)                         │
│            smart._load_roof_data_from_db(bundle)                           │
│  ✅ FIX: Blocking-Call entfernt (31.01.2026)                               │
│  Output:   SSEEvent(StreamStep.POLYGON, {...})                             │
│  Dauer:    ~300ms (Cache-Hit) oder ~5-10s (Download)                       │
│                                                                             │
│  ✅ NEU: Background-Prefetch (fire-and-forget)                              │
│  ─────────────────────────────────────────────                              │
│  asyncio.create_task(prefetch_and_cleanup(...))                            │
│  Läuft parallel zu Steps 4-8, blockiert NICHT!                             │
│                                                                             │
│  SCHRITT 4: HEIGHTS (Zeile 631-679)                                        │
│  ──────────────────────────────────                                         │
│  Funktion: Daten bereits in Schritt 3 gesammelt                            │
│  Output:   SSEEvent(StreamStep.HEIGHTS, {...})                             │
│  Dauer:    0ms (nur Event senden)                                          │
│                                                                             │
│  SCHRITT 5: TERRAIN (Zeile 681-729)                                        │
│  ──────────────────────────────────                                         │
│  Funktion: smart._collect_terrain_data(bundle)                             │
│  Output:   SSEEvent(StreamStep.TERRAIN, {...})                             │
│  Dauer:    ~50-100ms                                                       │
│                                                                             │
│  SCHRITT 6: ZONES (Zeile 731-786)                                          │
│  ─────────────────────────────────                                          │
│  Funktion: smart._needs_zones_analysis(bundle)                             │
│            smart._collect_zones_analysis(bundle) oder                      │
│            smart._create_default_zone(bundle)                              │
│  Output:   SSEEvent(StreamStep.ZONES, {...})                               │
│  Dauer:    ~30ms (Standard) oder ~500ms (Claude)                           │
│                                                                             │
│  SCHRITT 7: RESEARCH (Zeile 788-827)                                       │
│  ────────────────────────────────────                                       │
│  Funktion: smart._collect_research_data(bundle)                            │
│  Output:   SSEEvent(StreamStep.RESEARCH, {...})                            │
│  Dauer:    ~1-2ms (gecacht) oder ~1s (Claude)                              │
│                                                                             │
│  SCHRITT 8: COMPLETE (Zeile 829-887)                                       │
│  ─────────────────────────────────────                                      │
│  Funktion: smart._assess_data_quality(bundle)                              │
│            _calculate_object_data(bundles)                                 │
│  Output:   SSEEvent(StreamStep.COMPLETE, {...})                            │
│  Dauer:    ~5ms                                                            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Das Problem (GELÖST ✅)

### WAS DAS PROBLEM WAR

```python
# building_data_stream.py:574-600 (VOR DEM FIX)
if bundles and bundles[0].lv95_e and bundles[0].lv95_n:
    from .tile_prefetch import schedule_prefetch_with_neighbors  # ← IMPORT
    ...
    imm, bg = await schedule_prefetch_with_neighbors(  # ← BLOCKING!
        tile_id=tile_id,
        ...
    )
    # → BLOCKIERTE 141 SEKUNDEN bevor SSE-Event gesendet wurde!
```

### WAS JETZT PASSIERT (NACH DEM FIX)

```python
# building_data_stream.py (NACH DEM FIX)
# 1. POLYGON-Daten werden sofort gesendet
yield SSEEvent(StreamStep.POLYGON, {...})

# 2. Background-Task startet (fire-and-forget)
asyncio.create_task(
    prefetch_and_cleanup(tile_id, center_e, center_n, skip_egids)
)
# → BLOCKIERT NICHT! User bekommt sofort die Events.
```

---

## 3. Durchgeführte Änderungen (31.01.2026)

### 3.1 ✅ `building_data_stream.py`

**Zeilen 568-600:** Blocking-Call entfernt

```python
# ENTFERNT: schedule_prefetch_with_neighbors() Aufruf
# NEU: asyncio.create_task(prefetch_and_cleanup(...)) nach dem yield
```

### 3.2 ✅ `swissbuildings3d_fetcher.py`

**Zeilen 764-776 und 825-843:** Side-Effects entfernt

```python
# ENTFERNT: start_background_prefetch() Aufrufe
# ENTFERNT: skip_prefetch Parameter
# NEU: gdb_path wird im Result zurückgegeben (für Caller)
```

### 3.3 ✅ `address_parser.py`

```python
# ENTFERNT: skip_prefetch=True Parameter beim Aufruf
```

### 3.4 ✅ `neighbor_enrichment.py`

```python
# DEPRECATED: start_background_prefetch() - gibt Warning + tut nichts
# DEPRECATED: prefetch_3_stages() - gibt Warning
```

### 3.5 ✅ `tile_prefetch.py`

```python
# DEPRECATED: schedule_prefetch_with_neighbors() - gibt (0,0) zurück
# DEPRECATED: load_neighbors_and_save() - gibt Warning

# NEU: prefetch_and_cleanup() - schlanker Wrapper um prefetch_tile_buildings_async()
```

---

## 4. Die neue Architektur

### 4.1 Datenfluss (SAUBER)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  POLYGON-Step (SAUBER - keine Side-Effects!)                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  smart._collect_building_3d_data(bundle)                                   │
│      │                                                                     │
│      └─► fetch_building_polygon_for_coordinates(e, n)                      │
│              │                                                             │
│              ├─► Stufe 1: DB-Lookup (~1ms)                                 │
│              ├─► Stufe 2: GDB-Cache mit bbox (~280ms)                      │
│              └─► Stufe 3: Tile-Download (~5-10s)                           │
│              │                                                             │
│              └─► RETURN (gdb_path im Result)                               │
│                                                                             │
│  yield SSEEvent(StreamStep.POLYGON, {...})  ← SOFORT!                      │
│                                                                             │
│  asyncio.create_task(prefetch_and_cleanup(...))  ← Fire-and-forget        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Die neue `prefetch_and_cleanup()` Funktion

**Datei:** `tile_prefetch.py`
**Signatur:**
```python
async def prefetch_and_cleanup(
    tile_id: str,
    center_e: float,
    center_n: float,
    skip_egids: Optional[List[int]] = None
) -> int:
```

**Was sie macht:**
1. Holt GDB-Pfad (lädt ggf. neu wenn 'cleaned')
2. Ruft `prefetch_tile_buildings_async()` auf (Parquet-Pipeline)
3. Die Parquet-Pipeline macht: GDB → Parquet → DuckDB + Cleanup

**Wichtig:** GDB wird 2x geöffnet:
- 1x für das Haupt-Objekt (bbox-Filter, schnell ~280ms)
- 1x hier für den Rest (vollständiger Import, ~60-120s Background)

---

## 5. Performance nach dem Fix

| Schritt | VORHER | NACHHER |
|---------|--------|---------|
| GEOCODING | 1624ms | 1624ms |
| GWR | 0ms | 0ms |
| **POLYGON** | **148.104ms** | **~300ms** |
| HEIGHTS | 0ms | 0ms |
| TERRAIN | 98ms | 98ms |
| ZONES | 33ms | 33ms |
| RESEARCH | 2ms | 2ms |
| COMPLETE | 5ms | 5ms |
| **TOTAL** | **~150s** | **~2s** |

**User-Wartezeit:**
- Cache-Hit: ~500ms
- Cache-Miss (GDB vorhanden): ~700ms
- Komplett neu (Download): ~6-11s
- **Background-Prefetch:** ~60-120s (blockiert NICHT!)

---

## 6. Tile-Stati

| Status | local_path | Bedeutung |
|--------|------------|-----------|
| `pending` | Pfad | Tile heruntergeladen, noch nicht importiert |
| `imported` | Pfad | Daten in DB, GDB noch vorhanden |
| `cleaned` | NULL | Daten in DB, GDB gelöscht |
| `reloaded` | Pfad | Tile wurde neu geladen (war 'cleaned') |

---

## 7. Methoden-Übersicht

### WAS VERWENDET WIRD

| Methode | Datei | Funktion |
|---------|-------|----------|
| `fetch_building_polygon_for_coordinates()` | swissbuildings3d_fetcher.py | 3-Stufen Lookup (KEINE Side-Effects!) |
| `parse_gdb_for_building_polygon()` | swissbuildings3d_fetcher.py | bbox-Filter, 1 Gebäude |
| `prefetch_and_cleanup()` | tile_prefetch.py | Background-Task für Rest |
| `prefetch_tile_buildings_async()` | tile_prefetch.py | Parquet-Pipeline |
| `mark_tile_imported()` | tile_cache.py | Status='imported' |
| `mark_tile_cleaned()` | tile_cache.py | Status='cleaned' |

### WAS DEPRECATED IST

| Methode | Datei | Grund |
|---------|-------|-------|
| `start_background_prefetch()` | neighbor_enrichment.py | War Side-Effect im Fetcher |
| `prefetch_3_stages()` | neighbor_enrichment.py | Ersetzt durch prefetch_and_cleanup |
| `schedule_prefetch_with_neighbors()` | tile_prefetch.py | War blocking vor SSE-Event |
| `load_neighbors_and_save()` | tile_prefetch.py | Nicht mehr nötig |

---

## 8. WICHTIG für zukünftige Sessions

> **KEIN NEU BAUEN!**
>
> Die SSE-Pipeline ist fertig implementiert. Bei Problemen:
> 1. Prüfe ob der Background-Task läuft (Logs: `[PREFETCH]`)
> 2. Prüfe ob Side-Effects wieder eingeführt wurden
> 3. Diese Dokumentation lesen!
>
> Die Architektur ist:
> - Fetcher holt Daten, KEINE Side-Effects
> - SSE-Event wird SOFORT gesendet
> - Background-Task läuft parallel (fire-and-forget)
