# Objekt-Architektur Refactoring

**Stand: 19.01.2026 ~11:00**
**Status: IN ARBEIT**

## Kontext

Das bisherige Konzept "Hauptgebäude + additionalBuildings" war falsch. Die neue Architektur:

**Ein Projekt = Ein Objekt**

- `polygon_object`: Das Polygon für Gerüstplanung (IMMER vorhanden)
  - Single-Building: Das eine Polygon
  - Multi-Building: Union aller Polygone (äussere Kontur)
- `projectBuildings`: Metadaten aller Gebäude (Adressen, EGIDs)
- `neighbors`: Nachbargebäude in der Umgebung (unverändert)

## Alte vs. Neue Architektur

| Alt (FALSCH) | Neu (KORREKT) |
|--------------|---------------|
| `buildingData` (Hauptgebäude) | `polygon_object` (das Objekt) |
| `additionalBuildings[]` (weitere) | `projectBuildings[]` (nur Metadaten) |
| `polygon_combined` (optional) | `polygon_object` (IMMER vorhanden) |
| Gerüst nur auf erstem Gebäude | Gerüst auf gesamtem Objekt |

## Erledigte Schritte

### 1. Backend: `building_data_stream.py` ✅

**Datei:** `backend/app/services/building_data_stream.py`

**Änderungen:**
- `_calculate_combined_data()` → `_calculate_object_data()` umbenannt
- Funktion berechnet jetzt IMMER ein Ergebnis (auch bei Single-Building)
- Feldnamen geändert:
  - `polygon_combined` → `polygon_object`
  - `facades_combined` → `facades_object`
  - `roof_combined` → `roof_object`
- Neues Feld: `projectBuildings` (Metadaten aller Gebäude)
- SSE Response enthält `object_data` (statt `combined`)

**Zeilen:** 41-174 (Funktion), 775-806 (SSE Response)

### 2. Frontend Types: `geruestbau.ts` ✅

**Datei:** `geruestbau-app/src/api/geruestbau.ts`

**Neue Interfaces (Zeilen 47-94):**
```typescript
interface ProjectBuildingMetadata {
  egid: string
  address: string
  center_e: number
  center_n: number
}

interface ObjectFacade {
  index: number
  direction: string
  length_m: number
  height_m: number
  start_point: [number, number]
  end_point: [number, number]
  azimuth_deg: number
}

interface ObjectData {
  polygon_object: [number, number][]
  facades_object: ObjectFacade[]
  roof_object?: { z_min: number | null, z_max: number | null }
  projectBuildings: ProjectBuildingMetadata[]
  total_area_m2: number
  total_perimeter_m: number
  avg_traufhoehe_m: number | null
  building_count: number
}
```

**Deprecated Interfaces:**
- `MultiBuildingData` - für Rückwärtskompatibilität behalten
- `MultiBuildingFacade` - für Rückwärtskompatibilität behalten

## Offene Schritte

### 3. Backend testen ⏳

**Test-Befehle:**
```bash
# Backend starten
cd geodaten-ch/backend
".\venv\Scripts\python.exe" -m uvicorn app.main:app --port 8000

# Single-Building testen (Knospenweg 4)
curl "http://localhost:8000/api/v1/smart-building/stream?address=Knospenweg%204,%20Bern"
# Prüfen: object_data vorhanden mit polygon_object

# Multi-Building testen (Knospenweg 4-6)
curl "http://localhost:8000/api/v1/smart-building/stream?address=Knospenweg%204-6,%20Bern"
# Prüfen: object_data.building_count = 2, polygon_object = Union
```

**Erwartete Response (Single-Building):**
```json
{
  "status": "ok",
  "egid": "1243790",
  "bundle": {...},
  "object_data": {
    "polygon_object": [[2596300, 1199805], ...],
    "facades_object": [...],
    "roof_object": {"z_min": 555.0, "z_max": 562.0},
    "projectBuildings": [{"egid": "1243790", "address": "Knospenweg 4, Bern", ...}],
    "building_count": 1
  }
}
```

### 4. Frontend ConfiguratorPage ⏳

**Datei:** `geruestbau-app/src/pages/ConfiguratorPage.tsx`

**Zu entfernende States:**
- `manualAdditionalBuildings` (Zeile ~535)
- `setManualAdditionalBuildings` (Zeile ~880, 900, 930)
- `loadingAdditionalBuildings` (falls vorhanden)

