# ARCH-001: Vollständige Architektur-Bereinigung

**Erstellt:** 19.01.2026 20:00
**Priorität:** P1 - Kritisch
**Status:** Offen

---

## 1. Problem-Beschreibung

### Der Architektur-Bruch

Gemäss `docs/architecture/ARCHITECTURE.md` ist die Trennung klar definiert:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           GEODATEN-CH SYSTEM                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────┐    ┌─────────────────────────────┐│
│  │     GEODATEN-BACKEND (main.py)      │    │   GERÜSTBAU-BACKEND         ││
│  │                                     │    │   (geruestbau.py)           ││
│  │  Verantwortlich für:                │    │                             ││
│  │  • Gebäudedaten (Polygon, Höhe)     │    │  Verantwortlich für:        ││
│  │  • Nachbar-Suche                    │    │  • Projekte (CRUD)          ││
│  │  • 3D-Layer (Wall, Roof)            │    │  • Gerüst-Konfiguration     ││
│  │  • Terrain-Daten                    │    │  • Foto-Analyse             ││
│  │                                     │    │                             ││
│  │  ══════════════════════════         │    │  KEIN direkter DB-Zugriff!  ││
│  │  │ building_3d.duckdb     │         │    │  Nutzt Geodaten-API         ││
│  │  ══════════════════════════         │    │                             ││
│  └─────────────────────────────────────┘    └─────────────────────────────┘│
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**ABER:** Aktuell importiert `geruestbau.py` Services die DIREKT auf `building_3d.duckdb` zugreifen!

---

## 2. Analyse der Architektur-Brüche

### 2.1 Services mit direktem DB-Zugriff

| Service | Zeilen mit `get_building_3d_connection` | Von geruestbau.py importiert? |
|---------|----------------------------------------|-------------------------------|
| `layer_fetcher.py` | 286, 336, 380, 403, 435, 468 (6×) | ✅ **JA** (Zeilen 551, 614) |
| `neighbors_service.py` | 167, 308 (2×) | ⚠️ Indirekt möglich |
| `blocked_facades_service.py` | 192, 245 (2×) | ⚠️ Indirekt möglich |
| `address_parser.py` | 100 (1×) | ⚠️ Indirekt möglich |
| `neighbor_enrichment.py` | 522, 569, 701 (3×) | ⚠️ Indirekt möglich |
| `wall_facade_matcher.py` | 191, 470 (2×) | ⚠️ Indirekt möglich |

### 2.2 Direkter Import-Beweis in geruestbau.py

```python
# geruestbau.py:551
from app.services.layer_fetcher import get_layer_fetcher_service

# geruestbau.py:614
from app.services.layer_fetcher import get_layer_fetcher_service
```

**Das ist ein ARCHITEKTUR-BRUCH!** `geruestbau.py` sollte NIEMALS `layer_fetcher` importieren, sondern die Geodaten-API `/api/v1/building/*` nutzen.

### 2.3 Services die KORREKT in main.py gehören

Diese Services greifen auf `building_3d.duckdb` zu und gehören zum **Geodaten-Backend**:

| Service | Beschreibung | Korrekte Lokation |
|---------|--------------|-------------------|
| `building_3d_service.py` | Gebäude-CRUD | ✅ main.py |
| `building_3d_schema.py` | Schema-Init | ✅ main.py |
| `tile_prefetch.py` | Tile-Import | ✅ main.py |
| `tile_cache.py` | Tile-Metadaten | ✅ main.py |
| `parquet_writer.py` | Batch-Import | ✅ main.py |
| `roof_3d_service.py` | Dach-Daten | ✅ main.py |
| `layer_fetcher.py` | 3D-Layer | ✅ main.py |
| `neighbors_service.py` | Nachbar-Suche | ✅ main.py |
| `blocked_facades_service.py` | Blockierte Fassaden | ✅ main.py |
| `address_parser.py` | EGID-Lookup | ✅ main.py |
| `neighbor_enrichment.py` | Nachbar-Anreicherung | ✅ main.py |
| `wall_facade_matcher.py` | Wall-Matching | ✅ main.py |

---

## 3. Data-Flow Analyse

### 3.1 Vom Frontend verwendete Endpunkte

```
GERÜSTBAU-APP (Frontend)
         │
         ├─► /api/v1/geruestbau/address/resolve      → Adress-Auflösung
         ├─► /api/v1/geruestbau/projects             → Projekt-CRUD
         ├─► /api/v1/geruestbau/projects/{id}/geodata → Geodaten laden
         ├─► /api/v1/geruestbau/building/{egid}/neighbors → Nachbarn
         ├─► /api/v1/geruestbau/building/{egid}/blocked-facades → Blockiert
         ├─► /api/v1/geruestbau/configurator/facades → Fassaden-Config
         │
         └─► /api/v1/smart-building/data             → SmartBuildingService
```

