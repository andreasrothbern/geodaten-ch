# Verbesserungsvorschläge: SVG-Generierungs-Prompt

**Dokument:** SVG-Generierung für Gerüstplanung
**Gebäude:** Kirche St. Peter und Paul, Bern (EGID: 191821074)
**Datum:** 2025-12-30

---

## 1. Fehlender Längsschnitt (KRITISCH)

### Problem
Der aktuelle Prompt definiert nur einen **Querschnitt A-A** durch das Kirchenschiff. Der 54.6m hohe Westturm - das kritischste Element für die Gerüstplanung - fehlt im Schnitt komplett.

### Lösung
Abschnitt 13 ergänzen:

```markdown
### SVG 3a: Querschnitt A-A (durch Kirchenschiff)
- **Schnittebene:** Quer durch Mittelschiff
- **Zeigt:** Seitenschiffe, Mittelschiff, Gewölbestruktur
- **Gerüsthöhe:** max. 25m (Kirchenschiff-First)

### SVG 3b: Längsschnitt B-B (durch Turm + Schiff + Chor)
- **Schnittebene:** Längs durch Hauptachse (West-Ost)
- **Zeigt:** ALLE Höhenzonen in einer Ansicht
- **KRITISCH:** Turm-Einrüstung vollständig darstellen
- **Gerüsthöhe:** 54.6m = 27 Lagen (Sonderkonstruktion!)
- **Elemente:** Glockengeschoss, Geschossdecken, Triumphbogen, Apsis
```

---

## 2. Polygon-Vereinfachung unzureichend

### Problem
```
> Vereinfachte rechteckige Darstellung empfohlen
```
Ein Rechteck ist für eine dreischiffige Basilika mit Turm, Chor und Seitenschiffen ungeeignet.

### Lösung
Abschnitt 3 präzisieren:

```markdown
### Polygon-Vereinfachung
- **Grundform:** Kreuzgrundriss (nicht rechteckig!)
- **Komponenten:**
  - Westturm: Quadrat 11m × 8m
  - Kirchenschiff: Rechteck 11m × 20m
  - Seitenschiffe: 2× Rechteck 8.5m × 16m
  - Chor: Rechteck 8m × 7m + Apsis (halbrund)
```

---

## 3. Architektur-Details fehlen

### Problem
Der Prompt enthält keine spezifischen Angaben zu neugotischen Elementen, obwohl der Baustil als "Neugotik" identifiziert ist.

### Lösung
Neuen Abschnitt 9 einfügen:

```markdown
## 9. Architektur-Elemente (Neugotik)

| Element | Position | Darstellung |
|---------|----------|-------------|
| Spitzbogenfenster | Seitenschiffe, Obergaden | Spitzbogen-Kontur |
| Rosettenfenster | Westturm (Fassade) | Kreis mit Masswerk |
| Schallarkaden | Glockengeschoss | Doppel-Spitzbogen |
| Strebepfeiler | Turm, Chor | Vertikale Vorsprünge |
| Kreuzrippengewölbe | Mittelschiff (Schnitt) | Gewölberippen + Schlussstein |
| Turmkreuz | Turmspitze | Kreuz-Symbol |
| Turmuhr | Turm (ca. +28m) | Kreis mit Zeigern |

**Darstellungshinweis:** Elemente nur andeuten, nicht detailliert ausarbeiten.
```

---

## 4. Dachform-Konfidenz zu niedrig

### Problem
```
- **Dachform:** satteldach_mit_turm
- **Konfidenz:** 50%
```
Die generische Bezeichnung und niedrige Konfidenz führen zu ungenauen Darstellungen.

### Lösung
Abschnitt 5 präzisieren:

```markdown
## 5. Dach-Analyse

| Zone | Dachform | Neigung | Ausrichtung |
|------|----------|---------|-------------|
| Westturm | Spitzhelm (oktagonal) | 70° | - |
| Kirchenschiff | Satteldach | 29° | N-S |
| Seitenschiffe | Pultdach | 22° | O/W |
| Chor | Walmdach/Polygonal | 35° | - |

- **Konfidenz:** 85% (basierend auf Luftbild + Baustil)
```

---

## 5. Abschnitt 2 fehlt

### Problem
Der Prompt springt von Abschnitt 1 direkt zu Abschnitt 3.

### Lösung
Abschnitt 2 einfügen:

```markdown
## 2. Projektkontext

- **Auftragsart:** Fassadensanierung / Renovation
- **Gerüsttyp:** Layher Blitz 70, Fassadengerüst
- **Besonderheiten:** 
  - Turm >25m = Sonderkonstruktion (SUVA)
  - Denkmalschutz beachten
  - Kirchenbetrieb während Bauzeit
- **Priorität Ansichten:**
  1. Westfassade (Turm, Haupteingang)
  2. Längsschnitt (alle Höhenzonen)
  3. Querschnitt (Gewölbestruktur)
```

---

## 6. Fassadentabelle unvollständig

### Problem
```
| ... | (38 weitere) | ... |
```
Abgeschnittene Fassadendaten erschweren präzise SVG-Generierung.

### Lösung
Entweder vollständige Tabelle ODER aggregierte Zusammenfassung:

```markdown
## 7. Fassaden (Zusammenfassung)

| Himmelsrichtung | Gesamtlänge | Segmente | Hauptelemente |
|-----------------|-------------|----------|---------------|
| West | 29.1m | 3 | Turm, Portal, Rosette |
| Ost | 29.1m | 5 | Chor, Apsis, Seitenschiffe |
| Nord | 48.2m | 12 | Seitenschiff, Strebepfeiler |
| Süd | 48.2m | 12 | Seitenschiff, Strebepfeiler |

**Umfang gesamt:** 168.1m
**Einzurüstende Fläche:** ca. 2'800 m²
```

---

## 7. Gerüst-Sonderkonstruktion nicht hervorgehoben

### Problem
Der Turm erfordert eine Sonderkonstruktion (>25m), dies wird nur in der Höhenzonen-Tabelle erwähnt.

### Lösung
Abschnitt 11 ergänzen:

```markdown
## 11. Gerüst-Spezifikation (Layher Blitz 70)

### Standard-Parameter
[... bestehende Tabelle ...]

### ⚠️ SONDERKONSTRUKTION TURM (SUVA-relevant)

| Parameter | Wert | Vorschrift |
|-----------|------|------------|
| Gerüsthöhe | 54.6m | >25m = Sonderkonstruktion |
| Lagen | 27 | à 2.0m |
| Statik | Erforderlich | Ing.-Nachweis |
| Verankerung | Verstärkt | Alle 3m horizontal |
| Diagonalen | Zusätzlich | Jedes 2. Feld |
| Lastklasse | Min. 3 | 200 kg/m² |

**Für SVG-Zeichnung:**
- Turm-Gerüst mit Hinweis "SONDERKONSTRUKTION" beschriften
- Zusätzliche Diagonalen andeuten
- Verankerungsraster enger darstellen (3m statt 4m)
```

---

## 8. Output-Spezifikation erweitern

### Problem
Nur 3 SVGs definiert, aber 4 werden für vollständige Gerüstplanung benötigt.

### Lösung
Abschnitt 14 anpassen:

```markdown
## 14. Output

Erstelle **4 separate SVGs**, jeweils mit `viewBox="0 0 700 480"`:

1. **grundriss.svg** - Draufsicht mit Zonen und Gerüstbereich
2. **fassadenansicht.svg** - Westansicht mit Turm (Hauptansicht)
3. **querschnitt_A-A.svg** - Durch Kirchenschiff (Gewölbe)
4. **laengsschnitt_B-B.svg** - Durch Turm + Schiff + Chor (KRITISCH!)

**Dateinamen-Konvention:**
`{egid}_{ansicht}_{version}.svg`
Beispiel: `191821074_laengsschnitt_v1.svg`
```

---

## Zusammenfassung der Änderungen

| Abschnitt | Änderung | Priorität |
|-----------|----------|-----------|
| §2 | Neu: Projektkontext | Mittel |
| §3 | Polygon-Vereinfachung präzisieren | Hoch |
| §5 | Dachformen pro Zone | Mittel |
| §7 | Fassaden aggregieren | Niedrig |
| §9 | Neu: Architektur-Elemente | Mittel |
| §11 | Sonderkonstruktion hervorheben | Hoch |
| §13 | Längsschnitt B-B ergänzen | **KRITISCH** |
| §14 | 4 statt 3 SVGs | **KRITISCH** |

---

*Erstellt: 2025-12-30*
*Projekt: geodaten-ch / Gerüstplanung Schweiz*
