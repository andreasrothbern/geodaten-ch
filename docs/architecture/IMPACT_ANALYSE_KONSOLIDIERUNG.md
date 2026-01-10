# Impact-Analyse: Datenfluss-Konsolidierung

**Datum:** 04.01.2026
**Status:** In Arbeit

## Architektur-Entscheidung

```
┌─────────────────────────────────────────────────────────────────┐
│  GEBÄUDE-DATEN (building_contexts.db) - pro EGID               │
│  → Ändert sich NICHT, wird gecacht                              │
├─────────────────────────────────────────────────────────────────┤
│  • Grunddaten (Polygon, Höhen, GWR)                            │
│  • Enrichment (Terrain, Hanglage, Zonen)                       │
│  • SVG-Cache, Recherche-Cache                                   │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  PROJEKT-DATEN (geruestbau.db) - pro Projekt                   │
│  → User-spezifisch, ändert sich                                 │
├─────────────────────────────────────────────────────────────────┤
│  • EGID-Referenzen (buildings[])                               │
│  • Einstellungen (simplify_epsilon, field_length_ratio)        │
│  • Foto-Analyse, Vision (projekt-spezifisch!)                  │
│  • Client, Deadline, Status                                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 1. BACKEND - Impact-Analyse

### 1.1 Bereits angepasst ✅

| Datei | Änderung | Status |
|-------|----------|--------|
| `models/geruestbau.py` | `building_data` entfernt aus Project | ✅ |
| `services/geruestbau/project_service.py` | `enrich_with_geodata()` → speichert in `building_environment` | ✅ |
| `services/geruestbau/project_service.py` | `_row_to_project()` ohne `building_data` | ✅ |

### 1.2 Zu prüfen / anpassen ⚠️

| Datei | Was prüfen | Priorität |
|-------|------------|-----------|
| `services/smart_building/service.py` | Nutzt bereits `building_contexts.db`? | P1 |
| `services/building_context.py` | Integration mit SmartBuildingService | P1 |
| `services/intelligent_db.py` | `set_building_environment()` - Terrain-Format | P2 |
| `routers/geruestbau.py` | API-Responses anpassen (kein `building_data`) | P1 |
| `routers/smart_building.py` | Enrichment-Daten aus `building_environment` laden | P1 |

### 1.3 Foto/Vision - Projekt-spezifisch

**WICHTIG:** Foto-Analyse gehört ins PROJEKT, nicht ins Gebäude!

```python
# geruestbau.db → projects Tabelle
# Neue Spalte (oder in scaffold_config JSON):
photos: [
    {
        "id": "uuid",
        "filename": "fassade_nord.jpg",
        "facade_index": 0,
        "analysis": {
            "detected_elements": [...],
            "view_direction": "N",
            "confidence": 0.85
        }
    }
]
```

---

## 2. API - Impact-Analyse

### 2.1 Endpunkte die Gebäude-Daten liefern

| Endpunkt | Aktuell | Soll | Action |
|----------|---------|------|--------|
| `GET /smart-building/data` | Liefert BuildingDataBundle | ✅ OK (inkl. Terrain aus building_environment) | Prüfen |
| `GET /geruestbau/projects/{id}` | Hatte `building_data` | ❌ Entfernt | Frontend anpassen |
| `POST /geruestbau/projects/{id}/enrich` | Speicherte in `building_data` | ✅ Speichert in `building_environment` | OK |
| `GET /geruestbau/building/{egid}/neighbors` | Dynamisch | ✅ OK (nicht gespeichert) | OK |

### 2.2 API-Bereinigung nötig

| Endpunkt | Problem | Action |
|----------|---------|--------|
| `GET /building/context/{egid}` | Redundant zu SmartBuildingService? | Konsolidieren |
| `GET /building/{egid}/environment` | In `intelligent_db.py` | Prüfen ob genutzt |
| `POST /enrich` | Mehrere Varianten? | Vereinheitlichen |

### 2.3 Neue/Angepasste Responses

```typescript
// ALT: ProjectWithGeodata hatte building_data
interface ProjectWithGeodata {
    id: string;
    buildings: BuildingEntry[];
    building_data: {...};  // ❌ ENTFERNT
    geodata: {...};
}

