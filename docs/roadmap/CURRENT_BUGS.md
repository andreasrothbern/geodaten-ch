# Aktuelle Bugs und Fixes

> **Stand:** 30.12.2025
> **Branch:** `main` (Fixes auf main, dann Feature-Branch)

---

## Kritische Bugs (P0)

### BUG-001: Kunstmuseum Hoehendaten falsch ✅

**Status:** Gefixt (30.12.2025)
**Prioritaet:** P0 (Kritisch)
**Adresse:** Hodlerstrasse 8, 3011 Bern

**Problem:**
```
Erhalten:  7.9m First, 6.7m Traufe
Erwartet:  ~18m (Museumsgebaeude)
```

**Ursache:**
- swissBUILDINGS3D liefert falschen Wert (vermutlich Nebengebaeude)

**Loesung:**
- Kunstmuseum zu `known_buildings.py` hinzugefuegt mit korrekten Hoehenzonen:
  - Altbau: 15-18m
  - Neubau (Stettler): 12-15m
  - Erweiterung: 8-10m

---

## Hohe Prioritaet (P1)

### BUG-002: Unbekannte Gebaeude ohne Namen ✅

**Status:** Gefixt (30.12.2025)
**Prioritaet:** P1

**Problem:**
- 6 von 10 Testgebaeuden haben `building_name = N/A`
- Claude-Recherche findet keine Namen

**Betroffene Gebaeude:**
- Hotel Schweizerhof (Bahnhofplatz 11) ✅
- Hauptbahnhof Bern (Bahnhofplatz 10) ✅
- Kornhaus (Kornhausplatz 18) ✅
- Stadttheater (Theaterplatz 7) ✅
- Kunstmuseum (Hodlerstrasse 8) ✅
- Historisches Museum (Helvetiaplatz 5) ✅

**Loesung:**
- Alle 6 Gebaeude zu `known_buildings.py` hinzugefuegt
- ADDRESS_TO_EGID Mappings ergaenzt
- Hoehenzonen definiert:
  - Kunstmuseum: 3 Zonen (Altbau, Neubau, Erweiterung)
  - Kornhaus: 3 Zonen (Arkaden, Hauptbau, Dachreiter)
  - Hauptbahnhof: 3 Zonen (Baldachin, Bahnhofshalle, Bueroturm)
  - Stadttheater: 3 Zonen (Foyer, Zuschauerhaus, Buehnenturm)
  - Historisches Museum: 3 Zonen (Hauptbau, Seitenfluegel, Eckturm)
  - Hotel Schweizerhof: 2 Zonen (Hauptgebaeude, Dachaufbau)

---

### BUG-003: Doppelte API-Calls ✅

**Status:** Gefixt (30.12.2025)
**Prioritaet:** P1

**Problem (aus Log):**
```
INFO:httpx: GET .../SearchServer?searchText=Rathausgasse... (4x!)
INFO:httpx: GET .../height?easting=601009... (6x!)
```

**Ursache:**
- Parallele Requests ohne Koordination
- Fehlende Deduplizierung

**Loesung:**
- Request-Deduplizierung in `SmartBuildingService` implementiert:
  - `_address_locks: Dict[str, asyncio.Lock]` - Ein Lock pro Adresse
  - `_get_address_lock()` - Thread-safe Lock-Erstellung
  - Double-Check Pattern nach Lock-Erwerb
- Bei parallelen Anfragen fuer dieselbe Adresse:
  - Erste Anfrage sammelt Daten
  - Folgende Anfragen warten und erhalten Cache-Ergebnis
- Logging erweitert: "waited for other request"

---

### BUG-004: Einsteinhaus langsam (7.8s)

**Status:** Offen
**Prioritaet:** P1

**Problem:**
- Bekanntes Gebaeude, aber 7822ms Response-Zeit
- Andere bekannte Gebaeude: 329-816ms

**Ursache:**
- Moeglicherweise Cache-Miss
- Oder On-Demand Hoehendaten-Fetch

