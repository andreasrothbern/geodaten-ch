    Alles # Fassaden-Blockierung: Strategien und Vergleich

**Stand:** 25.01.2026 15:00
**Status:** Aktiv in Entwicklung
**Betroffene Datei:** `geruestbau-app/src/features/scaffold-configurator/components/FacadePanel.tsx`

## Übersicht

Bei der Gerüstplanung müssen blockierte Fassaden erkannt werden - Fassaden, die nicht direkt eingerüstet werden können, weil ein Nachbargebäude im Weg ist.

### Das Problem bei Reihenhäusern

```
┌─────────────────────────────────────────────────────────────────────────┐
│   KNOSPENWEG 1-3, BERN (Reihenhäuser)                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   N                                                                     │
│   ↑                                                                     │
│                                                                         │
│   ┌─────────┬─────────┬─────────┐                                      │
│   │         │         │         │                                      │
│   │  Kno 1  │  Kno 3  │  Kno 5  │    ← geteilte Wände!                │
│   │  EGID   │  EGID   │  EGID   │                                      │
│   │ 1243787 │ 1243789 │ 1243791 │                                      │
│   │         │         │         │                                      │
│   └─────────┴─────────┴─────────┘                                      │
│                                                                         │
│   Legende:                                                              │
│   ═══ Geteilte Wand (blockiert)                                        │
│   ─── Freie Fassade (auswählbar)                                       │
│                                                                         │
│   Wenn wir "Knospenweg 3" einrüsten wollen:                            │
│   - LINKS (W): Kno 1 grenzt an → BLOCKIERT                             │
│   - RECHTS (O): Kno 5 grenzt an → BLOCKIERT                            │
│   - VORNE (N): Frei → AUSWÄHLBAR                                       │
│   - HINTEN (S): Frei → AUSWÄHLBAR                                      │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Spezialfall: Partielle Blockierung (Knospenweg 1)

```
┌─────────────────────────────────────────────────────────────────────────┐
│   KNOSPENWEG 1 - Partielle Fassade                                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│        Strasse (N)                                                      │
│   ════════════════════                                                  │
│                                                                         │
│   ┌─────────────────┐                                                  │
│   │                 │                                                  │
│   │     Kno 1      ═│════  ← Nur TEIL der Ost-Fassade blockiert!      │
│   │                 │    │                                             │
│   │                 │    │ Kno 3                                       │
│   │                 │    │                                             │
│   └─────────────────┘    │                                             │
│   │←── freier Teil ─→│   │                                             │
│                          │                                             │
│   Bei Knospenweg 1:                                                    │
│   - Die Ost-Fassade ist nur TEILWEISE blockiert (ca. 60%)             │
│   - Der südliche Teil der Ost-Fassade ist FREI                        │
│   → Partielle Blockierung muss erkannt werden!                        │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Blockierungs-Strategien

### Flags in FacadePanel.tsx

```typescript
// ============================================================================
// BLOCKIERUNGS-FLAGS (zum Testen der verschiedenen Ansätze)
// ============================================================================
const DISABLE_FACADE_BLOCKING = true;   // Master-Schalter: KEINE Blockierung
const USE_UNION_BLOCKING = false;        // NEU: Union-basiert (Objekt + Nachbarn)
const USE_GEOMETRY_BLOCKING = false;     // Alt: Geometrie-basiert (facadeToPolygonDistance)
const USE_DIRECTION_BLOCKING = false;    // Alt: SSE-Richtungs-basiert (blockedDirectionsFromSSE)

const DEBUG_BLOCKING = true;             // Debug-Logging aktivieren
```

---

## Strategie 1: Geometrie-basiert (Alt)

**Flag:** `USE_GEOMETRY_BLOCKING = true`

### Algorithmus

```typescript
function facadeToPolygonDistance(facade, neighborPolygon): number {
  // Berechne minimale Distanz zwischen Fassaden-Kante und Nachbar-Polygon
  const facadeLine = [facade.start_point, facade.end_point];
  return minDistance(facadeLine, neighborPolygon);
}

// Blockiert wenn Distanz < BLOCKING_THRESHOLD_M (2.0m)
```