// NEU: Enrichment-Daten separat abrufen
interface ProjectWithGeodata {
    id: string;
    buildings: BuildingEntry[];
    geodata: {...};  // Aus building_3d.db (via tile_prefetch)
    // Terrain/Hanglage: GET /building/{egid}/environment
}
```

---

## 3. FRONTEND - Impact-Analyse

### 3.1 Betroffene Komponenten

| Komponente | Nutzt aktuell | Muss angepasst werden |
|------------|---------------|----------------------|
| `ProjectList.tsx` | `project.building_data` | ⚠️ Ja - Feld existiert nicht mehr |
| `ScaffoldConfigurator.tsx` | `building_data.terrain` | ⚠️ Ja - Separat laden |
| `BuildingView2D.tsx` | Polygon, Höhen | Prüfen - woher kommen Daten? |
| `BuildingView3D.tsx` | Terrain für Boden-Höhe | ⚠️ Ja - aus building_environment |
| `FacadeSelector.tsx` | Fassaden-Daten | Prüfen |

### 3.2 Datenfluss Frontend

```
┌─────────────────────────────────────────────────────────────────┐
│  AKTUELLER FLOW (zu prüfen)                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Projekt laden                                               │
│     GET /geruestbau/projects/{id}                              │
│     → Project (ohne building_data!)                            │
│                                                                 │
│  2. Gebäude-Daten laden (pro EGID)                             │
│     GET /smart-building/data?egid=...                          │
│     ODER: Aus project.buildings[] (bereits vorhanden?)         │
│                                                                 │
│  3. Terrain/Hanglage laden (wenn nötig)                        │
│     GET /building/{egid}/environment                           │
│     → { terrain_data: { height_m, slope_m, slope_class } }     │
│                                                                 │
│  4. Nachbarn laden (dynamisch bei Slider-Änderung)             │
│     GET /geruestbau/building/{egid}/neighbors?radius_m=X       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.3 Konkrete Frontend-Änderungen

| Datei | Änderung | Priorität |
|-------|----------|-----------|
| `src/types/project.ts` | `building_data` entfernen aus Interface | P1 |
| `src/api/projects.ts` | Response-Type anpassen | P1 |
| `src/hooks/useProject.ts` | Terrain separat laden wenn nötig | P2 |
| `src/components/ScaffoldConfigurator.tsx` | Terrain aus separatem Call | P2 |
| `src/components/BuildingView3D.tsx` | Terrain für Boden | P2 |

---

## 4. PRIORISIERTE TODO-LISTE

### Phase 1: Backend stabilisieren (P1)

- [ ] SmartBuildingService: Prüfen ob Terrain aus `building_environment` geladen wird
- [ ] API-Response: `ProjectWithGeodata` - was liefert `geodata`?
- [ ] Redundante Endpunkte identifizieren und konsolidieren

### Phase 2: Frontend anpassen (P1)

- [ ] TypeScript Interfaces aktualisieren (`building_data` entfernen)
- [ ] Prüfen welche Komponenten `building_data` nutzen
- [ ] Terrain-Daten separat laden wenn benötigt

### Phase 3: Foto/Vision korrekt einordnen (P2)

- [ ] Foto-Upload bleibt im Projekt (geruestbau.db)
- [ ] Vision-Analyse-Ergebnisse im Projekt speichern
- [ ] Klare Trennung: Gebäude-Daten vs. Projekt-Daten

### Phase 4: Cleanup (P3)

- [ ] Alte `building_data` Spalte in DB behalten (Migration)
- [ ] Unused APIs entfernen
- [ ] Dokumentation finalisieren

---

## 5. RISIKEN

| Risiko | Auswirkung | Mitigation |
|--------|------------|------------|
| Frontend bricht | Hoch | Interfaces zuerst anpassen, testen |
| Daten-Verlust | Mittel | `building_data` Spalte nicht löschen |
| Performance | Gering | Caching in `building_contexts.db` |

---

## 6. OFFENE FRAGEN

1. **Wie lädt das Frontend aktuell Terrain-Daten?**
   - Aus `project.building_data.terrain`? → Muss geändert werden
   - Aus `project.geodata`? → Prüfen was dort drin ist

2. **Was ist in `project.buildings[]`?**
   - Nur EGID-Referenzen?
   - Oder vollständige Gebäude-Daten (Polygon, Höhen)?

3. **Wird `GET /building/{egid}/environment` bereits genutzt?**
   - Im Frontend?
   - Oder nur Backend-intern?

---

## 7. FRONTEND-ANALYSE ERGEBNISSE

