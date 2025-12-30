# SVG Grundriss: Bundeshaus Bern

Kopiere diesen Prompt in Claude.ai um einen professionellen Gerüst-Grundriss zu generieren.

---

## Prompt

Erstelle einen technischen Grundriss mit Gerüstplanung als SVG für das Bundeshaus in Bern.

### Gebäudedaten

- **Adresse:** Bundesplatz 3, 3011 Bern
- **EGID:** 2242547
- **Koordinaten (LV95):** E 2600423, N 1199521
- **Gebäudename:** Bundeshaus (Schweizer Parlamentsgebäude)
- **Gebäudetyp:** Parlamentsgebäude
- **Umfang:** 285.4 m
- **Grundfläche:** 4200 m²

### Polygon (26 Punkte, vereinfacht)

Das Gebäude hat eine komplexe U-Form mit Ehrenhof zur Südseite.

### Höhenzonen (3 Zonen)

| Zone | Name | Farbe | Höhe |
|------|------|-------|------|
| 1 | Arkaden | Hellgrün #90EE90 | 6.0 m |
| 2 | Hauptgebäude | Hellblau #87CEEB | 25.0 m |
| 3 | Kuppel | Orange #FFA500 | 64.0 m |

### Fassaden

| ID | Richtung | Länge | Gerüsthöhe |
|----|----------|-------|------------|
| N | Nord | 45 m | 25 m |
| O | Ost | 85 m | 25 m |
| S | Süd (Ehrenhof) | 45 m | 25 m |
| W | West | 85 m | 25 m |

### SVG-Anforderungen

**Format:** 800 x 800 px, viewBox="0 0 800 800"

**Stil:**
- Technischer Grundriss (Draufsicht)
- Hintergrund: Weiss (#FFFFFF)
- Gebäude: Zonen-farbcodiert
- Fassaden-Linien: Schwarz, 2px

**Inhalt:**
1. Gebäude-Polygon mit Zonen-Farben
2. Fassaden-Beschriftung (N, O, S, W)
3. Ständerpositionen als rote Punkte (alle 2.57m)
4. Verankerungspunkte als blaue X
5. Zugänge (Z1, Z2) als gelbe Rechtecke
6. Nordpfeil oben rechts
7. Massstab unten
8. Legende mit Zonen-Farben

**Gerüst-Elemente:**
- Ständer: Rote Kreise, r=3px, alle 2.57m
- Verankerungen: Blaue X, alle 4m
- Zugänge: Gelbe Rechtecke, max 50m Abstand (SUVA)

**Fassaden-Labels:**
```
Fassade N: 45.0m, Höhe 25.0m
Fassade O: 85.0m, Höhe 25.0m
...
```

Generiere NUR das SVG, keine Erklärungen.