### Problem

Bei Reihenhäusern mit **geteilten Wänden** ist die Distanz = 0 für ALLE angrenzenden Fassaden, auch für die freien!

```
Knospenweg 3:
- Distanz zu Kno 1: 0m → BLOCKIERT ✓ (korrekt)
- Distanz zu Kno 5: 0m → BLOCKIERT ✓ (korrekt)
- Nord-Fassade: Polygon-zu-Polygon-Distanz zu Kno 1 = 0m → BLOCKIERT ✗ (FALSCH!)

Das Problem: Die Polygon-zu-Polygon Distanz misst den Abstand zwischen den
NÄCHSTEN Punkten beider Polygone. Bei Reihenhäusern liegt der nächste Punkt
immer an der geteilten Wand → Distanz = 0 für ALLE Nachbarn!
```

### Status: ❌ Nicht funktionsfähig

---

## Strategie 2: SSE-Richtungs-basiert (Alt)

**Flag:** `USE_DIRECTION_BLOCKING = true`

### Algorithmus

```typescript
// Backend berechnet blocked_facades per SSE
// Enthält: { egid: { blockers: [{ direction: "W", egid: "1234" }] }}

const blockedDirections = new Set<string>();
for (const blocker of blockedFacadesData[egid].blockers) {
  blockedDirections.add(blocker.direction);  // "N", "S", "E", "W", "NE", "NW", "SE", "SW"
}

// Fassade blockiert wenn ihre Richtung in blockedDirections
function isFacadeBlocked(facade) {
  return blockedDirections.has(facade.direction);
}
```

### Problem

Das Backend klassifiziert Nachbarn nach **Himmelsrichtung relativ zum Gebäude-Zentrum**.
Bei Reihenhäusern sind Nachbarn oft in **mehreren Richtungen** gleichzeitig:

```
Knospenweg 3:
- Kno 1 (links): direction = "W" und "SW" und "NW" (weil lang)
- Kno 5 (rechts): direction = "E" und "SE" und "NE"

→ SSE meldet 5-6 blockierte Richtungen statt 2!
→ Fast alle Fassaden werden als blockiert markiert
```

### Status: ❌ Nicht funktionsfähig für komplexe Fälle

---

## Strategie 3: Union-basiert (NEU - Empfohlen)

**Flag:** `USE_UNION_BLOCKING = true`

### Algorithmus

```typescript
// 1. Alle Polygone sammeln
const mainPolygon = turf.polygon([objectPolygon]);
const neighborPolygons = blockingNeighbors.map(n => turf.polygon([n.polygon]));

// 2. Union bilden (verschmelzen)
let unionPolygon = mainPolygon;
for (const neighbor of neighborPolygons) {
  unionPolygon = turf.union(unionPolygon, neighbor);
}

// 3. Für jede Fassade prüfen: Liegt sie auf der AUSSENKANTE der Union?
function isFacadeBlocked(facade) {
  const midpoint = facadeMidpoint(facade);
  const onOuterEdge = isPointOnPolygonEdge(midpoint, unionPolygon, TOLERANCE);
  return !onOuterEdge;  // Nicht auf Aussenkante = blockiert!
}
```

### Visualisierung

```
┌─────────────────────────────────────────────────────────────────────────┐
│   UNION-ANSATZ: Knospenweg 1-5                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   VORHER (separate Polygone):          NACHHER (Union):                │
│                                                                         │
│   ┌─────┬─────┬─────┐                  ┌─────────────────┐             │
│   │ K1  │ K3  │ K5  │       →          │                 │             │
│   │     │     │     │                  │  UNION-POLYGON  │             │
│   └─────┴─────┴─────┘                  └─────────────────┘             │
│                                                                         │
│   Die INNEREN Kanten verschwinden!                                     │
│   → Nur noch die AUSSENKANTE bleibt                                    │
│   → Fassaden auf Aussenkante = FREI                                    │
│   → Fassaden NICHT auf Aussenkante = BLOCKIERT                         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Beispiel Knospenweg 3

```
Projekt: Knospenweg 3 (EGID 1243789)
Nachbarn: Kno 1 (EGID 1243787), Kno 5 (EGID 1243791)