### 3.2 SOLL-Datenfluss (gemäss ARCHITECTURE.md)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SOLL-DATENFLUSS                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Frontend                                                                   │
│     │                                                                       │
│     │  1. Adresse eingeben                                                  │
│     ▼                                                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ Gerüstbau-Backend (geruestbau.py)                                   │   │
│  │                                                                     │   │
│  │  /api/v1/geruestbau/address/resolve                                │   │
│  │       │                                                             │   │
│  │       │ HTTP-Call (NICHT direkter DB-Zugriff!)                     │   │
│  │       ▼                                                             │   │
│  │  ┌───────────────────────────────────────────────────────────┐     │   │
│  │  │ Geodaten-API (main.py)                                    │     │   │
│  │  │                                                           │     │   │
│  │  │  /api/v1/building/area                                    │     │   │
│  │  │  /api/v1/building/neighbors/{egid}                        │     │   │
│  │  │  /api/v1/building/{egid}/3d-layers                        │     │   │
│  │  │       │                                                   │     │   │
│  │  │       ▼                                                   │     │   │
│  │  │  building_3d.duckdb                                       │     │   │
│  │  └───────────────────────────────────────────────────────────┘     │   │
│  │                                                                     │   │
│  │  Response ◄─────────────────────────────────────────────────────   │   │
│  │       │                                                             │   │
│  │       ▼                                                             │   │
│  │  geruestbau.db (NUR Projekt-Metadaten!)                            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.3 IST-Datenfluss (Architektur-Bruch!)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         IST-DATENFLUSS (FALSCH!)                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Frontend                                                                   │
│     │                                                                       │
│     ▼                                                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ Gerüstbau-Backend (geruestbau.py)                                   │   │
│  │                                                                     │   │
│  │  /api/v1/geruestbau/building/{egid}/neighbors                      │   │
│  │       │                                                             │   │
│  │       │ DIREKTER IMPORT (ARCHITEKTUR-BRUCH!)                       │   │
│  │       ▼                                                             │   │
│  │  layer_fetcher.py                                                   │   │
│  │       │                                                             │   │
│  │       │ get_building_3d_connection() ← FALSCH!                     │   │
│  │       ▼                                                             │   │
│  │  building_3d.duckdb ← DIREKTER ZUGRIFF VON GERÜSTBAU!              │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ❌ Geodaten-API wird UMGANGEN!                                            │
│  ❌ Doppelte Implementierung möglich                                       │
│  ❌ Wartung schwierig                                                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Vollständige Service-Liste

### 4.1 Services prüfen: Verwendet? Löschen?

| Service | Zweck | Von wem verwendet? | Aktion |
|---------|-------|-------------------|--------|
| `geodaten_client.py` | HTTP-Client für Geodaten-API | geruestbau.py | ✅ BEHALTEN (bereinigt 19.01.2026) |
| `layer_fetcher.py` | 3D-Layer laden | geruestbau.py (FALSCH!) | ⚠️ Import aus geruestbau.py ENTFERNEN |
| `neighbors_service.py` | Nachbar-Suche | geruestbau.py? | ⚠️ PRÜFEN - via API ersetzen |
| `blocked_facades_service.py` | Blockierte Fassaden | geruestbau.py? | ⚠️ PRÜFEN - via API ersetzen |
| `address_parser.py` | EGID-Lookup | geruestbau.py? | ⚠️ PRÜFEN - via API ersetzen |
| `neighbor_enrichment.py` | Nachbar-Anreicherung | SmartBuildingService | ✅ BEHALTEN (nur main.py) |
| `wall_facade_matcher.py` | Wall-Matching | deprecated? | ❓ PRÜFEN ob noch verwendet |

### 4.2 Services die SICHER in main.py bleiben

Diese Services sind korrekt und werden von main.py (Geodaten-Backend) verwendet:

- `building_3d_service.py` - Haupt-DB-Service
- `building_3d_schema.py` - Schema-Initialisierung
- `tile_prefetch.py` - Tile-Import
- `tile_cache.py` - Tile-Metadaten
- `parquet_writer.py` - Batch-Import
- `roof_3d_service.py` - Dach-Daten
- `smart_building/` - SmartBuildingService (orchestriert alles)

---

## 5. Bereinigungsplan

### Phase 1: Analyse (sofort)

| # | Aufgabe | Status |
|---|---------|--------|
| 1.1 | Alle `get_building_3d_connection` in geruestbau.py-Imports finden | ✅ Erledigt |
| 1.2 | Data-Flow dokumentieren | ✅ Erledigt |
| 1.3 | Ticket erstellen | ✅ Dieses Dokument |

### Phase 2: API-Endpunkte sicherstellen (P1)

Die Geodaten-API (`main.py`) muss ALLE benötigten Endpunkte bereitstellen:

