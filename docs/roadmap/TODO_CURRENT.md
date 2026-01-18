# Aktuelle TODOs (Stand 15.01.2026 11:00)

## P1: Bugs

### BUG-024: Wall-Layer Daten werden nicht korrekt ans Frontend gesendet

**Status:** 🟡 Backend erledigt, Frontend ausstehend (15.01.2026)
**Details:** Siehe `docs/architecture/3D_LAYER_USAGE_3D_VIEW.md` → BUG-024
**Branch:** `feature/exact-3d-walls`

**Problem:**
- `facade_z_min` enthält nur 1 von 5 Fassaden (nur "E" Richtung)
- `wall_facade_matcher.py` (505 Zeilen!) findet nur ~20% der Fassaden
- `service.py:1115` kehrt nach ANY Match zurück, überspringt restliche Fassaden

**Erledigt (15.01.2026):**
- ✅ `building_walls[]` in API-Response `/configurator/facades` hinzugefügt
  - Naming exakt wie DB-Tabelle (`building_walls`)
  - Volle 3D-Geometrie (`coords_3d`) - ALLE Polygone bei MultiPolygon!
  - Felder: `gebaeudeeinheit`, `egid`, `z_min`, `z_max`, `geometry_type`, `coords_3d`
- ✅ `BuildingWall` Interface in `project.ts` erstellt (DB-Naming!)
- ✅ `/building/{egid}/blocked-facades` als deprecated markiert
- ✅ `wall_facade_matcher.py` als deprecated markiert
- ✅ `_collect_facade_heights()` als deprecated markiert
- ✅ `facade_z_min`, `facade_z_max` in Frontend als deprecated markiert

**Noch offen:**
- [ ] Frontend: Geometrisches Matching für BuildingWall in `polygonSimplifier.ts`
- [ ] Frontend: z_min/z_max aus gematchten Wänden berechnen
- [ ] Testen mit Knospenweg 4, Bern

---

### BUG-023: TerrainProfile - Fassaden-Höhen werden falsch berechnet

**Status:** ✅ Gefixt am 15.01.2026 09:45
**Details:** Siehe `.claude/rules/known-bugs.md` → BUG-023

**Fix angewandt:**
- Zeile `height = dirZMax - dirZMin` entfernt in `polygonSimplifier.ts:362-370`
- `height` bleibt jetzt `defaultHeight` (Traufhöhe, konstant für alle Fassaden)
- `facade_z_min`/`facade_z_max` werden weiterhin für Stellspindeln-Visualisierung verwendet

**Verifiziert:**
- ✅ Build erfolgreich
- ✅ Knospenweg 4, Bern: Traufhöhe 5.54m konstant für alle Fassaden
- ✅ Terrain-Differenz 1.8m korrekt erkannt

---

## P1: Architektur-Vereinfachung (KRITISCH!)

> **WICHTIG:** Diese Architektur wird ständig gefixt und dann wieder kaputt gemacht.
> Muss ein für alle Mal sauber implementiert werden!

### Konzept-Trennung: Neighbors vs. Blocking

**Status:** 🔴 Muss stabilisiert werden
**Doku:** `docs/architecture/STREAMING_ARCHITECTURE.md` Teil I
**Branch:** `feature/exact-3d-walls`