Union = K1 + K3 + K5 = Grosses Rechteck

Fassaden von K3:
- Nord-Fassade: Mittelpunkt liegt auf Aussenkante der Union → FREI ✓
- Süd-Fassade: Mittelpunkt liegt auf Aussenkante der Union → FREI ✓
- West-Fassade: Mittelpunkt liegt NICHT auf Aussenkante → BLOCKIERT ✓
- Ost-Fassade: Mittelpunkt liegt NICHT auf Aussenkante → BLOCKIERT ✓
```

### Partielle Blockierung (Knospenweg 1)

```
Projekt: Knospenweg 1 (EGID 1243787)
Nachbar: Kno 3 (EGID 1243789)

Union = K1 + K3

Ost-Fassade von K1:
┌────────────────────────────┐
│                            │
│  K1       │░░░░░░│         │
│           │░K3░░░│         │  ← Nur oberer Teil blockiert
│           └──────┘         │
│           ↑                │
│     Hier endet K3          │
│                            │
└────────────────────────────┘

→ Oberer Teil der Ost-Fassade: NICHT auf Aussenkante → BLOCKIERT
→ Unterer Teil der Ost-Fassade: AUF Aussenkante → FREI

Für partielle Blockierung: Mehrere Punkte entlang der Fassade prüfen!
```

### Vorteile

1. **Geometrisch korrekt** - Funktioniert unabhängig von Himmelsrichtungen
2. **Partielle Blockierung erkennbar** - Durch Prüfung mehrerer Punkte
3. **Daten vorhanden** - `blockingNeighbors` und `polygon` sind bereits im Frontend
4. **Visualisierbar** - Union-Polygon kann in 3D angezeigt werden

### Status: 🔬 In Entwicklung / Test

---

## Strategie 4: Partielle Blockierung (Erweitert)

**Basiert auf:** Union-Strategie + Segment-Analyse

### Algorithmus

```typescript
// Statt nur Mittelpunkt: Mehrere Punkte entlang der Fassade prüfen
function getFacadeBlockedSegments(facade, unionPolygon): Segment[] {
  const segments: Segment[] = [];
  const SAMPLE_POINTS = 10;

  for (let i = 0; i < SAMPLE_POINTS; i++) {
    const ratio = i / (SAMPLE_POINTS - 1);
    const point = interpolate(facade.start_point, facade.end_point, ratio);
    const onEdge = isPointOnPolygonEdge(point, unionPolygon);

    segments.push({
      startRatio: ratio,
      endRatio: (i + 1) / SAMPLE_POINTS,
      isBlocked: !onEdge
    });
  }

  return mergeAdjacentSegments(segments);
}

// Fassade komplett blockiert wenn > 90% blockiert
function isFacadeFullyBlocked(facade): boolean {
  const segments = getFacadeBlockedSegments(facade);
  const blockedRatio = segments
    .filter(s => s.isBlocked)
    .reduce((sum, s) => sum + (s.endRatio - s.startRatio), 0);
  return blockedRatio >= 0.9;
}
```

### Visualisierung

```
Fassade mit partieller Blockierung:

┌──────────────────────────────────────────────────┐
│░░░░░░░░░░░░░░░░░░░│                              │
│     BLOCKIERT     │         FREI                 │
│     (60%)         │         (40%)                │
│░░░░░░░░░░░░░░░░░░░│                              │
└──────────────────────────────────────────────────┘