**Zu ändernde Logik:**
- Zeilen 817-907: Statt `additionalBuildings[]` laden → `object_data` verwenden
- Zeilen 1299-1325: Multi-Building Selektion anpassen
- Zeile 1530: Props an ScaffoldConfigurator anpassen

**Neuer State:**
```typescript
const [objectData, setObjectData] = useState<ObjectData | null>(null);
```

### 5. ScaffoldConfigurator Props ⏳

**Datei:** `geruestbau-app/src/features/scaffold-configurator/components/ScaffoldConfigurator.tsx`

**Zu ändern:**
- Zeile 33: `additionalBuildings?: MultiBuildingData[]` entfernen
- Zeile 60: `additionalBuildings = []` entfernen
- Zeile 169, 172: Props an FacadePanel/ThreeDPanel anpassen

**Neues Prop:**
```typescript
objectData?: ObjectData  // Statt additionalBuildings
```

### 6. FacadePanel ⏳

**Datei:** `geruestbau-app/src/features/scaffold-configurator/components/FacadePanel.tsx`

**Zu ändern:**
- Zeile 26: `additionalBuildings?: MultiBuildingData[]` entfernen
- Zeile 42: `additionalBuildings = []` entfernen
- Zeilen 243-283: additionalPolygons Logik anpassen

### 7. ThreeDPanel + ScaffoldScene ⏳

**Dateien:**
- `ThreeDPanel.tsx`
- `threeDView/ScaffoldScene.tsx`

**ScaffoldScene Änderungen:**
- Zeile 56: `additionalBuildings?: MultiBuildingData[]` → `objectData?: ObjectData`
- Zeile 1145: Props anpassen
- Zeilen 1502-1575: `multiBuildingData.forEach()` → nur projectBuildings für Metadaten

**Wichtig:** Bei der neuen Architektur wird das Gerüst am `polygon_object` geplant, nicht pro Gebäude!

## Testfälle nach Abschluss

1. **Single-Building (Knospenweg 4):**
   - [ ] polygon_object wird korrekt angezeigt
   - [ ] Fassaden werden berechnet
   - [ ] Gerüst wird korrekt dargestellt
   - [ ] Dach wird korrekt gerendert

2. **Multi-Building (Knospenweg 4-6):**
   - [ ] polygon_object = Union der Polygone
   - [ ] projectBuildings zeigt beide Adressen
   - [ ] Gerüst umfasst das gesamte Objekt
   - [ ] Dächer beider Gebäude werden gerendert

3. **Nachbarn:**
   - [ ] neighbors[] funktioniert weiterhin
   - [ ] Blockierte Fassaden werden erkannt

## Dateien-Übersicht

| Datei | Status | Änderungen |
|-------|--------|------------|
| `backend/app/services/building_data_stream.py` | ✅ Erledigt | _calculate_object_data(), object_data in SSE |
| `geruestbau-app/src/api/geruestbau.ts` | ✅ Erledigt | Neue Interfaces ObjectData, ProjectBuildingMetadata |
| `geruestbau-app/src/pages/ConfiguratorPage.tsx` | ⏳ Offen | States umbauen, object_data verwenden |
| `geruestbau-app/src/features/.../ScaffoldConfigurator.tsx` | ⏳ Offen | Props anpassen |
| `geruestbau-app/src/features/.../FacadePanel.tsx` | ⏳ Offen | additionalBuildings entfernen |
| `geruestbau-app/src/features/.../ThreeDPanel.tsx` | ⏳ Offen | Props anpassen |
| `geruestbau-app/src/features/.../ScaffoldScene.tsx` | ⏳ Offen | 3D-Rendering auf objectData umstellen |

## Wichtige Hinweise für nächste Session

1. **Rückwärtskompatibilität:** Die alten Interfaces (`MultiBuildingData`) sind noch vorhanden. Nach vollständigem Refactoring können sie entfernt werden.

2. **Testen mit Knospenweg:** Knospenweg 4-6 ist ein gutes Testprojekt für Multi-Building.

3. **Dächer prüfen:** Nach dem Refactoring sicherstellen, dass `roof_object.z_min/z_max` korrekt für die Dach-Darstellung verwendet wird.

4. **SSE-Hook:** Der `useProjectContextStream` Hook muss möglicherweise auch angepasst werden um `object_data` zu verarbeiten.