### Gute Nachrichten ✅

| Finding | Status |
|---------|--------|
| **Keine `building_data` Dependency** | Frontend nutzt lokale `ConfiguratorBuildingData` - NICHT Backend Project.building_data |
| **`geodata` wird genutzt** | ProjectWithGeodata.geodata für Cache (Polygon, Höhen) |
| **Terrain NICHT genutzt** | Kein Breaking Change - aber Feature-Gap |

### Aktueller Datenfluss (ConfiguratorPage.tsx)

```
1. GET /projects/{id}
   → Project + geodata (aus building_3d.db via tile_prefetch)

2. Falls keine geodata:
   GET /configurator/facades?address=...
   → Fassaden-Daten dynamisch berechnen

3. convertGeodataToConfiguratorFormat()
   → Lokale ConfiguratorBuildingData Struktur

4. <ScaffoldConfigurator {...props} />
```

### Was NICHT nötig ist

- ❌ `building_data` aus Interfaces entfernen (existiert nicht im Frontend)
- ❌ Project-Type ändern (nutzt bereits `geodata`, nicht `building_data`)

### Was OPTIONAL ist (Feature-Erweiterung)

| Feature | Aktuell | Sollte |
|---------|---------|--------|
| Terrain in 3D-View | ❌ Nicht vorhanden | Boden-Neigung visualisieren |
| Hanglage-Warnung | ❌ Nicht vorhanden | Bei slope > 1.5m warnen |
| SUVA Höhenausgleich | ❌ Nicht vorhanden | Ausgleichsrahmen empfehlen |

### API-Migration (optional, nicht dringend)

```
ALT (funktioniert weiterhin):
GET /geruestbau/configurator/facades?address=...

NEU (mit mehr Daten):
GET /smart-building/data?address=...&include_terrain=true
```

---

## 8. FAZIT

### Backend: Konsolidierung ABGESCHLOSSEN ✅

| Änderung | Status |
|----------|--------|
| `building_data` aus Project Model entfernt | ✅ |
| Terrain/Hanglage in `building_environment` | ✅ |
| `_row_to_project()` angepasst | ✅ |
| Dokumentation aktualisiert | ✅ |

### Frontend: KEINE Breaking Changes ✅

| Bereich | Status |
|---------|--------|
| TypeScript Interfaces | ✅ Keine Änderung nötig |
| API-Calls | ✅ Funktionieren weiterhin |
| Datenfluss | ✅ Nutzt `geodata`, nicht `building_data` |

### Offene Punkte (P2/P3)

1. **Terrain-Integration im Frontend** (Feature, nicht Bug)
2. **API-Konsolidierung** `/configurator/facades` vs `/smart-building/data`
3. **Foto/Vision** korrekt im Projekt speichern (nicht in building_contexts.db)

---

## 9. KORRIGIERTE ARCHITEKTUR

```
┌─────────────────────────────────────────────────────────────────┐
│  building_3d.db (Gebäude-Grunddaten via tile_prefetch)         │
├─────────────────────────────────────────────────────────────────┤
│  buildings_3d           → EGID, Polygon, Höhen, Koordinaten     │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  building_contexts.db (Enrichment pro EGID)                    │
├─────────────────────────────────────────────────────────────────┤
│  building_contexts      → Zonen (Claude/known_buildings)        │
│  building_environment   → Terrain, Hanglage                     │
│  svg_cache              → Generierte SVGs                       │
│  claude_research_cache  → API-Antworten (TTL 30d)               │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  geruestbau.db (pro Projekt - user-spezifisch)                 │
├─────────────────────────────────────────────────────────────────┤
│  projects                                                       │
│  ├─ egid / buildings[]  → Referenzen                           │
│  ├─ scaffold_config     → Einstellungen (epsilon, ratio)       │
│  ├─ photos              → Foto-Uploads + Vision-Analyse        │
│  └─ client, deadline    → Projekt-Metadaten                    │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  DYNAMISCH (nicht gespeichert)                                 │
├─────────────────────────────────────────────────────────────────┤
│  • Nachbar-Gebäude (Radius-Slider)                             │
│  • Fassaden-Vereinfachung (Epsilon-Regler)                     │
│  • Gerüst-Berechnung (Feldlängen-Slider)                       │
└─────────────────────────────────────────────────────────────────┘
```

---

*Analyse abgeschlossen: 04.01.2026*