→ In der UI: Teilweise grau, teilweise farbig
→ Auswählbar, aber mit Warnung
```

---

## Test-Szenarien

### Szenario 1: Einfaches Reihenhaus

```
Adresse: Knospenweg 3, Bern
Erwartung: N+S frei, O+W blockiert
```

### Szenario 2: Eck-Reihenhaus

```
Adresse: Knospenweg 1, Bern
Erwartung: N+W+S frei, O teilweise blockiert (ca. 60%)
```

### Szenario 3: Freistehendes Gebäude

```
Adresse: Bundesplatz 3, Bern
Erwartung: Alle Fassaden frei (keine blockierenden Nachbarn)
```

### Szenario 4: U-Form mit Innenhof

```
Adresse: (TODO: Beispiel finden)
Erwartung: Aussenfassaden frei, Innenhof-Fassaden blockiert
```

---

## Funktionen in FacadePanel.tsx

### Aktive Funktionen

| Funktion | Status | Beschreibung |
|----------|--------|--------------|
| `isFacadeBlocked()` | ✅ AKTIV | Zentrale Blockierungs-Prüfung, gesteuert durch Flags |

### Deaktivierte Funktionen (DEAKTIVIERT 25.01.2026)

| Funktion | Status | Problem |
|----------|--------|---------|
| `allBlockedSegmentsByFacadeIndex` | ⏸️ DEAKTIVIERT | SSE-Index-Referenzen auf ORIGINAL-Polygon. Bei Vereinfachung (Douglas-Peucker) stimmen Indizes nicht mehr. |
| `getFacadeSegments()` | ⏸️ DEAKTIVIERT | Nutzt `allBlockedSegmentsByFacadeIndex`, gleicher Index-Mismatch |
| `isFacadeFullyBlocked()` | ⏸️ DEAKTIVIERT | Segment-basierte Prüfung, Index-Problem vererbt von `getFacadeSegments()` |

### Datenfluss-Problem (Index-Mismatch)

```
┌─────────────────────────────────────────────────────────────────────────┐
│   INDEX-MISMATCH BEI POLYGON-VEREINFACHUNG                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ORIGINAL-Polygon (27 Fassaden):                                      │
│   [0]=N, [1]=NE, [2]=E, [3]=SE, [4]=S, ... [26]=NW                     │
│                                                                         │
│   SSE blocked_segments bezieht sich auf ORIGINAL-Indizes:              │
│   "facade_index: 3 ist blockiert"  → Index 3 = SE im Original          │
│                                                                         │
│   VEREINFACHTES Polygon (4 Fassaden):                                  │
│   [0]=N, [1]=E, [2]=S, [3]=W                                           │
│                                                                         │
│   PROBLEM: Index 3 im vereinfachten Polygon = W (NICHT SE!)            │
│   → Falsche Fassade wird als blockiert markiert                        │
│                                                                         │
│   LÖSUNG: Index-Mapping oder Geometrie-basierte Zuordnung nötig        │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Implementierungs-Status

| Strategie | Flag | Status | Funktioniert |
|-----------|------|--------|--------------|
| Deaktiviert | `DISABLE_FACADE_BLOCKING` | ✅ Aktiv | Ja (alle frei) |
| Union-basiert | `USE_UNION_BLOCKING` | ⏸️ Deaktiviert | Benötigt Test |
| Geometrie-basiert | `USE_GEOMETRY_BLOCKING` | ❌ Deaktiviert | Nein (Reihenhaus-Problem) |
| Richtungs-basiert | `USE_DIRECTION_BLOCKING` | ❌ Deaktiviert | Nein (Multi-Direction) |
| Partielle Blockierung | (SSE-basiert) | ❌ Deaktiviert | Nein (Index-Mismatch) |

---

## Nächste Schritte

1. **Union-Strategie testen**: `USE_UNION_BLOCKING = true` aktivieren und mit Reihenhäusern testen
2. **Index-Mapping implementieren**: Wenn partielle Blockierung gewünscht, muss Original→Vereinfacht Mapping erstellt werden
3. **Backend-Anpassung**: Alternativ könnte das Backend Blockierung auf Geometrie-Basis berechnen (nicht Index-basiert)

---

## Änderungs-Historie

| Datum | Änderung |
|-------|----------|
| 25.01.2026 18:30 | Alle Blockierungs-Funktionen dokumentiert, Fallbacks entfernt, Index-Mismatch Problem erklärt |
| 25.01.2026 15:00 | Dokument erstellt, Union-Strategie implementiert |
| 25.01.2026 12:00 | Alle Strategien temporär deaktiviert (DISABLE_FACADE_BLOCKING) |
| 24.01.2026 | Geometrie- und Richtungs-Strategien getestet, beide fehlgeschlagen |