| # | Endpunkt | Status | Beschreibung |
|---|----------|--------|--------------|
| 2.1 | `GET /api/v1/building/area` | ✅ Existiert | Gebäude im Umkreis |
| 2.2 | `GET /api/v1/building/neighbors/{egid}` | ✅ Existiert | Nachbarn per EGID |
| 2.3 | `GET /api/v1/building/{egid}/3d-layers` | ✅ Existiert | 3D-Layer laden |
| 2.4 | `GET /api/v1/building/{egid}/blocked-facades` | ⚠️ FEHLT? | → In main.py erstellen |

### Phase 3: geruestbau.py bereinigen (P1)

| # | Aufgabe | Datei | Zeilen |
|---|---------|-------|--------|
| 3.1 | `layer_fetcher` Import ENTFERNEN | geruestbau.py | 551, 614 |
| 3.2 | Durch `geodaten_client` HTTP-Calls ersetzen | geruestbau.py | - |
| 3.3 | Alle anderen direkten DB-Zugriffe entfernen | geruestbau.py | - |

### Phase 4: Unbenutzte Services löschen (P2)

Nach Phase 3 prüfen welche Services nicht mehr verwendet werden:

| # | Service | Prüfung | Aktion |
|---|---------|---------|--------|
| 4.1 | `wall_facade_matcher.py` | grep-Suche | Wenn unbenutzt: LÖSCHEN |
| 4.2 | `blocked_facades_service.py` | grep-Suche | In main.py verschieben? |
| 4.3 | Andere deprecated Services | grep-Suche | Bereinigen |

### Phase 5: Dokumentation aktualisieren (P3)

| # | Dokument | Änderung |
|---|----------|----------|
| 5.1 | ARCHITECTURE.md | Status auf "Bereinigt" |
| 5.2 | CLAUDE.md | Service-Übersicht aktualisieren |
| 5.3 | data-flow.md | Korrekten Flow dokumentieren |

---

## 6. Frontend API-Calls (Referenz)

Die folgenden Endpunkte werden vom Frontend (`geruestbau-app`) verwendet:

```typescript
// geruestbau.ts - Verwendete Endpunkte

// Projekte
GET  /api/v1/geruestbau/projects              // Liste
GET  /api/v1/geruestbau/projects/{id}         // Einzelnes Projekt
POST /api/v1/geruestbau/projects              // Erstellen
PUT  /api/v1/geruestbau/projects/{id}         // Aktualisieren
DELETE /api/v1/geruestbau/projects/{id}       // Löschen

// Geodaten (NEUER Endpunkt - 19.01.2026)
GET  /api/v1/geruestbau/projects/{id}/geodata // Geodaten laden

// Adress-Auflösung
GET  /api/v1/geruestbau/address/resolve       // Adresse → EGID

// Nachbarn & Blockierte Fassaden
GET  /api/v1/geruestbau/building/{egid}/neighbors        // Nachbarn
GET  /api/v1/geruestbau/building/{egid}/blocked-facades  // Blockiert

// Configurator
GET  /api/v1/geruestbau/configurator/facades  // Fassaden-Daten

// SmartBuilding (direkt, nicht über geruestbau)
GET  /api/v1/smart-building/data              // Alle Gebäudedaten
```

**Wichtig:** Die meisten Daten werden beim **Öffnen eines Projekts EINMAL geladen**.
Danach nur noch `/neighbors` und `/blocked-facades` bei Bedarf.

---

## 7. Zusammenfassung

### Das Kernproblem

`geruestbau.py` importiert `layer_fetcher.py` direkt, welcher auf `building_3d.duckdb` zugreift.
Das umgeht die Geodaten-API und verletzt die Architektur.

### Die Lösung

1. **Alle direkten DB-Zugriffe aus geruestbau.py entfernen**
2. **geodaten_client.py für HTTP-Calls verwenden** (bereits bereinigt)
3. **Fehlende API-Endpunkte in main.py erstellen**
4. **Unbenutzte Services löschen**

### Erwartetes Ergebnis

Nach der Bereinigung:
- `geruestbau.py` hat **KEINEN** Import von `get_building_3d_connection`
- `geruestbau.py` verwendet **NUR** `geodaten_client.py` für Geodaten
- Alle Geodaten-Zugriffe laufen über die API in `main.py`
- Die Architektur ist sauber getrennt

---

## 8. Nächste Schritte

1. **Phase 2 starten:** Fehlende API-Endpunkte in main.py erstellen
2. **Phase 3 starten:** geruestbau.py bereinigen
3. **Tests:** Alle Frontend-Funktionen testen
4. **Review:** Code-Review der Änderungen

---

**Verantwortlich:** [Name]
**Review:** [Name]
**Geplante Fertigstellung:** [Datum]