```
┌─────────────────────────────────────────────────────────────┐
│  KONZEPT 1: NEIGHBORS (Nachbar-Gebäude für Kontext)         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Datenquelle: SSE per Koordinaten (Centroid des Gebäudes)  │
│  Radius: 100m beim Start (nicht-blockierend!)              │
│  UI-Slider: 20m / 50m / 100m (filtert im Frontend)         │
│                                                             │
│  Ablauf:                                                    │
│  1. SSE Stream startet mit 100m Radius                     │
│  2. Alle Nachbarn werden ins Frontend geladen              │
│  3. User wählt Zoom-Level → Frontend filtert               │
│  4. Keine weiteren API-Calls nötig!                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  KONZEPT 2: BLOCKING (Fassaden die nicht einrüstbar sind)  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Berechnung: NUR im Frontend (geometrisch)                 │
│  Input: Nachbar-Polygone (aus Konzept 1)                   │
│  Threshold: 2.0m (wenn Nachbar näher → blockiert)          │
│                                                             │
│  Ablauf:                                                    │
│  1. Für jede Fassade: Prüfe Distanz zu allen Nachbarn     │
│  2. Distanz < 2.0m → Fassade ist blockiert                │
│  3. UI zeigt blockierte Fassaden grau/deaktiviert         │
│                                                             │
│  NICHT mehr verwenden:                                      │
│  - SSE blocked_facades Event (deprecated)                  │
│  - Neighbors API blockedSides (deprecated)                 │
│  - Backend-Berechnung (deprecated)                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Tasks:**
- [ ] SSE `blocked_facades` Event als deprecated markieren
- [ ] `blockedFacadesData` State entfernen (Frontend)
- [ ] `blockedDirectionsFromSSE` entfernen (Frontend)
- [ ] `blockedSides` Prop entfernen (Frontend)
- [ ] Nur `blockingNeighbors` verwenden (Frontend-Berechnung)
- [ ] Backend-Endpunkte als @deprecated markieren (nicht löschen!)

---

### 3D-Dachgeometrie: War implementiert, jetzt kaputt

**Status:** 🔴 Muss analysiert werden
**Problem:** 3D-Dachgeometrie war funktional, wurde dann wieder kaputt gemacht.

**TODO:**
- [ ] Analysieren: Was genau ist kaputt?
- [ ] Commit finden wo es zuletzt funktionierte
- [ ] Fix implementieren oder Revert

---

### Deprecation-Strategie

**WICHTIG:** Alte Endpunkte NICHT löschen, sondern als deprecated markieren!

```python
# Backend (FastAPI)
@router.get("/old-endpoint", deprecated=True)
async def old_endpoint():
    """DEPRECATED: Use /new-endpoint instead."""
    pass
```

```typescript
// Frontend (API-Calls)
/** @deprecated Use newEndpoint() instead */
export async function oldEndpoint() { ... }
```

**Grund:** Wir löschen erst wenn die neue Lösung stabil ist.

---

## Erledigt (15.01.2026)

- [x] Storage: Ephemeral vs Volume Trennung
- [x] Storage: DuckDB Temp auf Ephemeral (310 MB befreit)
- [x] Wall-Geometrie: geometry_wkb=NULL beim Prefetch
- [x] Wall-Geometrie: Bestehende Daten bereinigt (20 MB auf Railway)
- [x] Wall-Geometrie: Startup-Cleanup-Skript (CLEANUP_WALL_GEOMETRY Flag)
- [x] Doku: z_min/z_max Klarstellung (Skalar vs. geometry_wkb)
- [x] Debug-Endpoint: /debug/storage für Volume-Diagnose

---

## Kontext für nächste Session

### Wichtige Erkenntnisse heute:

1. **z_min/z_max vs geometry_wkb:**
   - `z_min`, `z_max` = Skalarwerte (beim Prefetch aus GDB-Attributen)
   - `geometry_wkb` = 3D-Form (nur On-Demand, spart ~250 MB)
   - Prefetch hat ALLE Höhen mit LiDAR-Konfidenz!

2. **Railway Storage:**
   - Volume (`/app/data`): Nur DBs (persistent)
   - Ephemeral (`/tmp/geodaten`): Tiles, Parquet, DuckDB-Temp (100GB)

3. **DuckDB Temp-Dateien:**
   - Waren auf Volume (~310 MB)
   - Jetzt auf Ephemeral via `temp_directory` Config

4. **GitHub Actions hängen:**
   - Mehrere Pipelines "In progress" seit Stunden
   - Manuell abbrechen wenn nötig
