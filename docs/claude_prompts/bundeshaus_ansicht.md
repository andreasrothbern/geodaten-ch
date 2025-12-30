# SVG Ansicht: Bundeshaus Bern

Kopiere diesen Prompt in Claude.ai um eine professionelle Fassadenansicht zu generieren.

---

## Prompt

Erstelle eine technische Fassadenansicht (Südfassade) als SVG für das Bundeshaus in Bern.

### Gebäudedaten

- **Adresse:** Bundesplatz 3, 3011 Bern
- **EGID:** 2242547
- **Koordinaten (LV95):** E 2600423, N 1199521
- **Gebäudename:** Bundeshaus (Schweizer Parlamentsgebäude)
- **Gebäudetyp:** Parlamentsgebäude
- **Baujahr:** 1902
- **Architekturstil:** Neorenaissance / Historismus

### Höhendaten

- **Terrain (m ü.M.):** 543.1
- **Traufhöhe:** 25.0 m (Hauptgebäude)
- **Firsthöhe:** 30.0 m (Hauptgebäude)
- **Kuppelhöhe:** 64.0 m (höchster Punkt)

### Höhenzonen (3 Zonen)

| Zone | Name | Typ | Traufhöhe | Firsthöhe | Sonderkonstruktion |
|------|------|-----|-----------|-----------|-------------------|
| 1 | Arkaden | arkade | 6.0 m | 6.0 m | Nein |
| 2 | Hauptgebäude | hauptgebaeude | 25.0 m | 30.0 m | Nein |
| 3 | Kuppel | kuppel | 30.0 m | 64.0 m | Ja |

### Fassaden-Details

- **Fassadenlänge:** ca. 110 m
- **Arkaden:** Säulenreihe mit Rundbögen, ca. 12 Bögen
- **Hauptfassade:** 3-4 Geschosse, symmetrisch
- **Kuppel:** Zentral, mit Laterne, Kupferpatina (grün)

### SVG-Anforderungen

**Format:** 1000 x 600 px, viewBox="0 0 1000 600"

**Stil:**
- Technische Architekturzeichnung (NICHT künstlerisch)
- Hintergrund: Weiss (#FFFFFF), KEIN Himmel!
- Gebäude: Schraffur-Pattern url(#hatch)
- Hauptlinien: Dunkelgrau (#333333), 2px
- Kuppel: Kupfer-Gradient (#7CB9A5 bis #4A8A77)

**Inhalt:**
1. Terrain-Linie unten (±0.00)
2. Arkaden mit Säulen und Bögen
3. Hauptfassade mit Fenstern (Raster)
4. Kuppel mit Laterne
5. Höhenskala links (0 bis 65m)
6. Lagenbeschriftung rechts
7. Legende oben rechts
8. Massstab 1:250

**Gerüst-Darstellung:**
- Ständer alle 2.57m (Layher Blitz 70)
- Verankerungen alle 4m horizontal/vertikal
- Gerüst-Farbe: Blau (#0066CC)
- Beläge: Braun (#8B4513)

**Patterns (in <defs>):**
```xml
<pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
  <path d="M0,0 l8,8 M-2,6 l4,4 M6,-2 l4,4" stroke="#999" stroke-width="0.5"/>
</pattern>
<linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
  <stop offset="0%" style="stop-color:#7CB9A5"/>
  <stop offset="100%" style="stop-color:#4A8A77"/>
</linearGradient>
```

Generiere NUR das SVG, keine Erklärungen.
