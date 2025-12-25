# CLAUDE_SVG_PROMPT.md - Prompt-Template für professionelle Gerüstpläne

> **Version:** 1.0
> **Datum:** 25.12.2025
> **Zweck:** Dieses Template wird zusammen mit den Gebäudedaten in Claude.ai eingefügt

---

# Professionelle Gerüstpläne erstellen

Ich habe Gebäudedaten aus einer Schweizer Geodaten-App exportiert. Die Daten enthalten:
- Exaktes Gebäude-Polygon (amtliche Vermessung, ±10cm)
- Gemessene Höhendaten (swissBUILDINGS3D)
- Analysierte Höhenzonen
- Berechnete Gerüst-Konfiguration (NPK 114)

Bitte erstelle professionelle Gerüstpläne als SVG.

---

## Gewünschte Ausgaben

### 1. Grundriss (Draufsicht) - M 1:200

**Inhalt:**
- Gebäude-Polygon mit farbcodierten Zonen
- Gerüstfläche (30cm Abstand zur Fassade, schraffiert)
- Ständerpositionen (schwarze Punkte, alle 2.5-3m)
- Verankerungspunkte (orange Kreise)
- Zugänge Z1, Z2, etc. (gelbe Rechtecke)
- Masslinien mit Pfeilen und Beschriftung
- Nordpfeil (oben rechts)
- Massstabsbalken (unten)
- Legende
- Titelblock mit Adresse und Datum

**Stil:**
```
Gebäude:     Zonen-Farben (siehe Daten), schwarzer Umriss 2px
Gerüst:      Grüne Schraffur 45°, Transparenz 30%
Ständer:     Schwarze Punkte, r=4px
Verankerung: Orange Kreise #FF5722, r=3px
Zugang:      Gelbe Rechtecke #FFC107, mit Label
Masslinien:  Dunkelgrau #666, mit Pfeilspitzen
Text:        Arial, schwarz
```

### 2. Schnitt - M 1:100

**Inhalt:**
- Gebäudeprofil mit unterschiedlichen Höhenzonen
- Dachform (Satteldach, Flachdach, etc.)
- Gerüst mit Lagen (L1, L2, L3, ...)
- Beläge (braune Linien)
- Terrain-Linie (wenn Hanglage)
- Höhenkoten (Terrain, Traufe, First)
- Verankerungspunkte an der Fassade

**Stil:**
```
Gebäude:     Hellgrau Füllung, schwarzer Umriss
Dach:        Schraffur für Dachfläche
Gerüst:      Grüne Linien für Rahmen
Beläge:      Braune Rechtecke #8D6E63
Terrain:     Braune Linie 2px
Höhenkoten:  Mit Dreieck-Symbol ▽
```

### 3. Ansicht Hauptfassade - M 1:100

**Inhalt:**
- Fassadenansicht (vereinfacht)
- Gerüst mit Feldern (F1, F2, F3, ...)
- Feldlängen beschriftet (3.07m, 2.57m, etc.)
- Lagen nummeriert (L1-L7)
- Verankerungsraster (4m × 4m)
- Zugang markiert
- Ausmass-Box mit Fläche

**Stil:**
```
Fassade:     Hellgrau, Fenster angedeutet
Gerüst:      Grüne Rahmenlinien
Felder:      Beschriftung oben (F1, F2, ...)
Lagen:       Beschriftung rechts (L1, L2, ...)
Verankerung: Orange Punkte im 4m-Raster
```

---

## Farb-Schema für Zonen

| Zone-Typ | Fill | Stroke |
|----------|------|--------|
| Hauptgebäude | #E3F2FD | #1976D2 |
| Turm | #FFF3E0 | #F57C00 |
| Anbau | #F3E5F5 | #7B1FA2 |
| Arkade | #E8F5E9 | #388E3C |
| Kuppel | #FCE4EC | #C2185B |

---

## Wichtige Regeln

1. **Masse übernehmen** - Alle Zahlen aus den Daten, NICHTS erfinden
2. **Massstab einhalten** - 1:200 für Grundriss, 1:100 für Schnitt/Ansicht
3. **Zonen unterscheiden** - Verschiedene Höhen = verschiedene Darstellung
4. **Professioneller Stil** - Architekturzeichnung, nicht technisches Diagramm
5. **Lesbarkeit** - Klare Beschriftungen, ausreichend Kontrast
6. **Druckfähig** - Funktioniert auf A3, auch in Schwarzweiss erkennbar

---

## Iterativer Prozess

Bitte generiere die SVGs nacheinander:

1. **Grundriss zuerst** - Ich gebe Feedback
2. **Dann Schnitt** - Nach Freigabe des Grundrisses
3. **Zuletzt Ansicht** - Nach Freigabe des Schnitts

Bei jedem SVG:
- Zeige mir das Ergebnis
- Ich sage was angepasst werden soll
- Du iterierst bis es passt

---

## SVG-Struktur (Empfehlung)

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600">
  <defs>
    <!-- Schraffur-Pattern -->
    <pattern id="hatch" ...>
    <!-- Pfeilspitzen -->
    <marker id="arrow" ...>
    <!-- Styles -->
    <style>
      .zone-hauptgebaeude { fill: #E3F2FD; stroke: #1976D2; }
      .zone-turm { fill: #FFF3E0; stroke: #F57C00; }
      ...
    </style>
  </defs>
  
  <!-- Titel -->
  <g id="title">...</g>
  
  <!-- Gebäude -->
  <g id="building">...</g>
  
  <!-- Gerüst -->
  <g id="scaffolding">...</g>
  
  <!-- Beschriftungen -->
  <g id="labels">...</g>
  
  <!-- Legende -->
  <g id="legend">...</g>
  
  <!-- Massstab -->
  <g id="scale">...</g>
</svg>
```

---

## Gebäudedaten

**[HIER WERDEN DIE DATEN EINGEFÜGT]**

```json
{
  "gebaeude": { ... },
  "zonen": [ ... ],
  "fassaden": [ ... ],
  "geruest": { ... },
  "zugaenge": [ ... ]
}
```

---

## Los geht's!

Bitte beginne mit dem **Grundriss**. Nutze die Polygon-Koordinaten für die exakte Form und die Zonen-Informationen für die Farbcodierung.
