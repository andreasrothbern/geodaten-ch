# Aktuelle Bugs und Fixes

> **Stand:** 30.12.2025
> **Branch:** `main` (Fixes auf main, dann Feature-Branch)

---

## Kritische Bugs (P0)

### BUG-001: Kunstmuseum Hoehendaten falsch

**Status:** Offen
**Prioritaet:** P0 (Kritisch)
**Adresse:** Hodlerstrasse 8, 3011 Bern

**Problem:**
```
Erhalten:  7.9m First, 6.7m Traufe
Erwartet:  ~18m (Museumsgebaeude)
```

**Ursache (vermutlich):**
- Falsches Gebaeude via EGID zugeordnet
- Neubau vs. Altbau verwechselt
- Koordinaten-Mismatch

**Loesung:**
1. EGID fuer Kunstmuseum recherchieren
2. Hoehendaten in swissBUILDINGS3D pruefen
3. Falls Fehler in Quelldaten: zu `known_buildings.py` hinzufuegen

---

## Hohe Prioritaet (P1)

### BUG-002: Unbekannte Gebaeude ohne Namen

**Status:** Offen
**Prioritaet:** P1

**Problem:**
- 6 von 10 Testgebaeuden haben `building_name = N/A`
- Claude-Recherche findet keine Namen

**Betroffene Gebaeude:**
- Hotel Schweizerhof (Marktgasse 67)
- Hauptbahnhof Bern (Bahnhofplatz 10)
- Kornhaus (Kornhausplatz 18)
- Stadttheater (Theaterplatz 7)
- Kunstmuseum (Hodlerstrasse 8)
- Historisches Museum (Helvetiaplatz 5)

**Loesung:**
1. Diese 6 Gebaeude zu `known_buildings.py` hinzufuegen
2. Korrekte EGIDs recherchieren
3. Hoehenzonen definieren

---

### BUG-003: Doppelte API-Calls

**Status:** Offen
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
1. Request-Deduplication in SmartBuildingService
2. Shared Cache fuer aktive Requests
3. Mutex/Lock fuer gleiche Adressen

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

1. **BUG-001** - Kunstmuseum Hoehen (kritisch, Datenqualitaet)
2. **BUG-002** - 6 Gebaeude zu known_buildings.py
3. **BUG-003** - Doppelte API-Calls (Performance)
4. **BUG-004** - Einsteinhaus langsam (Performance)
5. **BUG-005** - Stadttheater Hoehen (Datenqualitaet)
6. **BUG-006** - Zonen bei Unbekannten (UX)
7. **BUG-007** - Encoding (Kosmetik)

---

*Dokument erstellt: 30.12.2025*