**Loesung:**
1. Logging verbessern um Ursache zu identifizieren
2. Cache-Warmup fuer bekannte Gebaeude

---

## Mittlere Prioritaet (P2)

### BUG-005: Stadttheater Hoehen fragwuerdig

**Status:** Offen
**Prioritaet:** P2

**Problem:**
```
Erhalten:  15-17m
Erwartet:  ~25m (Theater mit Buehnenturm)
```

**Loesung:**
- Hoehendaten validieren
- Zu `known_buildings.py` hinzufuegen mit korrekten Zonen

---

### BUG-006: Nur 1-2 Zonen bei komplexen Gebaeuden

**Status:** Offen
**Prioritaet:** P2

**Problem:**
- Unbekannte komplexe Gebaeude erhalten nur 1-2 Zonen
- Sollten 3-4 Zonen haben

**Betroffene Gebaeude:**
- Hauptbahnhof: 1 Zone (sollte 3+)
- Historisches Museum: 1 Zone (sollte 3+)

**Loesung:**
- Claude-Analyse verbessern
- Oder: zu `known_buildings.py` hinzufuegen

---

## Niedrige Prioritaet (P3)

### BUG-007: Encoding teilweise inkonsistent

**Status:** Beobachten
**Prioritaet:** P3

**Problem:**
- UTF-8 in manchen Logs kaputt
- ASCII-Ersetzungen nicht ueberall konsistent

**Loesung:**
- Encoding in allen Services vereinheitlichen
- ASCII-only fuer Prompts (bereits implementiert)

---

## Gefixt (Erledigt)

### BUG-001: Kunstmuseum Hoehendaten ✅

**Status:** Gefixt (30.12.2025)

**Loesung:**
- Kunstmuseum zu `known_buildings.py` hinzugefuegt
- Korrekte Hoehenzonen: Altbau 18m, Neubau 15m, Erweiterung 10m

---

### BUG-002: 6 Berner Gebaeude ✅

**Status:** Gefixt (30.12.2025)

**Loesung:**
- Alle 6 Gebaeude mit korrekten Zonen hinzugefuegt
- ADDRESS_TO_EGID Mappings ergaenzt

---

### BUG-003: Doppelte API-Calls ✅

**Status:** Gefixt (30.12.2025)

**Loesung:**
- Request-Deduplizierung mit asyncio.Lock pro Adresse
- Double-Check Pattern nach Lock-Erwerb

---

### BUG-008: ConnectTimeout ohne Retry ✅

**Status:** Gefixt (30.12.2025)
**Commit:** 316bd35

**Problem:**
- swisstopo/geodienste.ch Timeout fuehrte zu 500 Error
- Keine Retry-Logik

**Loesung:**
- 3x Retry mit exponential backoff
- Timeout erhoeht auf 30s
- Logging fuer Retry-Versuche

---

## Bug-Fix Workflow

```bash
# 1. Bug auf main fixen (kleine Fixes)
git checkout main
# ... fix ...
git commit -m "fix: BUG-001 Kunstmuseum Hoehendaten"
git push

# 2. Groessere Features auf Branch
git checkout -b feature/ml-learning-system
# ... implement ...
git push -u origin feature/ml-learning-system
# PR erstellen
```

---

## Priorisierte Reihenfolge

1. ~~**BUG-001** - Kunstmuseum Hoehen~~ ✅ Gefixt
2. ~~**BUG-002** - 6 Gebaeude zu known_buildings.py~~ ✅ Gefixt
3. ~~**BUG-003** - Doppelte API-Calls~~ ✅ Gefixt
4. **BUG-004** - Einsteinhaus langsam (Performance)
5. **BUG-005** - Stadttheater Hoehen (Datenqualitaet)
6. **BUG-006** - Zonen bei Unbekannten (UX)
7. **BUG-007** - Encoding (Kosmetik)

---

*Dokument erstellt: 30.12.2025*
